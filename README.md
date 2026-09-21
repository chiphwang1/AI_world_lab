# OKE Bootcamp: Build, Run, and Scale Kubernetes on OCI

Build a Helm-based application deployment, run it on your assigned OKE cluster, and scale it as demand changes. Install Istio, Prometheus, Kiali, and Grafana to observe application traffic, health, and scaling. Your cluster is ready when the hands-on lab starts; cluster creation and manual resource cleanup are not student exercises.

Run these commands in a **Bash terminal on the Luna desktop**. Keep session credentials private.

| Exercise | Time | What you will demonstrate |
|---|---|---|
| 1. Connect | 5 min | Verify access to your prepared OKE cluster |
| 2. Install the mesh and monitoring tools | 20 min | Install Istio, Prometheus, Kiali, and Grafana using Helm |
| 3. Build and run the application | 10 min | Customize and deploy two replicas with an OCI LoadBalancer |
| 4. Observe traffic | 5 min | Read the Kiali traffic graph and Grafana metrics dashboard |
| 5. Scale | 15 min | Scale manually, then observe CPU-driven scale-out and scale-in |
| 6. Optional: pod recovery | 5 min | Delete one pod and observe its replacement |

**Hands-on target: 55 minutes, or 60 minutes with pod recovery.** Grafana is included in the core lab. The 90-minute session reserves the first 30 minutes for the introduction while Luna provisions the cluster, leaving five minutes for questions or delays after the core exercises. Do pod recovery only if ahead of schedule; completing it at the full target leaves no buffer. This schedule assumes the cluster is ready by minute 30; classroom timings still need a Luna rehearsal.

## 1. Connect to your prepared cluster — 5 minutes

Open your assigned Luna session as directed by the instructor. The desktop can appear before the cluster is ready. If provisioning is still running or has failed, ask the instructor; do not create a replacement cluster.

OCI API credentials are on the desktop in `~/.oci/config`. Obtain your **current session's region and compartment** from Luna's session details or the instructor; do not copy another learner's values. For console login, use Luna's console link and temporary console credentials, not the API private key.

Check the desktop tools. Ask the instructor if one is missing; `scripts/ci-tools.sh` is only for disposable CI containers, not the desktop.

```bash
oci --version
kubectl version --client
helm version --short
git --version
```

List your cluster, then copy its OCID into the following commands:

```bash
export LAB_REGION='<your-session-region>'
export LAB_COMPARTMENT_OCID='<your-session-compartment-ocid>'
oci ce cluster list --compartment-id "$LAB_COMPARTMENT_OCID" \
  --region "$LAB_REGION" \
  --query 'data[].{Name:name,State:"lifecycle-state",OCID:id}' --output table
export LAB_CLUSTER_OCID='<the-ACTIVE-cluster-ocid-from-that-list>'
export KUBECONFIG="$HOME/.kube/oke-lab"
mkdir -p "$HOME/.kube"
oci ce cluster create-kubeconfig --cluster-id "$LAB_CLUSTER_OCID" \
  --region "$LAB_REGION" --file "$KUBECONFIG" \
  --token-version 2.0.0 --kube-endpoint PUBLIC_ENDPOINT
kubectl config current-context
kubectl get nodes
kubectl top nodes
kubectl auth can-i create customresourcedefinitions.apiextensions.k8s.io
kubectl auth can-i create clusterroles.rbac.authorization.k8s.io
```

Expect two `Ready` nodes, CPU/memory readings from `kubectl top nodes`, and `yes` for both permission checks. Metrics Server must already be working for the scaling exercise. Installing the mesh requires cluster-level permissions in your **dedicated lab cluster**. Stop and ask the instructor if any check fails or the context is not your assigned cluster. Never use a shared or production cluster.

Get the lab materials using the repository URL supplied by the instructor. Replace the placeholder before running:

```bash
git clone '<instructor-provided-repository-url>' oke-bootcamp
cd oke-bootcamp
source helm/versions.env
```

Keep this terminal in the `oke-bootcamp` directory for the rest of the lab. The version variables loaded above pin the tools you will install.

**Checkpoint:** you can access your assigned cluster and its CPU metrics, and the lab files are available.

## 2. Install Istio, Prometheus, Kiali, and Grafana — 20 minutes

### Install Istio

This lab uses **sidecar mode**: Istio adds a proxy beside each application container. The pinned release supports Kubernetes 1.32–1.36. Check `kubectl version`; ask the instructor if your server is outside that range.

```bash
helm repo add istio https://blob.istio.io/istio-release/charts --force-update
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add kiali https://kiali.org/helm-charts
helm repo update

helm upgrade --install istio-base istio/base \
  --namespace istio-system --create-namespace --version "$ISTIO_VERSION" \
  --set defaultRevision=default --wait --timeout 10m
helm upgrade --install istiod istio/istiod \
  --namespace istio-system --version "$ISTIO_VERSION" \
  -f helm/values/istiod.yaml --wait --timeout 10m
kubectl -n istio-system rollout status deployment/istiod --timeout=300s

kubectl create namespace oke-lab --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace oke-lab istio-injection=enabled --overwrite
```

Namespace labeling enables injection for **new pods**. Do not label `istio-system` for injection.

### Install Prometheus, Kiali, and Grafana

Prometheus collects Istio request metrics. Kiali uses them to draw service-to-service traffic; Grafana uses the same Prometheus data source for time-series dashboards. All three stay inside the cluster. This short-lived lab uses no persistent telemetry volumes.

```bash
helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace istio-system --version "$PROMETHEUS_CHART_VERSION" \
  -f helm/values/prometheus.yaml --wait --timeout 10m
helm upgrade --install kiali-server kiali/kiali-server \
  --namespace istio-system --version "$KIALI_CHART_VERSION" \
  -f helm/values/kiali.yaml --wait --timeout 10m
helm upgrade --install grafana grafana \
  --repo https://grafana-community.github.io/helm-charts \
  --namespace istio-system --version "$GRAFANA_CHART_VERSION" \
  -f helm/values/grafana.yaml \
  --set-file dashboards.default.oke-lab.json=helm/dashboards/oke-lab.json \
  --wait --timeout 10m
helm list --namespace istio-system
kubectl -n istio-system get pods,svc
```

Kiali and Grafana use read-only, anonymous access for this dedicated training cluster. **Never expose them with a public LoadBalancer or Ingress.** Anyone with network access to their Services can read/query lab metrics; production requires authenticated access and appropriate network controls. Grafana's data source and dashboard are provisioned by Helm, so there is no manual import or administrator login step.

**Checkpoint:** all five monitoring/mesh releases (`istio-base`, `istiod`, `prometheus`, `kiali-server`, and `grafana`) are deployed and their workload pods are ready. The application has not been installed yet—that happens next, about 25 minutes into the hands-on lab. Dashboard traffic panels will be empty until the application and traffic generator are running. Ask the instructor if an installation stalls; do not spend the remaining lab time debugging it alone.

## 3. Build and run the application — 10 minutes

Open `helm/values/student.yaml` in the desktop editor and customize `message`, for example:

```yaml
message: Hello from my OKE bootcamp
```

Leave `replicaCount: 2` and the resource settings unchanged. Here, **build** means configuring the Kubernetes deployment, not compiling an image. The chart supplies a small Python application and its runtime; no image registry account is required.

Check the chart, then install the application:

```bash
helm lint ./charts/oke-mesh-app -f helm/values/student.yaml --strict
helm upgrade --install hello-oke ./charts/oke-mesh-app \
  --namespace oke-lab -f helm/values/student.yaml --wait --timeout 10m
kubectl -n oke-lab get deploy,pods,svc
kubectl -n oke-lab get pods -l app=hello-oke \
  -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.spec.containers[*].name}{"\n"}{end}'
```

Expect two application replicas with an `istio-proxy` beside the `web` container, normally showing `2/2` containers ready. Do not also apply the legacy `kubernetes/` manifests; they use the same application name but are not Helm-managed.

The Service requests one OCI LoadBalancer. Wait for its external IP, then test the application:

```bash
kubectl -n oke-lab get service hello-oke --watch
# Press Ctrl+C once EXTERNAL-IP is assigned.
APP_IP=$(kubectl -n oke-lab get svc hello-oke -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl --fail --max-time 10 "http://${APP_IP}/"
```

You can also open `http://<EXTERNAL-IP>/` in the desktop browser. The response contains your message and the responding pod's name. The endpoint is public and unauthenticated: use only training data, not secrets. If the IP stays Pending or the request fails, ask the instructor and see [troubleshooting](docs/troubleshooting.md).

Enable baseline traffic so metrics can accumulate before you open Kiali and Grafana:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set traffic.enabled=true --wait --timeout 10m
kubectl -n oke-lab logs deployment/hello-oke-traffic -c traffic --tail=10
```

The traffic generator makes one request approximately every two seconds. Leave it running during the exercise so Kiali can show a client-to-service edge.

**Checkpoint:** your application responds with the customized message, two app replicas are ready, and the traffic generator is running.

## 4. Explore traffic in Kiali and Grafana — 5 minutes

### Kiali: service-to-service traffic

In a second terminal on the **same Luna desktop**:

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
kubectl -n istio-system port-forward --address 127.0.0.1 svc/kiali 20001:20001
```

Open **http://localhost:20001/kiali** in the browser **inside that desktop**. Your laptop's localhost is different. Keep the terminal running; do not bind to `0.0.0.0`.

Select namespace `oke-lab`, open the traffic graph, choose a recent time range (such as last five minutes), and enable refresh. Allow a minute or two for metrics. Find `hello-oke-traffic → hello-oke` and inspect request rate, success rate, and latency. Kiali visualizes traffic; the application's response is at the LoadBalancer URL.

### Grafana: metrics over time

Leave the Kiali port-forward running. In a third terminal on the same desktop:

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
kubectl -n istio-system port-forward --address 127.0.0.1 svc/grafana 13000:80
```

Open **http://127.0.0.1:13000/d/oke-lab** in the desktop browser. No login is needed for Viewer access. Keep both port-forward terminals open and use the first terminal for lab commands. If a dashboard pod is replaced, restart its port-forward.

The **OKE Lab — Traffic & Scaling** dashboard opens with a 30-minute range and 15-second refresh. At baseline, look for:

- **Requests / second:** approximately 0.5 from the traffic generator.
- **Successful requests:** near 100% for healthy traffic; it counts HTTP 2xx/3xx responses.
- **Application proxies up:** two successfully scraped application proxies, excluding the generator.
- **Istiod scrape health:** `1` means Prometheus can scrape Istiod; this is not a complete control-plane health check.
- **Traffic, latency, response codes, and proxy-count graphs:** history to compare with the upcoming load burst.

The proxy-count panel is a scaling indicator, **not HPA desired replicas or pod readiness**. Scrape discovery can lag pod changes. Check `kubectl get hpa` and `kubectl get pods` for authoritative replica/health status. Missing data does not mean zero traffic or a healthy system; see [troubleshooting](docs/troubleshooting.md).

**Checkpoint:** find `hello-oke-traffic → hello-oke` in Kiali and record the Grafana baseline request rate, success rate, latency, and proxy count. Keep both dashboards open for scaling. The [monitoring guide](docs/monitoring.md) explains the underlying Prometheus queries and optional exercises.

## 5. Scale manually and automatically — 15 minutes

### Scale manually

Increase the application from two to four replicas:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set replicaCount=4 --wait --timeout 10m
kubectl -n oke-lab get pods -l app=hello-oke -o wide
kubectl -n oke-lab get deployment hello-oke
for request in {1..10}; do curl --fail --max-time 10 "http://${APP_IP}/"; done
```

Expect four ready app replicas without changing the Service IP. Responses may show different pod names, but equal distribution across a short sequence is not guaranteed. The nodes have not changed.

Restore the starting size before enabling the HPA:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set replicaCount=2 --wait --timeout 10m
```

### Enable CPU autoscaling

First verify the cluster's resource metrics:

```bash
kubectl top nodes
kubectl -n oke-lab top pods --containers
```

If metrics are unavailable, stop here and ask the instructor to check Metrics Server. **The Prometheus used by Kiali and Grafana does not supply this HPA's CPU metrics.**

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set autoscaling.enabled=true --wait --timeout 10m
kubectl -n oke-lab get hpa hello-oke
kubectl -n oke-lab describe hpa hello-oke
```

The HPA manages **2–6 application pods** and targets 60% of the `web` container's CPU request: `60m` per pod with our `100m` request. It excludes the Istio sidecar's CPU. Wait for a numeric current utilization and `ScalingActive=True` before generating load. A brief replica-count dip can occur when transferring ownership from Helm to the HPA; let it settle at two ready replicas. Do not manually scale the Deployment while the HPA owns its replica count.

### Generate a five-minute CPU load

The traffic generator sends two concurrent request streams to `/work`, then automatically returns to its low-rate `/` traffic after approximately five minutes. Run this only in your assigned lab cluster.

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set traffic.loadEnabled=true --wait --timeout 10m
kubectl -n oke-lab get hpa hello-oke --watch
# Observe CPU and replica changes for several minutes; Ctrl+C stops only the watch.
```

In another desktop terminal:

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
kubectl -n oke-lab top pods --containers
kubectl -n oke-lab get pods -l app=hello-oke -o wide
kubectl -n oke-lab logs deployment/hello-oke-traffic -c traffic --tail=10
```

Watch Grafana's **Traffic through Istio**, **Request latency**, and **Application proxy count — scaling indicator** panels alongside the HPA watch. Compare request rate and latency with the baseline, check success rate/response codes, and confirm the traffic edge remains visible in Kiali. The HPA should add pods when sustained CPU exceeds its target; the exact count depends on available CPU and demand, not a guaranteed six replicas. If pods stay Pending or utilization stays `<unknown>`, use [troubleshooting](docs/troubleshooting.md); do not enlarge the node pool.

### Stop load and observe scale-in

Explicitly reset burst mode after the test (this also stops an active burst early):

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set traffic.loadEnabled=false --wait --timeout 10m
kubectl -n oke-lab get hpa hello-oke --watch
# Wait for CPU to settle and replicas to return to two, then press Ctrl+C.
```

This lab shortens the downscale stabilization window to 60 seconds; metrics collection and reconciliation add delay, so allow several minutes. Kubernetes normally defaults to a five-minute window. The burst timer starts again if the traffic pod restarts while burst mode is enabled; resetting the flag prevents another burst.

Keep Grafana's range at **Last 30 minutes** to see the whole burst. Confirm request rate returns toward baseline and proxy count follows scale-in; the historical peak should remain visible. Prometheus retains two hours of data but loses it if its pod is replaced. Record observations before ending the session.

**Checkpoint:** record initial, peak, and final HPA replica counts and compare them with Grafana's proxy-count graph. Explain CPU request vs limit, manual scaling vs HPA, and pod scaling vs node scaling. HPA changes application replicas, not node-pool capacity; Grafana displays Prometheus telemetry, while Metrics Server supplies this HPA's CPU input. See the [Kubernetes HPA guide](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) for the metric and stabilization behavior.

## 6. Optional: observe pod recovery — 5 minutes

Do this only if time remains after observing scale-in. Leave baseline traffic running. Delete **one application pod**, not the Deployment:

```bash
POD_TO_REPLACE=$(kubectl -n oke-lab get pods -l app=hello-oke -o jsonpath='{.items[0].metadata.name}')
kubectl -n oke-lab delete pod "$POD_TO_REPLACE"
kubectl -n oke-lab get pods -l app=hello-oke --watch
# Press Ctrl+C once a replacement pod is Ready.
kubectl -n oke-lab rollout status deployment/hello-oke --timeout=300s
curl --fail --max-time 10 "http://${APP_IP}/"
kubectl -n oke-lab get events --sort-by=.lastTimestamp
```

**Checkpoint:** identify the replacement's new name. The Deployment's ReplicaSet restores the desired number of pods; this is self-healing, not an HPA scale-out. The Service IP stays the same. Inspect Kiali for any transient errors; deleting one of several healthy replicas need not cause a visible outage.

## 7. Finish the lab

You are finished when you have deployed your customized application, observed the Kiali traffic graph and Grafana metrics, and seen replicas increase and decrease with demand. Stop local watches and both dashboard port-forwards with Ctrl+C when you no longer need them. This does not uninstall the dashboards or stop the in-cluster traffic generator; burst mode must already be disabled in step 5.

**No manual resource cleanup is required from students.** Leave the application and Helm releases installed. Luna starts automated resource cleanup when the session ends or expires. Stopping CPU load in step 5 is part of observing scale-in, not a cleanup task.

## Instructor notes

A [local Phoenix rehearsal](docs/rehearsal-2026-09-18.md) successfully provisioned OKE without GitLab and verified the application, mesh, manual scaling, and CPU-driven HPA scale-out and scale-in (2 → 6 → 2). Browser checks verified Kiali and Grafana, including Grafana's rendering of that scaling history. Luna provisioning, session-end cleanup, the revised classroom timing, and concurrent learner capacity still need validation after the Luna VCN quota issue is resolved. Before publishing:

- Target a 90-minute session: introduction and provisioning in minutes 0–30, core hands-on work in minutes 30–85, and minutes 85–90 for questions or delays. Add pod recovery only when ahead of schedule; the full 60-minute hands-on version leaves no buffer. Provisioning within 30 minutes is a prerequisite, not a verified Luna result. If rehearsal misses the target, arrange earlier provisioning rather than silently consuming the hands-on time. This repository does not change Luna's time limit.
- Verify desktop tools (`oci`, `kubectl`, `helm`, `git`, and `curl`), current-session connection details, cluster-admin lab permissions, image access, and supported Kubernetes/Istio versions. Supply connection values and the clone URL before the hands-on segment. Ensure Metrics Server is ready with the cluster; never work around certificate problems by disabling TLS verification. Istio, Prometheus, Kiali, and Grafana remain student installations.
- Time the entire student workflow, including Grafana installation, chart/image downloads, cloud load-balancer readiness, and the five-minute CPU burst plus scale-in. The 55–60 minute agenda is a target, not a guarantee. Omit pod recovery and the additional monitoring exercises if time is tight.
- Students leave resources installed. Verify session-end automation removes the Kubernetes LoadBalancer before infrastructure destruction, without a student uninstall. Monitor the cleanup job through completion; charges continue until resources are deleted. Rehearse this path with the full Helm workload, not only a partially provisioned cluster.
- Complete security checks for the chart and runtime images before release. The existing CI scanner-image allowlist blocker is unresolved; passing local functional tests is not a security-scan result.
- Check allocatable capacity for up to six application pods plus proxies, traffic, Istio, Prometheus, Kiali, Grafana, and system pods. Grafana requests 100m CPU/256Mi memory, with 500m CPU/512Mi memory limits. Validate at expected concurrent learner count; do not promise the 2–6 range without a capacity check. Student actions create one cloud load balancer but no additional nodes or telemetry volumes.
- Supply the learner clone URL and tag. The separate GitHub repository is not published yet; owner/name/visibility still need to be selected. Never distribute infrastructure state or credentials with learner materials.

Suggested Luna description: **Build, run, and scale an application on a pre-provisioned OKE cluster. Customize a Helm deployment, expose it through an OCI LoadBalancer, and use Istio, Prometheus, Kiali, and Grafana to observe traffic and scaling. Test manual scaling and CPU-based autoscaling, with optional pod recovery.**

- [Infrastructure and CI administration](docs/gitlab-ci.md)
- [Maintainer-only local Terraform workflow](docs/maintainer-infrastructure.md)
- [Cleanup responsibilities](docs/cleanup.md)
- [Chart sources and packaging](helm/README.md)

`terraform/` and CI scripts are instructor-managed infrastructure. `charts/` and `helm/` are learner deployment materials. `kubernetes/` retains the earlier non-Helm exercise for maintainers.
