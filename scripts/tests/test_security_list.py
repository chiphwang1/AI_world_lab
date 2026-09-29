"""Offline regression checks for the explicitly approved Luna lab policy."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class LabSecurityList(unittest.TestCase):
    def test_single_owner_and_state_migration(self):
        main = (ROOT / "terraform/main.tf").read_text()
        rules = (ROOT / "terraform/security-list.tf").read_text()
        self.assertRegex(main, r"lockdown_default_seclist\s*=\s*null")
        self.assertIn("module.oke.module.vcn[0].oci_core_default_security_list.lockdown[0]", rules)
        self.assertRegex(rules, r"to\s*=\s*oci_core_default_security_list.lab")
        self.assertIn("data.oci_core_vcn.lab.default_security_list_id", rules)

    def test_exact_stateful_rules(self):
        rules = (ROOT / "terraform/security-list.tf").read_text()
        for direction, field, cidr in (("ingress", "source", "10.0.0.0/8"),
                                       ("egress", "destination", "0.0.0.0/0")):
            blocks = re.findall(rf"{direction}_security_rules\s*\{{([^}}]+)\}}", rules)
            self.assertEqual(len(blocks), 1)
            self.assertRegex(blocks[0], rf'{field}\s*=\s*"{re.escape(cidr)}"')
            self.assertRegex(blocks[0], r'protocol\s*=\s*"all"')
            self.assertRegex(blocks[0], r"stateless\s*=\s*false")


if __name__ == "__main__":
    unittest.main()
