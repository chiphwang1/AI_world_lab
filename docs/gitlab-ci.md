# GitLab CI setup

The pipeline runs Terraform formatting and validation, Kubernetes manifest rendering, ShellCheck, mocked credential/lifecycle tests, and an OCI CLI version check. GitLab security templates are also configured; their scanners require separately approved images.

For `LUNA_DEPLOYMENT=1` on the protected default branch, plan and apply run automatically. The only manual job is cleanup, which Luna starts at session end. Other default-branch pipelines retain manual plan/apply/destroy. Luna jobs are excluded from unprotected branches and non-default branches. Protect `main` and restrict pipeline-trigger/variable permissions: the Luna flag selects behavior and is not an authentication mechanism. If environments are protected, authorize the Luna automation identity for `luna/*` without a deployment-approval requirement; otherwise GitLab can still block automatic deployment.

## Runner requirements

The tool jobs use `container-registry.oracle.com/os/oraclelinux:9`, which the Luna runner accepts. `scripts/ci-tools.sh` installs the tool needed by each disposable Linux x86-64 job: Terraform 1.9.8, kubectl 1.36.1, ShellCheck 0.11.0, or OCI CLI 3.78.0. These are pinned versions, not a promise to track the latest release. Terraform and kubectl downloads are checked against vendor SHA-256 checksum files. OCI CLI is isolated in a Python virtual environment. This does not modify the shared Luna base image or local workstation tools.

Infrastructure jobs require isolated, disposable containers with a private `/tmp` for each job; do not use a shared shell executor. The credential path `/tmp/oke-api-key.pem` must be identical across plan/apply jobs because it is saved in the plan. `scripts/terraform-ci.sh` creates it with mode `0600`, refuses an existing file, validates the PEM without printing it, and removes it on exit. OpenSSL is installed with the Terraform tools.

Use a GitLab Runner with outbound access to:

- GitLab, to fetch source and report results.
- `registry.terraform.io`, to download Terraform providers and the OKE module.
- `container-registry.oracle.com` and Oracle Linux package repositories, for the base image and packages.
- `releases.hashicorp.com`, `dl.k8s.io`, GitHub release downloads (including redirect hosts), and PyPI/package download hosts, for the pinned tools and dependencies.
- OCI APIs in the selected region, for Terraform and cleanup.
- The OKE private Kubernetes API endpoint on TCP 6443, for Service and application cleanup.

The runner does not need inbound internet access. Do not use a runner connected to a production network for this lab.

### Private Kubernetes API access

GitLab infrastructure jobs default `TF_VAR_control_plane_is_public` to `false`. This sets both OKE module inputs, `control_plane_is_public` and `assign_public_ip_to_control_plane`, to `false`: the API endpoint has a private IP in a private subnet. The generated `kubeconfig_command` selects `PRIVATE_ENDPOINT`. The application's public LoadBalancer is unchanged. Standalone Terraform retains its public-endpoint default for existing local rehearsals.

Before launching, the platform administrator must provide a private network path from **both the Luna desktop and the cleanup runner** to the new lab VCN, with return routes and TCP 6443 allowed. The lab default security list allows all protocols from `10.0.0.0/8` and all outbound IPv4 traffic, both stateful. This broad lab-only policy applies to every associated subnet, not just the API endpoint; narrower NSG rules do not restrict these additive allows. For client sources outside that range, set `TF_VAR_control_plane_allowed_cidrs` to a JSON list of the actual routed client source CIDRs for TCP 6443. An allowlist alone does not create connectivity. This stack creates a separate VCN for each session; it does not configure peering, VPN, a bastion, or runner/desktop placement. A VPN that reaches GitLab does not by itself prove access to the lab VCN. See [Oracle's private cluster access requirements](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengdownloadkubeconfigfile.htm).

`terraform/security-list.tf` owns the default list. Its `moved` block migrates the previous VCN-module lockdown resource without replacing the list. Review the plan for an in-place rule update and state-address move only; do not apply a plan that replaces the VCN, cluster, or subnets for this change. No additional infrastructure is created or charged for these rules. Manual live changes require a later reviewed apply to reconcile Terraform state.

After Terraform applies, `scripts/ensure-subnet-security.py --apply` associates that default list with **every subnet in the session VCN**, including the public and internal load-balancer subnets. It preserves existing security-list associations and Kubernetes-managed load-balancer rules, uses ETags to reject concurrent changes, and verifies each association. The apply job fails if permissions or verification fail; rerunning is safe. The provisioning identity needs permission to read VCNs/security lists and update subnets. These association updates happen after the Terraform plan, not inside it; the OKE module ignores changes to subnet security-list associations. For a standalone Terraform deployment, run the same script with explicit `--vcn-id`, `--compartment-id`, and `--region` after applying; omit `--apply` to preview. This covers all subnets present when the script runs; rerun it for subnets added later. It establishes OCI security-rule coverage, not proof of application connectivity or missing routes.

Check for project/group or Luna launch variables overriding `TF_VAR_control_plane_is_public`, and review the plan for `endpoint_config.is_public_ip_enabled = false`. Use a new Luna launch for this configuration; retrying an old pipeline uses its old commit. Do not apply it to an existing cluster without reviewing potential subnet/cluster replacements.

Cleanup reads the actual cluster's endpoint configuration, so it supports both new private clusters and older public clusters. If the runner cannot reach the Kubernetes API, cleanup stops before Terraform destroy; restore connectivity and retry cleanup while the session credentials remain valid. A successful Terraform apply does not verify desktop or cleanup-runner Kubernetes access. Rehearse both before teaching.

## Toolchain test status

Pipeline [398025](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-bootcamp/-/pipelines/398025) passed Terraform initialization and validation after the `oci.home` provider and OKE module interface fixes. Formatting, Kubernetes rendering, and ShellCheck also passed. This is static configuration validation, not a successful OCI plan or deployment.

The OKE module is pinned to 5.5.1. Gateway inputs use `vcn_create_*_gateway = "always"`; managed nodes use `worker_pools` with `mode = "node-pool"` and `size`. The public `node_pool_ids` output is retained but reads the module's `worker_pool_ids`. The existing `create_policies` switch maps to `create_iam_resources`, which controls policies, dynamic groups, and tags. The cluster remains enhanced. Review a representative plan and quota/cost requirements before enabling the lab for learners; Luna applies its saved plan automatically.

The GitLab security templates retain their own analyzer images, so changing the default image does not resolve their runner allowlist restriction. An approved analyzer mirror or runner administrator change is still required. A skipped scanner is not a successful security scan.

## Luna integration

The [Luna ADB example](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/pipeline-examples/create-and-manipulate-adb-example-pipeline/-/blob/main/.gitlab-ci.yml) documents runtime injection of OCI API-key credentials by the Shared Platform. This repository accepts that interface; it does not require authors to download an OCI private key. Terraform still authenticates with the supplied API key.

Configure a private Luna lab with GitLab Content enabled, select this project and its protected default branch, then enable **Provision resources through the Shared Platform** in the lab's Oracle Cloud settings. A trusted launch must supply `LUNA_DEPLOYMENT=1` and these variables together:

| Luna variable | Meaning |
|---|---|
| `TF_VAR_private_key` | Complete, unencrypted PEM private key as a multiline value (not Base64 and not a filename) |
| `TF_VAR_user_ocid` | OCI user associated with that key |
| `TF_VAR_fingerprint` | Matching API-key fingerprint |
| `TF_VAR_tenancy_ocid` | Allocated tenancy |
| `TF_VAR_compartment_ocid` | Allocated lab compartment |
| `TF_VAR_region` | Allocated region |

Also supply `TF_VAR_kubernetes_version` with an OKE-supported version for the allocated region. Luna's `TF_VAR_ssh_pkey`, tenancy name, and compartment name are not needed by this OKE stack. Both OCI providers explicitly use API-key authentication and receive the same materialized key path. No `~/.oci/config` is needed for Terraform.

When `LUNA_DEPLOYMENT=1`, the bootstrap requires Luna's `TF_VAR_private_key` and discards any inherited `OCI_PRIVATE_KEY_B64` from that job's environment. A missing or invalid Luna key fails the job; it never falls back to a legacy key. This applies to plan, apply, and session-end cleanup. Existing project/group credentials can remain available to non-Luna manual jobs, which still reject simultaneous raw and Base64 keys. Disable CI debug tracing and never print environment variables. Ensure the launch overrides any old project/group identity and target variables as a complete set. Restrict who can trigger pipelines or change these values, and keep secrets out of job artifacts.

The documented example is from 2021. The session lifecycle follows the Luna guidance provided for this project: Luna starts the selected branch at session launch, records that pipeline, then starts every manual job in that same pipeline at session termination/expiry with the session variables restored (except `TF_VAR_tims_idcs_access_token`). These platform callbacks still need an end-to-end test. The pipeline does not use that excluded token. Other Luna tokens/passwords are not printed or added to artifacts.

Verify the session identity can create OKE, networking, and workers, read tenancy region subscriptions, list clusters in the session compartment, read cluster details, generate kubeconfig/tokens, and list/delete Kubernetes Services and the lab manifests. When `create_policies=true`, it must also create the module's IAM resources. If Luna restricts IAM creation, administrators must provision the required IAM resources before setting `TF_VAR_create_policies=false`.

At launch, validation is followed by automatic plan and apply. The desktop may become available before the cluster is ready. `terraform:destroy` is optional/manual (`allow_failure: true`), so its waiting state does not block provisioning completion. Luna starts it when the session ends. Never add manual provisioning jobs to a Luna pipeline: the platform would also start them during teardown. Cleanup failures show as warnings because the job is optional; monitor the job itself and retry failures before credentials expire.

Cleanup has no job/artifact dependencies and is playable even after failed or partial provisioning. It first writes a small `luna-oke-<pipeline-id>-closed` companion state through the authenticated GitLab HTTP backend. Plan and apply check this marker and skip provisioning once the session has closed. Marker read/write errors fail the job; retain the marker after cleanup and start a new Luna session to provision again. No Terraform state is stored as a normal job artifact.

With 50 concurrent sessions, the defaults imply up to 50 clusters and 100 worker nodes, plus each cluster's VCN, gateways, volumes, and any learner-created load balancers. Check tenancy quotas, regional shape capacity, runner concurrency, and lab duration. GitLab resource groups are not configured, so separate sessions can start Terraform jobs concurrently; they do not reserve OCI capacity.

## Protected, masked CI variables (direct GitLab use)

The default OCI provider uses `TF_VAR_region` for the cluster. The separate `oci.home` provider discovers the tenancy's home region from OCI region subscriptions and is explicitly passed to the OKE module for home-region operations. No additional home-region secret is required; the automation identity must be able to read its tenancy's region subscriptions. Validation does not query OCI; this lookup occurs during a plan or apply.

Managed worker pools set the OKE node metadata field `areLegacyImdsEndpointsDisabled` to `true`. This is the managed-node-pool API setting that disables IMDSv1; the module's similarly named `worker_legacy_imds_endpoints_disabled` input only reaches self-managed compute resources in the pinned module version.

In **Settings → CI/CD → Variables**, add these variables as protected and masked where GitLab permits masking:

| Variable | Value |
|---|---|
| `TF_VAR_tenancy_ocid` | Test tenancy OCID |
| `TF_VAR_user_ocid` | Terraform service user's OCID |
| `TF_VAR_fingerprint` | API key fingerprint |
| `OCI_PRIVATE_KEY_B64` | Base64 encoding of the entire PEM private key |
| `TF_VAR_region` | Target OCI region |
| `TF_VAR_compartment_ocid` | Dedicated lab compartment OCID |
| `TF_VAR_kubernetes_version` | A version currently supported in the target region |

Use **Masked and hidden** visibility for `OCI_PRIVATE_KEY_B64`, and do not enable variable expansion. The job decodes it into a `0600` PEM file only for the duration of the job. Alternatively, supply the Luna raw-key interface above, but never both. Deployment jobs require explicit region, compartment, and Kubernetes version variables, rather than relying on Terraform defaults. For OSPA2100, the selected region is `us-phoenix-1`; choose a dedicated OSPA2100 compartment before running a plan or deployment.

Create a dedicated OCI automation user/API key with least-privilege policies. Never store the PEM key, `terraform.tfvars`, Terraform state, or a tenancy credential in the repository.

## Operating the pipeline

CI uses the GitLab HTTP backend, with locking and per-job token authentication supplied through environment variables. State selection is:

- Luna jobs use `luna-oke-${CI_PIPELINE_ID}`, scoped by GitLab project. Cleanup and retries in the recorded launch pipeline resolve the identical state. Different sessions get different state even when Luna reuses a compartment. The cluster name is `oke-luna-${CI_PIPELINE_ID}`. A conflicting `TF_STATE_NAME` is rejected, preventing a project-wide override from merging learner states.
- For non-Luna jobs, explicit `TF_STATE_NAME` selects an existing state; only letters, digits, underscores, and hyphens are accepted.
- Non-Luna Base64-key jobs still default to `ospa2100-phoenix-oke-lab`, preserving the original deployment.
- Non-Luna raw-key jobs retain the earlier `luna-oke-<sha256>` default, hashing tenancy OCID, compartment OCID, and region (each followed by a newline). This compatibility path is for existing deployments, not new Luna sessions.

Do not adopt an **existing deployment** through a new Luna launch. Manage/recover it using a non-Luna manual pipeline with `TF_STATE_NAME` explicitly set to its existing state and the original target. This also applies to sessions created before this change using the compartment hash. For recovery of a current session from a new pipeline, use its original `luna-oke-<launch-pipeline-id>` state name, set `TF_VAR_cluster_name=oke-luna-<launch-pipeline-id>`, and use matching target credentials. Set `OKE_ENVIRONMENT=luna/oke-<launch-pipeline-id>` if the original pipeline could still be active. Prefer retrying cleanup in the original launch pipeline, which preserves the closure guard. No existing state is migrated or deleted by this change.

Plan and apply jobs are not interruptible. The plan job saves `lab.tfplan`, `lab.target` (backend/target/identity metadata, without private keys), and its provider lock file as maintainer-only artifacts. Apply consumes the saved plan from the same pipeline and refuses changed backend, target, user, or fingerprint values before initialization. Changing those inputs requires a new plan. Cleanup downloads no artifacts, so it remains independent of their one-day expiry. GitLab resource groups are intentionally not used; separate pipelines can run concurrently. Luna jobs use `luna/oke-${CI_PIPELINE_ID}` as their environment, while ordinary jobs retain `oke-lab-test`. Terraform still locks each backend state, so jobs targeting the same state cannot safely modify it simultaneously.

State must be retained until cleanup completes. Destroy requires credentials for the original tenancy/compartment/region. Keep that access available until cleanup; expired Luna credentials may require platform assistance. Local Terraform use requires HTTP backend credentials; do not switch back to local state for this environment. See [cleanup](cleanup.md) for Kubernetes finalizers and resources created outside Terraform.

Deployment attempt [985964](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-bootcamp/-/jobs/985964) initialized the backend but failed during planning because the OCI provider could not load a proper private-key configuration. No OCI resources were created by that job. The new bootstrap validates either credential input before initialization, but only an authorized live plan can verify OCI authentication and IAM permissions.

For ordinary, non-Luna runs:

1. Push a branch or use **Build → Pipelines → Run pipeline**. The validation and security jobs run automatically.
2. Review the `terraform:plan` job output on the protected `main` branch.
3. Start `terraform:apply` only after reviewing the plan and expected cost.
4. Deploy and validate the application from a suitably equipped runner or a trusted operator workstation.
5. Start `terraform:destroy` after the lab. It removes billable lab infrastructure.

`terraform:apply` executes the saved plan without another prompt; `terraform:destroy` uses `-auto-approve` after Kubernetes cleanup succeeds. For Luna, launching the lab authorizes provisioning and ending the session initiates cleanup. For ordinary pipelines, the manual buttons remain the approval gates.

Run `bash scripts/test-terraform-ci.sh` and `python3 -m unittest discover -s scripts/tests -v` locally (Python tests require PyYAML). They use disposable fixtures and mocked Terraform/OCI/kubectl/HTTP commands, without contacting cloud services. They cover credential handling, session state/closure, pipeline rules, partial-apply cleanup, already-deleted clusters, and failure handling. Run `shellcheck scripts/*.sh` as well. Local initialization was blocked by registry connectivity during development; a passing mock test is not evidence of a successful Luna provisioning/cleanup cycle.
