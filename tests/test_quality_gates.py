import copy
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-quality-gates.py"
SCHEMA_PATH = ROOT / "schemas" / "quality-gates.schema.json"
TEMPLATE_PATH = ROOT / "templates" / "project" / "quality-gates.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("quality_gates_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


def schema_accepts(value, schema, root=None):
    root = schema if root is None else root
    if "$ref" in schema:
        target = root
        for part in schema["$ref"][2:].split("/"):
            target = target[part]
        return schema_accepts(value, target, root)
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if "not" in schema and schema_accepts(value, schema["not"], root):
        return False
    if "allOf" in schema and not all(schema_accepts(value, item, root) for item in schema["allOf"]):
        return False
    if "anyOf" in schema and not any(schema_accepts(value, item, root) for item in schema["anyOf"]):
        return False
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        matches = []
        for kind in types:
            if kind == "object":
                matches.append(isinstance(value, dict))
            elif kind == "array":
                matches.append(isinstance(value, list))
            elif kind == "string":
                matches.append(isinstance(value, str))
            elif kind == "integer":
                matches.append(isinstance(value, (int, float)) and not isinstance(value, bool) and (not isinstance(value, float) or value.is_integer()))
            elif kind == "boolean":
                matches.append(isinstance(value, bool))
            else:
                raise AssertionError(f"unsupported schema type {kind}")
        if not any(matches):
            return False
    if isinstance(value, dict):
        if schema.get("additionalProperties") is False and set(value) - set(schema.get("properties", {})):
            return False
        if any(name not in value for name in schema.get("required", [])):
            return False
        return all(
            schema_accepts(value[name], child, root)
            for name, child in schema.get("properties", {}).items()
            if name in value
        )
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            return False
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            return False
        return all(schema_accepts(item, schema["items"], root) for item in value) if "items" in schema else True
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value)):
            return False
        return "pattern" not in schema or re.search(schema["pattern"], value) is not None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value >= schema.get("minimum", value) and value <= schema.get("maximum", value)
    return True


class QualityGatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def valid(self):
        return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))

    def assert_invalid(self, value, *, schema=True):
        with self.assertRaises(VALIDATOR.QualityGatesError):
            VALIDATOR.validate(value)
        if schema:
            self.assertFalse(schema_accepts(value, self.schema))

    def test_template_is_valid_and_has_exact_top_level_contract(self):
        value = self.valid()
        VALIDATOR.validate(value)
        self.assertTrue(schema_accepts(value, self.schema))
        self.assertEqual(set(value), {"schema_version", "unmatched_changed_path", "cleanup", "generated", "rules", "release"})
        self.assertFalse((ROOT / "quality-gates.json").exists())

    def test_duplicate_json_keys_and_symlink_input_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            duplicate = directory / "duplicate.json"
            duplicate.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
            with self.assertRaises(VALIDATOR.QualityGatesError):
                VALIDATOR.load_json(duplicate)
            link = directory / "link.json"
            link.symlink_to(TEMPLATE_PATH)
            with self.assertRaises(VALIDATOR.QualityGatesError):
                VALIDATOR.load_json(link)

    def test_unknown_fields_at_top_and_nested_levels_are_rejected(self):
        value = self.valid()
        value["unknown"] = True
        self.assert_invalid(value)
        value = self.valid()
        value["cleanup"]["extra"] = True
        self.assert_invalid(value)
        value = self.valid()
        value["rules"][0]["prepare"][0]["extra"] = True
        self.assert_invalid(value)

    def test_paths_are_relative_normalized_and_safe(self):
        for location, bad in (
            (("cleanup", "paths"), ["../tmp"]),
            (("cleanup", "paths"), ["/tmp/*"]),
            (("rules", 0, "paths"), ["src/../x"]),
            (("generated", 0, "input_globs"), ["src\\*.py"]),
            (("generated", 0, "output_paths"), ["build/*.json"]),
        ):
            value = self.valid()
            cursor = value
            for key in location[:-1]:
                cursor = cursor[key]
            cursor[location[-1]] = bad
            self.assert_invalid(value)

    def test_cleanup_rejects_universal_patterns_and_requires_true(self):
        for pattern in (".", "*", "**", "**/*", "/"):
            value = self.valid()
            value["cleanup"]["paths"] = [pattern]
            self.assert_invalid(value)
        value = self.valid()
        value["cleanup"]["untracked_only"] = False
        self.assert_invalid(value)

    def test_duplicate_rule_command_and_generated_output_ids_are_rejected(self):
        value = self.valid()
        value["rules"].append(copy.deepcopy(value["rules"][0]))
        self.assert_invalid(value, schema=False)

        value = self.valid()
        value["release"][0]["id"] = value["rules"][0]["prepare"][0]["id"]
        self.assert_invalid(value, schema=False)

        value = self.valid()
        value["generated"].append(copy.deepcopy(value["generated"][0]))
        self.assert_invalid(value, schema=False)

        value = self.valid()
        value["generated"].append({
            "id": "other-output",
            "input_globs": ["docs/*.md"],
            "output_paths": [value["generated"][0]["output_paths"][0]],
            "argv": ["python3", "tool.py"],
            "timeout_seconds": 1,
        })
        self.assert_invalid(value, schema=False)

    def test_changed_rule_must_have_a_nonempty_phase(self):
        value = self.valid()
        value["rules"][0]["prepare"] = []
        value["rules"][0]["merge"] = []
        self.assert_invalid(value)

    def test_fix_is_prepare_only_and_release_is_check_without_file_args(self):
        value = self.valid()
        value["rules"][0]["merge"][0]["mode"] = "fix"
        self.assert_invalid(value)
        value = self.valid()
        value["release"][0]["file_args"] = "append"
        self.assert_invalid(value)
        value = self.valid()
        value["release"] = []
        self.assert_invalid(value)

    def test_shell_evaluation_forms_are_rejected_but_direct_bash_check_is_valid(self):
        cases = (
            ["bash", "-c", "echo unsafe"],
            ["cmd", "/c", "echo unsafe"],
            ["pwsh", "-Command", "Write-Host unsafe"],
            ["python3", "-c", "print('unsafe')"],
        )
        for argv in cases:
            value = self.valid()
            value["rules"][0]["prepare"][0]["argv"] = argv
            self.assert_invalid(value, schema=False)
        value = self.valid()
        value["rules"][0]["prepare"][0]["argv"] = ["bash", "-n", "scripts/example.sh"]
        VALIDATOR.validate(value)

    def test_timeout_bounds_and_integer_semantics_are_strict(self):
        for timeout in (0, -1, 3601, 1.5, True, float("inf")):
            value = self.valid()
            value["release"][0]["timeout_seconds"] = timeout
            self.assert_invalid(value)
        value = self.valid()
        value["release"][0]["timeout_seconds"] = 1800.0
        VALIDATOR.validate(value)
        self.assertTrue(schema_accepts(value, self.schema))

    def test_unmatched_changed_path_is_fail_closed_and_command_selection_is_declarative(self):
        value = self.valid()
        value["unmatched_changed_path"] = "allow"
        self.assert_invalid(value)
        docs = (ROOT / "docs" / "QUALITY_GATES.md").read_text(encoding="utf-8")
        for phrase in (
            "declaration order",
            "de-duplicate",
            "sorted and unique",
            "fails closed",
            "untracked_only",
            "generated-output boundary",
            "task_merge",
            "full-suite run",
        ):
            self.assertIn(phrase, docs)


if __name__ == "__main__":
    unittest.main()
