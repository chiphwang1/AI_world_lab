"""No-cloud tests for additive VCN-wide security-list associations."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("subnet_security", ROOT / "scripts/ensure-subnet-security.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SubnetSecurity(unittest.TestCase):
    def setUp(self):
        self.subnets = {name: {"id": name, "vcn-id": "vcn", "compartment-id": "comp",
                              "security-list-ids": lists}
                        for name, lists in (("cp", ["default"]), ("workers", ["default"]),
                                            ("public-lb", ["ccm-public"]),
                                            ("internal-lb", ["ccm-internal"]))}
        self.rules = {"vcn-id": "vcn", "ingress-security-rules": [
            {"source": "10.0.0.0/8", "protocol": "all", "is-stateless": False}],
            "egress-security-rules": [
                {"destination": "0.0.0.0/0", "protocol": "all", "is-stateless": False}]}
        self.updates = []

    def call(self, *args):
        if args[:2] == ("vcn", "get"):
            return {"data": {"id": "vcn", "compartment-id": "comp", "default-security-list-id": "default"}}
        if args[:2] == ("security-list", "get"):
            return {"data": copy.deepcopy(self.rules)}
        if args[:2] == ("subnet", "list"):
            self.assertIn("--all", args)
            return {"data": copy.deepcopy(list(self.subnets.values()))}
        name = args[args.index("--subnet-id") + 1]
        if args[1] == "get":
            return {"data": copy.deepcopy(self.subnets[name]), "etag": "version-1"}
        if args[1] == "update":
            import json
            self.assertEqual(args[args.index("--if-match") + 1], "version-1")
            self.assertIn("--wait-for-state", args)
            self.updates.append(name)
            self.subnets[name]["security-list-ids"] = json.loads(args[args.index("--security-list-ids") + 1])
            return {}
        self.fail(f"Unexpected OCI call: {args}")

    def test_all_subnets_covered_without_removing_ccm_lists(self):
        self.assertEqual(MODULE.reconcile(self.call, "vcn", "comp", True), 4)
        self.assertEqual(self.updates, ["public-lb", "internal-lb"])
        self.assertEqual(self.subnets["public-lb"]["security-list-ids"], ["ccm-public", "default"])
        MODULE.reconcile(self.call, "vcn", "comp", True)
        self.assertEqual(len(self.updates), 2)

    def test_preview_does_not_mutate(self):
        MODULE.reconcile(self.call, "vcn", "comp")
        self.assertEqual(self.updates, [])

    def test_wrong_vcn_or_compartment_rejected(self):
        for vcn, compartment in (("other", "comp"), ("vcn", "other")):
            with self.assertRaises(MODULE.SafetyError):
                MODULE.reconcile(self.call, vcn, compartment, True)
        self.assertEqual(self.updates, [])

    def test_stateless_or_missing_rules_rejected(self):
        self.rules["ingress-security-rules"][0]["is-stateless"] = True
        with self.assertRaises(MODULE.SafetyError):
            MODULE.reconcile(self.call, "vcn", "comp", True)
        self.assertEqual(self.updates, [])

    def test_list_limit_rejected_before_any_update(self):
        self.subnets["internal-lb"]["security-list-ids"] = [str(i) for i in range(5)]
        with self.assertRaises(MODULE.SafetyError):
            MODULE.reconcile(self.call, "vcn", "comp", True)
        self.assertEqual(self.updates, [])

    def test_concurrent_update_failure_stops(self):
        def conflict(*args):
            if args[:2] == ("subnet", "update"):
                raise MODULE.SafetyError("ETag conflict")
            return self.call(*args)
        with self.assertRaisesRegex(MODULE.SafetyError, "ETag conflict"):
            MODULE.reconcile(conflict, "vcn", "comp", True)
        self.assertEqual(self.updates, [])


if __name__ == "__main__":
    unittest.main()
