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

output "kubeconfig_command" {
  description = "Run this command to configure kubectl."
  value       = "oci ce cluster create-kubeconfig --cluster-id ${module.oke.cluster_id} --region ${var.region} --token-version 2.0.0 --kubeconfig-file $HOME/.kube/config --overwrite"
}
