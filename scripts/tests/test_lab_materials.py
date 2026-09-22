"""Offline regression checks for learner links, commands, and release pins."""
import re
import subprocess
import unittest
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
LUNA_STEPS = "https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps"


class LabMaterials(unittest.TestCase):
    def test_readme_appendix_links_use_luna_page_and_existing_headings(self):
        readme = (ROOT / "README.md").read_text()
        # Luna rewrites bare fragments to /gitlab/#..., which returns a 404.
        self.assertNotRegex(readme, r"\]\(#[^)]+\)")
        headings = {
            re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
            for title in re.findall(r"^#{1,6} (.+)$", readme, re.M)
        }
        links = re.findall(r"\]\((https://luna\.oracle\.com/[^)]+)\)", readme)
        self.assertGreaterEqual(len(links), 5)
        for link in links:
            with self.subTest(link=link):
                self.assertEqual(link.split("#")[0], LUNA_STEPS)
                self.assertIn(urlsplit(link).fragment, headings)

    def test_learner_diagnostics_do_not_default_to_wrong_namespace(self):
        for name in ("README.md", "docs/completion-sheet.md", "docs/monitoring.md"):
            with self.subTest(file=name):
                self.assertNotRegex((ROOT / name).read_text(),
                                    r"kubectl\s+(?:get\s+(?:hpa|pods)|top\s+pods|describe\s+hpa)\b")

    def test_release_revision_agrees_across_preparation_documents(self):
        readme = (ROOT / "README.md").read_text()
        revision = re.search(r"Materials revision: `(lab-[^`]+)`", readme).group(1)
        for name in ("README.md", "docs/instructor-guide.md", "helm/README.md"):
            with self.subTest(file=name):
                self.assertEqual(set(re.findall(r"lab-\d{4}-\d{2}-\d{2}\.\d+",
                                               (ROOT / name).read_text())), {revision})
        self.assertNotIn("git clone", readme)
        self.assertIn("bash scripts/prepare-charts.sh --check", readme)
        self.assertNotIn("scripts/prepare-charts.sh --download", readme)

    def test_bash_blocks_parse_and_local_links_resolve(self):
        for path in (ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "helm/README.md"):
            text = path.read_text()
            for i, block in enumerate(re.findall(r"^\s*```bash\n(.*?)^\s*```", text, re.M | re.S)):
                with self.subTest(file=str(path.relative_to(ROOT)), block=i):
                    result = subprocess.run(["bash", "-n"], input=block, text=True,
                                            capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
            for target in re.findall(r"\]\(([^)\s]+)(?:\s+[^)]*)?\)", text):
                if "://" in target or target.startswith(("mailto:", "#")):
                    continue
                with self.subTest(file=str(path.relative_to(ROOT)), target=target):
                    self.assertTrue((path.parent / target.split("#", 1)[0]).exists())


if __name__ == "__main__":
    unittest.main()
