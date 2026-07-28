import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PostMergeBranchCleanupContractTests(unittest.TestCase):
    def setUp(self):
        self.runbook = (ROOT / "docs/POST_MERGE_BRANCH_CLEANUP.md").read_text(encoding="utf-8")
        self.planner = (ROOT / "GPT_REVIEW_PLANNER.md").read_text(encoding="utf-8")
        self.closure = (ROOT / "docs/REVIEW_CLOSURE_PROTOCOL.md").read_text(encoding="utf-8")
        self.handoff = (ROOT / "docs/PATCH_PACK_HANDOFF.md").read_text(encoding="utf-8")
        self.prompt = (ROOT / "prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md").read_text(encoding="utf-8")

    def test_statuses_and_exact_ci_cleanup_boundary(self):
        for value in ("MERGE_READY", "MERGE_FINALIZED", "MERGE_CLEANUP_BLOCKED"):
            self.assertIn(value, self.runbook)
        self.assertIn("exact-SHA CI succeeded", self.runbook)
        self.assertIn("git merge-base --is-ancestor", self.runbook)
        self.assertIn("git push origin --delete <FEATURE_BRANCH>", self.runbook)
        self.assertIn("git fetch origin --prune", self.runbook)

    def test_safety_rules_and_transport(self):
        for text in (
            "origin/main", "origin/HEAD", "not an ancestor", "current remote tip differs",
            "branch", "name, age, commit message", "merged/*", "archive/*", "git branch -d",
            "git branch -D", "fallback HTTPS remote", "`gh`", "GitHub REST or\nGraphQL APIs",
            "repository-setting mutation", "force-push", "squash", "rebase", "cherry-pick",
            "amend", "reset", "history rewriting", "git merge --no-ff", "individually reachable",
        ):
            self.assertIn(text, self.runbook)

    def test_review_ready_remains_review_verdict_and_handoff_is_separate(self):
        self.assertIn("MERGE_READY", self.closure)
        self.assertIn("terminal review verdict", self.runbook)
        self.assertIn("does not\nclaim that Git integration has happened", self.runbook)
        self.assertIn("MERGE_READY", self.planner)
        self.assertIn("MERGE_FINALIZED", self.planner)
        self.assertIn("POST_MERGE_BRANCH_CLEANUP.md", self.planner)

    def test_merge_prompt_and_reports_include_cleanup(self):
        self.assertIn("post-merge", self.handoff)
        self.assertIn("MERGE_FINALIZED", self.handoff)
        self.assertIn("MERGE_CLEANUP_BLOCKED", self.handoff)
        for text in (
            "git fetch origin --prune", "git merge-base --is-ancestor", "git push origin --delete",
            "final inventory", "MERGE_FINALIZED", "MERGE_CLEANUP_BLOCKED",
        ):
            self.assertIn(text, self.prompt)
        self.assertIn("same `AGENT_HANDOFF`", self.prompt)

    def test_no_cleanup_before_exact_ci_and_local_branch_retention(self):
        self.assertLess(self.runbook.index("exact-SHA CI succeeded"), self.runbook.index("git push origin --delete"))
        self.assertIn("local `<FEATURE_BRANCH>` still exists", self.runbook)
        self.assertIn("no tracked or untracked repository files", self.runbook)
        self.assertIn("worktree is clean", self.runbook)


if __name__ == "__main__":
    unittest.main()
