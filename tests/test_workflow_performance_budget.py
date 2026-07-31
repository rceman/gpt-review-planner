from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WorkflowPerformanceBudgetTests(unittest.TestCase):
    def setUp(self):
        self.planner = (ROOT / "GPT_REVIEW_PLANNER.md").read_text(encoding="utf-8")
        self.version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    def workflow_budget_section(self):
        heading = "### 17.1 Mandatory workflow performance budget and KPI"
        heading_match = re.search(
            rf"(?m)^{re.escape(heading)}\s*$", self.planner
        )
        self.assertIsNotNone(heading_match, "workflow budget heading is missing")

        body_start = heading_match.end()
        boundary = re.search(
            r"(?m)^(?:---|#{1,3}\s+\S.*)$", self.planner[body_start:]
        )
        self.assertIsNotNone(
            boundary, "workflow budget section has no terminating boundary"
        )
        section = self.planner[body_start : body_start + boundary.start()]
        self.assertTrue(section.strip(), "workflow budget section is empty")
        return " ".join(section.split())

    def test_version_synchronization(self):
        self.assertEqual(self.version, "2.0.0")
        self.assertIn("**Workflow version:** 2.0.0", self.planner)
        self.assertIn("2.0.0", self.changelog)

    def test_mandatory_budget_and_incident(self):
        section = self.workflow_budget_section()
        self.assertIn("within 10 minutes of successful dispatch", section)
        self.assertIn("dispatch time + 10 minutes", section)
        self.assertIn("workflow performance incident", section)
        self.assertIn("instead of treating the overrun as normal or merely waiting", section)
        self.assertIn("Repeated occurrences of the same delay class", section)

    def test_duration_facts_and_kpi_targets(self):
        section = self.workflow_budget_section()
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
        section = self.workflow_budget_section()
        for cause in ("oversized scope", "excessive exploration/token use", "redundant validation", "slow or noisy tooling", "gateway/Airelay latency", "model capacity/retry/unsent-prompt behavior", "dependency/environment bootstrap", "finalization/evidence delay", "unavoidable external service delay"):
            self.assertIn(cause, section)
        self.assertIn(
            "This budget is an operational target, not permission to skip gates, "
            "weaken tests, truncate evidence, or falsely terminalize runs.",
            section,
        )
        self.assertIn("MUST assess correctness and workflow efficiency", section)


if __name__ == "__main__":
    unittest.main()
