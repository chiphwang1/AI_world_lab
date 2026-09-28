"""Offline regression checks for the Luna-to-OKE learner access flow."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ClusterAccessMaterials(unittest.TestCase):
    def test_login_precedes_cluster_and_kubeconfig_steps(self):
        readme = (ROOT / "README.md").read_text()
        headings = ["### Find your lab login and compartment",
                    "### Open your own cluster in the OCI Console",
                    "### Verify your kubeconfig"]
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
            "### Verify your kubeconfig", 1)[0]
        for label in ("Developer Services", "Containers & Artifacts", "Kubernetes Clusters (OKE)",
                      "Compartment", "exact **Compartment Name**", "hierarchy"):
            with self.subTest(label=label):
                self.assertIn(label, cluster)
        self.assertNotIn("Compute", cluster)
        self.assertIn("each time", cluster)
        self.assertIn("do not use the tenancy root", cluster)

    def test_browser_login_does_not_replace_cli_authentication(self):
        readme = (ROOT / "README.md").read_text()
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("Console login does not authenticate this terminal", access)
        self.assertIn("[desktop OCI authentication settings](docs/cluster-access.md#generate-your-kubeconfig-on-the-desktop)", readme)
        self.assertIn('export KUBECONFIG="$HOME/.kube/oke-lab"', readme)
        self.assertIn("Do not add `--overwrite`", readme)
        self.assertIn("Example page only—not a shared student cluster", readme)
        self.assertIn("bash scripts/check-ready.sh", readme)

    def test_kubeconfig_is_created_before_commands_only_verification(self):
        readme = (ROOT / "README.md").read_text()
        creation, remainder = readme.split("### Verify your kubeconfig", 1)
        self.assertIn("Copy and **run** the displayed `oci ce cluster create-kubeconfig` command", creation)
        self.assertIn('Change `--file` to `"$HOME/.kube/oke-lab"`', creation)
        self.assertIn('`umask 077` and `mkdir -p "$HOME/.kube"`', creation)
        verification = remainder.split("### Check cluster readiness", 1)[0]
        blocks = re.findall(r"```bash\n(.*?)```", verification, re.S)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].splitlines(), [
            'export KUBECONFIG="$HOME/.kube/oke-lab"',
            'ls -l "$KUBECONFIG" &&',
            'test -s "$KUBECONFIG" &&',
            'kubectl config get-contexts &&',
            'kubectl config current-context',
        ])
        self.assertEqual(re.sub(r"```bash\n.*?```", "", verification, flags=re.S).strip(), "")

    def test_access_guide_and_instructor_gate_match_student_flow(self):
        access = (ROOT / "docs/cluster-access.md").read_text()
        instructor = (ROOT / "docs/instructor-guide.md").read_text()
        self.assertIn("../README.md#find-your-lab-login-and-compartment", access)
        self.assertIn("Use the cluster OCID and region from your assigned cluster's Console access command", access)
        self.assertIn("verify an actual Luna session exposes", instructor)
        self.assertIn("browser login alone is insufficient", instructor)

    def test_setup_runs_once_and_new_dashboard_terminals_select_the_same_file(self):
        readme = (ROOT / "README.md").read_text()
        core = readme.split("## Appendix A:", 1)[0]
        export = 'export KUBECONFIG="$HOME/.kube/oke-lab"'
        self.assertEqual(core.count(export), 3)
        self.assertEqual(core.split("## 2.", 1)[0].count(export), 1)
        self.assertEqual(core.count("bash scripts/check-ready.sh"), 1)
        self.assertEqual(core.count("bash scripts/prepare-charts.sh --check"), 1)
        self.assertNotIn("LAB_CONTEXT", readme)
        self.assertNotIn("kubectl --context", core)
        for service, ports in (("kiali", "20001:20001"), ("grafana", "13000:80")):
            self.assertIn(f"{export}\nkubectl -n istio-system port-forward "
                          f"--address 127.0.0.1 svc/{service} {ports}", core)
        self.assertIn("selected context stays saved in the file until changed", readme)
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("repeat `use-context` only when you need to switch it", access)


if __name__ == "__main__":
    unittest.main()
