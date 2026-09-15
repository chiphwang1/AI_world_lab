# Troubleshooting

| Symptom | Check | Typical fix |
|---|---|---|
| Terraform cannot download dependencies | Network/proxy and Terraform version | Configure a corporate proxy or provider mirror, then retry. |
| Kubernetes version rejected | `oci ce cluster-options get --cluster-option-id all` | Use a version supported by the selected region. |
| Nodes not `Ready` | OCI work requests; `kubectl get nodes` | Check quota, subnet capacity, and node-pool errors. |
| Pod is Pending | `kubectl -n oke-lab describe pod <name>` | Check worker capacity, CNI IP capacity, and quota. |
| Service remains Pending | `kubectl -n oke-lab describe svc hello-oke` | Check Service events, routing, and load-balancer quota. |
| App fails | `kubectl -n oke-lab logs deploy/hello-oke` | Confirm ready endpoints and probe results. |
| No OCI metrics/logs | Cluster observability settings and IAM | Enable Container Insights/log collection and wait for ingestion. |
| Destroy fails | `kubectl get svc -A` | Delete LoadBalancer Services and wait for OCI cleanup, then retry. |
