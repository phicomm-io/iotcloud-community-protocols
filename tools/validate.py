#!/usr/bin/env python3
"""Validate shared contracts, examples, wire vectors and optional consumer pins."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from jsonschema import Draft202012Validator, validators

ROOT = Path(__file__).resolve().parent.parent
# JSON-C ingress distinguishes integer tokens from floating-point tokens.
STRICT_TYPES = Draft202012Validator.TYPE_CHECKER.redefine(
    "integer", lambda checker, value: type(value) is int)
Validator = validators.extend(Draft202012Validator, type_checker=STRICT_TYPES)


def load(path):
    return json.loads(path.read_text(), parse_constant=lambda value: fail(f"Non-JSON number: {value}"))


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


def decode_vector(frame, role, definition):
    layout = definition[role]
    if (len(frame) != layout["length"] or list(frame[:len(layout["header"])]) != layout["header"]
            or frame[-1] != layout["footer"]):
        fail("Invalid frame boundary")
    if role == "button_event":
        start, count = layout["reserved_offset"], layout["reserved_length"]
        kind = frame[layout["kind_offset"]]
        if kind not in layout["kinds"] or any(frame[start:start + count]):
            fail("Invalid button kind or reserved byte")
        start = layout["held_offset"]
        return {"kind": kind, "sequence": frame[layout["sequence_offset"]],
                "held_ms": int.from_bytes(frame[start:start + layout["held_bytes"]], "big")}
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
    else:
        start = layout["arguments_offset"]
        output.update(decode_fields(frame[start:start + layout["arguments_length"]], operation["arguments"]))
        for condition in operation.get("conditions", []):
            if all(output.get(key) == value for key, value in condition["when"].items()):
                if any(output.get(key) != value for key, value in condition["require"].items()):
                    fail("Conditional argument constraint failed")
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


def validate_examples():
    schemas = {}
    for path in (ROOT / "contracts/schemas").glob("*.schema.json"):
        schema = load(path)
        Validator.check_schema(schema)
        schemas[path.name.removesuffix(".schema.json")] = Validator(schema)
    cases = load(ROOT / "contracts/examples/cases.json")["cases"]
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


def validate_uart():
    definition = load(ROOT / "contracts/m1-uart-v1.json")
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
        names = {field["name"] for field in operation["arguments"] if "name" in field}
        for condition in operation.get("conditions", []):
            if (set(condition["when"]) | set(condition["require"])) - names:
                fail("Conditional constraint references an undefined field")
    vectors = load(ROOT / "contracts/vectors/m1-uart-v1.json")["vectors"]
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
    print(f"PASS {len(vectors)} MCU wire vectors and opcode allocation")


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
    if args.sources:
        validate_sources(args.sources.resolve())
    if args.consumer:
        validate_consumer(args.consumer.resolve(), ids)


if __name__ == "__main__":
    main()
