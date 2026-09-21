# Maintainer-only infrastructure workflow

Learners use the [Luna walkthrough](../README.md). Luna creates the cluster; learners install Helm releases. Do not give learners Terraform state, deployment keys, or CI job tokens.

For authorized maintainers running outside Luna, configure the OCI provider inputs and protected HTTP backend described in [CI setup](gitlab-ci.md), then:

Before planning, verify the tenancy behind your OCI profile, resolve the intended compartment, and query the selected region's Kubernetes versions and node-pool shapes. On 2026-09-18, the `ospa2100` profile resolved to `ospatraining2100`, and `oke-bootcamp` was active in `us-phoenix-1`. That region offered Kubernetes `v1.36.1` and `VM.Standard.E5.Flex`; the repository's default `VM.Standard.E4.Flex` was absent from both Compute and OKE shape lists. Set `node_shape` explicitly for this deployment as shown in the example. A listed shape does not guarantee quota or capacity.

Set `control_plane_allowed_cidrs` to the public egress CIDRs of the operator, CI runner, and learner desktops that need Kubernetes access. Use `/32` for a single fixed IPv4 address. The default empty list denies external API access even though the API has a public IP. For CI/Luna, supply `TF_VAR_control_plane_allowed_cidrs` as a JSON list. Include cleanup-runner access so Kubernetes load balancers can be removed before cluster teardown.

The stack enables the OKE `KubernetesMetricsServer` add-on and its required `CertManager` dependency for the HPA exercise. Verify `kubectl top nodes` after provisioning; installing Prometheus alone does not provide the resource metrics API.

The pinned OKE module requires both `control_plane_is_public = true` and `assign_public_ip_to_control_plane = true` for a public API endpoint. A public subnet alone does not allocate that endpoint; verify `endpoint_config.is_public_ip_enabled` in the plan.

Local deployment requires `TF_HTTP_ADDRESS`, matching lock/unlock addresses, `TF_HTTP_LOCK_METHOD=POST`, `TF_HTTP_UNLOCK_METHOD=DELETE`, and securely supplied `TF_HTTP_USERNAME`/`TF_HTTP_PASSWORD`. Use the existing GitLab project and state name (`ospa2100-phoenix-oke-lab` for this maintainer deployment). Do not replace the HTTP backend with local state to bypass missing credentials. Inspect any existing state and review the plan for replacements before applying. The state and saved plan can contain sensitive values.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit local inputs; never commit them. Configure backend credentials securely.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=lab.tfplan
# Review the saved plan, target, replacements, and ongoing cost before applying.
terraform apply lab.tfplan
```

Connect using `oci ce cluster create-kubeconfig` with the resulting cluster ID, allocated region, `--file`, `--token-version 2.0.0`, and `--kube-endpoint PUBLIC_ENDPOINT`. Select the intended OCI profile and authentication mode and pass `--with-auth-context` so subsequent token generation uses that identity. For this workstation run, select `--profile ospa2100 --auth api_key`; the default profile points at a different tenancy. The `kubeconfig_command` output uses a dedicated `$HOME/.kube/oke-lab` file. Export that path as `KUBECONFIG` and verify the context before following the learner instructions. See [Oracle's cluster access instructions](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengdownloadkubeconfigfile.htm).

Deploy the Helm application from the learner walkthrough; do not also apply `kubernetes/`, which uses the same names. Run `bash scripts/validate-lab.sh` to check node readiness, rollout, and public HTTP reachability. It waits for the load balancer address and retries HTTP while OCI backends become healthy. Then rehearse Kiali traffic, Grafana's provisioned dashboard, manual scaling, and HPA scale-out/scale-in. Verify Grafana refreshes and displays the complete burst/recovery history, and compare its proxy count with actual HPA replicas. A passing static check does not validate these live exercises.

Infrastructure destroy remains a maintainer responsibility. Follow [cleanup](cleanup.md) to delete Kubernetes-created load balancers before destroying their cluster/network. Retain remote state.

## Separate rehearsal without GitLab

With explicit authorization for a new, independent rehearsal, use a separate Git-ignored `.oci-local/terraform/` directory with a local backend and a unique cluster name. Reference the repository's `main.tf`, `provider.tf`, `variables.tf`, and `outputs.tf` there; do not include its `backend.tf`. Keep the repository's HTTP backend and any existing shared state unchanged. Never adopt an existing shared deployment into this empty local state.

The 2026-09-18 rehearsal uses that layout and `.oci-local/rehearsal.tfvars`. Its local README contains the exact commands and credential configuration. Keep `.oci-local/terraform/terraform.tfstate` and its backups until cleanup completes; deleting the working directory does not delete OCI resources. Do not run concurrent operations against local state.

For this workstation rehearsal, Chicago IAM endpoints timed out during TLS connection. The local inputs set `create_policies=false` to avoid module IAM creation. This is specific to the managed-node lab with Oracle-managed encryption and existing provisioning permissions; it does not grant missing permissions or replace IAM setup for custom load-balancer NSGs, KMS, self-managed nodes, or other configurations. Verify the actual plan and live provisioning results before reusing this override.
