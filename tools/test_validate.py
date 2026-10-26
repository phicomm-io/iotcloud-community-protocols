"""Regressions for untrusted JSON numbers and schema numeric boundaries."""
import copy
from pathlib import Path
import tempfile
import unittest

import validate


class NumericValidation(unittest.TestCase):
    def test_json_overflow_and_non_json_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for token in ("1e999", "-1e999", "NaN", "Infinity", "-Infinity"):
                with self.subTest(token=token):
                    path.write_text('{"value":' + token + '}')
                    with self.assertRaises(ValueError):
                        validate.load(path)
            path.write_text('{"value":1.25}')
            self.assertEqual(validate.load(path), {"value": 1.25})

    def test_constructed_non_finite_numbers_fail_real_schemas(self):
        cases = validate.example_cases()
        fixtures = (
            ("m1-display-data-set-v2", "leased API value", lambda data, value: data.update(value=value)),
            ("m1-display-source-set-v2", "TC1 power and independent API reading",
             lambda data, value: data["lanes"][0]["color"].update(high=value)),
            ("sensor-values-v1", "TC1 fresh physical power",
             lambda data, value: data["sensors"]["power"].update(value=value)),
            ("m1-display-value-set-v3", "raw HCHO digits and mixed lamps",
             lambda data, value: data.update(number=value)),
            ("m1-display-profile-state-v3", "confirmed formatted state",
             lambda data, value: data["runtime"]["lanes"][0].update(value=value)),
            ("m1-display-profile-set-v3", "formatted API and external fan",
             lambda data, value: data["lanes"][1]["color"].update(high=value)),
        )
        for name, example, mutate in fixtures:
            schema = validate.load(validate.ROOT / f"contracts/schemas/{name}.schema.json")
            validator = validate.Validator(schema)
            fixture = next(case["data"] for case in cases
                           if case["schema"] == name and case["name"] == example)
            self.assertTrue(validator.is_valid(fixture))
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(schema=name, value=value):
                    invalid = copy.deepcopy(fixture)
                    mutate(invalid, value)
                    self.assertFalse(validator.is_valid(invalid))

    def test_large_integer_does_not_raise_float_overflow(self):
        validator = validate.Validator({"type": "number"})
        self.assertTrue(validator.is_valid(10 ** 1000))
        self.assertFalse(validator.is_valid(True))

    def test_v3_thresholds_remain_finite_and_ordered_as_float32(self):
        cases = validate.example_cases()
        boundaries = (
            (1000, 1500, True),
            (1, 1.000000001, False),  # Distinct JSON doubles collapse to one float32.
            (1e100, 2e100, False),
            (-2e100, -1e100, False),
            (1e-50, 2e-50, False),
            (0, 1.401298464324817e-45, True),  # Smallest positive float32.
            (1, 1.0000001192092896, True),  # Adjacent float32 values.
            (1, 1.0000000596046448, False),  # Midpoint rounds to even, i.e. 1.
            (1, 1.00000006, True),
            (3e38, 3.4028234663852886e38, True),
            (3e38, 3.4028236e38, False),
            (0, 10 ** 1000, False),
            (1, 1, False),
            (1500, 1000, False),
        )
        for kind, example in (("set", "formatted API and external fan"),
                              ("state", "confirmed formatted state")):
            name = f"m1-display-profile-{kind}-v3"
            schema = validate.load(validate.ROOT / f"contracts/schemas/{name}.schema.json")
            validator = validate.Validator(schema)
            fixture = next(case["data"] for case in cases
                           if case["schema"] == name and case["name"] == example)
            for low, high, expected in boundaries:
                with self.subTest(schema=name, low=low, high=high):
                    data = copy.deepcopy(fixture)
                    data["lanes"][0]["color"] = {"mode": "thresholds", "low": low, "high": high}
                    self.assertEqual(validator.is_valid(data), expected)

    def test_original_ordered_fields_does_not_gain_float32_semantics(self):
        validator = validate.Validator({"x-orderedFields": ["low", "high"]})
        self.assertTrue(validator.is_valid({"low": 1, "high": 1.000000001}))
        self.assertTrue(validator.is_valid({"low": 1e100, "high": 2e100}))
        self.assertFalse(validator.is_valid({"low": 1, "high": 1}))


if __name__ == "__main__":
    unittest.main()
