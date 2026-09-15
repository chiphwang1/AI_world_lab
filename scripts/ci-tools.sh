#!/usr/bin/env bash
set -euo pipefail

# Install only into this disposable CI job. Never print credentials.
dnf install -y curl unzip tar xz git python3 python3-pip
mkdir -p /usr/local/bin
task_tmp=$(mktemp -d)
trap 'rm -rf "$task_tmp"' EXIT
cd "$task_tmp"
case "${1:-}" in
  terraform)
    version=1.9.8
    archive="terraform_${version}_linux_amd64.zip"
    curl -fLsS --retry 3 -O "https://releases.hashicorp.com/terraform/$version/$archive"
    curl -fLsS --retry 3 -O "https://releases.hashicorp.com/terraform/$version/terraform_${version}_SHA256SUMS"
    grep " $archive$" "terraform_${version}_SHA256SUMS" | sha256sum -c -
    unzip "$archive"
    install -m 755 terraform /usr/local/bin/terraform
    terraform version
    ;;
  kubectl)
    version=v1.36.1
    curl -fLsS --retry 3 -o kubectl "https://dl.k8s.io/release/$version/bin/linux/amd64/kubectl"
    curl -fLsS --retry 3 -o kubectl.sha256 "https://dl.k8s.io/release/$version/bin/linux/amd64/kubectl.sha256"
    printf '%s  kubectl\n' "$(cat kubectl.sha256)" | sha256sum -c -
    install -m 755 kubectl /usr/local/bin/kubectl
    kubectl version --client
    ;;
  shellcheck)
    curl -fLsS --retry 3 -o shellcheck.tar.xz https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz
    tar -xf shellcheck.tar.xz
    install -m 755 shellcheck-v0.11.0/shellcheck /usr/local/bin/shellcheck
    shellcheck --version
    ;;
  oci)
    python3 -m venv /opt/oci-cli
    /opt/oci-cli/bin/pip install 'oci-cli==3.78.0'
    ln -sf /opt/oci-cli/bin/oci /usr/local/bin/oci
    oci --version
    ;;
  *) echo "Usage: $0 terraform|kubectl|shellcheck|oci" >&2; exit 2 ;;
esac
