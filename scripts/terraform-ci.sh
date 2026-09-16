#!/usr/bin/env bash
# Run from the repository root, inside a disposable CI job container.
# Required TF_VAR_* values are validated through indirect expansion below.
# shellcheck disable=SC2154
set +x
set -euo pipefail
umask 077

fail() { printf '%s\n' "$1" >&2; exit 1; }

action=${1:-}
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
case "$action" in
  plan|apply|destroy) ;;
  *) fail "Usage: bash scripts/terraform-ci.sh plan|apply|destroy" ;;
esac

[[ ${CI_DEBUG_TRACE:-false} != true ]] || fail "Disable CI_DEBUG_TRACE for credential-bearing jobs."
for name in CI_API_V4_URL CI_PROJECT_ID CI_JOB_TOKEN TF_VAR_tenancy_ocid TF_VAR_user_ocid \
  TF_VAR_fingerprint TF_VAR_region TF_VAR_compartment_ocid TF_VAR_kubernetes_version; do
  [[ -n ${!name:-} ]] || fail "$name is missing from this job."
done

if [[ -n ${TF_VAR_private_key:-} && -n ${OCI_PRIVATE_KEY_B64:-} ]]; then
  fail "Both TF_VAR_private_key and OCI_PRIVATE_KEY_B64 are set. Supply exactly one credential source."
elif [[ -n ${TF_VAR_private_key:-} ]]; then
  credential_source=luna
elif [[ -n ${OCI_PRIVATE_KEY_B64:-} ]]; then
  credential_source=base64
else
  fail "Supply Luna TF_VAR_private_key (raw PEM) or OCI_PRIVATE_KEY_B64 (Base64 PEM)."
fi

# Luna starts cleanup in the recorded launch pipeline. Job retries retain its ID.
# Keep non-Luna defaults for existing deployments and explicit recovery jobs.
if [[ ${LUNA_DEPLOYMENT:-0} == 1 ]]; then
  [[ ${CI_PIPELINE_ID:-} =~ ^[0-9]+$ ]] || fail "Luna requires CI_PIPELINE_ID."
  [[ ${CI_COMMIT_REF_PROTECTED:-false} == true && -n ${CI_DEFAULT_BRANCH:-} && ${CI_COMMIT_BRANCH:-} == "$CI_DEFAULT_BRANCH" ]] || fail "Luna requires the protected default branch."
  session_state="luna-oke-${CI_PIPELINE_ID}"
  [[ -z ${TF_STATE_NAME:-} || $TF_STATE_NAME == "$session_state" ]] || fail "Luna TF_STATE_NAME must match its launch pipeline; use a non-Luna recovery job for older states."
  TF_STATE_NAME=$session_state
  export TF_VAR_cluster_name="oke-luna-${CI_PIPELINE_ID}"
elif [[ -z ${TF_STATE_NAME:-} ]]; then
  if [[ $credential_source == luna ]]; then
    target_hash=$(printf '%s\n' "$TF_VAR_tenancy_ocid" "$TF_VAR_compartment_ocid" "$TF_VAR_region" | sha256sum)
    TF_STATE_NAME="luna-oke-${target_hash%% *}"
  else
    TF_STATE_NAME=ospa2100-phoenix-oke-lab
  fi
fi
[[ $TF_STATE_NAME =~ ^[a-zA-Z0-9_-]+$ ]] || fail "TF_STATE_NAME must contain only letters, digits, underscores, or hyphens."

export TF_HTTP_ADDRESS="${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/terraform/state/${TF_STATE_NAME}"
export TF_HTTP_LOCK_ADDRESS="${TF_HTTP_ADDRESS}/lock"
export TF_HTTP_UNLOCK_ADDRESS="${TF_HTTP_ADDRESS}/lock"
export TF_HTTP_USERNAME=gitlab-ci-token TF_HTTP_PASSWORD="$CI_JOB_TOKEN"
export TF_HTTP_LOCK_METHOD=POST TF_HTTP_UNLOCK_METHOD=DELETE TF_HTTP_RETRY_WAIT_MIN=5
export TF_INPUT=0 TF_IN_AUTOMATION=true

# Cleanup is independently playable after a provisioning failure. A companion
# HTTP state records session closure under the same CI resource-group lock.
# This prevents a queued/retried plan or apply from provisioning after cleanup.
if [[ ${LUNA_DEPLOYMENT:-0} == 1 ]]; then
  marker_address="${TF_HTTP_ADDRESS}-closed"
  marker_curl=(curl --silent --show-error --connect-timeout 10 --max-time 60
    --retry 3 --user "$TF_HTTP_USERNAME:$TF_HTTP_PASSWORD"
    --output /dev/null --write-out '%{http_code}')
  if [[ $action == destroy ]]; then
    marker_json=$(python3 -c 'import json, uuid; print(json.dumps({"version":4,"serial":1,"lineage":str(uuid.uuid4()),"outputs":{"session_closed":{"value":True,"type":"bool"}},"resources":[]}))')
    marker_status=$("${marker_curl[@]}" --request POST --header 'Content-Type: application/json' --data-binary "$marker_json" "$marker_address")
    [[ $marker_status == 200 || $marker_status == 201 ]] || fail "Cannot record Luna session closure (HTTP $marker_status); retry cleanup."
  else
    marker_status=$("${marker_curl[@]}" "$marker_address")
    case "$marker_status" in
      200) printf 'Luna session is closed; skipping provisioning.\n'; exit 0 ;;
      404) ;;
      *) fail "Cannot check Luna session closure (HTTP $marker_status)." ;;
    esac
  fi
fi

# A saved plan contains this provider path, so it must be identical in every job.
# Refuse an existing file rather than overwrite it. Each CI job needs its own /tmp.
key_file=/tmp/oke-api-key.pem
(set -o noclobber; : > "$key_file") 2>/dev/null || fail "Credential file already exists; use a fresh disposable job container."
trap 'rm -f -- "$key_file"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [[ $credential_source == luna ]]; then
  printf '%s\n' "$TF_VAR_private_key" > "$key_file"
else
  printf '%s' "$OCI_PRIVATE_KEY_B64" | base64 -d > "$key_file" 2>/dev/null || fail "The supplied credential is not a valid unencrypted PEM private key (check Base64 encoding)."
fi
chmod 600 "$key_file"
openssl pkey -in "$key_file" -passin pass: -noout >/dev/null 2>&1 || fail "The supplied credential is not a valid unencrypted PEM private key."
export TF_VAR_private_key_path="$key_file"
# Use the materialized key for both providers; do not pass raw key variables or
# inherited provider debug logging on to Terraform.
unset TF_VAR_private_key OCI_PRIVATE_KEY_B64 OCI_PRIVATE_KEY TF_LOG TF_LOG_PROVIDER TF_LOG_CORE TF_LOG_PATH

plan_target() {
  printf '%s\n' "$TF_HTTP_ADDRESS" "$TF_VAR_tenancy_ocid" "$TF_VAR_compartment_ocid" \
    "$TF_VAR_region" "$TF_VAR_user_ocid" "$TF_VAR_fingerprint"
}
if [[ $action == apply ]]; then
  [[ -s terraform/lab.tfplan && -s terraform/lab.target ]] || fail "Missing plan artifacts; run terraform:plan in this pipeline first."
  plan_target | cmp -s terraform/lab.target - || fail "Plan target or OCI identity changed. Generate and review a new plan."
fi

printf 'Terraform state: %s\n' "$TF_STATE_NAME"
terraform -chdir=terraform init -input=false -reconfigure
case "$action" in
  plan)
    terraform -chdir=terraform plan -input=false -out=lab.tfplan
    plan_target > terraform/lab.target
    ;;
  apply) terraform -chdir=terraform apply -input=false lab.tfplan ;;
  destroy)
    bash "$script_dir/cleanup-kubernetes.sh"
    terraform -chdir=terraform destroy -input=false -auto-approve
    ;;
esac
