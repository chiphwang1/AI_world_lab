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

    def test_browser_login_does_not_replace_cli_authentication(self):
        readme = (ROOT / "README.md").read_text()
        access = (ROOT / "docs/cluster-access.md").read_text()
        self.assertIn("Console login does not authenticate this terminal", access)
        self.assertIn("[desktop OCI authentication settings](docs/cluster-access.md#generate-your-kubeconfig-on-the-desktop)", readme)
        self.assertIn('export KUBECONFIG="$HOME/.kube/oke-lab"', readme)
        self.assertIn("Do not add `--overwrite`", readme)
        self.assertIn("Example page only—not a shared student cluster", readme)
        self.assertIn("bash scripts/check-ready.sh --context", readme)

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


if __name__ == "__main__":
    unittest.main()
