# GitLab CI setup

The pipeline runs Terraform formatting and validation, Kubernetes manifest rendering, ShellCheck, and an OCI CLI version check. GitLab security templates are also configured; their scanners require separately approved images. It never creates OCI resources automatically.

`terraform:plan`, `terraform:apply`, and `terraform:destroy` appear only for the default branch and require a manual click. Limit access to these jobs with a protected `main` branch and protected environment.

## Runner requirements

The tool jobs use `container-registry.oracle.com/os/oraclelinux:9`, which the Luna runner accepts. `scripts/ci-tools.sh` installs the tool needed by each disposable Linux x86-64 job: Terraform 1.9.8, kubectl 1.36.1, ShellCheck 0.11.0, or OCI CLI 3.78.0. These are pinned versions, not a promise to track the latest release. Terraform and kubectl downloads are checked against vendor SHA-256 checksum files. OCI CLI is isolated in a Python virtual environment. This does not modify the shared Luna base image or local workstation tools.

Use a GitLab Runner with outbound access to:

- GitLab, to fetch source and report results.
- `registry.terraform.io`, to download Terraform providers and the OKE module.
- `container-registry.oracle.com` and Oracle Linux package repositories, for the base image and packages.
- `releases.hashicorp.com`, `dl.k8s.io`, GitHub release downloads (including redirect hosts), and PyPI/package download hosts, for the pinned tools and dependencies.
- OCI APIs in the selected region, for the manual Terraform jobs.

The runner does not need inbound internet access. Do not use a runner connected to a production network for this lab.

## Toolchain test status

Pipeline [398021](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-bootcamp/-/pipelines/398021) verified the approved image and passed Terraform formatting, Kubernetes rendering, ShellCheck, and OCI CLI installation/version checks. Terraform initialization downloaded OKE module 5.5.1 but failed because the existing module call does not supply its required `oci.home` provider configuration. The infrastructure configuration needs repair and revalidation before deployment; this tool update does not claim a successful plan or deployment.

The GitLab security templates retain their own analyzer images, so changing the default image does not resolve their runner allowlist restriction. An approved analyzer mirror or runner administrator change is still required. A skipped scanner is not a successful security scan.

## Protected, masked CI variables

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

Use **Masked and hidden** visibility for `OCI_PRIVATE_KEY_B64`, and do not enable variable expansion. The job decodes it into a `0600` PEM file only for the duration of the job. The target region, compartment, and Kubernetes version are deliberately not stored in the repository; configure all three as protected variables for the selected tenancy. For OSPA2100, the selected region is `us-phoenix-1`; choose a dedicated OSPA2100 compartment before running a plan or deployment.

Create a dedicated OCI automation user/API key with least-privilege policies. Never store the PEM key, `terraform.tfvars`, Terraform state, or a tenancy credential in the repository.

## Operating the pipeline

1. Push a branch or use **Build → Pipelines → Run pipeline**. The validation and security jobs run automatically.
2. Review the `terraform:plan` job output on the protected `main` branch.
3. Start `terraform:apply` only after reviewing the plan and expected cost.
4. Deploy and validate the application from a suitably equipped runner or a trusted operator workstation.
5. Start `terraform:destroy` after the lab. It removes billable lab infrastructure.

`terraform:apply` and `terraform:destroy` use `-auto-approve` because the GitLab manual-job button is the approval gate. Do not change their rules to run automatically.
