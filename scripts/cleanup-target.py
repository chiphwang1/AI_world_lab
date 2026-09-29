"""Extract only cleanup targets from streamed Terraform/OCI/Kubernetes JSON."""

import json
import os
import sys


def cluster_target(state, compartment):
    target = state.get("values", {}).get("outputs", {}).get("deployment_target", {}).get("value")
    if target is not None and any(
        target.get(key) != os.environ.get(f"TF_VAR_{key}")
        for key in ("tenancy_ocid", "compartment_ocid", "region")
    ):
        raise ValueError("State deployment target differs from the cleanup session.")

    def resources(module):
        yield from module.get("resources", [])
        for child in module.get("child_modules", []):
            yield from resources(child)

    clusters = [
        resource["values"]
        for resource in resources(state.get("values", {}).get("root_module", {}))
        if resource.get("mode") == "managed"
        and resource.get("type") == "oci_containerengine_cluster"
    ]
    if len(clusters) > 1:
        raise ValueError("Multiple managed OKE clusters found; refusing ambiguous cleanup.")
    if not clusters:
        return ""
    cluster = clusters[0]
    if cluster.get("compartment_id") != compartment:
        raise ValueError("State cluster is outside the supplied session compartment.")
    if not cluster.get("id"):
        raise ValueError("State cluster has no ID; refusing ambiguous cleanup.")
    return cluster["id"]


def cluster_status(response, cluster_id):
    matches = [item for item in response["data"] if item["id"] == cluster_id]
    return matches[0]["lifecycle-state"] if matches else "ABSENT"


def cluster_endpoint(response, cluster_id, compartment):
    cluster = response["data"]
    if cluster["id"] != cluster_id or cluster["compartment-id"] != compartment:
        raise ValueError("Endpoint lookup does not match the cleanup target.")
    public = cluster["endpoint-config"]["is-public-ip-enabled"]
    if public is True:
        return "PUBLIC_ENDPOINT"
    if public is False:
        return "PRIVATE_ENDPOINT"
    raise ValueError("Cluster endpoint visibility is unknown.")


def load_balancers(response):
    return "\n".join(
        f'{item["metadata"]["namespace"]}\t{item["metadata"]["name"]}'
        for item in response["items"]
        if item.get("spec", {}).get("type") == "LoadBalancer"
    )


if __name__ == "__main__":
    try:
        payload = json.load(sys.stdin)
        mode = sys.argv[1]
        if mode == "cluster":
            result = cluster_target(payload, os.environ["TF_VAR_compartment_ocid"])
        elif mode == "status":
            result = cluster_status(payload, sys.argv[2])
        elif mode == "endpoint":
            result = cluster_endpoint(payload, sys.argv[2], os.environ["TF_VAR_compartment_ocid"])
        elif mode == "services":
            result = load_balancers(payload)
        else:
            raise ValueError("Unknown cleanup selector.")
        print(result)
    except (ValueError, KeyError, TypeError, IndexError):
        # Never echo malformed state/response contents: state may contain secrets.
        sys.exit("Cannot safely determine cleanup targets; refusing Terraform destroy.")
