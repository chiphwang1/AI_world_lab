#!/usr/bin/env bash
# The bootstrap exports TF_VAR_private_key_path to the mock Terraform process.
# shellcheck disable=SC2154
set -Eeuo pipefail
trap 'printf "Bootstrap test failed at line %s\n" "$LINENO" >&2' ERR

# Never test with inherited CI credentials, or invoke the real Terraform binary.
if [[ ${1:-} != --isolated ]]; then
  exec env -i PATH="$PATH" bash "$0" --isolated
fi
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
bootstrap="$script_dir/terraform-ci.sh"
[[ ! -e /tmp/oke-api-key.pem && ! -L /tmp/oke-api-key.pem ]] || {
  echo "Tests require /tmp/oke-api-key.pem to be absent; use an isolated container." >&2
  exit 1
}
test_dir=$(mktemp -d)
trap 'rm -rf -- "$test_dir"' EXIT
cd "$test_dir"
mkdir terraform markers
openssl genrsa -out test-key.pem 2048 >/dev/null 2>&1
export TEST_KEY_FILE="$test_dir/test-key.pem" TEST_CALLS="$test_dir/calls"
export TEST_MARKERS="$test_dir/markers" TEST_STATE_JSON='{}'
export CI_API_V4_URL=https://gitlab.example/api/v4 CI_PROJECT_ID=123 CI_JOB_TOKEN=test-token
export TF_VAR_tenancy_ocid=test-tenancy TF_VAR_user_ocid=test-user
export TF_VAR_compartment_ocid=test-compartment TF_VAR_region=us-phoenix-1
export TF_VAR_fingerprint=test-fingerprint TF_VAR_kubernetes_version=v1.36.1

terraform() {
  [[ -z ${TF_VAR_private_key:-} && -z ${OCI_PRIVATE_KEY_B64:-} && -z ${OCI_PRIVATE_KEY:-} ]] || return 90
  [[ -z ${TF_LOG:-} && -z ${TF_LOG_PROVIDER:-} ]] || return 91
  [[ $TF_VAR_private_key_path == /tmp/oke-api-key.pem ]] || return 92
  cmp -s "$TEST_KEY_FILE" "$TF_VAR_private_key_path" || return 93
  [[ $(ls -l "$TF_VAR_private_key_path") == -rw-------* ]] || return 94
  [[ $TF_HTTP_PASSWORD == "$CI_JOB_TOKEN" && $TF_HTTP_USERNAME == gitlab-ci-token ]] || return 95
  [[ $TF_HTTP_LOCK_ADDRESS == "$TF_HTTP_ADDRESS/lock" && $TF_HTTP_UNLOCK_ADDRESS == "$TF_HTTP_ADDRESS/lock" ]] || return 96
  [[ $TF_HTTP_LOCK_METHOD == POST && $TF_HTTP_UNLOCK_METHOD == DELETE ]] || return 97
  printf '%s|%s\n' "$*" "$TF_HTTP_ADDRESS" >> "$TEST_CALLS"
  [[ ${TEST_TF_FAIL:-false} != true ]] || return 98
  if [[ $2 == plan ]]; then
    printf 'mock plan\n' > terraform/lab.tfplan
  elif [[ $2 == show ]]; then
    printf '%s\n' "$TEST_STATE_JSON"
  fi
}
export -f terraform

curl() {
  local address=${!#}
  if [[ -n ${TEST_MARKER_STATUS:-} ]]; then
    printf '%s' "$TEST_MARKER_STATUS"
  elif [[ $* == *'--request POST'* ]]; then
    printf 'closed\n' > "$TEST_MARKERS/${address##*/}"
    printf '201'
  elif [[ -f $TEST_MARKERS/${address##*/} ]]; then
    printf '200'
  else
    printf '404'
  fi
}
export -f curl

success() {
  : > "$TEST_CALLS"
  if ! bash "$bootstrap" "$1" > result.log 2>&1; then
    cat result.log >&2
    echo "Expected $1 to succeed." >&2
    exit 1
  fi
  [[ ! -e /tmp/oke-api-key.pem ]]
  ! grep -q 'PRIVATE KEY' result.log
}
failure() {
  : > "$TEST_CALLS"
  if bash "$bootstrap" "${2:-plan}" > result.log 2>&1; then
    echo "Expected failure: $1" >&2
    exit 1
  fi
  if ! grep -qF "$1" result.log; then
    printf 'Expected diagnostic: %s\n' "$1" >&2
    cat result.log >&2
    exit 1
  fi
  if [[ -s $TEST_CALLS || -e /tmp/oke-api-key.pem ]]; then
    printf 'Unexpected Terraform invocation or leftover key: %s\n' "$1" >&2
    exit 1
  fi
}

failure 'Supply Luna TF_VAR_private_key'
export TF_VAR_private_key
TF_VAR_private_key=$(cat test-key.pem)
export OCI_PRIVATE_KEY=ignored TF_LOG=DEBUG TF_LOG_PROVIDER=DEBUG
success plan
grep -q 'terraform/state/luna-oke-' "$TEST_CALLS"
cp terraform/lab.target original.target
success apply
grep -q 'apply -input=false lab.tfplan' "$TEST_CALLS"
# State selection must survive a new pipeline for the same lab allocation.
export CI_PIPELINE_ID=456
success plan
cmp -s terraform/lab.target original.target
export TF_VAR_region=us-ashburn-1
failure 'Plan target or OCI identity changed' apply
success plan
if cmp -s terraform/lab.target original.target; then
  echo 'Different targets must select different states.' >&2
  exit 1
fi
export TF_VAR_region=us-phoenix-1
export TF_STATE_NAME=ospa2100-phoenix-oke-lab
success plan
grep -q 'terraform/state/ospa2100-phoenix-oke-lab' "$TEST_CALLS"
success apply
success destroy
grep -q 'destroy -input=false -auto-approve' "$TEST_CALLS"
export TF_STATE_NAME=../invalid
failure 'TF_STATE_NAME must contain'
unset TF_STATE_NAME
export OCI_PRIVATE_KEY_B64
OCI_PRIVATE_KEY_B64=$(base64 < test-key.pem)
failure 'Both TF_VAR_private_key and OCI_PRIVATE_KEY_B64'
unset TF_VAR_private_key
success plan
grep -q 'terraform/state/ospa2100-phoenix-oke-lab' "$TEST_CALLS"
success apply
export TF_VAR_user_ocid=different-user
failure 'Plan target or OCI identity changed' apply
export TF_VAR_user_ocid=test-user
mv terraform/lab.target saved.target
failure 'Missing plan artifacts' apply
mv saved.target terraform/lab.target
export OCI_PRIVATE_KEY_B64='not base64!'
failure 'not a valid unencrypted PEM private key'
unset OCI_PRIVATE_KEY_B64
export TF_VAR_private_key='not a PEM key'
failure 'not a valid unencrypted PEM'
TF_VAR_private_key=$(cat test-key.pem)
export TF_VAR_compartment_ocid=''
failure 'TF_VAR_compartment_ocid is missing'
export TF_VAR_compartment_ocid=test-compartment CI_DEBUG_TRACE=true
failure 'Disable CI_DEBUG_TRACE'
unset CI_DEBUG_TRACE

# Luna state follows the recorded launch pipeline, not a pooled compartment.
export LUNA_DEPLOYMENT=1 CI_COMMIT_BRANCH=main CI_DEFAULT_BRANCH=main CI_COMMIT_REF_PROTECTED=true
export CI_PIPELINE_ID=499
OCI_PRIVATE_KEY_B64=$(base64 < test-key.pem)
export OCI_PRIVATE_KEY_B64
unset TF_VAR_private_key
for test_action in plan apply destroy; do
  failure 'Luna requires TF_VAR_private_key' "$test_action"
done
export TF_VAR_private_key='not a PEM key'
# A valid legacy key must not rescue an invalid Luna key.
failure 'not a valid unencrypted PEM' plan
failure 'not a valid unencrypted PEM' apply
failure 'not a valid unencrypted PEM' destroy
TF_VAR_private_key=$(cat test-key.pem)
# Keep a conflicting, invalid legacy value through plan, apply, and destroy.
# The mock Terraform verifies it receives the Luna key and neither raw secret.
export OCI_PRIVATE_KEY_B64='ignored invalid legacy credential'
unset CI_PIPELINE_ID
failure 'Luna requires CI_PIPELINE_ID'
export CI_PIPELINE_ID=500 CI_COMMIT_REF_PROTECTED=false
failure 'Luna requires the protected default branch'
export CI_COMMIT_REF_PROTECTED=true TF_STATE_NAME=ospa2100-phoenix-oke-lab
failure 'Luna TF_STATE_NAME must match its launch pipeline'
unset TF_STATE_NAME
success plan
grep -q 'terraform/state/luna-oke-500' "$TEST_CALLS"
cp terraform/lab.target luna.target
export CI_JOB_ID=2000
success plan
cmp -s terraform/lab.target luna.target
success apply
export CI_PIPELINE_ID=501
failure 'Plan target or OCI identity changed' apply
success plan
grep -q 'terraform/state/luna-oke-501' "$TEST_CALLS"
export CI_PIPELINE_ID=500 TEST_MARKER_STATUS=503
failure 'Cannot check Luna session closure'
failure 'Cannot record Luna session closure' destroy
unset TEST_MARKER_STATUS
# Cleanup must work without saved plan artifacts, and closed sessions must not
# be recreated by queued/retried jobs even if artifacts no longer exist.
rm -f terraform/lab.tfplan terraform/lab.target
success destroy
[[ -f markers/luna-oke-500-closed ]]
success destroy
success plan
[[ ! -s $TEST_CALLS ]]
success apply
[[ ! -s $TEST_CALLS ]]
export CI_PIPELINE_ID=501
failure 'Missing plan artifacts' apply
success plan
success apply
# An unreadable state must block destroy, not be mistaken for an empty cluster.
export TEST_STATE_JSON='invalid json'
: > "$TEST_CALLS"
if bash "$bootstrap" destroy > result.log 2>&1; then
  echo 'Expected unsafe cleanup to block Terraform destroy.' >&2
  exit 1
fi
if grep -q 'destroy -input=false' "$TEST_CALLS"; then
  echo 'Terraform destroy ran after cleanup failed.' >&2
  exit 1
fi
[[ ! -e /tmp/oke-api-key.pem ]]
export TEST_STATE_JSON='{}'
unset LUNA_DEPLOYMENT OCI_PRIVATE_KEY_B64
# Terraform errors must also remove the materialized key.
export TEST_TF_FAIL=true
if bash "$bootstrap" plan > result.log 2>&1; then
  echo 'Expected Terraform failure.' >&2
  exit 1
fi
[[ ! -e /tmp/oke-api-key.pem ]]
printf 'Terraform CI bootstrap tests passed (mock Terraform; no cloud access).\n'
