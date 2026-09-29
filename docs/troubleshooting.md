# Troubleshooting

## Learner checks

Use your Luna desktop's `KUBECONFIG=$HOME/.kube/oke-lab` and confirm the context. Do not troubleshoot against a shared or production cluster.

| Symptom | Check / next step |
|---|---|
| Desktop ready, but no cluster | Infrastructure may still be provisioning. Ask the instructor for the Luna pipeline status; do not run Terraform yourself. |
| `no context exists`, wrong cluster, or missing kubeconfig | Follow [cluster access](cluster-access.md#verify-the-selected-file-and-context). Check `KUBECONFIG` and `kubectl config get-contexts` in the affected terminal; changing directories does not select a cluster. |
| Authentication works in one terminal but fails in another | Use the same kubeconfig and OCI credential configuration in each terminal. For named profiles, generate the kubeconfig with `--with-auth-context`; a custom `OCI_CLI_CONFIG_FILE` setting must also be supplied in new terminals. Never print keys or generated tokens. |
| GitHub says repository not found or requests credentials | The repository is private. Ask for the instructor-arranged GitHub access or prepared checkout; do not spend the lab configuring an unrelated account. |
| LoadBalancer has an IP but HTTP fails | OCI backends may still be becoming healthy. Wait 15–30 seconds and retry step 3's HTTP command. If requests still fail after a minute, check `kubectl -n oke-lab describe svc hello-oke` and ready app pods with the instructor. |
| `Forbidden` when installing charts | Istio/Kiali require cluster-level permissions. Ask the instructor to grant the approved lab access; do not alter tenancy IAM yourself. |
| App pods appear to have no `istio-proxy` | Inspect both `spec.containers` and `spec.initContainers` using step 3's command: a native sidecar is listed under init containers and keeps running. If absent from both, check `istio-injection=enabled` on `oke-lab` and injector events with the instructor before restarting only the lab app/traffic Deployments. |
| Helm reports an existing resource ownership conflict | Do not use `--take-ownership`. Ask the instructor to remove the legacy Kustomize exercise before Helm installation. |
| Empty Kiali graph | Enable `traffic.enabled=true`, check traffic logs, select `oke-lab`, and allow one or two minutes with a five-minute graph window. Confirm proxies are injected. |
| Kiali shows Degraded or Not Ready | Inspect the indicator's details, pod readiness, restart counts, and request errors using the [health checks below](#kiali-shows-degraded-or-not-ready). Do not assume a liveness failure or restart pods based only on the badge. |
| Traffic pod shows `ImageInspectError` | Describe the pod. If it reports an ambiguous short image name, use the fully qualified `docker.io/curlimages/curl:8.14.1`. After a failed Helm upgrade, explicitly set `traffic.enabled=true` again when retrying; `--reuse-values` may not include values from the failed attempt. |
| Kiali cannot reach Prometheus | Check `kubectl -n istio-system get pods,svc` for `prometheus-server`; its URL is in `helm/values/kiali.yaml`. |
| Kiali or Grafana page will not load | Follow the README's [port-forward troubleshooting in Luna](https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps#troubleshooting-dashboard-port-forwards): inspect local listeners, test HTTP access, confirm the context, and restart only the affected forward. Offline, scroll to the same heading in README Appendix A. Use the browser on the same workstation. |
| Port-forward reports `address already in use` | Identify the listener with `lsof` or `ss` using the [README commands in Luna](https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps#troubleshooting-dashboard-port-forwards). Reuse a working lab forward, stop your broken forward with Ctrl+C in its own terminal, or use a free alternative port (`20002` for Kiali; `13001` for Grafana). Update the browser URL; do not kill unrelated processes. |
| Grafana opens but the lab dashboard is missing | Confirm step 2 used both `-f helm/values/grafana.yaml` and `--set-file dashboards.default.oke-lab.json=helm/dashboards/oke-lab.json`. Rerun that complete pinned Helm command from the repository root; no manual import or admin login is required. |
| Grafana repeatedly loses browser access | Check restart count, last termination reason, and memory using [Grafana memory checks](#grafana-memory-and-repeated-restarts). A working health endpoint between crashes does not prove stability. |
| Grafana panels show no data or query errors | Check baseline traffic and Prometheus scrape targets using the commands below. The data source must reach `http://prometheus-server.istio-system.svc.cluster.local:80` from inside the cluster, not workstation localhost. Inspect Grafana/Prometheus pod logs. Missing metrics are not a healthy result. |
| Grafana history or refresh seems wrong | Select Last 30 minutes and 15-second refresh. Prometheus stores only two hours and loses history when its pod is replaced. Restore the repository dashboard via the complete Helm command if its refresh configuration was changed. |
| Grafana proxy count differs from HPA replicas | The panel counts successful application proxy scrapes, excluding the generator; it is not a readiness or desired-replica metric. Allow scrape/discovery and termination delay, then compare `kubectl -n oke-lab get hpa,pods`. |
| Pending dashboard pods | Check events and node capacity, including Grafana's 100m CPU/512Mi memory request. Prometheus and Grafana use ephemeral storage, so no telemetry PVC should be requested. |
| HPA CPU is `<unknown>` | Run `kubectl -n oke-lab describe hpa hello-oke` and `kubectl -n oke-lab top pods --containers`. Allow metrics collection after startup. If metrics remain unavailable, ask the instructor to repair Metrics Server; Kiali's Prometheus cannot replace it. Confirm `web` has a nonzero CPU request. |
| Load does not increase replicas | Confirm `autoscaling.enabled=true`, `traffic.enabled=true`, and `traffic.loadEnabled=true` with `helm get values hello-oke -n oke-lab`. Check traffic logs: the burst ends automatically after five minutes. Inspect current CPU, HPA conditions, and `/work` requests. Do not raise load limits or node counts without the instructor. |
| Need to stop CPU load now | Run `helm upgrade hello-oke ./charts/oke-mesh-app -n oke-lab --reuse-values --set traffic.loadEnabled=false --wait --timeout 10m`. Wait for the traffic rollout. Ctrl+C on a watch does not stop load. |
| HPA adds pods but they remain Pending | Describe the pending pod and check events for insufficient CPU/memory or IP capacity. Six replicas is a maximum, not reserved capacity. Ask the instructor; do not enlarge node pools or quotas yourself. |
| Replicas do not fall immediately | Stop burst mode, confirm CPU has dropped, and allow several minutes for metrics, the 60-second stabilization window, and reconciliation. Inspect HPA events if it remains above two. |
| `/work` returns 429 or times out | Per-pod work concurrency and CPU are capped. Compare success rate and latency under load in Kiali. Stop burst mode and verify baseline `/` requests recover. Persistent failures at baseline need investigation. |
| HPA resets manual replica changes | Do the manual exercise before enabling HPA. To return to manual mode, use `helm upgrade hello-oke ./charts/oke-mesh-app -n oke-lab --reuse-values --set autoscaling.enabled=false --set replicaCount=2 --set traffic.loadEnabled=false --wait --timeout 10m`. |
| OCI console sign-in is unclear | API credentials in `~/.oci/config` are not console credentials. Use Luna's console link/temporary login or ask the instructor. |

## Kiali shows Degraded or Not Ready

Kiali combines pod status and request traffic when calculating resource health. A traffic problem can remain even when every pod is Ready; a new pod can be Running before it is Ready. **Degraded is not a Kubernetes probe result.** Hover over the indicator, record its details and time, and check which resource it describes. See [Kiali health indicators](https://kiali.io/docs/features/health/).

In terminal 1, with your assigned lab context selected, run these read-only checks:

```bash
kubectl -n oke-lab get deployments hello-oke hello-oke-traffic
kubectl -n oke-lab get pods -o wide
kubectl -n oke-lab describe pods -l app=hello-oke
kubectl -n oke-lab get events --sort-by=.lastTimestamp
```

Compare the evidence:

- **Readiness:** a failed readiness check can keep a pod out of normal Service traffic without restarting it. Look for `Readiness probe failed`, the failing container, and the pod's current Ready condition. Old warning events can remain after recovery; compare their timestamps with current readiness.
- **Liveness:** consecutive failures reaching the configured threshold trigger a container restart. Look for liveness-failure and restart events, `Restart Count`, and `Last State`. A restart alone does not prove a liveness failure; inspect the termination reason and previous container logs.
- **Startup:** when configured, a startup probe gives a container time to initialize before its readiness/liveness checks run. Reaching its failure threshold also triggers a restart. The app chart does not define a startup probe for `web`; the injected Istio proxy has its own health checks. Do not confuse a proxy startup warning with an app liveness failure. See the [Kubernetes probe configuration guide](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/).
- **Traffic:** inspect response codes and success rate in Kiali. HTTP errors can make traffic unhealthy even with all pods Ready. Refresh the page and keep a recent graph window; historical errors may remain visible within that window. Do not dismiss persistent baseline failures as startup noise.

The app's readiness and liveness probes both target `/healthz`. Istio can rewrite application probes in the injected pod, so the live paths/ports may differ from the chart. Inspect the container and probe details before attributing a failure to the app or proxy. See [Istio probe rewriting](https://istio.io/latest/docs/ops/configuration/mesh/app-health-check/).

If pods remain unready, restarts increase, or baseline requests keep failing, record the evidence and ask the instructor. Do not disable probes, delete pods, or reinstall monitoring to clear the warning. These checks are an as-needed troubleshooting branch, not an extra mandatory exercise in the 60-minute lab.

### Rehearsal example: observed symptoms versus confirmed causes

During the September 21, 2026 rehearsal, scaling `hello-oke` from two to four replicas produced brief startup/readiness warnings on new pods, including a connection refusal on proxy health port `15021` and HTTP `500` readiness responses. Later, all four app pods were `2/2` Ready with zero restarts. Kiali then reported the app and generator Healthy, with approximately 0.5 requests/second and HTTP `200` responses.

This supports temporary startup/readiness issues during scaling, **not a confirmed explanation of the earlier Degraded badge**: its original details were not captured. There was no observed app liveness-triggered restart.

Grafana was a separate symptom: its local port-forward had stopped, while the recovered Grafana container was Ready and its health endpoint returned `database: ok`. The first observation showed exit code `137` and reason `Error`, which alone did not establish an out-of-memory kill or a liveness failure. A later clean-reset rehearsal captured `OOMKilled` with the original 512Mi container limit. That confirmed a memory kill for that restart, not the cause of every earlier disconnect. Restart an exited localhost forward after its pod is healthy; do not treat a browser connection failure as proof that the application is unhealthy.

## Grafana memory and repeated restarts

Use the three read-only commands under [Grafana repeatedly stops responding in Appendix A](https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps#grafana-repeatedly-stops-responding). Offline, scroll to that heading in the README. If the current pod has restarted, also inspect its previous container logs:

```bash
kubectl -n istio-system logs deployment/grafana -c grafana --previous --tail=80
kubectl -n istio-system get events --sort-by=.lastTimestamp
```

`--previous` has no logs when that container has not restarted. A new pod also starts its own restart count at zero; compare pod names and creation times. `kubectl top` is a point-in-time sample and can miss the peak that triggered a kill.

The revised lab values request 512Mi memory, cap the container at 1Gi, and set `GOMEMLIMIT=512MiB`. The Go setting is a soft runtime target, not a total-process or Kubernetes limit; plugins, mappings, and other memory need headroom. See the [Go memory-limit guide](https://go.dev/doc/gc-guide#Memory_limit). An extra node does not change the container cap. The scheduler instead uses resource requests when placing pods; see [Kubernetes resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

Instructor: record the live resources and termination reason before changing values. Apply a reviewed values change with the complete pinned Grafana command in step 2, then reopen any forward that lost its pod. Check refreshes and restart counts through load and scale-in, not only `/api/health` immediately after startup. Do not disable readiness/liveness probes to hide a restart or claim a memory leak from exit code 137 alone.

## Check Prometheus scrape targets

To check Istio metrics, run this in a separate desktop terminal:

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
kubectl -n istio-system port-forward --address 127.0.0.1 svc/prometheus-server 9090:80
```

Open `http://localhost:9090/targets` on that desktop. The `istio-workloads` targets should be up. In Prometheus, query `istio_requests_total`; after generating traffic, there should be samples for `hello-oke`. If targets are down, inspect pod ports, network access, and `helm/values/prometheus.yaml`. Stop the port-forward with Ctrl+C.

## Instructor / infrastructure checks

| Symptom | Check | Typical fix |
|---|---|---|
| Terraform cannot download dependencies | Network/proxy and Terraform version | Configure a corporate proxy or provider mirror, then retry. |
| Kubernetes version rejected | `oci ce cluster-options get --cluster-option-id all --region "$LAB_REGION"` (set `LAB_REGION` to the deployment region first) | Use a version supported by the selected region and the intended OCI profile. |
| Public API is unreachable | Inspect endpoint public-IP assignment and client CIDR rules in the plan | This module requires both `control_plane_is_public=true` and `assign_public_ip_to_control_plane=true`, plus appropriate `control_plane_allowed_cidrs`. |
| Private API is unreachable from Luna or cleanup | Check `PRIVATE_ENDPOINT` in kubeconfig, private routes in both directions, and TCP 6443 rules | GitLab defaults to a private endpoint. The platform must connect the desktop and cleanup runner to the lab VCN and allow their source CIDRs; a kubeconfig or GitLab VPN connection alone is insufficient. Do not switch to public access to bypass the failure. |
| Metrics Server add-on fails with `expected 'CertManager'` | OCI add-on work-request errors | Configure `CertManager` alongside `KubernetesMetricsServer`; the module installs that dependency first. |
| Nodes not `Ready` | OCI work requests; `kubectl get nodes` | Check quota, subnet capacity, and node-pool errors. |
| Pod is Pending | `kubectl -n oke-lab describe pod <name>` | Check worker capacity, CNI IP capacity, and quota. |
| Service remains Pending | `kubectl -n oke-lab describe svc hello-oke` | Check Service events, routing, and load-balancer quota. |
| App fails | `kubectl -n oke-lab logs deploy/hello-oke -c web` | Confirm ready endpoints and probe results. |
| No OCI metrics/logs | Cluster observability settings and IAM | Enable Container Insights/log collection and wait for ingestion. |
| Destroy fails | `kubectl get svc -A` | Delete LoadBalancer Services and wait for OCI cleanup, then retry. |
