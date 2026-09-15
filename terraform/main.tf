module "oke" {
  source  = "oracle-terraform-modules/oke/oci"
  version = "~> 5.0"

  providers = {
    oci      = oci
    oci.home = oci.home
  }

  tenancy_id     = var.tenancy_ocid
  compartment_id = var.compartment_ocid
  region         = var.region

  cluster_name            = var.cluster_name
  kubernetes_version      = var.kubernetes_version
  cluster_type            = "enhanced"
  control_plane_is_public = true

  create_vcn              = true
  vcn_cidrs               = [var.vcn_cidr]
  pods_cidr               = var.pods_cidr
  services_cidr           = var.services_cidr
  cni_type                = "npn"
  create_nat_gateway      = true
  create_service_gateway  = true
  create_internet_gateway = true
  create_bastion          = false
  create_operator         = false

  create_policies           = var.create_policies
  workload_identity_enabled = true

  node_pools = {
    workers = {
      shape                   = var.node_shape
      ocpus                   = var.node_ocpus
      memory                  = var.node_memory_gb
      node_pool_size          = var.node_count
      boot_volume_vpus_per_gb = 10
    }
  }
}
