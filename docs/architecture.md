# Lab architecture

Use this same diagram during the opening lecture and the [student walkthrough](../README.md). It shows logical relationships, not individual network hops. Each learner has a dedicated cluster with two worker nodes; the diagram shows one of several application pods.

```mermaid
flowchart TD
  browser["Browser or curl"] --> lb["OCI public LoadBalancer"]
  lb --> svc["Service: hello-oke"]
  generator["Traffic generator + Istio proxy"] --> svc
  subgraph pod["Application pod — repeated for each replica"]
    proxy["Istio proxy"] --> web["web container"]
  end
  svc --> proxy
  proxy -. "request metrics, scraped by Prometheus" .-> prometheus["Prometheus"]
  prometheus -. "traffic relationships" .-> kiali["Kiali"]
  prometheus -. "metric history" .-> grafana["Grafana"]
  web -- "CPU usage via kubelet" --> metrics["Metrics Server"]
  metrics -- "resource metrics" --> hpa["HPA"]
  hpa -- "desired replica count" --> deployment["Deployment / ReplicaSet"]
  deployment -- "maintains app pod count" --> pod
```

Trace three paths:

1. **Requests:** the public LoadBalancer reaches application pods through the Service. The in-cluster traffic generator uses the Service directly, without the public LoadBalancer. Istio proxies observe requests to the app.
2. **Dashboards:** Prometheus scrapes request metrics from the proxies. Kiali queries it for traffic relationships; Grafana queries it for history. Localhost port-forwards give your browser access to these internal dashboards. Prometheus also scrapes Istiod; this arrow is omitted for readability.
3. **Scaling:** Metrics Server obtains resource usage from the kubelets. The HPA uses the `web` container's CPU utilization to change the Deployment's replica count; its ReplicaSet maintains those pods. This path does not use Prometheus and does not add worker nodes.

Dashed arrows show telemetry data flowing to its consumers; Prometheus initiates the scrapes, and the dashboards initiate their queries. The diagram is rendered on GitHub; the descriptions above cover the same paths if your Markdown viewer cannot render Mermaid.

## Component ownership

| Component | Who provides it | Role |
|---|---|---|
| OKE, two workers, networking | Instructor/Luna provisioning | Runs the workloads; creation starts with the lecture |
| Cert Manager and Metrics Server | OCI-managed add-ons enabled by provisioning | Cert Manager is a dependency of this Metrics Server add-on; Metrics Server supplies resource metrics |
| Istio base and Istiod | Student, using Helm | Register Istio object types and configure the workload proxies |
| Prometheus | Student, using Helm | Scrapes and stores mesh metrics |
| Kiali and Grafana | Student, using Helm | Query Prometheus; remain internal, with anonymous read-only lab access |
| App, traffic generator, HPA | Student, using the local Helm chart | Serve requests, produce demand, and adjust replicas |
| OCI LoadBalancer | OCI, in response to the app's Service | Exposes the training app publicly; not the dashboards |

## Vocabulary for the lecture

| Term | Meaning in this lab |
|---|---|
| Pod | A running unit containing the app and its Istio proxy |
| Deployment / ReplicaSet | Declares the desired app state / maintains the desired pod count |
| Service | Gives selected pods a stable address as pods change |
| Namespace | Groups related resources, such as `oke-lab` |
| Helm chart / release | A package of Kubernetes templates / a named installation of that package |
| Readiness / liveness | Whether a container can accept traffic / whether it needs restarting |
| HPA | Horizontal Pod Autoscaler; adjusts application replicas from metrics |

Use only training data: the app is public and unauthenticated. Dashboard access is restricted to the cluster and localhost forwards, but anonymous access is still unsuitable for sensitive production data. Metrics are ephemeral; copy your observations before ending the session.
