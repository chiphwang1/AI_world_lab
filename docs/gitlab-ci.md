# GitLab CI setup

The pipeline runs Terraform formatting and validation, Kubernetes manifest rendering, ShellCheck, credential-bootstrap tests with mock Terraform, and an OCI CLI version check. GitLab security templates are also configured; their scanners require separately approved images. It never creates OCI resources automatically.

`terraform:plan`, `terraform:apply`, and `terraform:destroy` appear only for the default branch and require a manual click. Limit access to these jobs with a protected `main` branch and protected environment.

## Runner requirements

The tool jobs use `container-registry.oracle.com/os/oraclelinux:9`, which the Luna runner accepts. `scripts/ci-tools.sh` installs the tool needed by each disposable Linux x86-64 job: Terraform 1.9.8, kubectl 1.36.1, ShellCheck 0.11.0, or OCI CLI 3.78.0. These are pinned versions, not a promise to track the latest release. Terraform and kubectl downloads are checked against vendor SHA-256 checksum files. OCI CLI is isolated in a Python virtual environment. This does not modify the shared Luna base image or local workstation tools.

Infrastructure jobs require isolated, disposable containers with a private `/tmp` for each job; do not use a shared shell executor. The credential path `/tmp/oke-api-key.pem` must be identical across plan/apply jobs because it is saved in the plan. `scripts/terraform-ci.sh` creates it with mode `0600`, refuses an existing file, validates the PEM without printing it, and removes it on exit. OpenSSL is installed with the Terraform tools.

Use a GitLab Runner with outbound access to:

- GitLab, to fetch source and report results.
- `registry.terraform.io`, to download Terraform providers and the OKE module.
- `container-registry.oracle.com` and Oracle Linux package repositories, for the base image and packages.
- `releases.hashicorp.com`, `dl.k8s.io`, GitHub release downloads (including redirect hosts), and PyPI/package download hosts, for the pinned tools and dependencies.
- OCI APIs in the selected region, for the manual Terraform jobs.

The runner does not need inbound internet access. Do not use a runner connected to a production network for this lab.

## Toolchain test status

Pipeline [398025](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-bootcamp/-/pipelines/398025) passed Terraform initialization and validation after the `oci.home` provider and OKE module interface fixes. Formatting, Kubernetes rendering, and ShellCheck also passed. This is static configuration validation, not a successful OCI plan or deployment.

The OKE module is pinned to 5.5.1. Gateway inputs use `vcn_create_*_gateway = "always"`; managed nodes use `worker_pools` with `mode = "node-pool"` and `size`. The public `node_pool_ids` output is retained but reads the module's `worker_pool_ids`. The existing `create_policies` switch maps to `create_iam_resources`, which controls policies, dynamic groups, and tags. The unsupported workload-identity toggle was removed; the cluster remains enhanced. Review actual IAM and infrastructure changes in a plan before applying.

The GitLab security templates retain their own analyzer images, so changing the default image does not resolve their runner allowlist restriction. An approved analyzer mirror or runner administrator change is still required. A skipped scanner is not a successful security scan.

## Luna integration

The [Luna ADB example](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/pipeline-examples/create-and-manipulate-adb-example-pipeline/-/blob/main/.gitlab-ci.yml) documents runtime injection of OCI API-key credentials by the Shared Platform. This repository accepts that interface; it does not require authors to download an OCI private key. Terraform still authenticates with the supplied API key.

Configure the Luna lab to use this GitLab project and its protected default branch, then enable **Provision resources through the Shared Platform** in the lab's Oracle Cloud settings. A trusted launch must supply these variables together:

| Luna variable | Meaning |
|---|---|
| `TF_VAR_private_key` | Complete, unencrypted PEM private key as a multiline value (not Base64 and not a filename) |
| `TF_VAR_user_ocid` | OCI user associated with that key |
| `TF_VAR_fingerprint` | Matching API-key fingerprint |
| `TF_VAR_tenancy_ocid` | Allocated tenancy |
| `TF_VAR_compartment_ocid` | Allocated lab compartment |
| `TF_VAR_region` | Allocated region |

Also supply `TF_VAR_kubernetes_version` with an OKE-supported version for the allocated region. Luna's `TF_VAR_ssh_pkey`, tenancy name, and compartment name are not needed by this OKE stack. Both OCI providers explicitly use API-key authentication and receive the same materialized key path. No `~/.oci/config` is needed for Terraform.

Remove a project/group `OCI_PRIVATE_KEY_B64` variable from the Luna job's scope before using injection. The bootstrap rejects jobs containing both raw and Base64 keys, rather than silently choosing one. Disable CI debug tracing and never print environment variables. Ensure the launch overrides any old project/group identity and target variables as a complete set. Restrict who can trigger pipelines or change these values, and keep secrets out of job artifacts.

The documented example is from 2021: verify the current Luna launch actually supplies this interface and that its identity can create OKE, networking, and worker resources. It must also read tenancy region subscriptions and, when `create_policies = true`, create the module's IAM resources. If Luna restricts IAM creation, administrators must provision the required IAM resources before setting `TF_VAR_create_policies=false`.

Plan, apply, and destroy remain manual on the default branch. A Luna-triggered pipeline therefore waits for operator approval; this is not unattended lab provisioning. Do not enable the lab for unattended participants until its launch/timeout behavior has been verified with these approval gates.

## Protected, masked CI variables (direct GitLab use)

The default OCI provider uses `TF_VAR_region` for the cluster. The separate `oci.home` provider discovers the tenancy's home region from OCI region subscriptions and is explicitly passed to the OKE module for home-region operations. No additional home-region secret is required; the automation identity must be able to read its tenancy's region subscriptions. Validation does not query OCI; this lookup occurs during a plan or apply.

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

- An explicit `TF_STATE_NAME` selects an existing or deliberately named state; only letters, digits, underscores, and hyphens are accepted.
- Base64-key jobs default to the existing `ospa2100-phoenix-oke-lab` state, preserving the original deployment.
- Luna raw-key jobs default to `luna-oke-<sha256>`, hashing the tenancy OCID, compartment OCID, and region, each followed by a newline. This supports one OKE deployment per project/tenancy/compartment/region. Retries and cleanup use the same state; different allocated compartments use different states. For multiple independent clusters in the same compartment/region, supply distinct stable `TF_STATE_NAME` values.

When switching an **existing deployment** to Luna credentials, explicitly set `TF_STATE_NAME` to its existing state name (for the original deployment, `ospa2100-phoenix-oke-lab`) and keep the original target. Changing credentials must not move existing infrastructure to an empty state. Never point a newly allocated lab at another lab's state. No state migration or deletion is performed by this update.

Plan and apply jobs are not interruptible. The plan job saves `lab.tfplan`, `lab.target` (backend/target/identity metadata, without private keys), and its provider lock file as maintainer-only artifacts. Apply consumes the saved plan from the same pipeline and refuses changed backend, target, user, or fingerprint values before initialization. Changing those inputs requires a new reviewed plan. All infrastructure jobs retain the shared `oke-lab-test` resource group, serializing jobs across lab targets as well as using backend locks.

State must be retained until cleanup completes. Destroy requires credentials for the original tenancy/compartment/region and the same state selection, even in a later pipeline. Keep that access available until cleanup; expired Luna credentials may require platform assistance. Local Terraform use requires HTTP backend credentials; do not switch back to local state for this environment.

Deployment attempt [985964](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-bootcamp/-/jobs/985964) initialized the backend but failed during planning because the OCI provider could not load a proper private-key configuration. No OCI resources were created by that job. The new bootstrap validates either credential input before initialization, but only an authorized live plan can verify OCI authentication and IAM permissions.

1. Push a branch or use **Build → Pipelines → Run pipeline**. The validation and security jobs run automatically.
2. Review the `terraform:plan` job output on the protected `main` branch.
3. Start `terraform:apply` only after reviewing the plan and expected cost.
4. Deploy and validate the application from a suitably equipped runner or a trusted operator workstation.
5. Start `terraform:destroy` after the lab. It removes billable lab infrastructure.

`terraform:apply` executes the saved plan without another prompt; `terraform:destroy` uses `-auto-approve`. The GitLab manual-job button is the approval gate. Do not change their rules to run automatically.

Run `bash scripts/test-terraform-ci.sh` locally to check raw/Base64 credential handling, cleanup, state selection, and plan-target checks. It uses a generated disposable key and mock Terraform in an environment cleared of inherited credentials, without contacting OCI or GitLab. Include both new scripts in ShellCheck.
