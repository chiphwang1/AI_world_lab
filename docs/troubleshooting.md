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
| Kiali cannot reach Prometheus | Check `kubectl -n istio-system get pods,svc` for `prometheus-server`; its URL is in `helm/values/kiali.yaml`. |
| Kiali page will not load | Keep port-forwarding running and use the browser on the same Luna desktop, at `http://localhost:20001/kiali`. Do not expose an anonymous dashboard publicly. |
| Pending dashboard pods | Check events and node capacity. The lab uses ephemeral Prometheus storage, so no telemetry PVC should be requested. |
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
| Nodes not `Ready` | OCI work requests; `kubectl get nodes` | Check quota, subnet capacity, and node-pool errors. |
| Pod is Pending | `kubectl -n oke-lab describe pod <name>` | Check worker capacity, CNI IP capacity, and quota. |
| Service remains Pending | `kubectl -n oke-lab describe svc hello-oke` | Check Service events, routing, and load-balancer quota. |
| App fails | `kubectl -n oke-lab logs deploy/hello-oke -c web` | Confirm ready endpoints and probe results. |
| No OCI metrics/logs | Cluster observability settings and IAM | Enable Container Insights/log collection and wait for ingestion. |
| Destroy fails | `kubectl get svc -A` | Delete LoadBalancer Services and wait for OCI cleanup, then retry. |
