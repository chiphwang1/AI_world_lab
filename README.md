# OKE Application Monitoring Lab

Luna provisions your Oracle Kubernetes Engine (OKE) cluster automatically. You install Istio, deploy an application with Helm, generate traffic, and explore its health and traffic in Kiali.

Run these commands in a **Bash terminal on the Luna desktop**. Keep session credentials private.

## 1. Launch the lab and connect to OKE

Click **Launch lab** in Luna. The desktop can appear before the cluster is ready. Wait for provisioning to finish (allow 35–50 minutes). If it fails, ask the instructor rather than creating infrastructure yourself.

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
kubectl auth can-i create customresourcedefinitions.apiextensions.k8s.io
kubectl auth can-i create clusterroles.rbac.authorization.k8s.io
```

Expect two `Ready` nodes and `yes` for both permission checks. Installing the mesh requires cluster-level permissions in your **dedicated lab cluster**. Stop if access is denied or the context is not your assigned cluster. Never use a shared or production cluster.

## 2. Get the lab materials

Use the repository URL supplied by the instructor:

```bash
git clone <instructor-provided-repository-url> oke-monitoring-lab
cd oke-monitoring-lab
source helm/versions.env
```

These materials currently live alongside the infrastructure repository. A separate GitHub learner repository has not yet been published. Learners do not need Terraform state or CI credentials.

## 3. Install Istio with Helm

This lab uses **sidecar mode**: Istio adds a proxy beside each application container. The pinned release supports Kubernetes 1.32–1.36. Check `kubectl version`; ask the instructor if your server is outside that range.

```bash
helm repo add istio https://istio-release.storage.googleapis.com/charts
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

## 4. Install Prometheus and Kiali

Prometheus collects request metrics; Kiali uses them to draw the traffic graph. Both stay inside the cluster. This short-lived lab uses no persistent telemetry volumes.

```bash
helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace istio-system --version "$PROMETHEUS_CHART_VERSION" \
  -f helm/values/prometheus.yaml --wait --timeout 10m
helm upgrade --install kiali-server kiali/kiali-server \
  --namespace istio-system --version "$KIALI_CHART_VERSION" \
  -f helm/values/kiali.yaml --wait --timeout 10m
helm list --namespace istio-system
kubectl -n istio-system get pods,svc
```

Kiali uses read-only, anonymous access for this dedicated training cluster. **Never expose it with a public LoadBalancer or Ingress.** Anyone with network access to its Service can read mesh information; production requires authenticated access and appropriate network controls.

## 5. Deploy the application and generate traffic

The local chart includes two echo replicas and an optional traffic generator. Do not also apply the legacy `kubernetes/` manifests: they use the same application name but are not Helm-managed.

```bash
helm upgrade --install hello-oke ./charts/oke-mesh-app \
  --namespace oke-lab --wait --timeout 10m
kubectl -n oke-lab rollout status deployment/hello-oke --timeout=300s
kubectl -n oke-lab get pods,svc
kubectl -n oke-lab get pods -l app=hello-oke \
  -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.spec.containers[*].name}{"\n"}{end}'
```

App pods should contain `istio-proxy` and normally show `2/2` containers ready. The application uses one OCI LoadBalancer. Wait for its external IP, then test it:

```bash
kubectl -n oke-lab get service hello-oke --watch
# Press Ctrl+C once EXTERNAL-IP is assigned.
APP_IP=$(kubectl -n oke-lab get svc hello-oke -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl --fail --max-time 10 "http://${APP_IP}/"

helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --set traffic.enabled=true --wait --timeout 10m
kubectl -n oke-lab logs deployment/hello-oke-traffic -c traffic --tail=10
```

The traffic generator makes one request approximately every two seconds. Leave it running during the exercise so Kiali can show a client-to-service edge.

## 6. Explore the application in Kiali

In a second terminal on the **same Luna desktop**:

```bash
export KUBECONFIG="$HOME/.kube/oke-lab"
kubectl -n istio-system port-forward --address 127.0.0.1 svc/kiali 20001:20001
```

Open **http://localhost:20001/kiali** in the browser **inside that desktop**. Your laptop's localhost is different. Keep the terminal running; do not bind to `0.0.0.0`.

Select namespace `oke-lab`, open the traffic graph, choose a recent time range (such as last five minutes), and enable refresh. Allow a minute or two for metrics. Find `hello-oke-traffic → hello-oke` and inspect request rate, success rate, and latency. Kiali visualizes traffic; the application's response is at the LoadBalancer URL.

Continue with [monitoring exercises](docs/monitoring.md) for a controlled outage. For an empty graph, see [troubleshooting](docs/troubleshooting.md).

## 7. Finish the lab

Disable traffic and uninstall the application:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --set traffic.enabled=false --wait --timeout 10m
helm uninstall hello-oke --namespace oke-lab --wait --timeout 10m
kubectl -n oke-lab get services
```

Wait for the `hello-oke` Service to disappear so its cloud load balancer can be cleaned up. Stop port-forwarding with Ctrl+C, then use **End session in Luna**. Luna starts infrastructure cleanup; learners do not run Terraform destroy. Tell the instructor if cleanup fails or hangs. Running infrastructure incurs charges until deleted.

## Instructor notes

The full OKE/Istio/Kiali walkthrough still needs live validation after the Luna VCN quota issue is resolved. Helm rendering does not prove a successful deployment. Confirm desktop tools, cluster permissions, supported versions, image access, and sufficient session time before the workshop.

- [Infrastructure and CI administration](docs/gitlab-ci.md)
- [Maintainer-only local Terraform workflow](docs/maintainer-infrastructure.md)
- [Cleanup responsibilities](docs/cleanup.md)
- [Chart sources and packaging](helm/README.md)

`terraform/` and CI scripts are instructor-managed infrastructure. `charts/` and `helm/` are learner deployment materials. `kubernetes/` retains the earlier non-Helm exercise for maintainers.
