# Maintainer-only infrastructure workflow

Learners use the [Luna walkthrough](../README.md). Luna creates the cluster; learners install Helm releases. Do not give learners Terraform state, deployment keys, or CI job tokens.

For authorized maintainers running outside Luna, configure the OCI provider inputs and protected HTTP backend described in [CI setup](gitlab-ci.md), then:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit local inputs; never commit them. Configure backend credentials securely.
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

Connect using `oci ce cluster create-kubeconfig` with the resulting cluster ID, allocated region, `--file`, `--token-version 2.0.0`, and `--kube-endpoint PUBLIC_ENDPOINT`. Follow the learner instructions only after verifying the intended Kubernetes context.

Infrastructure destroy remains a maintainer responsibility. Follow [cleanup](cleanup.md) to delete Kubernetes-created load balancers before destroying their cluster/network. Retain remote state.
