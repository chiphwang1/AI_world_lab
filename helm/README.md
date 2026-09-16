# Learner Helm materials

Follow the root [walkthrough](../README.md). Install upstream charts separately and in order: Istio base (CRDs), istiod, Prometheus, Kiali, then the local app chart. An umbrella chart would obscure the CRD/control-plane readiness boundary.

`versions.env` pins upstream chart releases; `values/` holds our training configuration. We do not maintain copies of upstream charts. The local `charts/oke-mesh-app` chart owns the echo workload, one LoadBalancer Service, and optional low-rate mesh traffic.

Prometheus scrapes istiod on port 15014 and injected workload proxies' `http-envoy-prom` port (15090). This captures Istio request metrics without application instrumentation. Kiali uses that Prometheus instance. Grafana and tracing backends are intentionally omitted.

Kiali is read-only but anonymous, ClusterIP-only, and accessed through localhost port-forwarding. This is for disposable, per-learner clusters, not production. Prometheus uses ephemeral storage; metrics are lost when its pod is replaced. Dashboards request no additional cloud load balancers or persistent volumes.

## Validation and release

```bash
helm lint charts/oke-mesh-app --kube-version 1.36.1 --strict
bash scripts/test-helm.sh
```

The test script renders upstream releases and checks wiring without accessing a cluster. It requires Helm, Python 3/PyYAML, and network access to chart repositories. Then perform a live install, request/graph check, and uninstall in one dedicated Luna session before publishing a workshop release. The current VCN quota blocker prevents that live validation.

For an offline check of just the local app chart, run `bash scripts/test-helm.sh --local-only`; this explicitly skips upstream rendering. Run the full check before release. Existing GitLab lifecycle tests do not run these Helm checks automatically.

## Separate GitHub repository

Pending an approved GitHub owner, name, and visibility, package only learner content: `README.md`, `charts/`, `helm/`, `docs/monitoring.md`, `docs/troubleshooting.md`, `scripts/test-helm.sh`, and `scripts/tests/check_mesh_charts.py`. Adjust instructor-only links for the split and provide a tagged clone URL in Luna. Do not mirror the entire infrastructure repository or its history: exclude `.git/`, credentials, local config, Terraform inputs/state/plans, and internal operational logs.

## Upstream references

- [Istio Helm installation](https://istio.io/latest/docs/setup/install/helm/)
- [Istio supported Kubernetes releases](https://istio.io/latest/docs/releases/supported-releases/)
- [Istio Prometheus integration](https://istio.io/latest/docs/ops/integrations/prometheus/)
- [Kiali Helm installation](https://kiali.io/docs/installation/installation-guide/install-with-helm/)
- [Kiali prerequisites](https://kiali.io/docs/installation/installation-guide/prerequisites/)
- [Prometheus chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus)
