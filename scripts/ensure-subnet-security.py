#!/usr/bin/env python3
"""Attach the lab default list to all subnets, preserving existing lists.

Read-only unless --apply is supplied. Uses the caller's OCI CLI credentials.
"""
import argparse
import json
import subprocess
import sys


class SafetyError(RuntimeError):
    pass


def rule_present(rules, field, cidr):
    return any(rule.get(field) == cidr and rule.get("protocol") == "all"
               and rule.get("is-stateless") is False
               and rule.get(field + "-type", "CIDR_BLOCK") == "CIDR_BLOCK"
               for rule in rules)


def reconcile(call, vcn_id, compartment_id, apply=False):
    vcn = call("vcn", "get", "--vcn-id", vcn_id)["data"]
    if vcn.get("id") != vcn_id or vcn.get("compartment-id") != compartment_id:
        raise SafetyError("VCN identity or compartment mismatch")
    default_id = vcn["default-security-list-id"]
    rules = call("security-list", "get", "--security-list-id", default_id)["data"]
    if rules.get("vcn-id") != vcn_id:
        raise SafetyError("Default security list belongs to a different VCN")
    if not (rule_present(rules.get("ingress-security-rules", []), "source", "10.0.0.0/8")
            and rule_present(rules.get("egress-security-rules", []), "destination", "0.0.0.0/0")):
        raise SafetyError("Default list is missing the required stateful rules; apply Terraform first")
    subnets = call("subnet", "list", "--compartment-id", compartment_id,
                   "--vcn-id", vcn_id, "--all")["data"]
    if not subnets:
        raise SafetyError("No subnets found in the target VCN")
    targets = []
    # Validate all associations before making any changes.
    for subnet in subnets:
        if subnet.get("vcn-id") != vcn_id or subnet.get("compartment-id") != compartment_id:
            raise SafetyError("Subnet scope mismatch")
        ids = subnet.get("security-list-ids", [])
        if default_id not in ids and len(ids) >= 5:
            raise SafetyError("A subnet already has five security lists; refusing to replace one")
        targets.append(subnet["id"])
    for subnet_id in targets:
        current = call("subnet", "get", "--subnet-id", subnet_id)
        subnet = current["data"]
        if subnet.get("vcn-id") != vcn_id or subnet.get("compartment-id") != compartment_id:
            raise SafetyError("Subnet scope changed")
        ids = subnet.get("security-list-ids", [])
        if default_id not in ids:
            if len(ids) >= 5 or not current.get("etag"):
                raise SafetyError("Cannot safely update subnet: list limit or missing ETag")
            if not apply:
                print(f"WOULD ADD default security list: {subnet_id}")
                continue
            call("subnet", "update", "--subnet-id", subnet_id,
                 "--security-list-ids", json.dumps(ids + [default_id]),
                 "--if-match", current["etag"], "--force",
                 "--wait-for-state", "AVAILABLE", "--max-wait-seconds", "300")
            verified = call("subnet", "get", "--subnet-id", subnet_id)["data"]
            if not set(ids + [default_id]).issubset(verified.get("security-list-ids", [])):
                raise SafetyError("Subnet verification failed; required or existing list missing")
        print(f"PASS default security list associated: {subnet_id}")
    return len(targets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vcn-id", required=True)
    parser.add_argument("--compartment-id", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    def call(*command):
        result = subprocess.run(["oci", "network", *command, "--region", args.region,
                                 "--output", "json"], capture_output=True, text=True, timeout=360)
        if result.returncode:
            # Do not echo OCI authentication/debug output or credential material.
            raise SafetyError(f"OCI {command[0]} {command[1]} failed; verify permissions and retry")
        return json.loads(result.stdout)

    try:
        count = reconcile(call, args.vcn_id, args.compartment_id, args.apply)
        print(f"{'Verified' if args.apply else 'Inspected'} {count} subnets in the target VCN.")
    except (SafetyError, KeyError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"FAIL subnet security: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
