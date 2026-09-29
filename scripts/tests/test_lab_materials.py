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
        self.assertIn("bash scripts/prepare-charts.sh --download &&\n"
                      "bash scripts/prepare-charts.sh --check", readme)

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
        preparation, exercises = readme.split("## 1. Prepare and confirm your connection — 10 minutes", 1)
        self.assertIn("## Before hands-on: start preparation at the beginning of the lecture", preparation)
        self.assertNotIn("git clone --branch", preparation)
        for command in ("git clone --branch", "oci ce cluster create-kubeconfig",
                        "bash scripts/check-ready.sh",
                        "source helm/versions.env", "bash scripts/prepare-charts.sh --download",
                        "bash scripts/prepare-charts.sh --check"):
            with self.subTest(command=command):
                self.assertIn(command, exercises)
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("../README.md#1-prepare-and-confirm-your-connection--10-minutes", access)
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

    def test_application_configuration_and_deployment_are_explained(self):
        readme = (ROOT / "README.md").read_text()
        deployment = readme.split("## 3.", 1)[1].split("## 4.", 1)[0]
        for detail in ("Configure and deploy", "values file", "APP_MESSAGE",
                       "vim helm/values/student.yaml", "`:wq`",
                       "Saving the file does not change the cluster",
                       "ConfigMap", "two replicas", "without deploying anything",
                       "traffic generator and HPA are disabled initially"):
            with self.subTest(detail=detail):
                self.assertIn(detail, deployment)

    def test_public_ip_explanation_retains_reusable_variable(self):
        readme = (ROOT / "README.md").read_text()
        deployment = readme.split("## 3.", 1)[1].split("## 4.", 1)[0]
        self.assertIn('APP_IP=$(kubectl -n oke-lab get svc hello-oke', deployment)
        for detail in ("`EXTERNAL-IP`", "`-o jsonpath=...`", "`$(...)`",
                       "only in this terminal", "HTTP, not HTTPS"):
            with self.subTest(detail=detail):
                self.assertIn(detail, deployment)

    def test_generator_inspection_distinguishes_request_sender_from_app(self):
        readme = (ROOT / "README.md").read_text()
        deployment = readme.split("## 3.", 1)[1].split("## 4.", 1)[0]
        self.assertLess(deployment.index("--set traffic.enabled=true"),
                        deployment.index("kubectl -n oke-lab get pods -l app=hello-oke-traffic"))
        self.assertIn("application pod, not the generator", deployment)
        self.assertIn("snapshot", deployment)
        appendix = readme.split("### Traffic generator pod", 1)[1]
        self.assertIn("kubectl -n oke-lab describe pods -l app=hello-oke-traffic", appendix)
        self.assertIn("does not use the public `APP_IP`", appendix)

    def test_upstream_software_is_distinguished_from_lab_configuration(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("upstream open-source tools", readme)
        self.assertIn("do not modify their application source code", readme)
        self.assertIn("lab-specific settings", readme)
        self.assertIn("custom training materials", readme)

    def test_concepts_connect_counts_desired_state_and_observations(self):
        readme = (ROOT / "README.md").read_text()
        introduction = readme.split("## Schedule", 1)[0]
        for concept in ("worker nodes", "ReplicaSet", "Kubernetes control plane",
                        "manage application traffic through proxies"):
            with self.subTest(concept=concept):
                self.assertIn(concept, introduction)
        self.assertNotIn("`istiod`", introduction)
        istio_install = readme.split("### Install Istio", 1)[1].split("### Install Prometheus", 1)[0]
        self.assertIn("`istiod`, which configures the proxies", istio_install)
        for explanation in ("Deployment `READY 2/2`", "Each pod's `READY 2/2`",
                            "**desired state**", "`NODE` column",
                            "current average utilization / target utilization",
                            "evidence of increased demand", "evidence of Kubernetes' response"):
            with self.subTest(explanation=explanation):
                self.assertIn(explanation, readme)
        self.assertIn("generator bypass", readme)
        self.assertIn("Trace the monitoring path", readme)
        self.assertIn("Trace the CPU-based autoscaling path", readme)
        sheet = (ROOT / "docs/completion-sheet.md").read_text()
        for question in (2, 3):
            self.assertIn(f"My evidence (question {question}):", sheet)
        self.assertNotIn("assigned context", sheet)

    def test_hpa_inspection_follows_creation(self):
        readme = (ROOT / "README.md").read_text()
        before_scaling, scaling = readme.split("## 6. Optional: CPU-based autoscaling", 1)
        self.assertNotRegex(before_scaling, r"kubectl[^\n`]*\b(?:get|describe) hpa\b")
        self.assertNotIn("--set autoscaling.enabled=true", before_scaling)
        self.assertNotIn("--set traffic.loadEnabled=true", before_scaling)
        self.assertIn("HPA remains disabled throughout the core lab", before_scaling)
        self.assertLess(scaling.index("--set autoscaling.enabled=true"),
                        scaling.index("kubectl -n oke-lab get hpa hello-oke"))

    def test_optional_extensions_do_not_gate_core_completion(self):
        readme = (ROOT / "README.md").read_text()
        core_goals = readme.split("By the end, you should be able to:", 1)[1].split("If time permits", 1)[0]
        self.assertNotIn("load metrics", core_goals)
        self.assertNotIn("autoscaling", core_goals)
        self.assertIn("manual scaling", core_goals)
        manual = readme.split("## 5. Scale manually", 1)[1].split("## 6.", 1)[0]
        for detail in ("--set replicaCount=4", "--set replicaCount=2",
                       "**Core checkpoint:**", "Go to **step 8**"):
            self.assertIn(detail, manual)
        for detail in ("Neither extension is required", "at least 15 minutes",
                       "by lab minute 40", "by lab minute 50",
                       "**Only if you attempted the HPA extension:**"):
            self.assertIn(detail, readme)
        hpa = readme.split("## 6.", 1)[1].split("## 7.", 1)[0]
        self.assertIn("--set traffic.loadEnabled=false", hpa)
        self.assertIn("If time runs short, reset the load", hpa)
        recovery = readme.split("## 7.", 1)[1].split("## 8.", 1)[0]
        self.assertIn("does not require HPA", recovery)
        sheet = (ROOT / "docs/completion-sheet.md").read_text()
        core = sheet.split("## Optional HPA observations", 1)[0]
        self.assertEqual(core.count("- [ ]"), 4)
        self.assertNotIn("kubectl -n oke-lab get hpa", core)
        self.assertNotIn("traffic.loadEnabled", core)
        self.assertIn("Manual (4 replicas)", core)
        self.assertIn("Restored (2 replicas)", core)
        self.assertIn("Skipped extensions do not affect this result", sheet)
        self.assertIn("even if the extension was interrupted", sheet)
        instructor = (ROOT / "docs/instructor-guide.md").read_text()
        self.assertIn("No HPA resource, load burst, or automatic scale-in is required", instructor)
        self.assertIn("HPA disabled throughout", instructor)

    def test_beginner_explanations_precede_use_and_alternatives_are_separate(self):
        readme = (ROOT / "README.md").read_text()
        core = readme.split("## Appendix A:", 1)[0]
        self.assertNotIn("https://cloud.oracle.com/containers/clusters/", core)
        self.assertLess(core.index("Your **kubeconfig**"),
                        core.index("oci ce cluster create-kubeconfig"))
        self.assertLess(core.index("Horizontal Pod Autoscaler (HPA)"),
                        core.index("## 1."))
        self.assertIn("ready to observe the application when it starts", core)
        self.assertLess(core.index("called **scraping**"), core.index("Istiod scrape health"))
        self.assertIn("`/work` endpoint performs CPU-intensive calculations", core)
        self.assertIn("Heavier requests do not necessarily mean more requests per second", core)

    def test_provisional_core_schedule_reserves_debrief(self):
        readme = (ROOT / "README.md").read_text()
        schedule = readme.split("## Schedule", 1)[1].split("## Before hands-on", 1)[0]
        intervals = [(int(start), int(end)) for start, end in
                     re.findall(r"^\| (\d+)–(\d+) \|", schedule, re.M)]
        self.assertEqual(intervals, [(0, 10), (10, 28), (28, 40),
                                     (40, 48), (48, 55), (55, 60)])
        self.assertIn("provisional", schedule)
        self.assertIn("beginner pilot", schedule)

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
