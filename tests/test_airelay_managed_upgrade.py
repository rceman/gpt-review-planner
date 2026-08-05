import copy
import importlib.util
import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-airelay-managed-upgrade.py"
FIXTURES = ROOT / "fixtures" / "airelay-managed-upgrade"


def load_validator():
    spec = importlib.util.spec_from_file_location("airelay_upgrade_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def schema_validate(value, schema, root=None, path="$"):
    root = schema if root is None else root
    if "$ref" in schema:
        target = root
        for part in schema["$ref"][2:].split("/"):
            target = target[part]
        return schema_validate(value, target, root, path)
    if "allOf" in schema:
        for item in schema["allOf"]:
            schema_validate(value, item, root, path)
    if "if" in schema:
        try:
            schema_validate(value, schema["if"], root, path)
        except AssertionError:
            pass
        else:
            if "then" in schema:
                schema_validate(value, schema["then"], root, path)
    if "const" in schema:
        assert value == schema["const"], path
    if "enum" in schema:
        assert value in schema["enum"], path
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
            elif kind == "number":
                matches.append(isinstance(value, (int, float)) and not isinstance(value, bool))
            elif kind == "boolean":
                matches.append(isinstance(value, bool))
            elif kind == "null":
                matches.append(value is None)
            else:
                raise AssertionError(f"unsupported schema type {kind}")
        assert any(matches), path
    if isinstance(value, dict):
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(schema.get("properties", {})), path
        for name in schema.get("required", []):
            assert name in value, f"{path}.{name}"
        for name, child in schema.get("properties", {}).items():
            if name in value:
                schema_validate(value[name], child, root, f"{path}.{name}")
    if isinstance(value, list):
        if "minItems" in schema:
            assert len(value) >= schema["minItems"], path
        if "maxItems" in schema:
            assert len(value) <= schema["maxItems"], path
        if schema.get("uniqueItems"):
            assert len({json.dumps(item, sort_keys=True) for item in value}) == len(value), path
        if "items" in schema:
            for index, item in enumerate(value):
                schema_validate(item, schema["items"], root, f"{path}[{index}]")
    if isinstance(value, str):
        if "minLength" in schema:
            assert len(value) >= schema["minLength"], path
        if "maxLength" in schema:
            assert len(value) <= schema["maxLength"], path
        if "pattern" in schema:
            assert re.search(schema["pattern"], value), path
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            assert value >= schema["minimum"], path
        if "maximum" in schema:
            assert value <= schema["maximum"], path


class AirelayManagedUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe_schema = json.loads((ROOT / "schemas/airelay-session-launch-recipe.schema.json").read_text())
        cls.request_schema = json.loads((ROOT / "schemas/airelay-managed-upgrade-request.schema.json").read_text())
        cls.receipt_schema = json.loads((ROOT / "schemas/airelay-managed-upgrade-receipt.schema.json").read_text())

    def assert_invalid(self, function, value):
        with self.assertRaises(VALIDATOR.ValidationError):
            function(value)

    def assert_schema_and_validator_invalid(self, function, schema, value):
        self.assert_invalid(function, value)
        with self.assertRaises(AssertionError):
            schema_validate(value, schema)

    def test_canonical_recipe_digest_and_schema(self):
        recipe = load_fixture("airelay-master-recipe.json")
        VALIDATOR.validate_recipe(recipe)
        schema_validate(recipe, self.recipe_schema)
        self.assertEqual(recipe["recipe_sha256"], VALIDATOR._recipe_digest(recipe))

    def test_canonical_request_and_schema(self):
        request = load_fixture("rolling-upgrade-request.json")
        VALIDATOR.validate_request(request)
        schema_validate(request, self.request_schema)
        self.assertEqual(request["selected_sessions"][-1]["session_key"], "airelay_master")

    def test_canonical_receipt_and_schema(self):
        receipt = load_fixture("rolling-upgrade-success-receipt.json")
        VALIDATOR.validate_receipt(receipt)
        schema_validate(receipt, self.receipt_schema)

    def test_recipe_rejects_shell_secret_duplicates_and_unknown_fields(self):
        recipe = load_fixture("airelay-master-recipe.json")
        bad = copy.deepcopy(recipe)
        bad["child"]["argv"] = ["resume", "airelay_master", "--no-alt-screen", "--no-alt-screen"]
        self.assert_invalid(VALIDATOR.validate_recipe, bad)
        bad = copy.deepcopy(recipe)
        bad["child"]["argv"][0] = "token=secret"
        self.assert_invalid(VALIDATOR.validate_recipe, bad)
        bad = copy.deepcopy(recipe)
        bad["unexpected"] = True
        self.assert_schema_and_validator_invalid(VALIDATOR.validate_recipe, self.recipe_schema, bad)
        bad = copy.deepcopy(recipe)
        bad["working_directory"] = "../relative"
        self.assert_invalid(VALIDATOR.validate_recipe, bad)

    def test_recipe_authority_binds_resume_and_approved_flags(self):
        recipe = load_fixture("airelay-master-recipe.json")
        bad = copy.deepcopy(recipe)
        bad["resume"]["identity"] = "other"
        self.assert_invalid(VALIDATOR.validate_recipe, bad)
        bad = copy.deepcopy(recipe)
        bad["approved_flags"] = []
        self.assert_invalid(VALIDATOR.validate_recipe, bad)
        bad = copy.deepcopy(recipe)
        bad["child"]["argv"].append("--unapproved")
        self.assert_invalid(VALIDATOR.validate_recipe, bad)

    def test_request_authorization_and_ordering(self):
        request = load_fixture("rolling-upgrade-request.json")
        bad = copy.deepcopy(request)
        bad["selected_sessions"].reverse()
        self.assert_invalid(VALIDATOR.validate_request, bad)
        bad = copy.deepcopy(request)
        bad["authorizations"]["install"] = {"authorized": False}
        self.assert_invalid(VALIDATOR.validate_request, bad)
        bad = copy.deepcopy(request)
        bad["authorizations"]["force_stop"] = {"authorized": True, "source": "owner"}
        self.assert_invalid(VALIDATOR.validate_request, bad)
        bad = copy.deepcopy(request)
        bad["force_stop_policy"] = {"mode": "owner_authorized"}
        self.assert_invalid(VALIDATOR.validate_request, bad)
        bad = copy.deepcopy(request)
        bad["target_release"]["release_path"] = "/tmp/other"
        self.assert_invalid(VALIDATOR.validate_request, bad)

    def test_authorization_false_allows_absent_source_and_true_requires_source(self):
        request = load_fixture("rolling-upgrade-request.json")
        request["authorizations"]["force_stop"].pop("source")
        VALIDATOR.validate_request(request)
        request["authorizations"]["force_stop"] = {"authorized": False, "source": "not-null"}
        self.assert_invalid(VALIDATOR.validate_request, request)
        request["authorizations"]["force_stop"] = {"authorized": True}
        self.assert_invalid(VALIDATOR.validate_request, request)

    def test_receipt_success_requires_exact_identity_readiness_and_order(self):
        receipt = load_fixture("rolling-upgrade-success-receipt.json")
        bad = copy.deepcopy(receipt)
        bad["sessions"][0]["readiness"]["identity"]["pid"] += 1
        self.assert_invalid(VALIDATOR.validate_receipt, bad)
        bad = copy.deepcopy(receipt)
        bad["sessions"][1]["timestamps"]["ready_at"] = "2026-08-05T10:00:06Z"
        bad["sessions"][1]["timestamps"]["updated_at"] = "2026-08-05T10:00:05Z"
        self.assert_invalid(VALIDATOR.validate_receipt, bad)
        bad = copy.deepcopy(receipt)
        bad["sessions"][0]["state"] = "failed"
        bad["sessions"][0]["failure"] = {"code": "start_failed", "message": "no", "at": "2026-08-05T10:00:04Z"}
        self.assert_invalid(VALIDATOR.validate_receipt, bad)

    def test_receipt_failed_and_rollback_matrices(self):
        receipt = load_fixture("rolling-upgrade-success-receipt.json")
        failed = copy.deepcopy(receipt)
        failed["state"] = "failed"
        failed["failure"] = {"code": "readiness_failed", "message": "not ready", "at": "2026-08-05T10:00:06Z"}
        failed["sessions"][0]["state"] = "failed"
        failed["sessions"][0]["failure"] = {"code": "readiness_failed", "message": "not ready", "at": "2026-08-05T10:00:06Z"}
        failed["sessions"][0].pop("readiness")
        failed["timestamps"].pop("completed_at")
        VALIDATOR.validate_receipt(failed)
        rollback = copy.deepcopy(receipt)
        rollback["state"] = "rolled_back"
        rollback["timestamps"].pop("completed_at")
        rollback["timestamps"]["rollback_started_at"] = "2026-08-05T10:00:06Z"
        rollback["timestamps"]["rolled_back_at"] = "2026-08-05T10:00:09Z"
        rollback["rollback"] = {"reason": "new runtime failed", "started_at": "2026-08-05T10:00:06Z", "completed_at": "2026-08-05T10:00:09Z"}
        for session in rollback["sessions"]:
            session["state"] = "rolled_back"
            session.pop("readiness")
            session["timestamps"]["rollback_started_at"] = "2026-08-05T10:00:06Z"
            session["timestamps"]["rolled_back_at"] = "2026-08-05T10:00:09Z"
            session["timestamps"]["updated_at"] = "2026-08-05T10:00:09Z"
            session["rollback_proof"] = {"old_identity": copy.deepcopy(session["old_identity"]), "restored_at": "2026-08-05T10:00:09Z"}
        VALIDATOR.validate_receipt(rollback)
        bad = copy.deepcopy(rollback)
        bad["sessions"][0]["rollback_proof"]["old_identity"]["pid"] += 1
        self.assert_invalid(VALIDATOR.validate_receipt, bad)

    def test_numeric_json_schema_integer_semantics(self):
        request = load_fixture("rolling-upgrade-request.json")
        request["graceful_timeout_seconds"] = 30.0
        request["selected_sessions"][0]["expected_pid"] = 42001.0
        VALIDATOR.validate_request(request)
        schema_validate(request, self.request_schema)
        for value in (True, 0, -1, 1.5, float("inf")):
            bad = load_fixture("rolling-upgrade-request.json")
            bad["graceful_timeout_seconds"] = value
            self.assert_invalid(VALIDATOR.validate_request, bad)
            if math_is_json(value):
                with self.assertRaises(AssertionError):
                    schema_validate(bad, self.request_schema)
        receipt = load_fixture("rolling-upgrade-success-receipt.json")
        receipt["prompt_rejection_window"]["rejected_count"] = 2.0
        VALIDATOR.validate_receipt(receipt)
        schema_validate(receipt, self.receipt_schema)

    def test_schema_parity_for_controlled_shape_errors(self):
        cases = [
            ("recipe", self.recipe_schema, VALIDATOR.validate_recipe, {**load_fixture("airelay-master-recipe.json"), "extra": 1}),
            ("request", self.request_schema, VALIDATOR.validate_request, {**load_fixture("rolling-upgrade-request.json"), "extra": 1}),
            ("receipt", self.receipt_schema, VALIDATOR.validate_receipt, {**load_fixture("rolling-upgrade-success-receipt.json"), "extra": 1}),
        ]
        for name, schema, function, value in cases:
            with self.subTest(name=name):
                self.assert_schema_and_validator_invalid(function, schema, value)
        bad = load_fixture("rolling-upgrade-request.json")
        bad["target_release"]["version"] = "2"
        self.assert_schema_and_validator_invalid(VALIDATOR.validate_request, self.request_schema, bad)
        bad = load_fixture("rolling-upgrade-request.json")
        bad["selected_sessions"][0]["expected_pid"] = False
        self.assert_schema_and_validator_invalid(VALIDATOR.validate_request, self.request_schema, bad)

    def test_cli_accepts_all_three_canonical_fixtures(self):
        for option, name in (
            ("--recipe", "airelay-master-recipe.json"),
            ("--request", "rolling-upgrade-request.json"),
            ("--receipt", "rolling-upgrade-success-receipt.json"),
        ):
            result = subprocess.run(
                ["python3", str(SCRIPT), option, str(FIXTURES / name)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("valid", result.stdout)


def math_is_json(value):
    return not (isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))))


if __name__ == "__main__":
    unittest.main()
