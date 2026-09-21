# Phoenix rehearsal — 2026-09-18

The cluster and Helm lab were deployed using local Terraform, without GitLab. The user explicitly authorized a separate local-state rehearsal; the repository's HTTP backend and any existing shared state were left unchanged.

## Verified with OCI

- Profile `ospa2100`, API-key authentication, resolves to tenancy `ospatraining2100`.
- Compartment `oke-bootcamp` is active. The target region `us-phoenix-1` is subscribed; the tenancy home region is `us-chicago-1`.
- OKE lists Kubernetes `v1.36.1`, `VM.Standard.E5.Flex`, compatible Oracle Linux 8 images, and the `KubernetesMetricsServer` add-on.
- `VM.Standard.E4.Flex` is absent from both Compute and OKE shape lists in this region. The example inputs now select E5 explicitly; the Terraform variable default remains unchanged for existing deployments.
- Preflight reported available VCN, enhanced-cluster, and E5 capacity quotas. Actual cluster, worker, and load-balancer creation succeeded.
- Created `oke-bootcamp-rehearsal-20260918`: enhanced cluster, two private E5 workers at 1 OCPU/16 GB each, 50-GB boot volumes, and VCN-native networking. Cluster and VCN lists were empty before this run. Remote Terraform state has not been inspected or modified.

## Issues found and fixed

The OKE cluster and troubleshooting skills guided module inspection and live pod/event evidence collection. Diagnostic helpers were unavailable at their referenced paths, so scoped OCI/kubectl commands were used directly.

- Exposed `control_plane_allowed_cidrs` with IPv4 CIDR validation. Populate it before applying; its empty default denies external API access.
- The plan showed `is_public_ip_enabled=false` despite a public control-plane subnet. Added the module's separate `assign_public_ip_to_control_plane=true`; the deployed API is reachable.
- Enabled the managed Metrics Server add-on and its Cert Manager dependency. OCI initially rejected Metrics Server with `Invalid addon dependencies, expected 'CertManager'`. The corrected add-on apply succeeded, and resource metrics work.
- The traffic pod on `10.0.154.61` failed with `ImageInspectError`: `short name mode is enforcing, but image name curlimages/curl:8.14.1 returns ambiguous list`. Qualified it as `docker.io/curlimages/curl:8.14.1`; the replacement generated successful requests. Also qualified the Python and legacy echo image names. Confidence: high (10/10), based on the explicit runtime error and successful corrected rollout.
- Corrected the kubeconfig output to use `--file`, a dedicated lab file, public endpoint selection, and preserved OCI authentication context, consistent with [Oracle's access instructions](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengdownloadkubeconfigfile.htm).
- Added bounded readiness waits and HTTP retries to `scripts/validate-lab.sh`, plus four regression tests covering delayed HTTP readiness and failures.
- Updated maintainer instructions and Phoenix example inputs. Existing learner/chart changes were preserved.

## Validation

| Live check | Result |
|---|---|
| Terraform | Infrastructure created; follow-up plan reports no changes, detailed exit code 0 |
| Nodes and metrics | Two Ready nodes; `kubectl top nodes` and per-container metrics work; metrics APIService Available=True |
| Mesh/monitoring | Istio base/istiod 1.31.0, Prometheus chart 29.30.0, and Kiali chart 2.32.0 deployed |
| Application | Customized message returned through the public OCI load balancer; replicas include healthy Istio proxies |
| Baseline traffic | Approximately 0.49 successful requests/second in Prometheus |
| Kiali | Browser verified application/traffic-generator graph in `oke-lab`, with successful requests |
| Manual scaling | 2 → 4 → 2; all four replicas Ready; ten successful external requests included all four pod names |
| HPA scale-out | Numeric baseline metrics; five-minute CPU burst scaled from 2 to 6 replicas; public HTTP remained available |
| HPA scale-in | Burst stopped automatically; replicas returned from 6 to 2, with CPU back at 1%; burst flag reset to false |
| Pod recovery | Deleted one application pod; a new pod became Ready, two replicas were restored, and the same public Service endpoint returned HTTP success |

OCI cluster creation took 9m17s and worker-pool creation 3m1s. The add-on dependency required a second apply. This is one workstation rehearsal, not a timing guarantee for Luna or concurrent learners.

HPA observations (UTC): the burst began at 17:31:04, scale-out to six was requested at 17:31:40, the traffic log reported automatic burst completion at 17:36:11, and scale-in to two was requested at 17:37:25. All six application replicas became Ready during the burst, while the worker count remained two. Prometheus recorded roughly 9–11 successful requests/second under load. The final deployment settled at two Ready application replicas.

For recovery, pod `hello-oke-5df748f47f-424kd` was deleted and replaced by `hello-oke-5df748f47f-q8brm` on the other worker. Startup/termination readiness warnings appeared during replacement, but the new pod reached 2/2 Ready with zero restarts. The final `scripts/validate-lab.sh` run passed node readiness, application rollout, and public HTTP checks. This verifies recovery and post-recovery reachability, not uninterrupted availability throughout deletion.

Static checks passed: Terraform formatting, initialization and validation, Kustomize rendering, ShellCheck, mocked CI bootstrap checks, 18 Python tests, Helm lint, and chart tests. All nine chart tests passed before the live run. After qualifying image names, six local chart tests passed and three upstream rendering tests were explicitly skipped; those upstream charts were instead installed and checked live.

Security scans were not run: local vulnerability scanners are unavailable, and the GitLab analyzer-image restriction remains unresolved. Functional checks are not a vulnerability assessment. The pinned VCN module emits deprecated `route_rules.cidr_block` warnings with OCI provider 9.2.0; apply and the clean follow-up plan succeeded.

## Follow-up browser verification

A second five-minute load test was started at 17:44:09 UTC using the chart's existing two-worker traffic generator. HPA requested four replicas at 17:44:25 and six at 17:44:41. All six application pods reached 2/2 Ready with zero restarts.

The generator automatically ended its burst at 17:49:08 UTC. Burst mode was then explicitly disabled, CPU returned to 1%, and HPA requested scale-in to two at 17:50:26 UTC. The final HPA current/desired count was two, the application Deployment was 2/2 Ready, and both original worker nodes remained Ready. The complete observed cycle was 2 → 4 → 6 → 2.

Verified directly in the browser:

- Kiali Mesh showed one Istio 1.31.0 control plane and one data-plane namespace on Kubernetes v1.36.1.
- Kiali Workloads showed six application pods and Healthy status after transient scale-out degradation resolved. Its Envoy view contained the application service and inbound application port configuration.
- Kiali Traffic Graph showed the traffic generator reaching the application, with 9.87 requests/second and 100% success in the displayed five-minute window. External HTTP checks also remained successful.
- Prometheus returned `up=1` for Istiod and the baseline workload targets. Its request-rate graph showed the burst, and a separate application-proxy scrape-count graph increased from two to six. This is not a direct HPA replica metric: kube-state-metrics is disabled in this lightweight deployment.
- CLI evidence independently confirmed CPU above the 60% target and HPA current/desired replicas at six; all seven workload proxies were connected to Istiod.

The [monitoring guide](monitoring.md#prometheus-browser-checks-and-repeatable-load) now includes the exact browser queries, localhost access, and bounded start/stop commands. No extra worker nodes or monitoring components were provisioned for this test.

## Grafana extension

Added Grafana chart 13.2.5 (Grafana 13.2.2) in `istio-system`, with a provisioned `OKE Prometheus` data source and **OKE Lab — Traffic & Scaling** dashboard. Browser validation showed populated request-rate, success-rate, proxy-count, Istiod scrape-health, latency, and response-code panels, including the earlier scale-out and scale-in history. Baseline readings were approximately 0.49 requests/second, 100% successful requests, two application proxies, and Istiod `up=1`.

Access: `http://127.0.0.1:13000/d/oke-lab`, while forwarding `svc/grafana` port 80 to localhost 13000. The Deployment was 1/1 Ready. The Service is ClusterIP with no external IP; no PVC, ingress, cluster permissions, or API token mount is requested. Anonymous access is Viewer-only and is for this disposable lab, not production. Anyone with network access to the Service can query its metrics. The chart-generated administrator secret was not printed or committed.

Configuration and dashboard JSON are versioned under `helm/`; the [monitoring guide](monitoring.md#grafana-dashboard) has reinstall instructions. Grafana is ephemeral, but the repository-provisioned dashboard/data source return after replacement. Its extra resources are 100m CPU/256Mi memory requested and 500m CPU/512Mi memory limited on the existing nodes. No cloud infrastructure was added.

Eight focused chart/dashboard tests and 18 Python regression tests passed, along with the repository's Terraform, Kustomize, ShellCheck, and whitespace checks. The first direct chart-test invocation lacked the workspace Helm environment; it passed after sourcing the local environment. Security scans remain unperformed; installing the pinned chart is not a vulnerability assessment.

## Workstation workarounds and limits

- Chicago IAM endpoints timed out during TLS connection. Local inputs use `create_policies=false` for this managed-node lab with Oracle-managed encryption and no custom load-balancer NSGs. Provisioning succeeded with existing permissions; this override does not replace IAM setup for configurations requiring additional policies.
- The Istio chart host was unreachable from this workstation. Downloaded the official [Istio 1.31.0 release](https://github.com/istio/istio/releases/tag/1.31.0), verified its published SHA-256, and installed its bundled base/istiod charts. Prometheus and Kiali used their documented repositories. The [Istio Helm guide](https://istio.io/latest/docs/setup/install/helm/) supports local chart paths.
- After interrupting the failed traffic upgrade, `--reuse-values` did not retain `traffic.enabled=true` from that attempt. Recovery explicitly set the enable flag and qualified image.
- Luna launch/session-end callbacks, automated teardown, concurrent-session capacity, and the classroom schedule remain unverified. Infrastructure destruction was not requested.

## Reuse and ongoing cost

From the repository root:

```bash
source .oci-local/env.sh
kubectl get nodes
bash scripts/validate-lab.sh
terraform -chdir=.oci-local/terraform plan -var-file=../rehearsal.tfvars
```

Credentials, kubeconfig, inputs, logs, and state are under Git-ignored `.oci-local/`. Preserve `.oci-local/terraform/terraform.tfstate` and its backups until cleanup completes. The local working directory links to repository Terraform source files and has its own local backend. Do not manage these resources using an empty GitLab state.

Kiali remains internal. To access it, source the local environment and run `kubectl -n istio-system port-forward --address 127.0.0.1 svc/kiali 20001:20001`, then open `http://localhost:20001/kiali`.

Resources remain running. Ongoing charges include the enhanced cluster, two E5 workers, boot volumes, the flexible 10-Mbps application load balancer, and any billable network usage. No dollar estimate has been verified. Once cleanup is authorized, remove the Kubernetes-created load balancer before destroying the locally managed cluster and network.

## Timed learner-workflow continuation — 2026-09-18 18:18 UTC

This continuation used the existing local-state Phoenix cluster. It did **not** create, upgrade, scale, delete, or otherwise mutate cluster resources. Before timing, the current deployments were inspected: both workers were `Ready`; Metrics Server returned node and pod CPU; the CRD and ClusterRole authorization checks returned `yes`; all five mesh/monitoring releases and the Helm application release were `deployed`; the application had two `2/2 Ready` pods; its HPA was stable at two replicas with `cpu: 1%/60%`; and the LoadBalancer endpoint returned the customized response. Baseline traffic remained enabled and `/work` load remained disabled.

The node image inventories show that this environment has cached the application Python image, traffic-generator curl image, Istio proxy/pilot images, Prometheus, Kiali, and Grafana images. The existing LoadBalancer also already has a public IP. Consequently, the timings below are deliberately separated: the command measurements describe an already-warm cluster, while the learner plan includes an explicit first-time allowance for chart downloads, image pulls, OCI load-balancer readiness, reading, editing, command entry, and result interpretation.

### Measured execution (warm, non-mutating)

| Check | Elapsed |
|---|---:|
| Client tool versions | 1.087 s |
| Nodes, Metrics Server, and authorization checks | 5.907 s |
| Strict chart lint | 0.062 s |
| Application/HPA inventory | 3.033 s |
| Public HTTP response | 0.110 s |
| Traffic-generator log check | 1.527 s |
| `scripts/validate-lab.sh` | 12.312 s |
| **Total sequential command time** | **24.038 s** |

These figures exclude terminal startup, `source .oci-local/env.sh`, reading output, and the long waits that would occur for a fresh install. The validation script passed. They should not be presented as installation or rollout times.

### 60-minute learner plan (first-time estimate)

| Exercise | Measured machine work applicable today | Simulated learner/read/wait allowance | Planned total |
|---|---:|---:|---:|
| Connect and confirm cluster/metrics/RBAC | 7 s | 4 m 53 s | 5 m |
| Install Helm repositories, Istio, Prometheus, Kiali, Grafana | not re-run (already installed/cached) | 18 m (about 7 m learner command/read time, 11 m cold chart/image/readiness allowance) | 18 m |
| Edit, lint, deploy app, wait for LoadBalancer, start baseline traffic | 5 s of lint/inventory/HTTP checks | 10 m 55 s (includes 3 m LB/readiness allowance) | 11 m |
| Open dashboards and interpret baseline traffic | 2 s log check | 5 m 58 s (includes metric accumulation) | 6 m |
| Manual scale, HPA setup, five-minute burst, scale-in observation | not re-run to preserve the stable baseline | 14 m | 14 m |
| Recovery exercise, only if ahead | not re-run to preserve pods | 5 m | 5 m |
| **Total with recovery** | **24.038 s measured health-check subset** | **58 m 46 s modeled learner/wait time** | **59 m, leaving 1 m buffer** |

The five-minute burst fits only if the scale-in observation is bounded: after disabling burst mode, observe the HPA until it requests two replicas, then use the already-open Grafana range to discuss the historical curve. It must not become an open-ended wait for every graph to refresh.

### Recommended adjustments

1. Change the core schedule to 54 minutes plus a six-minute recovery/buffer block. Treat pod recovery as a 5-minute optional activity, not a promised core exercise; the remaining minute absorbs normal command-entry variance.
2. Pre-stage the Helm repositories and, where Luna images are not pre-pulled, pre-pull or allow an instructor-managed 10–11 minute cold-install buffer. The current 20-minute install heading is workable, but only with this buffer and no troubleshooting.
3. Have learners open the editor before the application section and provide the exact `student.yaml` line to change. Reserve 3 minutes of the app segment for OCI LoadBalancer readiness, even though today's assigned endpoint responded in 0.110 seconds.
4. Start dashboard port-forwards while baseline traffic accumulates, rather than serializing those tasks. Require one captured baseline reading, then move on after two minutes; do not wait for a perfect Kiali graph.
5. Place a hard instructor checkpoint after monitoring installation (minute 23) and after application traffic (minute 35). Learners blocked at either checkpoint should receive help rather than independently consuming the scaling block.

The cluster remains in its pre-rehearsal functional state: two Ready application replicas, one Ready traffic-generator pod, HPA minimum/desired replicas of two, baseline requests continuing, and no new cloud or Kubernetes resources created.
