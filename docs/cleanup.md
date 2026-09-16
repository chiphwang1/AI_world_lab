# Cleanup

## Learners: finish through Luna

Follow the [walkthrough](../README.md#7-finish-the-lab) to disable traffic, uninstall the `hello-oke` Helm release, and wait for its LoadBalancer Service to disappear. Stop localhost port-forwards, then choose **End session** in Luna. Do not run Terraform destroy.

Prometheus and Kiali use ClusterIP Services and no persistent telemetry volumes. Their in-cluster resources disappear with the dedicated cluster. If repeating the exercise in the same active session, uninstall `kiali-server`, `prometheus`, `istiod`, and `istio-base` from `istio-system` in that order, after uninstalling the app. Helm retains Istio CRDs; do not broadly delete CRDs from any shared cluster.

The remainder of this page is for maintainers.

## Luna session cleanup

Luna starts `terraform:destroy`, the only manual job in a Luna pipeline, when the session ends/expires. The job is independently runnable after failed provisioning and does not download plan artifacts. It uses the recorded launch pipeline's `luna-oke-<pipeline-id>` remote state and credentials, marks the session closed to prevent later provisioning, and performs these steps:

1. Read the managed cluster ID from Terraform state, including after a partial apply without outputs. Refuse ambiguous clusters or mismatched deployment targets.
2. Confirm the cluster still exists through an authenticated OCI compartment listing. Empty state and already-deleted clusters skip Kubernetes cleanup; lookup errors stop the job.
3. Create a temporary kubeconfig using the session API key. Delete all `LoadBalancer` Services in the session-owned cluster, including learner-created Services, and wait up to ten minutes per Service for deletion/finalizers. Then delete the repository's Kubernetes manifests.
4. Run Terraform destroy only after Kubernetes cleanup succeeds. Retain remote state and the session-closed marker for retries/audit.

An inaccessible Kubernetes API or stuck finalizer stops cleanup before Terraform tears down the cluster/network. Resolve the cause and retry the cleanup job in the same pipeline. Do not force-remove cloud-controller finalizers as a substitute for deleting their OCI resources. Because cleanup is an optional manual job, its failure may leave the overall pipeline showing a warning; inspect `terraform:destroy` itself.

Terraform only manages resources recorded in its state. The Service cleanup covers Kubernetes-created OCI load balancers; it does not sweep arbitrary learner-created OCI resources, persistent volumes, or other controllers' external resources. Define those activities and their cleanup explicitly before a workshop. Luna's removal of learner access is not a substitute for successful infrastructure cleanup.

## Maintainer-only local cleanup

Delete Kubernetes objects first; this gives the cloud controller time to remove the OCI Load Balancer:

```bash
kubectl delete -k kubernetes
kubectl -n oke-lab get service hello-oke --watch
```

When the Service is gone, stop the watch and destroy the lab infrastructure:

```bash
cd terraform
terraform plan -destroy
terraform destroy
```

Verify in OCI Console that the OKE cluster, node pool, load balancer, and lab VCN are gone. Terraform state is sensitive operational data: retain it under your team policy and never commit it.
