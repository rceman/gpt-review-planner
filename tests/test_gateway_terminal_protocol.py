from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("completion", ROOT / "scripts/validate-gpt-tunnel-completion.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GatewayTerminalProtocolTests(unittest.TestCase):
    def test_completion_is_the_only_tunnel_contract(self):
        validator = load()
        value = {
            "schema_version": 1, "run_id": "run-1", "task_sha256": "a" * 64,
            "status": "succeeded", "summary": "done",
            "gate_results": [{"id": "G1", "exit_code": 0}],
            "acceptance_coverage": ["AC1"], "deviations": [], "remaining_risks": [],
        }
        self.assertEqual(validator.validate_value(value, expected_run_id="run-1", expected_task_sha256="a" * 64, gate_count=1, acceptance_count=1), [])

    def test_old_gateway_result_schema_is_not_supported(self):
        self.assertFalse((ROOT / "schemas/gateway-agent-result-v2.schema.json").exists())
        self.assertFalse((ROOT / "scripts/validate-gateway-agent-result.py").exists())


if __name__ == "__main__":
    unittest.main()
