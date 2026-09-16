# OKE Application Monitoring Lab

This hands-on lab provisions an Oracle Kubernetes Engine (OKE) cluster, deploys a small web application, and validates cluster health, logs, metrics, and a safe availability-alert test.

It uses the official `terraform-oci-oke` module for infrastructure. The app uses plain Kubernetes objects so each resource is easy to inspect and remove.

## Architecture

```text
Internet → OCI Load Balancer → Service: LoadBalancer → hello-oke (2 pods)
                                      \→ private worker nodes → OCI monitoring/logging
```

The public Kubernetes API endpoint keeps this beginner lab approachable. Worker nodes remain private. Use a private API endpoint and a bastion/operator host for production.

## Cost and prerequisites

Provisioning usually takes 35–50 minutes. Worker compute, boot volumes, the load balancer, network resources, and retained logs may incur charges. Destroy the lab after use.

- An OCI account, a target compartment, and permission to create OKE, VCN, compute, load-balancer, and monitoring resources.
- Terraform 1.5+, OCI CLI 3.x, and a compatible `kubectl`.
- OCI API-key auth configured locally, or equivalent OCI provider authentication.

## Run the lab

For GitLab/Luna execution without downloading an OCI private key, follow the [Luna integration and CI setup](docs/gitlab-ci.md#luna-integration). Luna supplies credentials to the job; plan, apply, and destroy still require manual approval. The commands below are for local execution with OCI credentials and the existing HTTP backend configured.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your OCIDs, key path, region, and compartment.
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply

# Connect kubectl using the command Terraform prints.
$(terraform output -raw kubeconfig_command)
kubectl get nodes

# Deploy the application.
kubectl apply -k ../kubernetes
kubectl -n oke-lab rollout status deployment/hello-oke
kubectl -n oke-lab get pods,svc
```

Wait for the Service external IP, then test it:

```bash
APP_IP=$(kubectl -n oke-lab get svc hello-oke -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -fsS "http://${APP_IP}/"
```

Run `../scripts/validate-lab.sh` from `terraform/` to check nodes, rollout state, events, and endpoint reachability. Follow [monitoring exercises](docs/monitoring.md) for OCI dashboards and a safe alert test.

## Repository layout

```text
terraform/   Cluster infrastructure and outputs
kubernetes/  Application manifests
scripts/     Validation helper
docs/        Monitoring, cleanup, and troubleshooting
```

## Cleanup

First remove Kubernetes resources and wait for the OCI Load Balancer to be deleted:

```bash
kubectl delete -k kubernetes
cd terraform
terraform destroy
```

See [cleanup details](docs/cleanup.md) and [troubleshooting](docs/troubleshooting.md).
