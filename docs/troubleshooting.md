# Troubleshooting

## Learner checks

Use your Luna desktop's `KUBECONFIG=$HOME/.kube/oke-lab` and confirm the context. Do not troubleshoot against a shared or production cluster.

| Symptom | Check / next step |
|---|---|
| Desktop ready, but no cluster | Infrastructure may still be provisioning. Ask the instructor for the Luna pipeline status; do not run Terraform yourself. |
| `Forbidden` when installing charts | Istio/Kiali require cluster-level permissions. Ask the instructor to grant the approved lab access; do not alter tenancy IAM yourself. |
| App pods have no `istio-proxy` | Check `kubectl get namespace oke-lab --show-labels` for `istio-injection=enabled`, then restart only the lab app and traffic Deployments. Check injector events if still absent. |
| Helm reports an existing resource ownership conflict | Do not use `--take-ownership`. Ask the instructor to remove the legacy Kustomize exercise before Helm installation. |
| Empty Kiali graph | Enable `traffic.enabled=true`, check traffic logs, select `oke-lab`, and allow one or two minutes with a five-minute graph window. Confirm proxies are injected. |
| Traffic pod shows `ImageInspectError` | Describe the pod. If it reports an ambiguous short image name, use the fully qualified `docker.io/curlimages/curl:8.14.1`. After a failed Helm upgrade, explicitly set `traffic.enabled=true` again when retrying; `--reuse-values` may not include values from the failed attempt. |
| Kiali cannot reach Prometheus | Check `kubectl -n istio-system get pods,svc` for `prometheus-server`; its URL is in `helm/values/kiali.yaml`. |
| Kiali page will not load | Keep port-forwarding running and use the browser on the same Luna desktop, at `http://localhost:20001/kiali`. Do not expose an anonymous dashboard publicly. |
| Grafana page will not load | Check `kubectl -n istio-system get deploy/grafana svc/grafana`. Run `kubectl -n istio-system port-forward --address 127.0.0.1 svc/grafana 13000:80` and open `http://127.0.0.1:13000/d/oke-lab` on that same desktop. Restart the forward after a Grafana pod replacement; do not expose it publicly. |
| Grafana opens but the lab dashboard is missing | Confirm step 2 used both `-f helm/values/grafana.yaml` and `--set-file dashboards.default.oke-lab.json=helm/dashboards/oke-lab.json`. Rerun that complete pinned Helm command from the repository root; no manual import or admin login is required. |
| Grafana panels show no data or query errors | Check baseline traffic and Prometheus scrape targets using the commands below. The data source must reach `http://prometheus-server.istio-system.svc.cluster.local:80` from inside the cluster, not workstation localhost. Inspect Grafana/Prometheus pod logs. Missing metrics are not a healthy result. |
| Grafana history or refresh seems wrong | Select Last 30 minutes and 15-second refresh. Prometheus stores only two hours and loses history when its pod is replaced. Restore the repository dashboard via the complete Helm command if its refresh configuration was changed. |
| Grafana proxy count differs from HPA replicas | The panel counts successful application proxy scrapes, excluding the generator; it is not a readiness or desired-replica metric. Allow scrape/discovery and termination delay, then compare `kubectl -n oke-lab get hpa,pods`. |
| Pending dashboard pods | Check events and node capacity, including Grafana's 100m CPU/256Mi memory request. Prometheus and Grafana use ephemeral storage, so no telemetry PVC should be requested. |
| HPA CPU is `<unknown>` | Run `kubectl -n oke-lab describe hpa hello-oke` and `kubectl -n oke-lab top pods --containers`. Allow metrics collection after startup. If metrics remain unavailable, ask the instructor to repair Metrics Server; Kiali's Prometheus cannot replace it. Confirm `web` has a nonzero CPU request. |
| Load does not increase replicas | Confirm `autoscaling.enabled=true`, `traffic.enabled=true`, and `traffic.loadEnabled=true` with `helm get values hello-oke -n oke-lab`. Check traffic logs: the burst ends automatically after five minutes. Inspect current CPU, HPA conditions, and `/work` requests. Do not raise load limits or node counts without the instructor. |
| Need to stop CPU load now | Run `helm upgrade hello-oke ./charts/oke-mesh-app -n oke-lab --reuse-values --set traffic.loadEnabled=false --wait --timeout 10m`. Wait for the traffic rollout. Ctrl+C on a watch does not stop load. |
| HPA adds pods but they remain Pending | Describe the pending pod and check events for insufficient CPU/memory or IP capacity. Six replicas is a maximum, not reserved capacity. Ask the instructor; do not enlarge node pools or quotas yourself. |
| Replicas do not fall immediately | Stop burst mode, confirm CPU has dropped, and allow several minutes for metrics, the 60-second stabilization window, and reconciliation. Inspect HPA events if it remains above two. |
| `/work` returns 429 or times out | Per-pod work concurrency and CPU are capped. Compare success rate and latency under load in Kiali. Stop burst mode and verify baseline `/` requests recover. Persistent failures at baseline need investigation. |
| HPA resets manual replica changes | Do the manual exercise before enabling HPA. To return to manual mode, use `helm upgrade hello-oke ./charts/oke-mesh-app -n oke-lab --reuse-values --set autoscaling.enabled=false --set replicaCount=2 --set traffic.loadEnabled=false --wait --timeout 10m`. |
| OCI console sign-in is unclear | API credentials in `~/.oci/config` are not console credentials. Use Luna's console link/temporary login or ask the instructor. |

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
| Kubernetes version rejected | `oci ce cluster-options get --cluster-option-id all` | Use a version supported by the selected region. |
| Public API is unreachable | Inspect endpoint public-IP assignment and client CIDR rules in the plan | This module requires both `control_plane_is_public=true` and `assign_public_ip_to_control_plane=true`, plus appropriate `control_plane_allowed_cidrs`. |
| Metrics Server add-on fails with `expected 'CertManager'` | OCI add-on work-request errors | Configure `CertManager` alongside `KubernetesMetricsServer`; the module installs that dependency first. |
| Nodes not `Ready` | OCI work requests; `kubectl get nodes` | Check quota, subnet capacity, and node-pool errors. |
| Pod is Pending | `kubectl -n oke-lab describe pod <name>` | Check worker capacity, CNI IP capacity, and quota. |
| Service remains Pending | `kubectl -n oke-lab describe svc hello-oke` | Check Service events, routing, and load-balancer quota. |
| App fails | `kubectl -n oke-lab logs deploy/hello-oke -c web` | Confirm ready endpoints and probe results. |
| No OCI metrics/logs | Cluster observability settings and IAM | Enable Container Insights/log collection and wait for ingestion. |
| Destroy fails | `kubectl get svc -A` | Delete LoadBalancer Services and wait for OCI cleanup, then retry. |
