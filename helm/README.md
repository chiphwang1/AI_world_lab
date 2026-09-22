# Learner Helm materials

Follow the root [walkthrough](../README.md). Students install the charts in this order: Istio base (CRDs), istiod, Prometheus, Kiali, Grafana, then the local application. The application exercise starts at minute 23 in the planned 55-minute core lab, followed by five minutes for debrief and delays. Pod recovery is optional only when core work finishes five minutes early. An umbrella chart would obscure the CRD/control-plane readiness boundary.

`versions.env` pins upstream chart releases; `values/` holds our training configuration. Students edit `values/student.yaml` to customize their deployment. We do not maintain copies of upstream charts. The local `charts/oke-mesh-app` chart owns the Python workload and ConfigMap, one LoadBalancer Service, optional mesh traffic, and an optional HPA. Its Python runtime image is pinned by version; no student image build or registry credentials are required.

Use Istio's current chart repository, `https://blob.istio.io/istio-release/charts`, as documented in its installation guide. The older `storage.googleapis.com` index did not contain the pinned 1.31.0 release during validation.

The app exposes `/` (message and pod identity), `/healthz` (cheap probe), and `/work` (fixed CPU work). CPU work is limited to two concurrent requests per app pod; requests beyond that receive HTTP 429. Container resource limits cap CPU and memory. This is a disposable, unauthenticated training server, not a production deployment.

The traffic Deployment normally makes a request every two seconds. `traffic.loadEnabled=true` adds two concurrent `/work` request streams for 300 seconds, then falls back to baseline. The schema bounds burst duration to 600 seconds and concurrency to four. Reset the flag afterward: restarting the pod while it is true starts a new burst. An early stop rolls the traffic pod back to baseline configuration.

The HPA uses `autoscaling/v2` container-resource CPU metrics for `web`, excluding the Istio sidecar. It requires Metrics Server independently of Prometheus. With autoscaling enabled, the chart omits Deployment `spec.replicas` so subsequent Helm upgrades do not reset the HPA's count. The one-time transition from a previously declared count can briefly reset replicas before the HPA reconciles; enable HPA and wait for it before load. The 60-second downscale stabilization is deliberately shorter than the Kubernetes default and is not a production recommendation.

Prometheus scrapes istiod on port 15014 and injected workload proxies' `http-envoy-prom` port (15090). This captures Istio request metrics without application instrumentation. Kiali uses that Prometheus instance. The core [Grafana dashboard](../docs/monitoring.md#grafana-dashboard) uses the same data source and provisions `dashboards/oke-lab.json`; tracing backends remain omitted. Keep the `--set-file dashboards.default.oke-lab.json=helm/dashboards/oke-lab.json` argument in every Grafana install/upgrade so the dashboard is included.

Kiali is read-only but anonymous, ClusterIP-only, and accessed through localhost port-forwarding. This is for disposable, per-learner clusters, not production. Prometheus uses ephemeral storage; metrics are lost when its pod is replaced. Dashboards request no additional cloud load balancers or persistent volumes.

Grafana uses anonymous Viewer access, no Kubernetes API permissions or service-account token, a ClusterIP Service, and ephemeral storage. The pinned chart provisions the read-only data source and dashboard from repository files on every install. Admin credentials are generated into a Kubernetes Secret by the chart, never stored in this repository. Anyone who can reach the Service can view/query the lab metrics; do not expose it publicly or use this access model for sensitive production data. Manual UI changes are not retained after pod replacement; update the versioned dashboard instead.

Grafana requests 100m CPU/512Mi memory and has limits of 500m CPU/1Gi memory. Its explicit `GOMEMLIMIT=512MiB` overrides the chart's automatic runtime target and leaves space below the container cap for other process memory. These are measured-training configuration values, not production sizing guidance. The previous 512Mi container limit produced a confirmed OOM kill during rehearsal. Retest sustained dashboard refreshes after changing Grafana versions or panel/query counts.

## Validation and release

```bash
helm lint charts/oke-mesh-app --kube-version 1.36.1 --strict
bash scripts/test-helm.sh
python3 -m unittest discover -s scripts/tests -v
```

The Helm test script renders releases and checks wiring without accessing a cluster, including Grafana's data source, dashboard, and internal-only access. It requires Helm, Python 3/PyYAML, and network access to chart repositories. The unit tests exercise application routes on loopback, mocked CI lifecycle behavior, read-only preflight, prepared-chart safety, and learner links/commands. Dashboard contracts require instant queries for summary cards and range queries for historical graphs. A [local rehearsal](../docs/rehearsal-2026-09-18.md) verified deployment, mesh traffic, scaling, recovery, and Grafana rendering. Use the [instructor pilot checklist](../docs/instructor-guide.md#classroom-pilot-and-release-gates) to validate a complete 90-minute Luna session, including the student install order, both dashboard UIs, manual 2→4→2 scaling, HPA scale-out/scale-in, and session-end cleanup. Luna timing, cleanup, and concurrent capacity remain unverified.

For an offline check of just the local app chart, run `bash scripts/test-helm.sh --local-only`; this explicitly skips upstream rendering. Run the full check before release. Existing GitLab lifecycle tests do not run these Helm checks automatically.

Contract tests accept the learner's current `student.yaml` message and separately verify a message override without editing that file. Full upstream tests also check Grafana's memory request, limit, and single explicit Go memory target. Do not restore a learner's customized message just to make tests pass.

The [September 21 improvement retest](../docs/rehearsal-2026-09-21-improvements.md) records the memory fix, existing-release timing, capacity/cost comparison, and remaining classroom-release gates. Warm upgrades are not cold-install measurements.

## GitHub distribution

The private distribution repository is [chiphwang1/AI_world_lab](https://github.com/chiphwang1/AI_world_lab); Luna reads the GitLab source. Both must publish materials tag `lab-2026-09-21.1` at the same commit before distributing these instructions. Prepare that checkout and chart archives before class, and verify the matching revision in Luna using the [instructor preparation steps](../docs/instructor-guide.md#one-materials-revision). Chart version pins do not pin the repository revision. Classroom pilot and security gates remain separate from publishing a materials tag.

If creating a learner-only bundle, include `README.md`, `charts/`, `helm/`, `docs/architecture.md`, `docs/images/oke-lab-architecture.png`, `docs/completion-sheet.md`, `docs/completion-sheet.pdf`, `docs/cluster-access.md`, `docs/monitoring.md`, `docs/troubleshooting.md`, `scripts/check-ready.sh`, `scripts/test-helm.sh`, `scripts/tests/check_mesh_charts.py`, `scripts/tests/test_bootcamp_app.py`, and `scripts/tests/test_check_ready.py`. Adjust maintainer links and test commands for that bundle; keep the instructor guide and answer key in the instructor distribution. Exclude `.git/`, credentials, private local configuration, Terraform inputs/state/plans, and internal operational logs. Do not change repository visibility as part of preparing lab instructions.

Also include `scripts/prepare-charts.sh` and the prepared `.lab-cache/charts/` archives. A filtered bundle without `.git/` cannot run the README's exact-tag check: the instructor must provide a recorded source commit and a matching bundle-specific revision check before distributing it. The supported default is the prepared, tagged checkout. Students run only `prepare-charts.sh --check`; `--download` is an instructor preparation step.

## Upstream references

- [Istio Helm installation](https://istio.io/latest/docs/setup/install/helm/)
- [Istio supported Kubernetes releases](https://istio.io/latest/docs/releases/supported-releases/)
- [Istio Prometheus integration](https://istio.io/latest/docs/ops/integrations/prometheus/)
- [Kiali Helm installation](https://kiali.io/docs/installation/installation-guide/install-with-helm/)
- [Kiali prerequisites](https://kiali.io/docs/installation/installation-guide/prerequisites/)
- [Prometheus chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus)
- [Grafana Helm installation](https://grafana.com/docs/grafana/latest/setup-grafana/installation/helm/)
- [Kubernetes HPA behavior and container-resource metrics](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
