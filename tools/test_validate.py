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


if __name__ == "__main__":
    unittest.main()
