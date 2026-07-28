import re
import subprocess
import tempfile
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
        self.assertIn("git push origin --delete \"${FEATURE_BRANCH}\"", self.runbook)
        self.assertIn("git fetch origin --prune", self.runbook)

    def test_fully_qualified_refs_and_no_ambiguous_machine_commands(self):
        for text in (
            "REMOTE_MAIN_REF=\"refs/remotes/origin/main\"",
            "REMOTE_FEATURE_REF=\"refs/remotes/origin/${FEATURE_BRANCH}\"",
            "LOCAL_FEATURE_REF=\"refs/heads/${FEATURE_BRANCH}\"",
        ):
            self.assertIn(text, self.runbook)
        self.assertIn("docs/POST_MERGE_BRANCH_CLEANUP.md", self.prompt)
        self.assertIn("prompts/AGENT_FINALIZE_MERGE.md", self.prompt)
        code = "\n".join(re.findall(r"```(?:bash)?\n(.*?)```", self.runbook + self.prompt, re.S))
        for forbidden in (
            "git rev-parse origin/main",
            "git rev-parse origin/<FEATURE_BRANCH>",
            "git merge-base --is-ancestor origin/<FEATURE_BRANCH> origin/main",
        ):
            self.assertNotIn(forbidden, code)

    def test_shadowing_local_branch_does_not_change_qualified_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            def run(*args):
                return subprocess.run(["git", *args], cwd=repo, check=True, text=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

            run("init", "-q")
            run("config", "user.email", "test@example.invalid")
            run("config", "user.name", "Contract Test")
            (repo / "first.txt").write_text("first\n", encoding="utf-8")
            run("add", "first.txt")
            run("commit", "-qm", "expected")
            expected = run("rev-parse", "HEAD")
            (repo / "second.txt").write_text("second\n", encoding="utf-8")
            run("add", "second.txt")
            run("commit", "-qm", "shadow")
            shadow = run("rev-parse", "HEAD")
            run("update-ref", "refs/remotes/origin/main", expected)
            run("update-ref", "refs/remotes/origin/feature/test", expected)
            run("update-ref", "refs/heads/feature/test", expected)
            run("update-ref", "refs/heads/origin/main", shadow)

            qualified = run("rev-parse", "--verify", "refs/remotes/origin/main^{commit}")
            self.assertEqual(qualified, expected)
            self.assertNotEqual(run("rev-parse", "--verify", "refs/heads/origin/main^{commit}"), expected)
            self.assertEqual(run("rev-parse", "--verify", "refs/remotes/origin/feature/test^{commit}"), expected)
            self.assertEqual(run("merge-base", "--is-ancestor", "refs/remotes/origin/feature/test", "refs/remotes/origin/main"), "")

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
        for text in ("git fetch origin --prune", "git merge-base --is-ancestor", "git push origin --delete", "final inventory", "MERGE_FINALIZED", "MERGE_CLEANUP_BLOCKED"):
            self.assertIn(text, self.runbook)
        self.assertIn("AGENT_FINALIZE_MERGE.md", self.prompt)

    def test_no_cleanup_before_exact_ci_and_local_branch_retention(self):
        self.assertLess(self.runbook.index("exact-SHA CI succeeded"), self.runbook.index("git push origin --delete"))
        self.assertIn("local `<FEATURE_BRANCH>` still exists", self.runbook)
        self.assertIn("no tracked or untracked repository files", self.runbook)
        self.assertIn("worktree is clean", self.runbook)


if __name__ == "__main__":
    unittest.main()
