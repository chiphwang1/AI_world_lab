# Access your assigned OKE cluster

Use this page to obtain your own kubeconfig using the OCI Console, or if selecting the cluster fails. Complete access setup during the lecture, once your assigned cluster is ready, before the 60-minute hands-on clock starts. Return to the README's connection checks in [step 1](../README.md#1-prepare-and-confirm-your-connection--5-minutes). If access remains blocked, ask the instructor before starting the timed exercises.

## Start with your Luna session

Follow [Find your lab login and compartment](../README.md#find-your-lab-login-and-compartment): open the **Luna-Lab** desktop icon (also labeled **Luna Lab**), choose **Quick Links → OCI Console**, and sign in with your assigned username and password from **Credentials**. Do not use the SSO Link. Paste with **Ctrl+V** or right-click **Paste**, then click **Sign In**. Find your assigned region and **Compartment Name** in **Lab Details** or the page's **Oracle Cloud** section. Missing login/session details require instructor help, not Terraform-log inspection or a new personal account.

In the Console, select the assigned region. Open the navigation menu, then **Developer Services → Containers & Artifacts → Kubernetes Clusters (OKE)**. In the **Compartment** filter, expand the hierarchy if needed and select the exact compartment shown on your Luna Lab page. Check the region and compartment each time you open a resource list; do not infer the assignment from a `luna` name prefix. Select your assigned cluster and verify its name and OCID. Open **Actions → Access cluster → Local Access** and copy the displayed command's cluster OCID and region into the example below. Run it in the **Luna desktop's Bash terminal**. Console login does not authenticate this terminal; its OCI CLI identity must already be configured. See [Oracle's cluster access guide](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengdownloadkubeconfigfile.htm).

## Generate your kubeconfig on the desktop

Use the cluster OCID and region from your assigned cluster's Console access command. An OCID is OCI's resource identifier. Confirm the expected cluster name and desktop OCI profile with the instructor. API credentials should already be configured in `~/.oci/config`; do not generate new keys for this exercise. `DEFAULT` is appropriate only if the instructor confirms it identifies this session.

Replace the three placeholders below before running. This example uses the lab's API-key authentication and public Kubernetes endpoint:

```bash
export LAB_REGION='<your-session-region>'
export LAB_CLUSTER_OCID='<your-assigned-cluster-ocid>'
export LAB_OCI_PROFILE='<your-session-profile>'
export KUBECONFIG="$HOME/.kube/oke-lab"
umask 077
mkdir -p "$HOME/.kube"
oci ce cluster create-kubeconfig --cluster-id "$LAB_CLUSTER_OCID" \
  --region "$LAB_REGION" --file "$KUBECONFIG" \
  --token-version 2.0.0 --kube-endpoint PUBLIC_ENDPOINT \
  --profile "$LAB_OCI_PROFILE" --auth api_key --with-auth-context &&
chmod 600 "$KUBECONFIG"
```

This writes connection settings for an existing cluster. `--file` selects the destination, and `--with-auth-context` preserves the selected profile and authentication mode for later token generation. If the file already contains contexts, Oracle's command merges the cluster details and selects the added context. Do not add `--overwrite`. See [Oracle's kubeconfig command reference](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/ce/cluster/create-kubeconfig.html) and [cluster access guide](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengdownloadkubeconfigfile.htm).

If your instructor supplies a different OCI config-file location, use that `OCI_CLI_CONFIG_FILE` setting in **every** new terminal. `--with-auth-context` preserves profile/auth choices, not a custom config-file location. Keep OCI CLI installed and credentials available: the kubeconfig invokes `oci ce cluster generate-token` automatically when Kubernetes tools need authentication. You do not run or copy that token yourself.

## Alternative: browser download through Cloud Shell

Skip this if you generated the file on the desktop above. In the assigned cluster's **Access cluster** dialog, select **Cloud Shell Access → Launch Cloud Shell**. Cloud Shell is a separate machine with its own pre-authenticated OCI CLI.

Run `umask 077`, then run the Console's `create-kubeconfig` command in Cloud Shell with its assigned OCID/region/endpoint, changing only `--file` to `"$HOME/oke-lab-kubeconfig"`. Use a new filename if it already exists. Do not add the desktop's API-key/profile flags or `--with-auth-context`: Cloud Shell authentication settings must not be embedded for desktop use.

Open the Cloud Shell menu at the top left, choose **Download**, enter `oke-lab-kubeconfig`, and click **Download**. Use the browser inside the Luna desktop so the download lands there. Then, in a **desktop terminal**:

```bash
mkdir -p "$HOME/.kube"
cp -i "$HOME/Downloads/oke-lab-kubeconfig" "$HOME/.kube/oke-lab"
chmod 600 "$HOME/.kube/oke-lab"
export KUBECONFIG="$HOME/.kube/oke-lab"
export OCI_CLI_PROFILE='<your-session-profile>'
export OCI_CLI_AUTH=api_key
```

Adjust the source path if the browser used another download directory. If prompted to overwrite a file, answer **no** and ask the instructor which file to retain. File transfers do not preserve permissions. Set the profile/auth variables in **every new desktop terminal** for this alternative, plus the instructor's `OCI_CLI_CONFIG_FILE` if needed. These use the lab's existing desktop credentials; never copy Cloud Shell's `/etc/oci` credentials. See [Oracle's Cloud Shell download and authentication instructions](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/devcloudshellgettingstarted.htm).

A downloaded kubeconfig does not establish network access or grant permissions. A private endpoint requires an instructor-provided private network path; even a public endpoint may restrict source addresses. Do not change endpoint/firewall settings or create credentials to bypass a connection failure.

## Verify the selected file and context

`KUBECONFIG` selects a file; the current context selects an entry inside it. Changing directories does not select a cluster. Set `KUBECONFIG` once in each new terminal, using the same path as the walkthrough; no need to repeat the export between commands:

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

This saves the selection in the kubeconfig. New terminals using that file share the saved context; repeat `use-context` only when you need to switch it. `kubectl config current-context` and the lab preflight check the selection without changing it.

If the assigned context is absent, confirm the file path or generate the kubeconfig above. `no context exists` refers to the selected file; the same context may exist in another kubeconfig. After selecting the assigned context, return to the README's read-only preflight check.

For the maintainer's existing local rehearsal, follow [the rehearsal environment instructions](rehearsal-2026-09-18.md#reuse-and-ongoing-cost). That environment uses a dedicated project kubeconfig; its private files are not distributed to learners. When using that path, use it consistently in the dashboard terminals too.

## Optional extension: discover the cluster with OCI CLI

This is outside the 60-minute core workflow. The main walkthrough obtains the assigned cluster OCID through the Console, so students can skip CLI discovery. For a separate OCI discovery exercise, obtain the session's compartment OCID, region, and profile, then list all pages:

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
| `oci ce cluster create-kubeconfig` | Write Kubernetes connection settings | Console-guided student setup; retain in Terraform's connection output and cleanup automation |
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
