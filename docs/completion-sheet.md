# OKE lab completion sheet

Copy this sheet into your own notes. Fill it during the existing [lab checkpoints](../README.md), not as an extra exercise. Keep credentials, kubeconfig contents, and tokens out of your notes.

Name: __________  Date: __________  Tested repository revision: __________

## Checkpoints

- [ ] Preflight passed for my assigned context; two workers are Ready with numeric resource metrics.
- [ ] My public app returned my customized message; two app pods showed `2/2` Ready.
- [ ] I identified `web` and `istio-proxy` and found `hello-oke-traffic → hello-oke` in Kiali.
- [ ] Manual scaling changed app replicas 2 → 4 → 2; worker count and Service IP stayed unchanged.
- [ ] HPA utilization became numeric; I observed scale-out above two and scale-in back to two.
- [ ] I explicitly reset `traffic.loadEnabled=false` and confirmed two Ready app pods.

My customized response message: __________

## Observations

Use Grafana's **Last 30 minutes** range and p95 latency for each row. Record HPA replicas with `kubectl get hpa` and Ready app pods with `kubectl get pods`; the Grafana proxy count is not a readiness check. Write `no data` if a panel is empty, rather than treating it as zero.

| Phase | HPA replicas / Ready app pods | Requests/s | Success % | p95 latency (ms) | App proxies up |
|---|---|---|---|---|---|
| Baseline (`/`) | Not enabled / ___ | ___ | ___ | ___ | ___ |
| During load (`/work`) | ___ / ___ | ___ | ___ | ___ | ___ |
| After scale-in (`/`) | ___ / ___ | ___ | ___ | ___ | ___ |

Peak HPA replica count observed: ___  Time load started: ___  Time scale-in finished: ___

Six replicas is a limit, not a required peak. The two endpoints do different work; this comparison does not isolate autoscaling's effect on latency.

## Five-minute debrief

1. Which Kubernetes object keeps the application reachable as pods change?
2. Which component supplies this HPA's CPU metrics, and which supplies dashboard data?
3. What changed during scaling: app replicas, worker nodes, Service IP?
4. What proves scale-in finished? Why can Grafana's proxy count lag?
5. Which probe removes an unready pod from normal Service traffic, and which can restart a container? Does Kiali's **Degraded** label identify a failed probe?

Prediction from step 5: a `200m` CPU request with a 60% HPA target corresponds to ___ CPU usage.

Optional pod recovery: skipped / completed / blocked. Replacement pod name, if observed: __________

Result: completed / needs instructor help / demonstration only.

If blocked, record the step, symptom, and last observed state: __________

Leave releases installed for Luna's session-end cleanup. Stop local watches and port-forwards after recording your results; doing so does not stop in-cluster traffic. Give the instructor your blocked checkpoint before leaving.
