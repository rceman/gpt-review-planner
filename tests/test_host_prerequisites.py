import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class HostPrerequisiteContractTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_host_document_and_preflight(self):
        text = self.read("docs/HOST_PREREQUISITES.md")
        for value in ("git --version", "bash --version", "python3 --version", "python3 -m pytest --version", "python3 -m pytest -q", "sudo apt install -y python3-pytest"):
            self.assertIn(value, text)
        self.assertIn("sudo authorization", text)
        self.assertIn("sudo pip", text)

    def test_discovery_links(self):
        self.assertIn("docs/HOST_PREREQUISITES.md", self.read("README.md"))
        self.assertIn("docs/HOST_PREREQUISITES.md", self.read("GPT_REVIEW_PLANNER.md"))
        release = self.read("docs/RELEASE_PROCESS.md")
        self.assertIn("HOST_PREREQUISITES.md", release)
        self.assertLess(release.index("HOST_PREREQUISITES.md"), release.index("python3 -m pytest --version"))

    def test_evidence_and_prompts_require_preflight(self):
        evidence = self.read("docs/AGENT_EVIDENCE.md")
        self.assertIn("missing required runner", evidence)
        self.assertIn("status: pass", evidence)
        self.assertIn("required tool was unavailable", evidence)
        pack = self.read("prompts/GPT_CREATE_PATCH_PACK.md")
        self.assertIn("runtime gates", pack)
        self.assertIn("local agent", pack)
        release_prompt = self.read("prompts/AGENT_RELEASE_VERSION.md")
        self.assertIn("docs/HOST_PREREQUISITES.md", release_prompt)
        self.assertIn("python3 -m pytest --version", release_prompt)


if __name__ == "__main__":
    unittest.main()
