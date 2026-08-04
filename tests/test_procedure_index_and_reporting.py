from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ProcedureIndexAndReportingTests(unittest.TestCase):
    def read(self, path): return (ROOT / path).read_text(encoding='utf-8')
    def test_documents_exist(self):
        for p in ('docs/PROCEDURE_INDEX.md','docs/AGENT_REPORTING.md','prompts/AGENT_FINALIZE_MERGE.md'): self.assertTrue((ROOT/p).exists())
    def test_discovery_links_are_early(self):
        for p in ('README.md','GPT_REVIEW_PLANNER.md','templates/project/AGENTS.managed-block.md'):
            text=self.read(p); self.assertLess(text.find('PROCEDURE_INDEX.md'), 1200, p)
    def test_index_covers_contracts(self):
        text=self.read('docs/PROCEDURE_INDEX.md')
        for value in ('PATCH_PACK_HANDOFF.md','AGENT_EVIDENCE.md','POST_MERGE_BRANCH_CLEANUP.md','RELEASE_PROCESS.md','GPT_CREATE_PATCH_PACK.md','AGENT_FINALIZE_MERGE.md','COMPATIBILITY_AUTHORIZATION.md'): self.assertIn(value,text)
    def test_transitions_and_ownership(self):
        text=self.read('docs/PROCEDURE_INDEX.md')
        for value in ('IMPLEMENTATION_COMPLETE','GPT_DELTA_REVIEW','CORRECTION_REQUIRED','MERGE_READY','MERGE_FINALIZED','MERGE_CLEANUP_BLOCKED','GPT owns','local agent owns','separate task'): self.assertIn(value,text)
        self.assertIn('GPT_CORRECTION_PATCH → AGENT_IMPLEMENTATION', text)
        self.assertIn('OWNER_DECISION → task-specific approved transition', text)
        self.assertIn('MERGE_READY\n    → GPT_MERGE_HANDOFF → MERGE_EXECUTION', text)
        self.assertNotIn('OWNER_DECISION_REQUIRED → MERGE_EXECUTION', text)
    def test_archive_roles_and_prompts(self):
        text=self.read('docs/PROCEDURE_INDEX.md')
        self.assertIn('| PROC-ARCHIVE-PREP | project requested | Local agent |', text)
        self.assertIn('PROJECT_ARCHIVE_REVIEW.md', text)
        self.assertIn('AGENT_PREPARE_PROJECT_ARCHIVE.md', text)
        self.assertIn('GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md', text)
        self.assertIn('GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md', text)
    def test_merge_prompt_parameters_and_safety(self):
        text=self.read('prompts/AGENT_FINALIZE_MERGE.md')
        for value in ('<REPOSITORY>','<LOCAL_REPOSITORY>','<SSH_ORIGIN>','<MAIN_BRANCH>','<FEATURE_BRANCH>','<EXPECTED_MAIN_BEFORE>','<EXPECTED_FEATURE_HEAD>','<EXPECTED_VERSION>','<CI_POLICY>','<CI_WORKFLOW>','<CI_EVENT>','git merge --no-ff','exact merge-SHA CI','MERGE_FINALIZED','MERGE_CLEANUP_BLOCKED','MERGE_BLOCKED','delete only the remote'):
            self.assertIn(value,text)
        for value in ('REMOTE_MAIN_REF="refs/remotes/origin/${MAIN_BRANCH}"','LOCAL_MAIN_REF="refs/heads/${MAIN_BRANCH}"','git switch "${MAIN_BRANCH}"','git push origin "refs/heads/${MAIN_BRANCH}:refs/heads/${MAIN_BRANCH}"','git diff --quiet','PARENT_ONE','PARENT_TWO','git push origin --delete "${FEATURE_BRANCH}"'):
            self.assertIn(value,text)
        self.assertNotIn('refs/remotes/origin/main',text); self.assertNotIn('refs/heads/main',text); self.assertNotIn('git switch main',text)
    def test_reporting_contract(self):
        text=self.read('docs/AGENT_REPORTING.md')
        self.assertIn('Merge CI: success | sha=<SHA> | run=<RUN_ID>',text)
        self.assertIn('Successful helper JSON is not pasted before repeated fields.',text)
        self.assertIn('no_run | blocking=false',text)

    def test_owner_report_keeps_operational_states_separate(self):
        text = self.read('docs/AGENT_REPORTING.md')
        lower = text.lower()
        lower = lower[lower.index('## separate owner-state reporting'):]
        expected = (
            'implementation merged', 'release commit', 'main', 'tag created',
            'tag pushed', 'tag ci', 'auto workflow', 'github release', 'assets',
            'installed version', 'running version', 'activated',
            'connector refresh',
        )
        positions = []
        for number, state in enumerate(expected, 1):
            marker = f'{number}. {state}'
            match = re.search(rf'^\s*{re.escape(marker)}\s*$', lower, re.MULTILINE)
            self.assertIsNotNone(match, state)
            positions.append(match.start())
        self.assertEqual(positions, sorted(positions))
        self.assertIn('cannot be inferred from an earlier one', lower)
        self.assertIn('tag creation does not prove tag push or tag ci', lower)
        self.assertIn('installed version, running version, activation, and connector refresh remain separate', lower)

    def test_release_prompts_validate_publication_before_gates_and_reject_contradictions(self):
        authoring = self.read('prompts/GPT_CREATE_PATCH_PACK.md')
        review = self.read('prompts/GPT_REVIEW_AGENT_RESULT.md')
        for text in (authoring, review):
            self.assertIn('release-publication.json', text)
            self.assertIn(
                'python3 scripts/validate-release-publication.py <PROJECT>/release-publication.json --repo <PROJECT>',
                text,
            )
            self.assertIn('mode/workflow/proof contradictions', text)
            self.assertIn('local `gh`', text)
            self.assertIn('GH_TOKEN', text)
            self.assertIn('GITHUB_TOKEN', text)
        self.assertLess(
            authoring.index('validate the explicit'),
            authoring.index('writing the immutable gate list'),
        )
        self.assertLess(
            review.index('independently load and validate the'),
            review.index('accepting immutable gates'),
        )

    def test_release_agent_prompt_binds_declaration_tag_push_and_post_tag_proofs(self):
        text = self.read('prompts/AGENT_RELEASE_VERSION.md')
        for value in (
            'release-publication.json',
            'python3 scripts/validate-release-publication.py',
            '<PROJECT>/release-publication.json',
            '--repo <PROJECT>',
            'git push origin refs/tags/v<TARGET_VERSION>:refs/tags/v<TARGET_VERSION>',
            'workflow: null',
            'scripts/verify-release-publication.py',
            'github_actions',
            'GitHub Release',
            'assets',
            'local `gh`',
            'curl',
            'wget',
            'GH_TOKEN',
            'GITHUB_TOKEN',
        ):
            self.assertIn(value, text)
        self.assertLess(text.index('validate the explicit declaration'), text.index('git push origin refs/tags'))
        self.assertLess(text.index('git push origin refs/tags'), text.index('Derive post-tag proofs'))

    def test_publication_policy_cross_references_are_complete(self):
        lifecycle = self.read('docs/RELEASE_LIFECYCLE.md')
        versioning = self.read('docs/VERSIONING.md')
        host = self.read('docs/HOST_PREREQUISITES.md')
        procedure = self.read('docs/PROCEDURE_INDEX.md')
        integration = self.read('docs/PROJECT_INTEGRATION.md')
        managed = self.read('templates/project/AGENTS.managed-block.md')
        merge = self.read('prompts/AGENT_FINALIZE_MERGE.md')
        changelog = self.read('CHANGELOG.md')

        self.assertIn('release-publication.json', lifecycle)
        self.assertIn('RELEASE_PUBLICATION.md', lifecycle)
        self.assertIn('RELEASE_PUBLICATION.md', versioning)
        self.assertIn('PROJECT_INTEGRATION.md', host)
        self.assertIn('PROC-PUBLICATION', procedure)
        self.assertIn('PROJECT_INTEGRATION.md', procedure)
        self.assertIn('--release-publication-file', integration)
        for script in (
            'scripts/release.py',
            'scripts/check-github-ci.py',
            'scripts/validate-release-publication.py',
            'scripts/verify-release-publication.py',
        ):
            self.assertIn(script, integration)
        self.assertIn('release-publication.json', managed)
        self.assertIn('release-publication.json', merge)
        self.assertIn('RELEASE_PUBLICATION.md', merge)
        self.assertIn('release-publication declaration', changelog)
    def test_cross_references(self):
        self.assertIn('AGENT_REPORTING.md',self.read('docs/POST_MERGE_BRANCH_CLEANUP.md'))
        self.assertIn('AGENT_REPORTING.md',self.read('docs/RELEASE_PROCESS.md'))
        archive=self.read('prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md')
        self.assertIn('AGENT_FINALIZE_MERGE.md',archive); self.assertNotIn('git push origin --delete "${FEATURE_BRANCH}"',archive)
        self.assertIn('AGENT_REPORTING.md',self.read('prompts/GPT_CREATE_PATCH_PACK.md'))
    def test_handoff_and_closure_contracts(self):
        handoff=self.read('docs/PATCH_PACK_HANDOFF.md')
        self.assertIn('Canonical invocation', handoff)
        self.assertNotIn('must include the complete post-merge procedure',handoff)
        archive=self.read('prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md')
        self.assertNotIn('Stop after declaring `MERGE_READY`;',archive)
        self.assertIn('Do not end the actionable response before emitting',archive)
        self.assertIn('docs/PROCEDURE_INDEX.md',self.read('docs/REVIEW_CLOSURE_PROTOCOL.md'))
        self.assertIn('does not suppress the next-transition handoff',self.read('docs/REVIEW_CLOSURE_PROTOCOL.md'))
        for p in ('docs/AGENT_EVIDENCE.md','prompts/AGENT_RELEASE_VERSION.md'):
            self.assertTrue(self.read(p))

if __name__ == '__main__': unittest.main()
