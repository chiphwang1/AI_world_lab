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
        self.assertIn(f"git clone --branch {revision} --single-branch", readme)
        self.assertIn('https://github.com/chiphwang1/AI_world_lab.git "$HOME/oke-bootcamp" &&\n'
                      '  cd "$HOME/oke-bootcamp"', readme)
        self.assertNotIn("git describe --tags --exact-match HEAD", readme)
        self.assertIn("bash scripts/prepare-charts.sh --check", readme)
        self.assertNotIn("scripts/prepare-charts.sh --download", readme)

    def test_repository_download_is_one_instruction_and_command(self):
        readme = (ROOT / "README.md").read_text()
        instruction = "In a **Bash terminal** on your Luna desktop, download the lab repository. Keep this window open as **terminal 1**:"
        section = readme.split(instruction, 1)[1].split("### Find your lab login and compartment", 1)[0]
        blocks = re.findall(r"```bash\n(.*?)```", section, re.S)
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0].startswith("git clone --branch "))
        self.assertEqual(re.sub(r"```bash\n.*?```", "", section, flags=re.S).strip(), "")

    def test_connection_setup_starts_the_timed_exercises(self):
        readme = (ROOT / "README.md").read_text()
        preparation, exercises = readme.split("## 1. Prepare and confirm your connection — 5 minutes", 1)
        self.assertIn("## Before hands-on: start preparation at the beginning of the lecture", preparation)
        self.assertNotIn("git clone --branch", preparation)
        for command in ("git clone --branch", "oci ce cluster create-kubeconfig",
                        "bash scripts/check-ready.sh",
                        "source helm/versions.env", "bash scripts/prepare-charts.sh --check"):
            with self.subTest(command=command):
                self.assertIn(command, exercises)
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("../README.md#1-prepare-and-confirm-your-connection--5-minutes", access)
        for name in ("docs/instructor-guide.md", "helm/README.md"):
            with self.subTest(file=name):
                text = (ROOT / name).read_text()
                self.assertIn("Before hands-on", text)
                self.assertNotIn("README step 1", text)

    def test_detailed_sidecar_inspection_is_optional(self):
        readme = (ROOT / "README.md").read_text()
        core = readme.split("## Appendix A:", 1)[0]
        appendix = readme.split("## Appendix B: Optional pod inspection", 1)[1]
        for detail in (".spec.initContainers", "restartPolicy", "native sidecar"):
            with self.subTest(detail=detail):
                self.assertNotIn(detail, core)
                self.assertIn(detail, appendix)
        deployment = core.split("## 3.", 1)[1].split("## 4.", 1)[0]
        self.assertNotIn("kubectl -n oke-lab describe pods", deployment)
        self.assertIn('curl --fail --max-time 10 "http://${APP_IP}/"', deployment)
        for concept in ("**Deployment**", "**Pod**", "**Service**"):
            self.assertLess(deployment.index(concept), deployment.index("helm upgrade --install"))

    def test_hpa_inspection_follows_creation(self):
        readme = (ROOT / "README.md").read_text()
        before_scaling, scaling = readme.split("## 5.", 1)
        self.assertNotRegex(before_scaling, r"kubectl[^\n`]*\b(?:get|describe) hpa\b")
        self.assertIn("Not enabled", before_scaling.split("## 4.", 1)[1])
        self.assertLess(scaling.index("--set autoscaling.enabled=true"),
                        scaling.index("kubectl -n oke-lab get hpa hello-oke"))

    def test_dashboard_guidance_explains_results(self):
        readme = (ROOT / "README.md").read_text()
        dashboards = readme.split("## 4.", 1)[1].split("## 5.", 1)[0]
        for explanation in ("95th percentile", "percentage of requests", "average request rate",
                            "Forwarding from 127.0.0.1:20001", "Forwarding from 127.0.0.1:13000"):
            with self.subTest(explanation=explanation):
                self.assertIn(explanation, dashboards)
        self.assertIn("--reuse-values` keeps your existing release settings", readme)
        self.assertIn("Use one baseline reading and one load reading", readme)
        self.assertIn("cannot isolate autoscaling's effect on latency", readme)

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
