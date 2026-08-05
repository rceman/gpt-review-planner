import copy
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-project-onboarding.py"
REQUEST_PATH = ROOT / "fixtures" / "project-onboarding" / "airelay-request.json"
RECEIPT_PATH = ROOT / "fixtures" / "project-onboarding" / "airelay-activated-receipt.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_project_onboarding", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def schema_accepts(value, schema, root_schema=None):
    """Small dependency-free parity checker for the controlled schemas."""

    root_schema = root_schema or schema
    if "anyOf" in schema and not any(schema_accepts(value, branch, root_schema) for branch in schema["anyOf"]):
        return False
    if "oneOf" in schema and sum(schema_accepts(value, branch, root_schema) for branch in schema["oneOf"]) != 1:
        return False
    if "$ref" in schema:
        target = root_schema
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return schema_accepts(value, target, root_schema)
    if "const" in schema and not json_equal(value, schema["const"]):
        return False
    if "enum" in schema and not any(json_equal(value, item) for item in schema["enum"]):
        return False
    if "type" in schema:
        expected = schema["type"]
        type_ok = {
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "boolean": isinstance(value, bool),
            "integer": isinstance(value, (int, float)) and not isinstance(value, bool) and float(value).is_integer(),
        }.get(expected, True)
        if not type_ok:
            return False
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf")):
            return False
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            return False
        if schema.get("format") == "date-time":
            candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
            try:
                parsed = dt.datetime.fromisoformat(candidate)
            except ValueError:
                return False
            if parsed.tzinfo is None or ("T" not in value and "t" not in value):
                return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            return False
        if "maximum" in schema and value > schema["maximum"]:
            return False
    if isinstance(value, dict):
        required = schema.get("required", [])
        if any(key not in value for key in required):
            return False
        if schema.get("additionalProperties") is False and any(key not in schema.get("properties", {}) for key in value):
            return False
        for key, item in value.items():
            if key in schema.get("properties", {}) and not schema_accepts(item, schema["properties"][key], root_schema):
                return False
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            return False
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            return False
        if "items" in schema and any(not schema_accepts(item, schema["items"], root_schema) for item in value):
            return False
    for branch in schema.get("allOf", []):
        if not schema_accepts(value, branch, root_schema):
            return False
    if "if" in schema and schema_accepts(value, schema["if"], root_schema):
        if "then" in schema and not schema_accepts(value, schema["then"], root_schema):
            return False
    if "not" in schema and schema_accepts(value, schema["not"], root_schema):
        return False
    return True


def json_equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left) == float(right)
    return left == right


class ProjectOnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.request = validator.load_json(REQUEST_PATH)
        cls.receipt = validator.load_json(RECEIPT_PATH)
        cls.request_schema = read_json(ROOT / "schemas" / "project-onboarding-request.schema.json")
        cls.receipt_schema = read_json(ROOT / "schemas" / "project-onboarding-receipt.schema.json")

    def assertRequestInvalid(self, document, *, schema=True):
        with self.assertRaises(validator.ValidationError):
            validator.validate_request(document)
        if schema:
            self.assertFalse(schema_accepts(document, self.request_schema))

    def assertReceiptInvalid(self, document, *, schema=True):
        with self.assertRaises(validator.ValidationError):
            validator.validate_receipt(document)
        if schema:
            self.assertFalse(schema_accepts(document, self.receipt_schema))

    def test_canonical_fixtures_pass_validator_and_schema(self):
        validator.validate_request(self.request)
        validator.validate_receipt(self.receipt)
        self.assertTrue(schema_accepts(self.request, self.request_schema))
        self.assertTrue(schema_accepts(self.receipt, self.receipt_schema))

    def test_request_strict_identity_and_unknown_fields(self):
        document = copy.deepcopy(self.request)
        document["unexpected"] = True
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["project_id"] = "Airelay"
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["project_code"] = "air"
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["root"] = "/tmp/../repo"
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["default_branch"] = "main..next"
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["expected_hub_revision"] = "A" * 40
        self.assertRequestInvalid(document)

    def test_request_session_and_workflow_binding(self):
        document = copy.deepcopy(self.request)
        document["airelay"] = {"session_required": False, "session_key": "forbidden"}
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["airelay"] = {"session_required": True}
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["workflow"]["commit"] = "0" * 39
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        del document["workflow"]["repository"]
        self.assertRequestInvalid(document)

    def test_initial_plan_is_schema_v2_and_project_bound(self):
        document = copy.deepcopy(self.request)
        document["initial_plan"]["schema_version"] = 1
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["initial_plan"]["project_id"] = "other"
        self.assertRequestInvalid(document, schema=False)
        document = copy.deepcopy(self.request)
        document["initial_plan"]["queue"] = ["same", "same"]
        self.assertRequestInvalid(document)
        document = copy.deepcopy(self.request)
        document["initial_plan"]["sections"] = [{"id": "s", "title": "S", "short_description": "ok", "revision": 0}]
        self.assertRequestInvalid(document)

    def test_receipt_state_matrix(self):
        prepared = copy.deepcopy(self.receipt)
        prepared["state"] = "prepared"
        prepared["hub"].pop("after")
        prepared["timestamps"].pop("prepared_at", None)
        prepared["timestamps"].pop("hub_committed_at", None)
        prepared["timestamps"].pop("activated_at", None)
        for key in ("created_project", "created_plan", "created_identifiers", "mirror_proof"):
            prepared.pop(key, None)
        prepared["timestamps"]["prepared_at"] = "2026-08-05T09:00:01Z"
        validator.validate_receipt(prepared)

        committed = copy.deepcopy(self.receipt)
        committed["state"] = "hub_committed"
        committed.pop("mirror_proof")
        committed["timestamps"].pop("activated_at")
        validator.validate_receipt(committed)

        recovery = copy.deepcopy(self.receipt)
        recovery["state"] = "recovery_required"
        recovery.pop("mirror_proof")
        recovery["recovery"] = {"status": "required", "reason": "target decoder rejected old state"}
        validator.validate_receipt(recovery)

        rolled_back = copy.deepcopy(self.receipt)
        rolled_back["state"] = "rolled_back"
        rolled_back.pop("mirror_proof")
        rolled_back["timestamps"]["rolled_back_at"] = "2026-08-05T09:00:04Z"
        rolled_back["recovery"] = {
            "status": "complete",
            "reason": "rollback completed",
            "rolled_back_at": "2026-08-05T09:00:04Z",
        }
        validator.validate_receipt(rolled_back)

        invalid = copy.deepcopy(self.receipt)
        invalid.pop("created_plan")
        self.assertReceiptInvalid(invalid, schema=False)
        invalid = copy.deepcopy(self.receipt)
        invalid["recovery"] = {"status": "required", "reason": "oops"}
        self.assertReceiptInvalid(invalid, schema=False)
        invalid = copy.deepcopy(rolled_back)
        invalid["recovery"].pop("rolled_back_at")
        self.assertReceiptInvalid(invalid, schema=False)

    def test_receipt_proof_identity_and_path_rules(self):
        invalid = copy.deepcopy(self.receipt)
        invalid["repository_proof"]["head"] = "z" * 40
        self.assertReceiptInvalid(invalid)
        invalid = copy.deepcopy(self.receipt)
        invalid["hub"]["paths"].append("../outside")
        self.assertReceiptInvalid(invalid)
        invalid = copy.deepcopy(self.receipt)
        invalid["session_proof"] = {"required": False, "status": "active", "session_key": "bad"}
        self.assertReceiptInvalid(invalid)
        invalid = copy.deepcopy(self.receipt)
        invalid["created_plan"]["path"] = "plan/current.json"
        self.assertReceiptInvalid(invalid, schema=False)

    def test_json_schema_integer_semantics(self):
        for value in (1.0, 2.0):
            request = copy.deepcopy(self.request)
            request["initial_plan"]["revision"] = value
            validator.validate_request(request)
            receipt = copy.deepcopy(self.receipt)
            receipt["created_plan"]["revision"] = value
            validator.validate_receipt(receipt)
        for value in (True, 0, -1, 1.5, float("inf")):
            request = copy.deepcopy(self.request)
            request["initial_plan"]["revision"] = value
            with self.assertRaises(validator.ValidationError):
                validator.validate_request(request)
            receipt = copy.deepcopy(self.receipt)
            receipt["created_plan"]["revision"] = value
            with self.assertRaises(validator.ValidationError):
                validator.validate_receipt(receipt)

    def test_duplicate_keys_and_file_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
            with self.assertRaises(validator.ValidationError):
                validator.load_json(path)
            invalid_utf8 = Path(directory) / "bad.json"
            invalid_utf8.write_bytes(b"{\xff")
            with self.assertRaises(validator.ValidationError):
                validator.load_json(invalid_utf8)
            symlink = Path(directory) / "link.json"
            symlink.symlink_to(REQUEST_PATH)
            with self.assertRaises(validator.ValidationError):
                validator.load_json(symlink)

    def test_cli_validates_both_canonical_files(self):
        for option, path, label in (("--request", REQUEST_PATH, "request"), ("--receipt", RECEIPT_PATH, "receipt")):
            result = subprocess.run(
                ["python3", str(VALIDATOR_PATH), option, str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"VALID {label}:", result.stdout)


if __name__ == "__main__":
    unittest.main()
