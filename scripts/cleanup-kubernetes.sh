#!/usr/bin/env bash
# Invoked by terraform-ci.sh after authenticated backend initialization.
set +x
set -euo pipefail
umask 077
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
: "${TF_VAR_compartment_ocid:?}"

# Read resources, not outputs: outputs may be absent after a partial apply.
# State stays in this pipe and is never printed or uploaded as an artifact.
cluster_id=$(terraform -chdir=terraform show -json | python3 "$script_dir/cleanup-target.py" cluster)
if [[ -z $cluster_id ]]; then
  echo 'No managed OKE cluster in state; proceeding with Terraform cleanup.'
  exit 0
fi

export OCI_CLI_AUTH=api_key OCI_CLI_USER="${TF_VAR_user_ocid:?}"
export OCI_CLI_FINGERPRINT="${TF_VAR_fingerprint:?}" OCI_CLI_TENANCY="${TF_VAR_tenancy_ocid:?}"
export OCI_CLI_REGION="${TF_VAR_region:?}" OCI_CLI_KEY_FILE="${TF_VAR_private_key_path:?}"
unset OCI_CLI_KEY_CONTENT OCI_CLI_SECURITY_TOKEN_FILE

# A failed lookup is not evidence of deletion. Only skip Kubernetes when a
# successful compartment listing confirms the cluster is absent/deleted.
cluster_status=$(oci ce cluster list --compartment-id "$TF_VAR_compartment_ocid" --region "$TF_VAR_region" --all --output json |
  python3 "$script_dir/cleanup-target.py" status "$cluster_id")
if [[ $cluster_status == ABSENT || $cluster_status == DELETED ]]; then
  echo 'OKE cluster is already absent; proceeding with Terraform cleanup.'
  exit 0
fi

cleanup_tmp=$(mktemp -d)
trap 'rm -rf -- "$cleanup_tmp"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
export KUBECONFIG="$cleanup_tmp/kubeconfig"
oci ce cluster create-kubeconfig --cluster-id "$cluster_id" --region "$TF_VAR_region" \
  --file "$KUBECONFIG" --token-version 2.0.0 --kube-endpoint PUBLIC_ENDPOINT >/dev/null

# The session owns this cluster. Include learner-created LoadBalancer Services,
# whose OCI load balancers are not resources in this Terraform state.
services=$(kubectl --request-timeout=30s get services --all-namespaces -o json |
  python3 "$script_dir/cleanup-target.py" services)
while IFS=$'\t' read -r namespace service; do
  [[ -n $namespace && -n $service ]] || continue
  kubectl --request-timeout=30s -n "$namespace" delete service "$service" \
    --ignore-not-found=true --wait=true --timeout=600s
done <<< "$services"

kubectl --request-timeout=30s delete -k "$script_dir/../kubernetes" \
  --ignore-not-found=true --wait=true --timeout=600s
echo 'Kubernetes cleanup completed; proceeding with Terraform destroy.'
