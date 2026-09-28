# OKE Bootcamp: Build, Run, and Scale Kubernetes on OCI

Luna provisions your Oracle Kubernetes Engine (OKE) cluster. Use Helm to deploy an application and install Istio, Prometheus, Kiali, and Grafana to observe its traffic and scaling.

This **60-minute hands-on lab and debrief** follows a 30-minute lecture while the cluster provisions (**90 minutes total**). Compare traffic and latency, scale the app manually and automatically, and optionally test pod recovery. Luna handles cluster creation and cleanup.

This lab assumes you can navigate a terminal, copy commands, and edit a YAML value. By the end, you should be able to:

- Customize and deploy an application with Helm, then explain how its Service reaches its pods.
- Identify the application container and its Istio proxy, and follow traffic in Kiali.
- Compare baseline and load metrics using your Grafana readings.
- Explain manual scaling, CPU-driven autoscaling, and why neither adds worker nodes in this lab.
- Distinguish readiness from liveness and use pod events to investigate a health warning.

Run commands in a **Bash terminal on the Luna desktop**. Keep session credentials private.

Materials revision: `lab-2026-09-28.3`. Your checkout and Luna instructions must show this same revision.

Record checkpoints in the [completion sheet (PDF)](docs/completion-sheet.pdf) or [Markdown version](docs/completion-sheet.md). You can save or print the PDF.

![OKE lab architecture: application requests through an OCI LoadBalancer, Prometheus feeding Kiali and Grafana, and Metrics Server supplying CPU metrics to the HPA.](docs/images/oke-lab-architecture.png)

The diagram shows the setup after traffic and autoscaling are enabled, not live health. [View full-size](docs/images/oke-lab-architecture.png) or read the [component guide](docs/architecture.md).

## Schedule

| Approximate hands-on minutes | Exercise | What you will demonstrate |
|---|---|---|
| 0–5 | 1. Prepare your connection | Download lab files, connect to your cluster, and verify resource metrics |
| 5–23 | 2. Install mesh and monitoring | Install Istio, Prometheus, Kiali, and Grafana with Helm |
| 23–33 | 3. Build and run | Customize and deploy two replicas with an OCI LoadBalancer |
| 33–40 | 4. Observe traffic | Interpret the Kiali graph and Grafana baseline |
| 40–55 | 5. Scale | Scale manually, then observe CPU-driven scale-out and scale-in |
| 55–60 | 7. Debrief and buffer | Explain your observations and absorb delays |

Step 6, pod recovery, is optional: do it only if step 5 is complete by minute 50. Save the last five minutes for debrief and delays. Direct Prometheus queries, controlled outages, and OCI alarms are extensions outside this hour.

Times include setup, reading, commands, waits, and interpretation. Downloads and cluster readiness vary; ask for help at blocked checkpoints.

## Before hands-on: start preparation at the beginning of the lecture

Start the Luna lab when the lecture begins so the cluster can provision during the lecture.

## 1. Prepare and confirm your connection — 5 minutes

In a **Bash terminal** on your Luna desktop, download the lab repository. Keep this window open as **terminal 1**:

```bash
git clone --branch lab-2026-09-28.3 --single-branch \
  https://github.com/chiphwang1/AI_world_lab.git "$HOME/oke-bootcamp" &&
  cd "$HOME/oke-bootcamp"
```

### Find your lab login and compartment

Sign in with your temporary Luna account:

1. Double-click **Luna-Lab** (or **Luna Lab**) on the desktop. Keep this session-information page open.
2. Under **Quick Links**, click **OCI Console** to open the sign-in tab.
3. Copy your assigned username and password from **Credentials** into **User Name** and **Password**. **Do not use the SSO Link.**
4. Paste with **Ctrl+V** or right-click **Paste**, then click **Sign In**.
5. Return to Luna Lab and note your **Compartment Name** and **region** under **Lab Details** (or the **Oracle Cloud** section). Use these to select your cluster.

If session details are missing, stop and ask the instructor; do not use a personal account or another learner's credentials. See [Oracle's Luna login instructions](https://docs.oracle.com/en/learn/build-cloud-native-java-applications-with-micronaut-and-graalvm/lab1/configure-db-access.html); its database exercises do not apply here.

### Open your own cluster in the OCI Console

Use the assigned compartment and region shown in Luna Lab.

1. Select your **region** in the OCI Console. Open the upper-left navigation menu → **Developer Services → Containers & Artifacts → Kubernetes Clusters (OKE)**. See [Oracle's navigation instructions](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/list-clusters.htm).
2. Open the **Compartment** filter. Expand the compartment hierarchy if needed and select the exact **Compartment Name** shown on your Luna Lab page. Do not choose a compartment just because its name begins with `luna`, and do not use the tenancy root.
3. Open the cluster Luna created for you. If it is still provisioning, wait until it is ready.

   **Example page only—not a shared student cluster:** [Phoenix cluster details](https://cloud.oracle.com/containers/clusters/ocid1.cluster.oc1.phx.aaaaaaaa5mwgyqarbllvk7xavr2qkvipop7ihd6i4i5vejaoxctcyaybtyaq?region=us-phoenix-1). Use your own cluster's OCID and region.

   To construct the details URL manually, replace both placeholders:

   ```text
   https://cloud.oracle.com/containers/clusters/<your-cluster-ocid>?region=<your-region>
   ```

4. On your cluster's details page, open **Actions → Access cluster → Local Access**. “Local” means the terminal on your Luna desktop, not your personal laptop.
5. In **terminal 1**, run `umask 077` and `mkdir -p "$HOME/.kube"`.
6. Copy and **run** the displayed `oci ce cluster create-kubeconfig` command in terminal 1 to create your kubeconfig. Change `--file` to `"$HOME/.kube/oke-lab"`; keep **your cluster's** OCID, region, and endpoint. Use the [desktop OCI authentication settings](docs/cluster-access.md#generate-your-kubeconfig-on-the-desktop). Do not add `--overwrite`.

### Verify your kubeconfig

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
ls -l "$KUBECONFIG" &&
test -s "$KUBECONFIG" &&
kubectl config get-contexts &&
kubectl config current-context
```

### Check cluster readiness

In terminal 1, run preflight from the repository root:

```bash
bash scripts/check-ready.sh
```

Preflight checks files, tools, API access, version compatibility, two Ready workers, and resource metrics using your current kubeconfig context. It makes no cluster changes. OCI CLI must remain available to generate authentication tokens.

Expect these lines and numeric CPU/memory readings (values vary):

```text
PASS Workers: 2/2 Ready and not cordoned
PASS Resource metrics: numeric CPU and memory for both workers
```

Continue only after `Preflight passed`. On `FAIL`, follow its message or ask the instructor; see [preflight troubleshooting](https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps#preflight-fails).

Load the chart-version variables, download the five pinned Helm charts, and check the files. Downloads are saved in `.lab-cache/charts/`; these commands do not install anything in the cluster:

```bash
source helm/versions.env
bash scripts/prepare-charts.sh --download &&
bash scripts/prepare-charts.sh --check
```

Expect five `PASS Prepared chart` lines from each successful command. Matching downloads are reused if you rerun it. On failure, follow the message or ask for help. The Git tag pins lab files, and `helm/versions.env` pins upstream charts.

Continue after preflight and all five chart checks pass. Keep terminal 1 open for later commands.

### Confirm your prepared connection

In terminal 1, confirm your directory, context, workers, and resource metrics:

```bash
pwd
kubectl config current-context
kubectl get nodes
kubectl top nodes
```

Expect a path ending in `oke-bootcamp`, your cluster's context, two `Ready` workers, and numeric CPU/memory readings. Ask for help if they differ.

**Checkpoint:** confirm those results. Which file selects your Kubernetes connection, and which component supplies CPU metrics?

`KUBECONFIG` points to `~/.kube/oke-lab`; the selected context inside that file identifies the cluster and user. Metrics Server supplies the resource metrics used by `kubectl top` and this lab's HPA; Prometheus supplies the dashboard metrics. See [kubectl top node](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_top/kubectl_top_node/).

## 2. Install Istio, Prometheus, Kiali, and Grafana — 18 minutes

### What the tools do

| Tool or component | Purpose in this lab | Setup |
|---|---|---|
| Helm | Installs and upgrades Kubernetes resources packaged as charts. | Already on the desktop |
| Istio | Adds proxies beside app containers to manage traffic and report request metrics. | You install it below |
| Prometheus | Stores Istio metrics for dashboard queries. | You install it below |
| Kiali | Maps service traffic, request rates, errors, latency, and workload health. | You install it below |
| Grafana | Charts metrics to compare baseline traffic, load, and scaling. | You install it below |
| Metrics Server | Supplies CPU and memory readings to `kubectl top` and CPU metrics to this lab's HPA. | Provided with the cluster |
| Cert Manager | Manages TLS certificates; it is a dependency of this OCI-managed Metrics Server add-on. | Provided with the cluster |
| HPA | Adjusts app replicas using CPU metrics; it does not add worker nodes. | You enable it in step 5 |

`kubectl` manages Kubernetes resources; OCI CLI authenticates the connection. Both are preinstalled. The [architecture diagram](docs/architecture.md) separates dashboard and HPA metrics paths.

A **namespace** groups resources: monitoring uses `istio-system`; the app uses `oke-lab`. Select it with Helm's `--namespace` or kubectl's `-n`.

### Install Istio

Istio uses **sidecar mode**, adding a proxy beside each app container.

A **chart** packages Kubernetes templates; a **release** is its named installation. `upgrade --install` creates or updates a release, `-f` supplies lab values, and `--wait` waits for readiness. You install the charts downloaded in step 1. Workers may still need to pull images.

**For every Helm install or upgrade:** expect `STATUS: deployed` and a returned prompt. Ask for help on errors or timeouts before continuing.

Install Istio base for its custom resource definitions (CRDs, extra Kubernetes object types), then `istiod`, the control plane. While waiting, trace the metrics path on the [architecture diagram](docs/architecture.md).

```bash
helm upgrade --install istio-base ".lab-cache/charts/base-${ISTIO_VERSION}.tgz" \
  --namespace istio-system --create-namespace \
  --set defaultRevision=default --wait --timeout 10m
helm upgrade --install istiod ".lab-cache/charts/istiod-${ISTIO_VERSION}.tgz" \
  --namespace istio-system \
  -f helm/values/istiod.yaml --wait --timeout 10m
kubectl -n istio-system rollout status deployment/istiod --timeout=300s

kubectl create namespace oke-lab --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace oke-lab istio-injection=enabled --overwrite
```

Expect `deployment "istiod" successfully rolled out` and confirmation that `oke-lab` was labeled. The label tells Istio to add a proxy to **new pods** in that namespace. Do not label `istio-system` for injection.

### Install Prometheus

Prometheus stores metrics temporarily; replacing its pod loses metric history.

```bash
helm upgrade --install prometheus ".lab-cache/charts/prometheus-${PROMETHEUS_CHART_VERSION}.tgz" \
  --namespace istio-system \
  -f helm/values/prometheus.yaml --wait --timeout 10m
```

Application traffic metrics appear after you deploy the app and start the traffic generator.

### Install Kiali

The Kiali values file connects it to the Prometheus instance you just installed.

```bash
helm upgrade --install kiali-server ".lab-cache/charts/kiali-server-${KIALI_CHART_VERSION}.tgz" \
  --namespace istio-system \
  -f helm/values/kiali.yaml --wait --timeout 10m
```

Open Kiali in step 4, after the app and traffic generator are running.

### Install Grafana

Install Grafana with the supplied dashboard and Prometheus data source. All three monitoring tools stay internal, with no persistent telemetry volumes.

```bash
helm upgrade --install grafana ".lab-cache/charts/grafana-${GRAFANA_CHART_VERSION}.tgz" \
  --namespace istio-system \
  -f helm/values/grafana.yaml \
  --set-file dashboards.default.oke-lab.json=helm/dashboards/oke-lab.json \
  --wait --timeout 10m
helm list --namespace istio-system
kubectl -n istio-system get pods,svc
```

Kiali and Grafana allow anonymous, read-only access. **Never expose them with a public LoadBalancer or Ingress:** anyone reaching them can query metrics. Production needs authentication and network controls. Helm configures Grafana's dashboard and data source; use step 4's Viewer URL instead of the generic administrator-login instructions.

**Checkpoint:** all five releases (`istio-base`, `istiod`, `prometheus`, `kiali-server`, `grafana`) show deployed and workload pods are ready. Why install Istio base first? Why does Grafana need Prometheus?

## 3. Build and run the application — 10 minutes

A **Deployment** maintains application copies (replicas), each in a **Pod** with an Istio proxy. A **Service** provides a stable address as pods change. Helm creates these objects from the app chart.

Open `helm/values/student.yaml` in the desktop editor and customize `message`, for example:

```yaml
message: "Hello from YOUR-NAME's OKE lab"
```

Replace `YOUR-NAME`, save, and leave replicas and resource settings unchanged. **Build** here means configuring the deployment; the chart supplies Python code and its runtime. No image registry account is needed.

Lint the chart, install release `hello-oke`, then list its Deployment (`deploy`), pods, and Service (`svc`):

```bash
helm lint ./charts/oke-mesh-app -f helm/values/student.yaml --strict
helm upgrade --install hello-oke ./charts/oke-mesh-app \
  --namespace oke-lab -f helm/values/student.yaml --wait --timeout 10m
kubectl -n oke-lab get deploy,pods,svc
```

Expect `0 chart(s) failed` (an icon recommendation is informational), a `2/2` Ready Deployment, and two `2/2 Running` pods. Each pod's `2/2` means both `web` (HTTP app) and `istio-proxy` (mesh traffic) are ready.

For optional container inspection or troubleshooting, see [Appendix B](https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps#appendix-b-optional-pod-inspection).

The Service requests an OCI LoadBalancer. Save its public IP for later commands:

```bash
APP_IP=$(kubectl -n oke-lab get svc hello-oke -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "$APP_IP"
```

If blank, check `kubectl -n oke-lab get svc hello-oke`. For `<pending>`, wait 30 seconds and rerun the assignment and echo; ask for help after three minutes. Continue once `APP_IP` contains an IP.

Test the application in the same terminal:

```bash
curl --fail --max-time 10 "http://${APP_IP}/"
```

Expected response (illustrative; your message and pod name will differ):

```json
{"message":"Hello from YOUR-NAME's OKE lab","pod":"hello-oke-example-abc12","work":false}
```

You can also open `http://<EXTERNAL-IP>/` in the desktop browser. Backends may become healthy after IP assignment: retry HTTP after 15–30 seconds; ask for help after a minute ([troubleshooting](docs/troubleshooting.md)). This public, unauthenticated endpoint must contain only training data.

Enable baseline traffic and inspect its logs. `--reuse-values` keeps your existing release settings, including your message; `--set traffic.enabled=true` enables the generator:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set traffic.enabled=true --wait --timeout 10m
kubectl -n oke-lab logs -l app=hello-oke-traffic -c traffic --prefix --timestamps --tail=10
```

Expect JSON responses with your message and pod names about every two seconds. Leave the generator running.

**Checkpoint:** the app returns your customized message, two app replicas are ready, and the generator is running. Find `web` and `istio-proxy` in the architecture diagram and explain each container's job. Would replacing a pod require a new Service IP? If HTTP or traffic is still failing, ask for help before continuing.

## 4. Explore traffic in Kiali and Grafana — 7 minutes

A Kubernetes Service gives an application a stable network address, even when its pods change. Port-forwarding lets you access that Service from your Luna desktop using a local port. Use three terminals on the **same Luna desktop**:

| Terminal | Purpose |
|---|---|
| 1 | Lab commands at the repository root |
| 2 | Kiali port-forward; leave running |
| 3 | Grafana port-forward; leave running |

Set `KUBECONFIG` once in each new terminal, substituting your path if different. The selected context stays saved in the file until changed. Open forwards while baseline metrics accumulate.

### Kiali: service-to-service traffic

In **terminal 2** on the same Luna desktop:

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
kubectl -n istio-system port-forward --address 127.0.0.1 svc/kiali 20001:20001
```

Expect `Forwarding from 127.0.0.1:20001`; the command stays running. Open **http://localhost:20001/kiali** in the **Luna desktop browser**—your laptop's localhost is different. Do not bind to `0.0.0.0`.

Select `oke-lab`, open the traffic graph, choose **Last 5 minutes**, and enable refresh. Allow 1–2 minutes for metrics. Find `hello-oke-traffic → hello-oke` and inspect request rate, success, and latency.

If Kiali shows **Degraded**, see [Kiali health warnings in Appendix A](https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps#kiali-health-warnings).

### Grafana: metrics over time

Leave the Kiali port-forward running. In **terminal 3** on the same desktop:

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
kubectl -n istio-system port-forward --address 127.0.0.1 svc/grafana 13000:80
```

Expect `Forwarding from 127.0.0.1:13000`. Open **http://127.0.0.1:13000/d/oke-lab** in the desktop browser; Viewer access needs no login. For failed access or `address already in use`, see [port-forward troubleshooting](https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps#troubleshooting-dashboard-port-forwards).

The **OKE Lab — Traffic & Scaling** dashboard opens with a 30-minute range and 15-second refresh. At baseline, look for:

- **Requests / second:** the average request rate over the last minute. Expect about 0.5 (one request every two seconds).
- **Successful requests:** the percentage of requests with HTTP 2xx/3xx responses. Expect near 100% for healthy traffic.
- **Request latency, p95:** estimated response time at the 95th percentile. A p95 of 100 ms means about 95% of requests finished within 100 ms. Record p95, not the average or p50.
- **Application proxies up:** two successfully scraped application proxies, excluding the generator.
- **Istiod scrape health:** `1` means Prometheus can scrape Istiod; this is not a complete control-plane health check.
- **Traffic, latency, response codes, and proxy-count graphs:** history to compare with the upcoming load burst.

**Proxy count is not HPA desired replicas or pod readiness**; scrape discovery can lag. Confirm two Ready pods with `kubectl -n oke-lab get pods -l app=hello-oke`. The HPA is enabled in step 5, so record baseline HPA as `Not enabled`. Empty panels mean `no data`, not zero traffic or health ([troubleshooting](docs/troubleshooting.md)).

**Checkpoint:** record baseline request rate, success rate, p95 latency, and proxy count in your [completion sheet (PDF)](docs/completion-sheet.pdf). Explain the baseline using the Kiali traffic edge and one Grafana reading. Which component supplies both views?

Keep both dashboards open, using the same Grafana time range and p95 statistic throughout scaling. The [monitoring guide](docs/monitoring.md) covers queries and optional exercises.

Ask for help if panels remain empty after two minutes of traffic.

## 5. Scale manually and automatically — 15 minutes

Return to **terminal 1 at the repository root**, using your verified lab context; leave both port-forwards running. For a new terminal, see [fresh-terminal setup in Appendix A](https://luna.oracle.com/lab/8f468598-9993-41b8-92ce-e643f5603f9b/steps#fresh-terminal-setup-errors).

### Scale manually

Before scaling, predict what will happen to the app pod count, worker count, and Service IP. Note your predictions beside question 3 on the completion sheet, then increase the application from two to four replicas:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set replicaCount=4 --wait --timeout 10m
kubectl -n oke-lab get pods -l app=hello-oke -o wide
kubectl -n oke-lab get deployment hello-oke
kubectl get nodes
kubectl -n oke-lab get svc hello-oke
for request in {1..10}; do curl --fail --max-time 10 "http://${APP_IP}/"; done
```

Compare replicas, workers, Service IP, and response pod names with your predictions. Expect four Ready app replicas, unchanged Service IP, and two workers. A short request sequence need not reach each pod equally.

**Readiness and liveness:** a pod can be `Running` while its app or Istio proxy is still initializing. In this lab, `2/2` means both are ready.

| Probe | Question it answers | What a failed check does after its failure threshold |
|---|---|---|
| Readiness | Can this container accept traffic now? | Marks the pod not Ready, keeping it out of normal Service traffic; does not restart the container. |
| Liveness | Does this container need restarting? | Triggers a restart of the failing container, not replacement of the whole Deployment. |

The [app chart](charts/oke-mesh-app/templates/application.yaml) checks `/healthz` for both probes; liveness starts after a 10-second initial delay. Inspect the `READY` and `RESTARTS` columns above. Could a pod be `Running` but not ready, with zero restarts? Record your reasoning under question 5 on the completion sheet. See the [Kubernetes probe guide](https://kubernetes.io/docs/concepts/workloads/pods/probes/) for more detail.

Restore the starting size before enabling the HPA:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set replicaCount=2 --wait --timeout 10m
```

### Enable CPU autoscaling

Check worker and per-container CPU/memory readings:

```bash
kubectl top nodes
kubectl -n oke-lab top pods --containers
```

Expect numeric readings in the CPU and memory columns. If metrics are unavailable, stop here and ask the instructor to check Metrics Server. **The Prometheus used by Kiali and Grafana does not supply this HPA's CPU metrics.**

Enable the HPA to control app replicas, then inspect its target and conditions:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set autoscaling.enabled=true --wait --timeout 10m
kubectl -n oke-lab get hpa hello-oke
kubectl -n oke-lab describe hpa hello-oke
```

Expected `get hpa` output once baseline metrics are available (illustrative; age and CPU vary):

```text
NAME        REFERENCE              TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
hello-oke   Deployment/hello-oke    cpu: 1%/60%   2         6         2          1m
```

The HPA manages **2–6 application pods** and targets average CPU utilization of 60% of the `web` container's `100m` request, equivalent to `60m` per pod. It excludes the Istio sidecar's CPU. `100m` is one tenth of a CPU; the request is used for scheduling and HPA utilization, while the `250m` CPU limit caps the container's CPU use.

Rerun the two HPA checks until utilization is numeric and `ScalingActive=True`; ask for help after two minutes without metrics. Let any brief Helm-to-HPA replica dip settle at two Ready replicas before load. Do not manually scale while the HPA controls replicas.

If the CPU request were `200m` with the same 60% target, what CPU usage would that mean? Write your calculation in the completion sheet's prediction field. Keep the lab's resource settings unchanged.

### Generate a five-minute CPU load

Start by minute 47 to allow scale-in before minute 55. The generator sends two concurrent streams to `/work` for five minutes, then returns to low-rate `/` traffic:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set traffic.loadEnabled=true --wait --timeout 10m
kubectl -n oke-lab get hpa hello-oke --watch
# Observe CPU and replica changes for several minutes; Ctrl+C stops only the watch.
```

To inspect CPU and logs, press Ctrl+C in **terminal 1** to stop only the watch, then run:

```bash
kubectl -n oke-lab top pods --containers
kubectl -n oke-lab get pods -l app=hello-oke -o wide
kubectl -n oke-lab logs -l app=hello-oke-traffic -c traffic --prefix --timestamps --tail=10
```

Resume `kubectl -n oke-lab get hpa hello-oke --watch` as needed. Traffic logs show burst completion; prefixes and timestamps distinguish old and new generator pods during rollouts. Leave dashboard forwards running.

Watch Grafana's **Traffic through Istio**, **Request latency**, and **Application proxy count — scaling indicator** alongside the HPA. Record load readings, peak replicas, and success/response codes; check the Kiali traffic edge. Six replicas is a limit, not a guaranteed peak. For Pending pods or `<unknown>` CPU, use [troubleshooting](docs/troubleshooting.md); do not enlarge the node pool.

Baseline `/` and burst `/work` do different work; two concurrent streams produce a variable request rate. Because both workload and replicas change, this comparison cannot isolate autoscaling's effect on latency.

Use one baseline reading and one load reading to compare request rate, p95 latency, and replicas with your partner. Explain the HPA and dashboard data sources. Record results even if they differ from your prediction.

### Stop load and observe scale-in

Explicitly reset burst mode after the test (this also stops an active burst early):

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set traffic.loadEnabled=false --wait --timeout 10m
kubectl -n oke-lab get hpa hello-oke --watch
# Wait for CPU to settle and replicas to return to two, then press Ctrl+C.
# If this takes more than three minutes, stop the watch and ask the instructor.
```

Downscale stabilization is 60 seconds here (Kubernetes defaults to five minutes); metrics and reconciliation add delay. Reset the burst flag even after automatic completion: a generator restart with burst mode enabled starts another burst.

Confirm two Ready pods with `kubectl -n oke-lab get pods -l app=hello-oke`. Keep Grafana at **Last 30 minutes**: rate should approach baseline and proxy count follow scale-in, retaining the peak. Prometheus retains two hours of data unless its pod is replaced. If blocked at minute 55, record the state and ask for help.

**Checkpoint:** record initial, peak, and final HPA replicas. Finish when HPA and Ready app pods both return to two. Explain any lag in Grafana proxy count; complete the observation table and questions 2–4. See the [HPA guide](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) for metrics and stabilization.

## 6. Optional: observe pod recovery — 5 minutes

Only proceed if step 5 finishes by minute 50; otherwise skip to step 7. Leave baseline traffic running. Predict whether deleting one pod changes desired replicas, then delete **one app pod**, not its Deployment:

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

Stop watches and dashboard forwards with Ctrl+C; this leaves the releases and in-cluster generator running. Check that burst mode is disabled:

```bash
helm get values hello-oke --namespace oke-lab
```

Confirm `traffic.loadEnabled: false`; baseline traffic remains enabled. Complete your [sheet and debrief (PDF)](docs/completion-sheet.pdf), discuss readings and peak replicas with a partner or instructor, and record blocked checkpoints honestly.

**Leave the app and Helm releases installed.** Luna starts cleanup when the session ends or expires.

## Appendix A: Troubleshooting

Use the matching symptom, then return to your lab step. Appendix links open Luna Lab Steps; offline, scroll to the heading. These are optional diagnostics; also see the [full troubleshooting guide](docs/troubleshooting.md).

### Preflight fails

Correct the first `FAIL` before rerunning preflight; the script stops there without repairing anything.

- Missing repository files: return to the checkout root or ask for the complete checkout.
- Missing tool or unsupported kubectl version: ask the instructor to check the actual Bash `PATH`; do not run `scripts/ci-tools.sh` on the desktop.
- Missing kubeconfig, wrong context, or authentication failure: follow [cluster access](docs/cluster-access.md#verify-the-selected-file-and-context).
- Workers or resource metrics not ready: ask the instructor to check provisioning and the managed Metrics Server add-on. Do not resize the node pool or reinstall add-ons.

### Fresh-terminal setup errors

In a new terminal, use the existing checkout, `KUBECONFIG`, and required OCI settings. Verify `kubectl config current-context`. A correct saved context needs no reselection or regenerated kubeconfig.

- `path "./charts/oke-mesh-app" not found`: the relative chart path is wrong for your current directory. Return to the repository root, where `README.md`, `charts/`, and `helm/` are located.
- Connection refused at `localhost:8080`: usually no usable cluster configuration was selected. Follow [cluster access](docs/cluster-access.md#verify-the-selected-file-and-context); changing directories alone does not select a cluster.
- `zsh: command not found: #` or `Ctrl+C`: use the lab's Bash terminal, or omit lines beginning with `#` when pasting into interactive zsh. **Ctrl+C is a keyboard shortcut**, not a command to paste.

Run Helm in terminal 1 and forwards separately. Fix directory and connection errors individually; do not reinstall the lab to fix terminal setup.

### Troubleshooting: dashboard port-forwards

For failed dashboard access or `address already in use`, run these read-only checks in **terminal 1 on the same desktop**. Forwards are local processes, not Kubernetes resources; there is no `kubectl get port-forwards` command.

**1. Show which processes are listening on the dashboard ports.** On macOS or Linux with `lsof`:

```bash
lsof -nP -iTCP:13000 -iTCP:13001 -iTCP:20001 -iTCP:20002 -sTCP:LISTEN
```

`COMMAND`/`PID` identify the process; `NAME` shows address/port. Expect `kubectl` (possibly truncated) on `127.0.0.1:13000` (Grafana) and `127.0.0.1:20001` (Kiali). Alternatives are `13001`/`20002`. No row means no visible listener; a listener alone does not prove access.

If `lsof` is unavailable on the Linux Luna desktop, use:

```bash
ss -ltnp '( sport = :13000 or sport = :13001 or sport = :20001 or sport = :20002 )'
```

**2. Test the forwarded dashboard.** These commands use the default lab ports; substitute `13001` or `20002` if you selected an alternative:

```bash
curl --fail --silent --show-error --max-time 5 \
  http://127.0.0.1:13000/api/health
curl --fail --silent --show-error --max-time 5 \
  --output /dev/null --write-out 'Kiali HTTP %{http_code}\n' \
  http://127.0.0.1:20001/kiali/
```

Expect Grafana `"database": "ok"` and `Kiali HTTP 200`. These check dashboard access, not app health. For refusal, check the listener; for timeouts/resets, inspect the forward's terminal. If both pass, refresh the correct browser URL instead of starting duplicate forwards.

**3. Restore a stopped or broken forward.** Verify `kubectl config current-context` using the prepared kubeconfig and OCI settings. Stop on a wrong context; fix [cluster access](docs/cluster-access.md#verify-the-selected-file-and-context) for authentication or `localhost:8080` errors, rather than reinstalling dashboards.

Press **Ctrl+C in the broken forward's own terminal**; do not kill unrelated processes. Rerun only the affected command and leave it running:

Terminal 2 — Kiali:

```bash
kubectl -n istio-system port-forward --address 127.0.0.1 svc/kiali 20001:20001
```

Terminal 3 — Grafana:

```bash
kubectl -n istio-system port-forward --address 127.0.0.1 svc/grafana 13000:80
```

Wait for `Forwarding from 127.0.0.1:...`, then repeat the HTTP checks in terminal 1. Closing the terminal, Ctrl+C, or termination of the selected pod ends forwarding—even through a Service. Rerun for the replacement pod; the dashboard remains installed. See [port-forward reference](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/).

**4. For an occupied local port, use a free alternative.** Check listeners first. If the owner cannot safely be stopped, run the needed alternative in its dedicated terminal:

```bash
# Alternative Kiali command: terminal 2
kubectl -n istio-system port-forward --address 127.0.0.1 svc/kiali 20002:20001
```

```bash
# Alternative Grafana command: terminal 3
kubectl -n istio-system port-forward --address 127.0.0.1 svc/grafana 13001:80
```

Open **http://127.0.0.1:20002/kiali/** or **http://127.0.0.1:13001/d/oke-lab**. Only the local port (left of `:`) changes. Never bind anonymous dashboards to `0.0.0.0`. If access still fails in the correct context, inspect `kubectl -n istio-system get deploy,pods,svc` with the instructor.

### Kiali health warnings

If Kiali shows **Degraded**, hover over the indicator to identify the affected component. The label alone does not prove a probe failure, and healthy pods do not guarantee healthy requests. Use the [read-only health checks](docs/troubleshooting.md#kiali-shows-degraded-or-not-ready) to compare pod readiness with request errors. Scaling warnings may clear; do not disable probes or restart healthy pods to clear a badge.

### Grafana repeatedly stops responding

If restarting the port-forward helps only briefly, check whether the Grafana container is restarting:

```bash
kubectl -n istio-system get pods -l app.kubernetes.io/name=grafana
kubectl -n istio-system describe pods -l app.kubernetes.io/name=grafana
kubectl -n istio-system top pods -l app.kubernetes.io/name=grafana --containers
```

Record restart count and `Last State` before asking the instructor. `OOMKilled` confirms a memory kill; exit code `137` alone does not. Adding a worker cannot raise this container's memory limit. See the [memory troubleshooting notes](docs/troubleshooting.md#grafana-memory-and-repeated-restarts); do not disable probes or enlarge the node pool.

### Repeating the manual-scaling exercise

An existing HPA overrides manual `replicaCount=4`. For a repeat run, restore the manual baseline from the repository root in your verified context:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set autoscaling.enabled=false --set replicaCount=2 \
  --set traffic.loadEnabled=false --wait --timeout 10m
```

Resume step 5. This updates only the release, retaining the cluster and LoadBalancer. Skip this reset on a first run.

## Appendix B: Optional pod inspection

After the core lab, or with the instructor for an unready pod, run these in terminal 1 using your verified context. JSONPath lists containers; `describe` shows state, readiness, and events:

```bash
kubectl -n oke-lab get pods -l app=hello-oke \
  -o 'jsonpath={range .items[*]}{.metadata.name}{"\n  app containers: "}{.spec.containers[*].name}{"\n  init/sidecars: "}{.spec.initContainers[*].name}{"\n"}{end}'
kubectl -n oke-lab describe pods -l app=hello-oke
```

This setup uses a **native sidecar**. Expect:

| Container | Listed under | Expected state |
|---|---|---|
| `web` | Containers | Running, Ready=True |
| `istio-proxy` | Init Containers | Running, Ready=True |
| `istio-init` | Init Containers | Terminated, Completed, Exit Code=0 |

A native sidecar keeps running alongside the app; an ordinary init container finishes before the app starts.

To confirm the native sidecar's per-container restart policy:

```bash
kubectl -n oke-lab get pods -l app=hello-oke \
  -o 'jsonpath={range .items[*]}{.metadata.name}{": istio-proxy restartPolicy="}{.spec.initContainers[?(@.name=="istio-proxy")].restartPolicy}{"\n"}{end}'
```

Expect `Always` for each application's `istio-proxy`. See [Kubernetes sidecar containers](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/). If these checks differ, ask the instructor; do not apply the legacy manifests or reinstall components merely to match the example.

For instructors: [delivery notes, preparation, and release checklist](docs/instructor-guide.md).
