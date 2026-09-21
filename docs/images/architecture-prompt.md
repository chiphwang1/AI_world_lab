# Architecture image authoring notes

The published `oke-lab-architecture.png` was created with built-in image generation, then revised for technical accuracy. It depicts the repository's documented end-of-lab setup, not a live inventory or health check. The initial candidate was rejected because its arrows and missing Prometheus node were inaccurate.

When updating the image, compare every path with `../architecture.md` and the Helm values. Preserve the distinction between Prometheus dashboard data and Metrics Server CPU input. Readable text and correct arrow endpoints matter more than decorative detail.

## Final revision prompt

```text
Use case: infographic-diagram.
Redesign the attached OKE architecture image into a much simpler technically accurate three-lane diagram. Keep the polished white-background, blue/teal/amber teaching style and readable dark type. Replace ALL boxes and arrows with the specification below. Previous image omitted Prometheus and connected incorrect components; do not preserve those mistakes. Use generous whitespace. Landscape PNG.

Title "OKE lab architecture"
Subtitle "Three paths to understand"

A large OKE cluster boundary contains three horizontal panels stacked vertically. A top strip inside the cluster says "Luna-provisioned OKE: managed control plane + two worker nodes". Do not draw individual worker boxes or detailed namespace boundaries.

Panel 1 title "1  Application requests". Blue arrows.
Outside the cluster on the left: "Browser / curl" -> "OCI public LoadBalancer".
This arrow enters panel 1 inside the cluster:
"hello-oke Service" -> a pod box containing "Istio proxy" -> "web container".
Below the Service is a box "Traffic generator + Istio proxy" with an upward blue arrow to the Service. One note "App and generator run in oke-lab".
Do not draw any other arrows in panel 1.

Panel 2 title "2  Monitoring". Teal arrows showing METRIC DATA flowing left to right.
Exactly three columns:
left box "Istio proxies + Istiod";
middle box "Prometheus" with subtitle "scrapes and stores metrics";
right box split into two clearly labeled rows "Kiali - service map" and "Grafana - metric history".
Arrow from left box to Prometheus. Arrow from Prometheus to each of Kiali and Grafana.
Below this panel, note "Prometheus initiates scrapes; Kiali and Grafana query Prometheus."
Next line "Dashboard access: localhost port-forwards. No public dashboard endpoint."
No arrows to any other panel.

Panel 3 title "3  CPU-based autoscaling". Amber arrows.
One clean left-to-right chain with exactly five boxes:
"Worker kubelets" -> "Metrics Server" -> "HPA" -> "Deployment / ReplicaSet" -> "App replicas".
Labels along the chain: kubelets to Metrics Server "resource usage"; Metrics Server to HPA "web CPU"; HPA to Deployment "desired replicas"; Deployment to replicas "maintains pods".
Below note "HPA scales application pods, not worker nodes. This path does not use Prometheus."
No arrows to any other panel.

A bottom strip inside the cluster has three support cards, NO connecting arrows:
"Istio base + Istiod" / "CRDs and proxy configuration";
"Cert Manager" / "Certificates; dependency of this OCI Metrics Server add-on";
"Namespace: istio-system" / "Istiod, Prometheus, Kiali, Grafana".
The repeated Istiod label in panel 2 identifies a metric source, not a duplicate installation.

Outside the boundary, bottom footer:
"Student tools: Helm installs charts | kubectl controls resources | OCI CLI authenticates access"
"Logical lab setup after traffic and HPA are enabled. Not a live health snapshot."

No extra arrows, no arrows between panels, no status indicators, no icons unless simple and restrained. Ensure the literal label "Prometheus" is present in the central panel, and "Metrics Server" is in the autoscaling chain, not bypassed. Do not mix dashboards with Cert Manager. No public IPs or secrets.
```
