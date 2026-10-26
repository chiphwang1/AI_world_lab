"""Offline regression checks for the Luna-to-OKE learner access flow."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ClusterAccessMaterials(unittest.TestCase):
    def test_public_api_access_guide_matches_gitlab_default(self):
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("--kube-endpoint PUBLIC_ENDPOINT", access)
        self.assertNotIn("--kube-endpoint PRIVATE_ENDPOINT", access)
        self.assertIn("private network path", access)
        ci = (ROOT / "docs/gitlab-ci.md").read_text()
        for requirement in ("TCP 6443", "cleanup runner", "TF_VAR_control_plane_allowed_cidrs"):
            self.assertIn(requirement, ci)

    def test_login_precedes_cluster_and_kubeconfig_steps(self):
        readme = (ROOT / "README.md").read_text()
        headings = ["### Find your lab login and compartment",
                    "### Open your own cluster in the OCI Console",
                    "### Check cluster readiness"]
        positions = [readme.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        login = readme[positions[0]:positions[1]]
        for label in ("Luna Lab", "OCI Console", "Credentials", "Oracle Cloud", "Compartment Name"):
            self.assertIn(label, login)
        self.assertIn("stop and ask the instructor", login)

    def test_luna_sign_in_has_explicit_credentials_and_paste_steps(self):
        readme = (ROOT / "README.md").read_text()
        login = readme.split("### Find your lab login and compartment", 1)[1].split(
            "### Open your own cluster in the OCI Console", 1)[0]
        for label in ("Luna-Lab", "Quick Links", "User Name", "Password",
                      "Do not use the SSO Link", "Ctrl+V", "Paste", "Sign In",
                      "Lab Details", "region"):
            with self.subTest(label=label):
                self.assertIn(label, login)
        self.assertLess(login.index("OCI Console"), login.index("User Name"))
        self.assertLess(login.index("User Name"), login.index("Sign In"))
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("Do not use the SSO Link", access)
        self.assertIn("Lab Details", access)

    def test_console_selection_uses_oke_and_exact_assigned_compartment(self):
        readme = (ROOT / "README.md").read_text()
        cluster = readme.split("### Open your own cluster in the OCI Console", 1)[1].split(
            "### Check cluster readiness", 1)[0]
        for label in ("Developer Services", "Containers & Artifacts", "Kubernetes Clusters (OKE)",
                      "Compartment", "exact **Compartment Name**", "hierarchy"):
            with self.subTest(label=label):
                self.assertIn(label, cluster)
        self.assertNotIn("Compute", cluster)
        self.assertIn("Use the assigned compartment and region shown in Luna Lab.", cluster)
        self.assertIn("do not use the tenancy root", cluster)

    def test_browser_login_does_not_replace_cli_authentication(self):
        readme = (ROOT / "README.md").read_text()
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("Console login does not authenticate this terminal", access)
        self.assertIn("Do not add `--overwrite`", access)
        self.assertIn("Example page only—not a shared student cluster", readme)
        self.assertIn("bash scripts/check-ready.sh", readme)

    def test_fresh_vm_setup_creates_kubeconfig_then_runs_preflight(self):
        readme = (ROOT / "README.md").read_text()
        creation, remainder = readme.split("### Check cluster readiness", 1)
        self.assertIn("run the displayed commands in order, including `oci ce cluster create-kubeconfig`", creation)
        self.assertIn("`~/.kube/config`", creation)
        self.assertNotIn("prepare the kubeconfig directory", creation)
        self.assertIn("**Public Endpoint**", creation)
        self.assertNotIn("Before running it:", creation)
        self.assertIn("In **terminal 1**, follow the **Local Access** instructions", creation)
        self.assertIn("bash scripts/check-ready.sh", remainder)
        core = readme.split("## Appendix A:", 1)[0]
        for diagnostic in ("unset KUBECONFIG", "kubectl config get-contexts",
                           'ls -l "$HOME/.kube/config"', 'test -s "$HOME/.kube/config"'):
            self.assertNotIn(diagnostic, core)
        access = (ROOT / "docs/cluster-access.md").read_text()
        recovery = access.split("## Verify the selected file and context", 1)[1]
        self.assertIn("**troubleshooting only**", recovery)
        self.assertIn("unset KUBECONFIG", recovery)

    def test_learner_commands_do_not_export_a_kubeconfig_override(self):
        for name in ("README.md", "docs/cluster-access.md", "docs/troubleshooting.md",
                     "docs/monitoring.md", "docs/cleanup.md"):
            with self.subTest(file=name):
                contents = (ROOT / name).read_text()
                blocks = re.findall(r"```(?:bash|sh)?\n(.*?)```", contents, re.S)
                for block in blocks:
                    self.assertNotRegex(block, r"(?m)^\s*export KUBECONFIG=")
                    self.assertNotIn(".kube/oke-lab", block)
        outputs = (ROOT / "terraform/outputs.tf").read_text()
        self.assertIn('$HOME/.kube/config', outputs)
        self.assertNotIn('.kube/oke-lab', outputs)

    def test_access_guide_and_instructor_gate_match_student_flow(self):
        access = (ROOT / "docs/cluster-access.md").read_text()
        instructor = (ROOT / "docs/instructor-guide.md").read_text()
        self.assertIn("../README.md#find-your-lab-login-and-compartment", access)
        self.assertIn("Use the cluster OCID and region from your cluster's Console access command", access)
        self.assertIn("verify an actual Luna session exposes", instructor)
        self.assertIn("browser login alone is insufficient", instructor)

    def test_access_setup_is_in_hands_on_and_context_selection_is_optional(self):
        access = (ROOT / "docs/cluster-access.md").read_text()
        instructor = (ROOT / "docs/instructor-guide.md").read_text()
        self.assertIn("during hands-on [step 1]", access)
        self.assertIn("only that context, no selection command is needed", access)
        self.assertIn("uses the current context without a `--context` argument", access)
        self.assertNotIn("assignment from the instructor", access)
        self.assertIn("do no further setup during the lecture", instructor)
        self.assertIn("Count all step 1 setup within the hands-on hour", instructor)
        self.assertNotIn("setup during the lecture", access)
        self.assertNotIn("clones it during the lecture", instructor)

    def test_students_download_charts_during_hands_on(self):
        readme = (ROOT / "README.md").read_text()
        instructor = (ROOT / "docs/instructor-guide.md").read_text()
        self.assertIn("download the five pinned Helm charts", readme)
        self.assertNotIn("instructor supplies", readme)
        self.assertIn("Students download the charts in hands-on step 1", instructor)
        self.assertNotIn("instructor chart delivery", instructor)

    def test_setup_runs_once_and_new_dashboard_terminals_select_the_same_file(self):
        readme = (ROOT / "README.md").read_text()
        core = readme.split("## Appendix A:", 1)[0]
        self.assertNotIn('unset KUBECONFIG', core)
        self.assertEqual(core.count("bash scripts/check-ready.sh"), 1)
        self.assertEqual(core.count("bash scripts/prepare-charts.sh --check"), 1)
        self.assertNotIn("LAB_CONTEXT", readme)
        self.assertNotIn("kubectl --context", core)
        for service, ports in (("kiali", "20001:20001"), ("grafana", "13000:80")):
            self.assertIn(f"kubectl -n istio-system port-forward "
                          f"--address 127.0.0.1 svc/{service} {ports}", core)
        self.assertIn("All three terminals use the `~/.kube/config` created in step 1", readme)
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("repeat `use-context` only when you need to switch it", access)


if __name__ == "__main__":
    unittest.main()
