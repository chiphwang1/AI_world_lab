# Monitoring exercises

Start with Kubernetes, which gives immediate state and application evidence:

```bash
kubectl get nodes
kubectl -n oke-lab get deploy,pods,svc
kubectl -n oke-lab top nodes
kubectl -n oke-lab top pods
kubectl -n oke-lab logs deployment/hello-oke --tail=50
kubectl -n oke-lab get events --sort-by=.lastTimestamp
```

Expected: all nodes are `Ready`, the Deployment has `2/2` ready replicas, and the Service has an external IP.

## OCI dashboard

Open **Observability & Management → Monitoring → Metrics Explorer**. Enable Container Insights and workload log collection for the cluster if they are not enabled in your tenancy. Build a dashboard with the available Container Engine / Container Insights metrics:

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
kubectl -n oke-lab logs deployment/hello-oke --since=15m
```

For OCI-collected workload logs, use **Logging → Log Search**, then filter to the cluster, `oke-lab` namespace, and `hello-oke` workload. Make one `curl` request and correlate it to its log record.

## Safe alarm test

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
