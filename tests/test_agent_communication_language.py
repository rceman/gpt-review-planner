import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentCommunicationLanguageContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = (ROOT / "docs/AGENT_COMMUNICATION_LANGUAGE.md").read_text(encoding="utf-8")
        self.planner = (ROOT / "GPT_REVIEW_PLANNER.md").read_text(encoding="utf-8")
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.handoff = (ROOT / "docs/PATCH_PACK_HANDOFF.md").read_text(encoding="utf-8")
        self.cleanup = (ROOT / "docs/POST_MERGE_BRANCH_CLEANUP.md").read_text(encoding="utf-8")
        self.create_pack = (ROOT / "prompts/GPT_CREATE_PATCH_PACK.md").read_text(encoding="utf-8")
        self.review_implement = (ROOT / "prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md").read_text(encoding="utf-8")
        self.review_only = (ROOT / "prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md").read_text(encoding="utf-8")
        self.prepare = (ROOT / "prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md").read_text(encoding="utf-8")
        self.release = (ROOT / "prompts/AGENT_RELEASE_VERSION.md").read_text(encoding="utf-8")
        self.managed = (ROOT / "templates/project/AGENTS.managed-block.md").read_text(encoding="utf-8")

    def test_directional_language_contract(self):
        for text in (
            "The owner may communicate with GPT in any language",
            "All local-agent-facing communication MUST be written in English",
            "The local agent MUST write all execution communication in English",
            "owner conversation language MUST NOT propagate",
        ):
            self.assertIn(text, self.contract)

    def test_agent_artifacts_and_reports_are_covered(self):
        for text in (
            "`## AGENT_HANDOFF`",
            "`AGENT_PROMPT.md`",
            "implementation, correction, merge, post-merge cleanup, and release prompts",
            "progress updates, questions, blockers, deviations",
            "final implementation reports",
        ):
            self.assertIn(text, self.contract)

    def test_bilingual_duplication_is_forbidden(self):
        self.assertIn("MUST NOT duplicate instructions in two languages", self.contract)
        self.assertIn("must not contain a second translated copy", self.contract)
        self.assertIn("bilingual agent instructions are forbidden", self.planner)

    def test_allowed_literals_and_repository_boundary(self):
        for text in (
            "exact error messages and log excerpts",
            "user-visible product copy, localization resources, and domain fixtures",
            "does not impose English on application UI text",
            "embedded in otherwise English instructions or reports",
        ):
            self.assertIn(text, self.contract)

    def test_canonical_handoff_sentences_remain_english(self):
        no_action = "No agent action is required. Preserve the reported state and wait for the next owner instruction."
        patch_pack = "Apply patch pack `<EXACT_ARCHIVE_FILENAME>` from the Downloads folder."
        self.assertIn(no_action, self.contract)
        self.assertIn("Canonical invocation", self.handoff)
        self.assertIn(patch_pack, self.contract)
        self.assertIn("Canonical invocation", self.handoff)

    def test_planner_and_readme_link_normative_contract(self):
        self.assertIn("AGENT_COMMUNICATION_LANGUAGE.md", self.planner)
        self.assertIn("AGENT_COMMUNICATION_LANGUAGE.md", self.readme)
        self.assertIn("All local-agent-facing communication MUST be written in English", self.planner)

    def test_patch_pack_and_merge_contracts_require_english(self):
        self.assertIn("AGENT_TASK.md", self.handoff)
        self.assertIn("All merge and cleanup instructions and reports MUST be written in English", self.cleanup)
        self.assertIn("Generated task instructions", self.create_pack)
        self.assertIn("All local-agent-facing communication MUST be written in English", self.review_implement)

    def test_reusable_prompts_and_managed_agent_block(self):
        self.assertIn("Any later local-agent-facing artifact MUST be written in English", self.review_only)
        self.assertIn("Write all execution communication and the final report in English", self.prepare)
        self.assertIn("Write all execution communication and the final report in English", self.release)
        self.assertIn("all local-agent communication and execution reports must be written in English", self.managed)

    def test_commit_messages_default_to_english(self):
        self.assertIn("commit messages MUST be written in English", self.contract)


if __name__ == "__main__":
    unittest.main()
