# Learner Helm materials

Follow the root [walkthrough](../README.md). Students install the charts in this order: Istio base (CRDs), istiod, Prometheus, Kiali, Grafana, then the local application. The application is installed about 25 minutes into the targeted 55-minute core hands-on lab (60 minutes with optional recovery). An umbrella chart would obscure the CRD/control-plane readiness boundary.

`versions.env` pins upstream chart releases; `values/` holds our training configuration. Students edit `values/student.yaml` to customize their deployment. We do not maintain copies of upstream charts. The local `charts/oke-mesh-app` chart owns the Python workload and ConfigMap, one LoadBalancer Service, optional mesh traffic, and an optional HPA. Its Python runtime image is pinned by version; no student image build or registry credentials are required.

Use Istio's current chart repository, `https://blob.istio.io/istio-release/charts`, as documented in its installation guide. The older `storage.googleapis.com` index did not contain the pinned 1.31.0 release during validation.

The app exposes `/` (message and pod identity), `/healthz` (cheap probe), and `/work` (fixed CPU work). CPU work is limited to two concurrent requests per app pod; requests beyond that receive HTTP 429. Container resource limits cap CPU and memory. This is a disposable, unauthenticated training server, not a production deployment.

The traffic Deployment normally makes a request every two seconds. `traffic.loadEnabled=true` adds two concurrent `/work` request streams for 300 seconds, then falls back to baseline. The schema bounds burst duration to 600 seconds and concurrency to four. Reset the flag afterward: restarting the pod while it is true starts a new burst. An early stop rolls the traffic pod back to baseline configuration.

The HPA uses `autoscaling/v2` container-resource CPU metrics for `web`, excluding the Istio sidecar. It requires Metrics Server independently of Prometheus. With autoscaling enabled, the chart omits Deployment `spec.replicas` so subsequent Helm upgrades do not reset the HPA's count. The one-time transition from a previously declared count can briefly reset replicas before the HPA reconciles; enable HPA and wait for it before load. The 60-second downscale stabilization is deliberately shorter than the Kubernetes default and is not a production recommendation.

Prometheus scrapes istiod on port 15014 and injected workload proxies' `http-envoy-prom` port (15090). This captures Istio request metrics without application instrumentation. Kiali uses that Prometheus instance. The core [Grafana dashboard](../docs/monitoring.md#grafana-dashboard) uses the same data source and provisions `dashboards/oke-lab.json`; tracing backends remain omitted. Keep the `--set-file dashboards.default.oke-lab.json=helm/dashboards/oke-lab.json` argument in every Grafana install/upgrade so the dashboard is included.

Kiali is read-only but anonymous, ClusterIP-only, and accessed through localhost port-forwarding. This is for disposable, per-learner clusters, not production. Prometheus uses ephemeral storage; metrics are lost when its pod is replaced. Dashboards request no additional cloud load balancers or persistent volumes.

Grafana uses anonymous Viewer access, no Kubernetes API permissions or service-account token, a ClusterIP Service, and ephemeral storage. The pinned chart provisions the read-only data source and dashboard from repository files on every install. Admin credentials are generated into a Kubernetes Secret by the chart, never stored in this repository. Anyone who can reach the Service can view/query the lab metrics; do not expose it publicly or use this access model for sensitive production data. Manual UI changes are not retained after pod replacement; update the versioned dashboard instead.

## Validation and release

```bash
helm lint charts/oke-mesh-app --kube-version 1.36.1 --strict
bash scripts/test-helm.sh
python3 -m unittest discover -s scripts/tests -v
```

The Helm test script renders releases and checks wiring without accessing a cluster, including Grafana's data source, dashboard, and internal-only access. It requires Helm, Python 3/PyYAML, and network access to chart repositories. The unit tests exercise application routes on loopback and existing mocked CI lifecycle behavior. A [local rehearsal](../docs/rehearsal-2026-09-18.md) verified deployment, mesh traffic, scaling, recovery, and Grafana rendering. Still rehearse the complete student install order, both dashboard checks, manual 2→4→2 scaling, HPA scale-out/scale-in, and optional recovery in one dedicated Luna session before publishing. Leave releases installed and verify automated session-end cleanup removes the cloud LoadBalancer and infrastructure without a student uninstall. Record peak replicas and timing, verify both Metrics Server and scheduling capacity, and tune the bounded load if necessary. Confirm the revised core workflow fits 55 minutes after the cluster is ready; Luna timing, cleanup, and concurrent capacity remain unverified.

For an offline check of just the local app chart, run `bash scripts/test-helm.sh --local-only`; this explicitly skips upstream rendering. Run the full check before release. Existing GitLab lifecycle tests do not run these Helm checks automatically.

## Separate GitHub repository

Pending an approved GitHub owner, name, and visibility, package only learner content: `README.md`, `charts/`, `helm/`, `docs/monitoring.md`, `docs/troubleshooting.md`, `scripts/test-helm.sh`, `scripts/tests/check_mesh_charts.py`, and `scripts/tests/test_bootcamp_app.py`. Adjust instructor-only links and test commands for the split and provide a tagged clone URL in Luna. Do not mirror the entire infrastructure repository or its history: exclude `.git/`, credentials, local config, Terraform inputs/state/plans, and internal operational logs.

## Upstream references

- [Istio Helm installation](https://istio.io/latest/docs/setup/install/helm/)
- [Istio supported Kubernetes releases](https://istio.io/latest/docs/releases/supported-releases/)
- [Istio Prometheus integration](https://istio.io/latest/docs/ops/integrations/prometheus/)
- [Kiali Helm installation](https://kiali.io/docs/installation/installation-guide/install-with-helm/)
- [Kiali prerequisites](https://kiali.io/docs/installation/installation-guide/prerequisites/)
- [Prometheus chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus)
- [Grafana Helm installation](https://grafana.com/docs/grafana/latest/setup-grafana/installation/helm/)
- [Kubernetes HPA behavior and container-resource metrics](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
