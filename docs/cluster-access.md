# Access your assigned OKE cluster

Use this page if your instructor has not prepared a working kubeconfig, or if selecting the cluster fails. Cluster creation is completed before the student lab. Return to [step 1](../README.md#1-connect-to-your-prepared-cluster--5-minutes) once access works.

## Generate a kubeconfig only when needed

Obtain the current session's cluster OCID, region, expected cluster name, and OCI profile from the instructor. An OCID is OCI's resource identifier. API credentials should already be configured in `~/.oci/config`; do not generate new keys for this exercise. `DEFAULT` is appropriate only if the instructor confirms it identifies this session.

Replace the three placeholders below before running. This example uses the lab's API-key authentication and public Kubernetes endpoint:

```bash
export LAB_REGION='<your-session-region>'
export LAB_CLUSTER_OCID='<your-assigned-cluster-ocid>'
export LAB_OCI_PROFILE='<your-session-profile>'
export KUBECONFIG="$HOME/.kube/oke-lab"
mkdir -p "$HOME/.kube"
oci ce cluster create-kubeconfig --cluster-id "$LAB_CLUSTER_OCID" \
  --region "$LAB_REGION" --file "$KUBECONFIG" \
  --token-version 2.0.0 --kube-endpoint PUBLIC_ENDPOINT \
  --profile "$LAB_OCI_PROFILE" --auth api_key --with-auth-context
```

This writes connection settings for an existing cluster. `--file` selects the destination, and `--with-auth-context` preserves the selected profile and authentication mode for later token generation. If the file already contains contexts, Oracle's command merges the cluster details and selects the added context. Do not add `--overwrite`. See [Oracle's kubeconfig command reference](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/ce/cluster/create-kubeconfig.html) and [cluster access guide](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengdownloadkubeconfigfile.htm).

If your instructor supplies a different OCI config-file location, use that `OCI_CLI_CONFIG_FILE` setting in **every** new terminal. `--with-auth-context` preserves profile/auth choices, not a custom config-file location. Keep OCI CLI installed and credentials available: the kubeconfig invokes `oci ce cluster generate-token` automatically when Kubernetes tools need authentication. You do not run or copy that token yourself.

## Verify the selected file and context

`KUBECONFIG` selects a file; the current context selects an entry inside it. Changing directories does not select a cluster. In each new terminal, set the same kubeconfig path used by the walkthrough:

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
printf 'Kubeconfig: %s\n' "$KUBECONFIG"
kubectl config get-contexts
kubectl config current-context
```

Compare the context with the assignment from the instructor. If the assigned context appears in the list but is not current, copy its exact name:

```bash
kubectl config use-context '<assigned-context-name-from-the-list>'
```

If it is absent, confirm the file path or generate the kubeconfig above. `no context exists` refers to the selected file; the same context may exist in another kubeconfig. After selecting the assigned context, return to the README's read-only preflight check.

For the maintainer's existing local rehearsal, follow [the rehearsal environment instructions](rehearsal-2026-09-18.md#reuse-and-ongoing-cost). That environment uses a dedicated project kubeconfig; its private files are not distributed to learners. When using that path, use it consistently in the dashboard terminals too.

## Optional extension: discover the cluster with OCI CLI

This is outside the 60-minute core workflow. The instructor should supply the cluster OCID or a working kubeconfig so students can skip discovery. For a separate OCI discovery exercise, obtain the session's compartment OCID, region, and profile, then list all pages:

```bash
export LAB_REGION='<your-session-region>'
export LAB_OCI_PROFILE='<your-session-profile>'
export LAB_COMPARTMENT_OCID='<your-session-compartment-ocid>'
oci ce cluster list --compartment-id "$LAB_COMPARTMENT_OCID" \
  --region "$LAB_REGION" --profile "$LAB_OCI_PROFILE" --auth api_key --all \
  --query 'data[].{Name:name,State:"lifecycle-state",OCID:id}' --output table
```

Match the name to your assignment and confirm `ACTIVE`. Do not choose another learner's cluster or infer ownership from `ACTIVE` alone. If the assigned cluster is missing or ambiguous, ask the instructor. Oracle documents pagination and filters in the [cluster list reference](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/ce/cluster/list.html).

## Instructor reference: which OCI commands belong in the lab?

| Command | Purpose | Placement |
|---|---|---|
| `oci --version` | Check the installed CLI | Optional diagnostic; instructor desktop preflight |
| `oci ce cluster list` | Discover an assigned cluster ID | Instructor setup or optional extension outside the hour; also required by cleanup's independent existence check |
| `oci ce cluster create-kubeconfig` | Write Kubernetes connection settings | Setup only if a working file is absent; retain in Terraform's connection output and cleanup automation |
| `oci ce cluster generate-token` | Authenticate Kubernetes requests | Automatic kubeconfig dependency; no manual student command |
| `oci ce cluster-options get --cluster-option-id all --region "$LAB_REGION"` | Check supported cluster options in the target region | Instructor provisioning/troubleshooting only |

The version checks in CI/bootstrap and the OCI calls in `scripts/cleanup-kubernetes.sh` remain maintainer operations. Terraform provisions the cluster and managed add-ons; students do not need OCI create/delete commands for those resources. The Service requests its load balancer through Kubernetes.

During desktop preflight, check the tools before handing over the session:

```bash
oci --version
kubectl version --client
helm version --short
git --version
curl --version
```

Using the learner's identity and assigned cluster context, check permissions before class:

```bash
kubectl auth can-i create customresourcedefinitions.apiextensions.k8s.io
kubectl auth can-i create clusterroles.rbac.authorization.k8s.io
```

Both should return `yes`. These checks assess permission to create Istio's extra resource types and the charts' cluster-level role definitions; they do not create resources or grant access. They cover only two actions, so also verify the complete Helm installation with the learner's identity during rehearsal. Permission checks are instructor preflight, not student exercise steps.

Verify the actual connection, cluster permissions, repository access, and chart/image downloads as well; a version check alone does not prove readiness. See Oracle's [token generation](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/ce/cluster/generate-token.html) and [cluster options](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/ce/cluster-options/get.html) references.
