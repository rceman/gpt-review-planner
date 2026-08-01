from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-runtime-upgrade-task.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("runtime_upgrade_validator", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeUpgradePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_validator()
        cls.valid = json.loads((ROOT / "templates/runtime-upgrade-task.json").read_text(encoding="utf-8"))

    def assert_valid(self, value):
        self.assertEqual(self.validator.validate_task(value), [], value)

    def assert_invalid(self, value, needle=None):
        errors = self.validator.validate_task(value)
        self.assertTrue(errors, value)
        if needle:
            self.assertTrue(any(needle in error for error in errors), errors)

    def test_complete_runtime_upgrade_declaration_passes(self):
        self.assert_valid(self.valid)
        result = subprocess.run(["python3", str(SCRIPT), str(ROOT / "templates/runtime-upgrade-task.json")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_running_version_check_fails(self):
        value = copy.deepcopy(self.valid)
        del value["preflight"]["running_version_check"]
        self.assert_invalid(value, "preflight")

    def test_missing_persisted_state_declaration_fails(self):
        value = copy.deepcopy(self.valid)
        value["persisted_state_scope"] = []
        self.assert_invalid(value, "persisted_state_scope")

    def test_schema_change_without_migration_fails(self):
        value = copy.deepcopy(self.valid)
        value["migration_required"] = False
        value["migration"]["authorized"] = False
        value["compatibility"] = {"scope": "none", "authorized": False, "authorization_source": None, "supported_legacy_versions": [], "direction": "none", "removal_condition": None}
        self.assert_invalid(value, "schema-changing")

    def test_migration_without_explicit_compatibility_authorization_fails(self):
        value = copy.deepcopy(self.valid)
        value["compatibility"]["authorized"] = False
        value["compatibility"]["scope"] = "none"
        value["compatibility"]["authorization_source"] = None
        value["compatibility"]["supported_legacy_versions"] = []
        value["compatibility"]["direction"] = "none"
        value["compatibility"]["removal_condition"] = None
        self.assert_invalid(value, "compatibility")

    def test_permanent_fallback_compatibility_is_rejected(self):
        value = copy.deepcopy(self.valid)
        value["compatibility"]["removal_condition"] = "permanent fallback compatibility"
        self.assert_invalid(value, "fallback")

    def test_target_activation_before_decoder_validation_fails(self):
        value = copy.deepcopy(self.valid)
        value["activation"]["order"] = ["inspect", "activate", "target_decoder_validation"]
        self.assert_invalid(value, "precede")

    def test_preparation_only_can_be_modeled_as_non_shutdown(self):
        value = copy.deepcopy(self.valid)
        value["activation"]["shutdown_required"] = False
        value["success_criterion"] = "Preparation-only validation and backup complete; no activation was claimed."
        self.assert_valid(value)

    def test_full_upgrade_requires_activation_and_unchanged_process_proof(self):
        value = copy.deepcopy(self.valid)
        value["activation"]["order"] = ["inspect", "prepare", "target_decoder_validation", "verify"]
        self.assert_invalid(value, "activation")
        value = copy.deepcopy(self.valid)
        value["verification"]["unchanged_processes"] = ["gateway"]
        self.assert_invalid(value, "unchanged_processes")

    def test_noop_gate_is_rejected(self):
        value = copy.deepcopy(self.valid)
        value["required_gates"][0]["argv"] = ["true"]
        self.assert_invalid(value, "no-op")

    def test_unknown_fields_and_duplicate_json_keys_fail(self):
        value = copy.deepcopy(self.valid)
        value["unexpected"] = True
        self.assert_invalid(value, "unknown")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(self.validator.DuplicateKey):
                self.validator.load_json(path)

    def test_authorized_and_unauthorized_compatibility_contracts(self):
        unauthorized = copy.deepcopy(self.valid)
        unauthorized["migration_required"] = False
        unauthorized["migration"].update({"authorized": False, "authorization_source": None, "direction": "none", "old_schema": None, "new_schema": None, "removal_condition": None})
        unauthorized["compatibility"] = {"scope": "none", "authorized": False, "authorization_source": None, "supported_legacy_versions": [], "direction": "none", "removal_condition": None}
        self.assert_valid(unauthorized)
        authorized = copy.deepcopy(self.valid)
        authorized["compatibility"]["supported_legacy_versions"] = ["workflow-v1"]
        self.assert_valid(authorized)
        incomplete = copy.deepcopy(authorized)
        incomplete["compatibility"]["authorization_source"] = None
        self.assert_invalid(incomplete, "explicit compatibility")

    def test_repo_identity_can_be_checked_against_authoritative_ref(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "VERSION").write_text("2.0.0\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "VERSION"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "base"], check=True)
            sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            value = copy.deepcopy(self.valid)
            value["source_sha"] = sha
            path = repo.parent / f"{repo.name}-task.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            errors = self.validator.validate_task(value, repo=repo, authoritative_ref="HEAD")
            self.assertEqual(errors, [], errors)


class PolicySurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = json.loads((ROOT / "templates/runtime-upgrade-task.json").read_text(encoding="utf-8"))
        cls.validator = load_validator()
        cls.docs = {
            path: (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "GPT_REVIEW_PLANNER.md",
                "docs/RUNTIME_UPGRADE_POLICY.md",
                "docs/PERSISTED_STATE_MIGRATION_POLICY.md",
                "docs/INCIDENT_RESPONSE_POLICY.md",
                "docs/DIRECT_AGENT_SESSION_CONTROL_POLICY.md",
                "docs/TOOL_CONTRACT_INTEGRITY_POLICY.md",
                "docs/CHAT_HANDOFF_CHECKPOINT.md",
                "docs/AGENT_REPORTING.md",
                "docs/RELEASE_PROCESS.md",
                "docs/PROCEDURE_INDEX.md",
            )
        }
        cls.prompts = {
            path: (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "prompts/AGENT_RUNTIME_UPGRADE.md",
                "prompts/AGENT_RUNTIME_RECOVERY.md",
                "prompts/AGENT_INCIDENT_DIAGNOSIS.md",
                "prompts/AGENT_PERSISTED_STATE_MIGRATION.md",
                "prompts/AGENT_STATE_RECONCILIATION.md",
                "prompts/AGENT_DIRECT_SESSION_CONTROL_IMPLEMENTATION.md",
                "prompts/AGENT_TOOL_CONTRACT_AUDIT.md",
                "prompts/AGENT_CHAT_HANDOFF.md",
            )
        }

    def test_runtime_policy_declares_transaction_phases_and_proofs(self):
        text = self.docs["docs/RUNTIME_UPGRADE_POLICY.md"]
        for phrase in ("inspect", "prepare", "backup", "migrate", "validate", "activate", "verify", "rollback", "installed and running versions", "unchanged"):
            self.assertIn(phrase, text)

    def test_migration_policy_preserves_history_and_forbids_dual_readers(self):
        text = self.docs["docs/PERSISTED_STATE_MIGRATION_POLICY.md"]
        self.assertIn("Permanent dual readers", text)
        self.assertIn("historical", text)
        self.assertIn("current operational pointers", text.lower())

    def test_incident_policy_has_triggers_and_no_blind_retry(self):
        text = self.docs["docs/INCIDENT_RESPONSE_POLICY.md"]
        for phrase in ("two failed activation attempts", "15 minutes", "exact first fatal line", "blind retry"):
            self.assertIn(phrase, text)

    def test_direct_session_policy_forbids_durable_mutation(self):
        text = self.docs["docs/DIRECT_AGENT_SESSION_CONTROL_POLICY.md"]
        for phrase in ("no task", "no run", "no plan mutation", "no Git mutation", "registered project/session", "serialized sends"):
            self.assertIn(phrase, text)

    def test_tool_policy_requires_schema_parity_and_rejects_magic_counts(self):
        text = self.docs["docs/TOOL_CONTRACT_INTEGRITY_POLICY.md"]
        self.assertIn("tools/list", text)
        self.assertIn("outputSchema", text)
        self.assertIn("Fixed magic tool counts are forbidden", text)

    def test_chat_handoff_requires_exact_operational_facts(self):
        text = self.docs["docs/CHAT_HANDOFF_CHECKPOINT.md"]
        for phrase in ("exact main SHAs", "installed and running versions", "MCP tool surface", "durable plans", "exact next action"):
            self.assertIn(phrase, text)

    def test_full_upgrade_cannot_claim_pending_activation(self):
        text = self.docs["docs/RUNTIME_UPGRADE_POLICY.md"]
        self.assertIn("cannot claim success while activation", text)
        self.assertIn("activation and verification", text)

    def test_release_and_reporting_link_runtime_contract(self):
        self.assertIn("RUNTIME_UPGRADE_POLICY.md", self.docs["docs/RELEASE_PROCESS.md"])
        self.assertIn("installed version", self.docs["docs/AGENT_REPORTING.md"])

    def test_procedure_index_exposes_all_new_procedures(self):
        text = self.docs["docs/PROCEDURE_INDEX.md"]
        for marker in ("PROC-RUNTIME-UPGRADE", "PROC-INCIDENT", "PROC-STATE-MIGRATION", "PROC-DIRECT-SESSION", "PROC-TOOL-AUDIT", "PROC-CHAT-HANDOFF"):
            self.assertIn(marker, text)

    def test_prompts_cover_required_execution_surfaces(self):
        self.assertIn("target-decoder", self.prompts["prompts/AGENT_RUNTIME_UPGRADE.md"])
        self.assertIn("stale PIDs", self.prompts["prompts/AGENT_RUNTIME_RECOVERY.md"])
        self.assertIn("first fatal line", self.prompts["prompts/AGENT_INCIDENT_DIAGNOSIS.md"])
        self.assertIn("atomic", self.prompts["prompts/AGENT_PERSISTED_STATE_MIGRATION.md"])
        self.assertIn("history-only", self.prompts["prompts/AGENT_STATE_RECONCILIATION.md"])
        self.assertIn("agent_send", self.prompts["prompts/AGENT_DIRECT_SESSION_CONTROL_IMPLEMENTATION.md"])
        self.assertIn("tools/list", self.prompts["prompts/AGENT_TOOL_CONTRACT_AUDIT.md"])
        self.assertIn("exact SHAs", self.prompts["prompts/AGENT_CHAT_HANDOFF.md"])

    def test_schema_defines_preflight_command_shape(self):
        schema = json.loads((ROOT / "schemas/runtime-upgrade-task.schema.json").read_text(encoding="utf-8"))
        preflight = schema["properties"]["preflight"]
        self.assertTrue(preflight["additionalProperties"] is False)
        self.assertEqual(set(preflight["properties"]), set(preflight["required"]))
        self.assertIn("command", schema["$defs"])

    def test_checker_rejects_activation_without_decoder(self):
        value = copy.deepcopy(self.valid)
        value["activation"]["order"] = ["inspect", "prepare", "activate", "verify"]
        self.assertTrue(self.validator.validate_task(value))

    def test_checker_rejects_migration_without_authorization(self):
        value = copy.deepcopy(self.valid)
        value["migration"]["authorized"] = False
        value["migration"]["authorization_source"] = None
        self.assertTrue(self.validator.validate_task(value))

    def test_checker_rejects_permanent_compatibility(self):
        value = copy.deepcopy(self.valid)
        value["compatibility"]["removal_condition"] = "permanent dual reader"
        self.assertTrue(self.validator.validate_task(value))

    def test_checker_rejects_missing_unchanged_process_proof(self):
        value = copy.deepcopy(self.valid)
        value["verification"]["unchanged_processes"] = ["gateway only"]
        self.assertTrue(self.validator.validate_task(value))


if __name__ == "__main__":
    unittest.main()
