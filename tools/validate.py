#!/usr/bin/env python3
"""Validate shared contracts, examples, wire vectors and optional consumer pins."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess

from jsonschema import Draft202012Validator, validators
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parent.parent
# JSON-C ingress distinguishes integer tokens from floating-point tokens.
STRICT_TYPES = Draft202012Validator.TYPE_CHECKER.redefine(
    "integer", lambda checker, value: type(value) is int).redefine(
    "number", lambda checker, value: type(value) is int
    or (type(value) is float and math.isfinite(value)))


def ordered_fields(validator, fields, instance, schema):
    """Declarative cross-field ordering, which JSON Schema cannot express."""
    if not isinstance(instance, dict) or len(fields) != 2:
        return
    left, right = (instance.get(field) for field in fields)
    if (type(left) in (int, float) and type(right) in (int, float)
            and left >= right):
        yield ValidationError(f"{fields[0]} must be less than {fields[1]}")


Validator = validators.extend(Draft202012Validator,
                             {"x-orderedFields": ordered_fields},
                             type_checker=STRICT_TYPES)


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        fail("Non-finite JSON number: " + value)
    return number


def load(path):
    return json.loads(path.read_text(), parse_float=finite_float,
                      parse_constant=lambda value: fail(f"Non-JSON number: {value}"))


def fail(message):
    raise ValueError(message)


def decode_fields(data, fields):
    output = {}
    for field in fields:
        start = field["offset"]
        value = int.from_bytes(data[start:start + field["bytes"]], "big")
        if (value < field.get("minimum", 0) or value > field.get("maximum", 2 ** (8 * field["bytes"]) - 1)
                or ("values" in field and value not in field["values"])
                or ("value" in field and value != field["value"])):
            fail("Invalid field: " + field.get("name", "reserved"))
        if "name" in field:
            output[field["name"]] = value
    return output


def check_conditions(output, conditions):
    for condition in conditions:
        if not all(output.get(key) == value for key, value in condition["when"].items()):
            continue
        if (any(output.get(key) != value for key, value in condition.get("require", {}).items())
                or any(output[key] & mask for key, mask in condition.get("forbid_bits", {}).items())
                or any(output[key] < value for key, value in condition.get("minimum", {}).items())):
            fail("Conditional wire constraint failed")


def decode_vector(frame, role, definition):
    layout = definition[role]
    if (len(frame) != layout["length"] or list(frame[:len(layout["header"])]) != layout["header"]
            or frame[-1] != layout["footer"]):
        fail("Invalid frame boundary")
    if role in ("button_event", "reset_request", "reset_ack"):
        start, count = layout["reserved_offset"], layout["reserved_length"]
        kind = frame[layout["kind_offset"]]
        if kind not in layout["kinds"] or any(frame[start:start + count]):
            fail("Invalid kind or reserved byte")
        output = {"kind": kind, "sequence": frame[layout["sequence_offset"]]}
        if role == "button_event":
            start = layout["held_offset"]
            output["held_ms"] = int.from_bytes(frame[start:start + layout["held_bytes"]], "big")
        return output
    op = frame[layout["op_offset"]]
    operation = next((item for item in definition["operations"] if item["op"] == op), None)
    if operation is None:
        fail("Vector uses an undefined operation")
    output = {"op": op, "sequence": frame[layout["sequence_offset"]]}
    if role == "reply":
        status = frame[layout["status_offset"]]
        if str(status) not in definition["statuses"]:
            fail("Unknown reply status")
        output["status"] = status
        start = layout["data_offset"]
        data = frame[start:start + layout["data_length"]]
        if status:
            if operation.get("error_data_zero") and any(data):
                fail("Nonzero error reply data")
        else:
            if "reply" not in operation:
                fail("Operation has no reply field contract")
            output.update(decode_fields(data, operation["reply"]))
            check_conditions(output, operation.get("reply_conditions", []))
    else:
        start = layout["arguments_offset"]
        output.update(decode_fields(frame[start:start + layout["arguments_length"]], operation["arguments"]))
        check_conditions(output, operation.get("conditions", []))
    return output


def validate_registry():
    registry = load(ROOT / "contracts/registry.json")
    if registry["schema"] != 1:
        fail("Unknown registry schema")
    ids = set()
    repositories = registry["repositories"]
    for item in registry["contracts"]:
        if item["id"] in ids or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["id"]):
            fail("Duplicate or invalid contract ID")
        ids.add(item["id"])
        if item["status"] not in ("draft", "implemented-unreleased", "released"):
            fail("Unknown contract status")
        if item["status"] != "draft" and not item["implementation"]:
            fail("Implemented contract needs source references")
        if item["status"] == "released" and not item.get("releases"):
            fail("Released contract needs release references")
        for source in item["implementation"] + item.get("verification", []):
            if source.split("/", 1)[0] not in repositories or ".." in Path(source).parts:
                fail("Unknown or unsafe source reference: " + source)
        for artifact in item.get("artifacts", []):
            if not (ROOT / artifact).is_file() or ".." in Path(artifact).parts:
                fail("Missing or unsafe contract artifact: " + artifact)
            if artifact.endswith(".json"):
                load(ROOT / artifact)
        for language in ("zh", "en"):
            if not (ROOT / "docs" / language / item["document"]).is_file():
                fail(f"Missing {language} contract document: {item['id']}")
    zh = {path.name for path in (ROOT / "docs/zh").glob("*.md")}
    en = {path.name for path in (ROOT / "docs/en").glob("*.md")}
    if zh != en:
        fail("Chinese and English pages differ")
    print(f"PASS registry: {len(ids)} interfaces, {len(zh)} pages per language")
    return ids


def example_cases():
    return [case for path in sorted((ROOT / "contracts/examples").glob("*.json"))
            for case in load(path)["cases"]]


def validate_examples():
    schemas = {}
    for path in (ROOT / "contracts/schemas").glob("*.schema.json"):
        schema = load(path)
        Validator.check_schema(schema)
        schemas[path.name.removesuffix(".schema.json")] = Validator(schema)
    cases = example_cases()
    names = set()
    for case in cases:
        key = (case["schema"], case["name"])
        if key in names:
            fail("Duplicate example name")
        names.add(key)
        errors = list(schemas[case["schema"]].iter_errors(case["data"]))
        if bool(errors) == case["valid"]:
            fail(f"Example {case['name']} disagrees with schema: {errors}")
    print(f"PASS {len(schemas)} schemas and {len(cases)} positive/negative examples")


def validate_wire_vectors(definition, vectors):
    for vector in vectors:
        decoded = None
        try:
            decoded = decode_vector(bytes.fromhex(vector["hex"]), vector["role"], definition)
        except ValueError:
            if vector["valid"]:
                raise
        else:
            if not vector["valid"]:
                fail("Invalid vector was accepted: " + vector["name"])
        for name, value in vector.get("expected", {}).items():
            if decoded is None or decoded.get(name) != value:
                fail("Decoded vector mismatch: " + vector["name"])


def validate_uart_artifact(definition_path, vectors_path):
    definition = load(definition_path)
    opcodes = set()
    for operation in definition["operations"]:
        if operation["op"] in opcodes:
            fail("Duplicate MCU opcode")
        opcodes.add(operation["op"])
        for key, size in (("arguments", definition["request"]["arguments_length"]),
                          ("reply", definition["reply"]["data_length"])):
            if key not in operation:
                continue
            covered = []
            for field in operation[key]:
                if type(field["offset"]) is not int or type(field["bytes"]) is not int or field["bytes"] < 1:
                    fail("Invalid wire field range")
                covered.extend(range(field["offset"], field["offset"] + field["bytes"]))
            if sorted(covered) != list(range(size)):
                fail("Incomplete or overlapping wire field definition")
        for fields, key in (("arguments", "conditions"), ("reply", "reply_conditions")):
            names = {field["name"] for field in operation.get(fields, []) if "name" in field}
            for condition in operation.get(key, []):
                if set().union(*(condition.get(part, {}) for part in
                                 ("when", "require", "forbid_bits", "minimum"))) - names:
                    fail("Conditional constraint references an undefined field")
    fixtures = load(vectors_path)
    vectors = fixtures["vectors"]
    validate_wire_vectors(definition, vectors)
    print(f"PASS {definition_path.name}: {len(vectors)} MCU wire vectors and opcode allocation")
    if fixtures.get("lamp_mask_sweep"):
        for slot in (0, 1):
            for mask in range(512):
                frame = bytes([35, 112, 24, 0, 0, 123, 0, mask >> 8, mask & 255, 1, slot, 33])
                actual = decode_vector(frame, "request", definition)
                if actual["lamps"] != mask or actual["slot"] != slot:
                    fail("UART lamp mask sweep mismatch")
        print("PASS formatted UART writes: all 512 lamp masks in both slots")


def validate_uart():
    for version in ("v1", "v3", "v4"):
        validate_uart_artifact(ROOT / f"contracts/m1-uart-{version}.json",
                               ROOT / f"contracts/vectors/m1-uart-{version}.json")
    legacy = load(ROOT / "contracts/m1-uart-v1.json")
    dual = load(ROOT / "contracts/m1-uart-v3.json")
    for key in ("request", "reply", "statuses", "button_event"):
        if legacy[key] != dual[key]:
            fail("UART v3 changed legacy frame layout: " + key)
    for old in legacy["operations"]:
        new = next(item for item in dual["operations"] if item["op"] == old["op"])
        if old["op"]:
            if any(new.get(key) != value for key, value in old.items()):
                fail("UART v3 redefined a legacy opcode")
        elif old["arguments"] != new["arguments"] or old["reply"][:-1] != new["reply"][:-1]:
            fail("UART v3 changed an existing capability field")
    print("PASS UART v3 preserves legacy operations and adds the D13 capability")
    formatted = load(ROOT / "contracts/m1-uart-v4.json")
    for key, value in dual.items():
        if key not in ("operations", "contract_revision") and formatted.get(key) != value:
            fail("UART v4 changed a legacy field: " + key)
    for old in dual["operations"]:
        if old != next(item for item in formatted["operations"] if item["op"] == old["op"]):
            fail("UART v4 redefined a legacy opcode")
    validate_frozen_artifacts(formatted)
    print("PASS UART v4 preserves every v3 capability/operation and frozen UART artifact")


def validate_frozen_artifacts(definition):
    for relative, expected in definition["frozen_artifacts"].items():
        if ".." in Path(relative).parts or Path(relative).is_absolute():
            fail("Unsafe frozen artifact reference")
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            fail("Changed frozen artifact: " + relative)


def binary32(value):
    try:
        return struct.unpack("!f", struct.pack("!f", value))[0]
    except OverflowError:
        return math.copysign(float("inf"), value)


def format_display_value(value, mode, slot, show_label, show_unit, definition):
    """Reference local/MQTT float32 conversion; raw API writes bypass this policy."""
    value = binary32(value)
    policy = definition["modes"].get(mode)
    if (policy is None or slot not in policy["slots"] or not math.isfinite(value)
            or value < 0 or value > definition["input"]["maximum"]):
        return None
    if "integer_below" in policy and value < policy["integer_below"]:
        policy = definition["modes"]["integer"]
    scaled = binary32(value * policy.get("count_multiplier", 1)
                      / policy.get("count_divisor", 1))
    number = min(policy["max_step_count"], int(binary32(scaled + 0.5)))
    return {"number": number * policy["digits_multiplier"],
            "format": int(policy["decimal"]) | (int(show_label) << 1) | (int(show_unit) << 2)}


def validate_formatted_display():
    definition = load(ROOT / "contracts/m1-display-v3.json")
    validate_frozen_artifacts(definition)
    vectors = load(ROOT / "contracts/vectors/m1-display-v3.json")
    for case in vectors["formatting_cases"]:
        actual = format_display_value(case["value"], case["mode"], case["slot"],
                                      case["show_label"], case["show_unit"], definition)
        if actual != case["expected"]:
            fail("Formatted display conversion mismatch: " + case["name"])
    raw_validator = Validator(load(ROOT / "contracts/schemas/m1-display-value-set-v3.schema.json"))
    for case in vectors["raw_api_cases"]:
        request = case["request"]
        if not raw_validator.is_valid(request):
            fail("Invalid raw API vector: " + case["name"])
        actual = None
        if request["ttl_seconds"]:
            actual = {
                "number": request["number"],
                "format": int(request["decimal"]) | (int(request["show_label"]) << 1)
                          | (int(request["show_unit"]) << 2),
                "lamps": sum(int(lamp[color]) << (offset + position)
                             for color, offset in definition["lamps"]["bit_offsets"].items()
                             for position, lamp in enumerate(request["lamps"])),
                "value": binary32(request["number"] / (100 if request["decimal"] else 1)),
                "unit": (definition["raw_api"]["runtime_native_unit"][str(request["slot"])]
                         if request["show_unit"] else ""),
            }
        expected = case["expected"]
        if expected is not None:
            expected = dict(expected, value=binary32(expected["value"]))
        if actual != expected:
            fail("Raw API display mismatch: " + case["name"])
    lamp_schema = load(ROOT / "contracts/schemas/m1-display-profile-set-v3.schema.json")["$defs"]["lamps"]
    lamp_validator = Validator(lamp_schema)
    regions = [sum(bits) for bits in definition["lamps"]["glass_bits"].values()]
    if regions[0] & regions[1]:
        fail("Formatted lamp regions overlap")
    for slot, bits in definition["lamps"]["glass_bits"].items():
        region = sum(bits)
        for mask in range(definition["lamps"]["maximum_mask"] + 1):
            lamps = [{color: bool(mask & (1 << (offset + position)))
                      for color, offset in definition["lamps"]["bit_offsets"].items()}
                     for position in range(3)]
            if not lamp_validator.is_valid(lamps):
                fail("Invalid exhaustive lamp object")
            rebuilt = sum(int(lamps[position][color]) << (offset + position)
                          for color, offset in definition["lamps"]["bit_offsets"].items()
                          for position in range(3))
            if rebuilt != mask:
                fail("Lamp mask round trip failed")
            for color in definition["lamps"]["bit_offsets"]:
                segments = sum(bits[position] for position in range(3) if lamps[position][color])
                for original in (0, 0x55, 0xaa, 0xff):
                    updated = (original & ~region) | segments
                    if updated & region != segments or updated & ~region != original & ~region:
                        fail("Lamp update changed another region")
    print(f"PASS m1-display-v3: {len(vectors['formatting_cases'])} physical format vectors, "
          f"{len(vectors['raw_api_cases'])} raw API vectors, "
          "1024 lamp masks with region isolation; frozen JSON schemas/examples preserved")


def reset_ack_matches(frame, pending, elapsed_ms, definition):
    """A valid wire ACK alone cannot authorize a sensor restart."""
    try:
        decoded = decode_vector(frame, "reset_ack", definition)
    except ValueError:
        return False
    return (pending is not None and 0 <= elapsed_ms < definition["sensor"]["timeout_ms"]
            and decoded == pending)


def reset_request_result(frame, committed, busy, persist_ok, definition):
    """Reference the persistence/deduplication boundary, without performing I/O."""
    result = {"ack": False, "persist": False, "committed": committed}
    try:
        decoded = decode_vector(frame, "reset_request", definition)
    except ValueError:
        return result
    if committed is not None:
        result["ack"] = decoded == committed
    elif not busy:
        result["persist"] = True
        if persist_ok:
            result.update(ack=True, committed=decoded)
    return result


def validate_reset():
    definition = load(ROOT / "contracts/m1-reset-v1.json")
    for role in ("reset_request", "reset_ack"):
        layout = definition[role]
        covered = (list(range(len(layout["header"])))
                   + [layout["kind_offset"], layout["sequence_offset"]]
                   + list(range(layout["reserved_offset"],
                                layout["reserved_offset"] + layout["reserved_length"]))
                   + [layout["length"] - 1])
        if sorted(covered) != list(range(layout["length"])):
            fail("Incomplete or overlapping reset frame layout")
    fixtures = load(ROOT / "contracts/vectors/m1-reset-v1.json")
    validate_wire_vectors(definition, fixtures["vectors"])
    for case in fixtures["sensor_ack_cases"]:
        actual = reset_ack_matches(bytes.fromhex(case["hex"]), case["pending"],
                                   case["elapsed_ms"], definition)
        if actual != case["restart"]:
            fail("Reset ACK transaction mismatch: " + case["name"])
    steps = 0
    for case in fixtures["wifi_request_cases"]:
        committed = None
        for step in case["steps"]:
            actual = reset_request_result(bytes.fromhex(step["hex"]), committed,
                                          step["busy"], step["persist_ok"], definition)
            if actual != step["expected"]:
                fail("Reset persistence transaction mismatch: " + case["name"])
            committed = actual["committed"]
            steps += 1
    print(f"PASS m1-reset-v1: {len(fixtures['vectors'])} wire vectors, "
          f"{len(fixtures['sensor_ack_cases'])} pending ACK cases, {steps} persistence steps")


def validate_sources(workspace):
    registry = load(ROOT / "contracts/registry.json")
    sources = {source for item in registry["contracts"]
               for source in item["implementation"] + item.get("verification", [])}
    for source in sorted(sources):
        if not (workspace / source).is_file():
            fail("Missing implementation/verification reference: " + source)
    print(f"PASS {len(sources)} cross-repository source references")


def validate_consumer(consumer, ids):
    lock = load(consumer / "protocols.lock.json")
    if lock["schema"] != 1 or lock["repository"] != "phicomm-io/iotcloud-community-protocols":
        fail("Unsupported consumer lock")
    if not re.fullmatch("[0-9a-f]{40}", lock["commit"]):
        fail("Consumer must pin a full commit")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != lock["commit"]:
        fail("Check out the consumer's pinned specification commit first")
    digest = hashlib.sha256((ROOT / "contracts/registry.json").read_bytes()).hexdigest()
    if lock["registry_sha256"] != digest:
        fail("Consumer registry digest mismatch")
    if not lock["contracts"] or len(set(lock["contracts"])) != len(lock["contracts"]) or set(lock["contracts"]) - ids:
        fail("Consumer references missing or duplicate interfaces")
    print(f"PASS consumer pin: {consumer.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer", type=Path)
    parser.add_argument("--sources", type=Path, help="workspace containing the named implementation repositories")
    args = parser.parse_args()
    ids = validate_registry()
    validate_examples()
    validate_uart()
    validate_formatted_display()
    validate_reset()
    if args.sources:
        validate_sources(args.sources.resolve())
    if args.consumer:
        validate_consumer(args.consumer.resolve(), ids)


if __name__ == "__main__":
    main()
