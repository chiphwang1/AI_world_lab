output "cluster_id" {
  description = "OKE cluster OCID."
  value       = module.oke.cluster_id
}

output "vcn_id" {
  description = "Lab VCN OCID."
  value       = module.oke.vcn_id
}

output "node_pool_ids" {
  description = "Worker pool OCIDs."
  value       = module.oke.worker_pool_ids
}

output "deployment_target" {
  description = "Non-secret target identity used to verify session cleanup."
  value = {
    tenancy_ocid     = var.tenancy_ocid
    compartment_ocid = var.compartment_ocid
    region           = var.region
  }
}

output "kubeconfig_command" {
  description = "Run with the intended OCI profile/auth selected, then export KUBECONFIG=$HOME/.kube/oke-lab."
  value       = "oci ce cluster create-kubeconfig --cluster-id ${module.oke.cluster_id} --region ${var.region} --token-version 2.0.0 --file \"$HOME/.kube/oke-lab\" --kube-endpoint PUBLIC_ENDPOINT --with-auth-context"
}
