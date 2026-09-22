"""Offline regression checks for the Luna-to-OKE learner access flow."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ClusterAccessMaterials(unittest.TestCase):
    def test_login_precedes_cluster_and_kubeconfig_steps(self):
        readme = (ROOT / "README.md").read_text()
        headings = ["### Find your lab login and compartment",
                    "### Open your own cluster in the OCI Console",
                    "### Generate your kubeconfig in the Luna terminal"]
        positions = [readme.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        login = readme[positions[0]:positions[1]]
        for label in ("Luna Lab", "OCI Console", "Credentials", "Oracle Cloud", "Compartment Name"):
            self.assertIn(label, login)
        self.assertIn("stop and ask the instructor", login)

    def test_browser_login_does_not_replace_cli_authentication(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("Signing in to the Console does **not** authenticate the terminal", readme)
        self.assertIn('export KUBECONFIG="$HOME/.kube/oke-lab"', readme)
        self.assertIn("Do not add `--overwrite`", readme)
        self.assertIn("Example page only—not a shared student cluster", readme)
        self.assertIn("bash scripts/check-ready.sh --context", readme)

    def test_access_guide_and_instructor_gate_match_student_flow(self):
        access = (ROOT / "docs/cluster-access.md").read_text()
        instructor = (ROOT / "docs/instructor-guide.md").read_text()
        self.assertIn("../README.md#find-your-lab-login-and-compartment", access)
        self.assertIn("Use the cluster OCID and region from your assigned cluster's Console access command", access)
        self.assertIn("verify an actual Luna session exposes", instructor)
        self.assertIn("browser login alone is insufficient", instructor)


if __name__ == "__main__":
    unittest.main()
