# Observe the application with Kiali

Complete the [learner walkthrough](../README.md) first: Istio, Prometheus, Kiali, and the Helm application must be installed, with traffic enabled. Use the Luna desktop and your dedicated lab kubeconfig. No Terraform commands are needed.

## Traffic and health

1. Open Kiali through the localhost port-forward in the walkthrough.
2. Select `oke-lab`, a recent time range, and automatic refresh.
3. Find the `hello-oke-traffic` client and `hello-oke` service/workload. Observe HTTP request volume, success rate, and latency; graph names/grouping vary with the selected view.
4. Open the workload details and inspect its replicas and proxy status. This lab supplies metrics, not distributed tracing or Grafana dashboards.

## Controlled outage and recovery

Only do this in your own disposable lab cluster, while the traffic generator is running.

```bash
kubectl -n oke-lab scale deployment/hello-oke --replicas=0
kubectl -n oke-lab logs deployment/hello-oke-traffic -c traffic --tail=10
# Wait 30–60 seconds, observe failed requests in Kiali, then restore promptly:
kubectl -n oke-lab scale deployment/hello-oke --replicas=2
kubectl -n oke-lab rollout status deployment/hello-oke --timeout=300s
```

The client's proxy should record failures while the service has no ready endpoints. After restoring the app, new requests should succeed. A five-minute graph still includes older errors until they age out; do not confuse historical errors with a continuing outage. Helm's desired replica count remains two.

## Kubernetes evidence

Start with Kubernetes, which gives immediate state and application evidence:

```bash
kubectl get nodes
kubectl -n oke-lab get deploy,pods,svc
kubectl top nodes
kubectl -n oke-lab top pods
kubectl -n oke-lab logs deployment/hello-oke -c web --tail=50
kubectl -n oke-lab logs deployment/hello-oke -c istio-proxy --tail=50
kubectl -n oke-lab get events --sort-by=.lastTimestamp
```

Expected: all nodes are `Ready`, the Deployment has `2/2` ready replicas, each app pod has its injected proxy, and the Service has an external IP. `kubectl top` needs Metrics Server; its absence does not mean Istio/Prometheus is broken. The echo container may only log startup; use `istio-proxy` logs for request access logs.

## Optional: OCI dashboard (instructor-enabled)

This is separate from Kiali. Only continue if the instructor has enabled the required telemetry and permissions. Open **Observability & Management → Monitoring → Metrics Explorer** and build a dashboard with available Container Engine / Container Insights metrics:

| Signal | Why it matters | Suggested alarm |
|---|---|---|
| Unhealthy nodes | Detects loss of compute capacity | Any unhealthy node for 5 minutes |
| Node CPU/memory | Detects saturation | Above 80% for 10 minutes |
| Pod restarts | Detects crashes or failed probes | More than 3 in 10 minutes |
| Ready vs desired replicas | Detects failed rollout | Ready below desired for 5 minutes |
| LB backend health | Measures user reachability | Healthy backends below expected |

Metric names and dimensions differ by OKE version, region, and enabled services. Select them from Metrics Explorer rather than copying values from another tenancy. Set log retention deliberately: telemetry creates cost and can contain sensitive output.

## Logs

```bash
kubectl -n oke-lab logs deployment/hello-oke -c istio-proxy --since=15m
```

For OCI-collected workload logs, use **Logging → Log Search**, then filter to the cluster, `oke-lab` namespace, and `hello-oke` workload. Make one `curl` request and correlate it to its log record.

## Optional: OCI alarm test

1. Create an OCI Monitoring alarm on pod readiness or Load Balancer backend health, routed to a test Notifications topic.
2. Record its normal `OK` state.
3. Cause a temporary, reversible outage:

   ```bash
   kubectl -n oke-lab scale deployment/hello-oke --replicas=0
   ```

4. Verify zero ready replicas and wait for the evaluation window.
5. Restore immediately:

   ```bash
   kubectl -n oke-lab scale deployment/hello-oke --replicas=2
   kubectl -n oke-lab rollout status deployment/hello-oke
   ```

6. Confirm the alarm returns to `OK`, then remove test alerting resources when finished.

Finish using the Helm uninstall and **End session** steps in the learner walkthrough. Learners do not destroy the infrastructure directly.
