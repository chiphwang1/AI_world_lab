# Repository Guidelines

## Project Structure & Module Organization

This lab provisions Oracle Kubernetes Engine (OKE) and deploys a small HTTP echo application.

- `terraform/`: cluster configuration, providers, HTTP backend, variables, outputs, and example inputs. The OKE module is pinned in `main.tf`.
- `kubernetes/`: Kustomize configuration, namespace, Deployment, and LoadBalancer Service for `hello-oke` in `oke-lab`.
- `scripts/`: live-cluster validation and disposable CI tool installation.
- `docs/`: monitoring exercises, cleanup, troubleshooting, and GitLab CI setup.
- `.gitlab-ci.yml`: validation, security scanning, and manual infrastructure jobs.

There is no application source tree, asset bundle, or dedicated unit-test suite; the workload uses a published container image.

## Build, Test, and Development Commands

Run these checks from the repository root:

```bash
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
kubectl kustomize kubernetes
shellcheck scripts/validate-lab.sh scripts/ci-tools.sh
```

These check formatting, initialize dependencies without the backend, validate Terraform, render manifests, and lint Bash. Use `terraform -chdir=terraform fmt -recursive` to format changes.

With an authorized cluster and kubeconfig, deploy using `kubectl apply -k kubernetes`, then run `bash scripts/validate-lab.sh` to check nodes, rollout, events, and HTTP reachability. There is no separate build step. Run `scripts/ci-tools.sh` only in disposable CI environments; it installs system tools.

## Coding Style & Naming Conventions

Use two-space indentation in Terraform and Kubernetes YAML, following surrounding files. Let `terraform fmt` align HCL assignments. Use `snake_case` for Terraform variables and outputs, and lowercase hyphenated Kubernetes resource names. Keep selectors and `app.kubernetes.io/name` labels consistent. Bash scripts use `set -euo pipefail`; quote variable expansions and pass ShellCheck.

## Testing Guidelines

Run the static checks above before submitting changes. No coverage threshold is configured. For deployment changes, report live validation when available; static validation does not prove a successful OCI deployment. Report skipped or blocked security scans explicitly.

## Commit & Pull Request Guidelines

Follow existing commit subjects such as `fix(ci): reject missing deployment keys`, `fix(terraform): ...`, and `docs: ...`. Keep commits focused. Pull requests should describe the change, relevant issues, validation results, and infrastructure or cost implications. Include reviewed plan details for infrastructure changes without exposing secrets.

## Security & Configuration

Never commit credentials, local `.tfvars`, state, or saved plans. Follow `docs/gitlab-ci.md` for protected variables and HTTP backend access; retain shared state. Keep plan, apply, and destroy jobs manual. Follow `docs/cleanup.md` to remove Kubernetes resources before destroying infrastructure.
