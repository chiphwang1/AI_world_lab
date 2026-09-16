"""Lifecycle regression tests; no OCI, Kubernetes, or GitLab calls are made."""

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cleanup_target", ROOT / "scripts/cleanup-target.py")
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


def state_for(compartment="session-compartment"):
    return {"values": {"root_module": {"child_modules": [{"resources": [{
        "mode": "managed", "type": "oci_containerengine_cluster",
        "values": {"id": "session-cluster", "compartment_id": compartment},
    }]}]}}}


class RulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text())

    def matched_rule(self, job, variables):
        rules = self.config[job].get("rules", self.config[".oci_terraform"]["rules"])
        for rule in rules:
            matches = []
            for term in rule["if"].split(" && "):
                match = re.fullmatch(r'\$(\w+) (==|!=) (?:"([^"]*)"|\$(\w+))', term)
                self.assertIsNotNone(match, f"Unsupported rule expression: {term}")
                left, operator, literal, right = match.groups()
                equal = variables.get(left, "") == (literal if literal is not None else variables.get(right, ""))
                matches.append(equal if operator == "==" else not equal)
            if all(matches):
                return rule
        return None

    def test_only_cleanup_is_manual_for_luna(self):
        variables = dict(LUNA_DEPLOYMENT="1", CI_COMMIT_BRANCH="main", CI_DEFAULT_BRANCH="main", CI_COMMIT_REF_PROTECTED="true")
        for name in ("terraform:plan", "terraform:apply"):
            rule = self.matched_rule(name, variables)
            self.assertEqual(rule["when"], "on_success")
            self.assertEqual(rule["variables"]["OKE_RESOURCE_GROUP"], "luna-oke-$CI_PIPELINE_ID")
        rule = self.matched_rule("terraform:destroy", variables)
        self.assertEqual(rule["when"], "manual")
        self.assertTrue(rule["allow_failure"])
        self.assertEqual(rule["variables"]["OKE_ENVIRONMENT"], "luna/oke-$CI_PIPELINE_ID")
        self.assertEqual(self.config["terraform:destroy"]["needs"], [])
        self.assertNotIn("dependencies", self.config["terraform:destroy"])

    def test_other_runs_stay_manual_and_luna_unprotected_runs_are_excluded(self):
        for luna, branch, protected, expected in (
            ("", "main", "true", "manual"),
            ("0", "main", "true", "manual"),
            ("1", "main", "false", None),
            ("1", "feature", "true", None),
            ("", "feature", "false", None),
        ):
            for job in ("terraform:plan", "terraform:apply", "terraform:destroy"):
                with self.subTest(luna=luna, branch=branch, protected=protected, job=job):
                    rule = self.matched_rule(job, dict(LUNA_DEPLOYMENT=luna, CI_COMMIT_BRANCH=branch, CI_DEFAULT_BRANCH="main", CI_COMMIT_REF_PROTECTED=protected))
                    self.assertEqual(rule["when"] if rule else None, expected)


MOCK_TOOL = '''#!{python}
import json, os, pathlib, sys
tool = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["CALL_LOG"], "a") as stream:
    stream.write(json.dumps([tool, *args]) + "\\n")
if tool == "terraform":
    print(os.environ["STATE_JSON"])
elif tool == "oci" and args[:3] == ["ce", "cluster", "list"]:
    if os.environ.get("FAIL_AT") == "oci-list": sys.exit(1)
    print(os.environ["OCI_JSON"])
elif tool == "oci":
    assert os.environ["OCI_CLI_AUTH"] == "api_key"
    assert os.environ["OCI_CLI_KEY_FILE"] == "/dummy/key"
    pathlib.Path(args[args.index("--file") + 1]).write_text("mock kubeconfig")
elif "get" in args:
    if os.environ.get("FAIL_AT") == "kubectl-get": sys.exit(1)
    print(os.environ["SERVICES_JSON"])
elif os.environ.get("FAIL_AT") == "kubectl-delete":
    sys.exit(1)
'''


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        for tool in ("terraform", "oci", "kubectl"):
            path = self.directory / tool
            path.write_text(MOCK_TOOL.format(python=sys.executable))
            path.chmod(0o755)
        self.log = self.directory / "calls"
        self.env = {
            "PATH": f'{self.directory}:{os.environ["PATH"]}',
            "CALL_LOG": str(self.log),
            "STATE_JSON": json.dumps(state_for()),
            "OCI_JSON": json.dumps({"data": [{"id": "session-cluster", "lifecycle-state": "ACTIVE"}]}),
            "SERVICES_JSON": json.dumps({"items": [
                {"metadata": {"namespace": "oke-lab", "name": "hello-oke"}, "spec": {"type": "LoadBalancer"}},
                {"metadata": {"namespace": "learner", "name": "custom-lb"}, "spec": {"type": "LoadBalancer"}},
                {"metadata": {"namespace": "default", "name": "kubernetes"}, "spec": {"type": "ClusterIP"}},
            ]}),
            "TF_VAR_compartment_ocid": "session-compartment",
            "TF_VAR_user_ocid": "dummy-user", "TF_VAR_fingerprint": "dummy-fingerprint",
            "TF_VAR_tenancy_ocid": "dummy-tenancy", "TF_VAR_region": "us-phoenix-1",
            "TF_VAR_private_key_path": "/dummy/key",
        }

    def run_cleanup(self):
        result = subprocess.run(["bash", str(ROOT / "scripts/cleanup-kubernetes.sh")], cwd=ROOT, env=self.env, capture_output=True, text=True)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        return result, calls

    def test_partial_apply_without_outputs_cleans_both_lab_and_learner_load_balancers(self):
        result, calls = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        deletes = [call for call in calls if call[0] == "kubectl" and "delete" in call]
        self.assertEqual(len(deletes), 3)
        self.assertIn("hello-oke", deletes[0])
        self.assertIn("custom-lb", deletes[1])
        for call in deletes:
            self.assertIn("--wait=true", call)
            self.assertIn("--timeout=600s", call)
        create = next(call for call in calls if "create-kubeconfig" in call)
        self.assertFalse(Path(create[create.index("--file") + 1]).exists())

    def test_empty_state_is_a_successful_noop(self):
        self.env["STATE_JSON"] = "{}"
        result, calls = self.run_cleanup()
        self.assertEqual(result.returncode, 0)
        self.assertEqual([call[0] for call in calls], ["terraform"])

    def test_already_deleted_cluster_skips_kubernetes(self):
        self.env["OCI_JSON"] = '{"data": []}'
        result, calls = self.run_cleanup()
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("kubectl", [call[0] for call in calls])

    def test_wrong_compartment_blocks_cleanup(self):
        self.env["STATE_JSON"] = json.dumps(state_for("another-session"))
        result, calls = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_changed_region_in_saved_target_blocks_cleanup(self):
        state = state_for()
        state["values"]["outputs"] = {"deployment_target": {"value": {
            "tenancy_ocid": "dummy-tenancy", "compartment_ocid": "session-compartment",
            "region": "us-ashburn-1",
        }}}
        self.env["STATE_JSON"] = json.dumps(state)
        result, calls = self.run_cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_api_errors_and_stuck_finalizers_fail_closed(self):
        for failure in ("oci-list", "kubectl-get", "kubectl-delete"):
            with self.subTest(failure=failure):
                self.log.write_text("")
                self.env["FAIL_AT"] = failure
                result, calls = self.run_cleanup()
                self.assertNotEqual(result.returncode, 0)
                if failure == "oci-list":
                    self.assertNotIn("kubectl", [call[0] for call in calls])

    def test_multiple_clusters_are_rejected(self):
        state = state_for()
        module = state["values"]["root_module"]["child_modules"][0]
        module["resources"] *= 2
        with self.assertRaises(ValueError):
            selector.cluster_target(state, "session-compartment")


if __name__ == "__main__":
    unittest.main()
