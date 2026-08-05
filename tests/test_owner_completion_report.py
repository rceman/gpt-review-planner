from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates" / "owner-completion-report"


class OwnerCompletionReportTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def template(self, name: str) -> str:
        return (TEMPLATE_ROOT / name).read_text(encoding="utf-8")

    def test_exactly_six_generic_templates_exist(self) -> None:
        expected = {
            "implementation-complete.md",
            "review-correction-required.md",
            "merge-complete.md",
            "release-complete.md",
            "runtime-activation-complete.md",
            "blocked-failed.md",
        }
        actual = {path.name for path in TEMPLATE_ROOT.glob("*.md")}
        self.assertEqual(actual, expected)

    def test_successful_templates_use_exact_heading_order(self) -> None:
        headings = (
            "## What changed",
            "## Why it matters",
            "## Availability",
            "## Next action",
            "## Technical record",
        )
        for name in (
            "implementation-complete.md",
            "merge-complete.md",
            "release-complete.md",
            "runtime-activation-complete.md",
        ):
            text = self.template(name)
            positions = [text.index(heading) for heading in headings]
            self.assertEqual(positions, sorted(positions), name)
            technical_tail = text[text.index("## Technical record") + len("## Technical record") :]
            self.assertNotRegex(technical_tail, r"^## ", re.MULTILINE)
            self.assertIn("None — no owner action required", text)

    def test_blocked_templates_lead_with_blocker_projection(self) -> None:
        headings = (
            "## Owner impact",
            "## Required decision",
            "## Preserved state",
            "## Technical record",
        )
        for name in ("review-correction-required.md", "blocked-failed.md"):
            text = self.template(name)
            self.assertIn("Outcome: `BLOCKED`", text)
            positions = [text.index(heading) for heading in headings]
            self.assertEqual(positions, sorted(positions), name)
            self.assertNotIn("## What changed", text)
            technical_tail = text[text.index("## Technical record") + len("## Technical record") :]
            self.assertNotRegex(technical_tail, r"^## ", re.MULTILINE)

    def test_normative_order_and_machine_evidence_separation(self) -> None:
        text = self.read("docs/OWNER_COMPLETION_REPORT.md")
        for phrase in (
            "sole normative authority",
            "completion.json",
            "run reports",
            "CI JSON",
            "evidence manifests",
            "terminal logs",
            "One-line outcome in plain language",
            "`What changed`",
            "`Why it matters`",
            "`Availability`",
            "`Next action`",
            "`Technical record`, last",
            "None — no owner action required",
        ):
            self.assertIn(phrase, text)
        order = [
            text.index("One-line outcome in plain language"),
            text.index("`What changed`"),
            text.index("`Why it matters`"),
            text.index("`Availability`"),
            text.index("`Next action`"),
            text.index("`Technical record`, last"),
        ]
        self.assertEqual(order, sorted(order))
        self.assertIn("OWNER_COMPLETION_REPORT.md", self.read("docs/AGENT_REPORTING.md"))
        self.assertIn("machine/agent execution-evidence authority", self.read("docs/AGENT_REPORTING.md"))

    def test_owner_projection_has_one_normative_authority(self) -> None:
        owner = self.read("docs/OWNER_COMPLETION_REPORT.md")
        reporting = self.read("docs/AGENT_REPORTING.md")
        self.assertIn("sole normative authority", owner)
        self.assertIn("Machine evidence lifecycle facts", reporting)
        self.assertIn("not a second owner-report contract", reporting)
        self.assertNotIn("## Separate owner-state reporting", reporting)
        self.assertIn("owner-facing projection order", reporting)

    def test_state_vocabulary_and_independent_availability(self) -> None:
        text = self.read("docs/OWNER_COMPLETION_REPORT.md")
        for state in (
            "implemented",
            "reviewed",
            "merged",
            "released",
            "installed",
            "running",
            "activated",
            "blocked",
        ):
            self.assertIn(f"`{state}`", text)
        for forbidden in ("`done`", "complete everywhere"):
            self.assertIn(forbidden, text)
        for phrase in (
            "are independent states",
            "A source merge is never runtime availability",
            "released does not prove installed",
            "installed does not prove running",
            "running does not prove activated",
        ):
            self.assertIn(phrase, text)

    def test_tool_groups_and_per_tool_form(self) -> None:
        normative = self.read("docs/OWNER_COMPLETION_REPORT.md")
        for text in (normative, self.template("release-complete.md"), self.template("runtime-activation-complete.md")):
            for group in ("New tools", "Updated tools", "Removed tools"):
                self.assertIn(f"### {group}", text)
            self.assertIn("<tool>", text)
            self.assertIn("None", text)
            self.assertIn("mutually exclusive", text)
            self.assertIn("Delete the unused alternative before delivery", text)
            self.assertIn("never retain both", text)
        self.assertIn("Bare comma-separated endpoint lists are not a report", normative)

    def test_all_templates_have_complete_technical_record(self) -> None:
        required_fields = (
            "Final/accepted/source/runtime identity:",
            "Relevant CI/evidence/diagnostic:",
            "Task/run:",
            "Deviations:",
            "Prohibited operations:",
        )
        for name in (
            "implementation-complete.md",
            "review-correction-required.md",
            "merge-complete.md",
            "release-complete.md",
            "runtime-activation-complete.md",
            "blocked-failed.md",
        ):
            text = self.template(name)
            technical = text.index("## Technical record")
            self.assertEqual(text.rfind("## Technical record"), technical, name)
            for field in required_fields:
                self.assertGreater(text.index(field), technical, (name, field))

    def test_blocked_required_decision_is_actionable(self) -> None:
        for name in ("review-correction-required.md", "blocked-failed.md"):
            text = self.template(name)
            start = text.index("## Required decision")
            end = text.index("## Preserved state")
            decision = text[start:end]
            self.assertNotIn("None", decision, name)
            self.assertRegex(
                decision,
                r"decision|authorization|recovery action|external dependency",
                name,
            )

    def test_all_required_authorities_link_the_owner_contract(self) -> None:
        for relative in (
            "docs/AGENT_REPORTING.md",
            "docs/PROCEDURE_INDEX.md",
            "GPT_REVIEW_PLANNER.md",
            "docs/CHAT_HANDOFF_CHECKPOINT.md",
            "prompts/AGENT_CHAT_HANDOFF.md",
            "prompts/AGENT_FINALIZE_MERGE.md",
            "prompts/AGENT_RELEASE_VERSION.md",
            "prompts/GPT_REVIEW_AGENT_RESULT.md",
        ):
            self.assertIn("OWNER_COMPLETION_REPORT.md", self.read(relative), relative)
        procedure = self.read("docs/PROCEDURE_INDEX.md")
        self.assertIn("PROC-OWNER-REPORT", procedure)
        self.assertIn("MACHINE_EVIDENCE_READ", procedure)
        self.assertIn("OWNER_COMPLETION_REPORT", procedure)
        self.assertIn("GPT authors that", procedure)
        self.assertIn("local agent supplies machine evidence", procedure)

    def test_future_gateway_enforcement_is_not_claimed(self) -> None:
        text = self.read("docs/OWNER_COMPLETION_REPORT.md")
        self.assertIn("does not install or claim", text)
        self.assertIn("versioned GPT Tunnel Operator Guide", text)
        self.assertIn("`session_start`", text)
        self.assertIn("`session_sync`", text)
        self.assertIn("later gateway integration", text)
        self.assertIn("Manual handoffs are the interim enforcement boundary", text)

    def test_templates_have_no_project_specific_literals(self) -> None:
        for path in TEMPLATE_ROOT.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\bv\d+\.\d+\.\d+\b", path.name)
            self.assertNotRegex(text, r"\b[0-9a-f]{40}\b", path.name)
            self.assertNotRegex(text, r"https?://", path.name)
            for literal in ("gpt-review-planner", "gpt-tunnel", "release.py", "check-github-ci"):
                self.assertNotIn(literal, text, path.name)


if __name__ == "__main__":
    unittest.main()
