from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WorkflowPerformanceBudgetTests(unittest.TestCase):
    def setUp(self):
        self.planner = (ROOT / "GPT_REVIEW_PLANNER.md").read_text(encoding="utf-8")
        self.version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    def test_version_synchronization(self):
        self.assertEqual(self.version, "1.4.0")
        self.assertIn("**Workflow version:** 1.4.0", self.planner)
        self.assertIn("1.4.0", self.changelog)

    def test_mandatory_budget_and_incident(self):
        section = " ".join(self.planner.split("### 17.1 Mandatory workflow performance budget and KPI", 1)[1].split())
        self.assertIn("within 10 minutes of successful dispatch", section)
        self.assertIn("dispatch time + 10 minutes", section)
        self.assertIn("workflow performance incident", section)
        self.assertIn("instead of treating the overrun as normal or merely waiting", section)
        self.assertIn("Repeated occurrences of the same delay class", section)

    def test_duration_facts_and_kpi_targets(self):
        section = " ".join(self.planner.split("### 17.1 Mandatory workflow performance budget and KPI", 1)[1].split())
        for literal in (
            "terminal_finalized_at - dispatch_succeeded_at",
            "run ID, task ID",
            "project ID",
            "duration seconds",
            "terminal status",
            "ten-minute-check outcome",
            "overrun boolean",
            "primary delay class",
            "sample count",
            "P50 duration",
            "P95 duration",
            "overrun count",
            "overrun rate",
            "nearest-rank percentile",
            "P50 bounded-run duration <= 5 minutes",
            "P95 <= 10 minutes",
        ):
            self.assertIn(literal, section)

    def test_delay_classes_and_safety_boundary(self):
        section = " ".join(self.planner.split("### 17.1 Mandatory workflow performance budget and KPI", 1)[1].split())
        for cause in ("oversized scope", "excessive exploration/token use", "redundant validation", "slow or noisy tooling", "gateway/Airelay latency", "model capacity/retry/unsent-prompt behavior", "dependency/environment bootstrap", "finalization/evidence delay", "unavoidable external service delay"):
            self.assertIn(cause, section)
        self.assertRegex(section, re.compile(r"MUST NOT.*skip gates", re.S))
        self.assertIn("MUST assess correctness and workflow efficiency", section)


if __name__ == "__main__":
    unittest.main()
