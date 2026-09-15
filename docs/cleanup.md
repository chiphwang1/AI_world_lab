# Cleanup

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
