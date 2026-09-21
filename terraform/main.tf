module "oke" {
  source  = "oracle-terraform-modules/oke/oci"
  version = "5.5.1"

  providers = {
    oci      = oci
    oci.home = oci.home
  }

  tenancy_id     = var.tenancy_ocid
  compartment_id = var.compartment_ocid
  region         = var.region

  cluster_name                      = var.cluster_name
  kubernetes_version                = var.kubernetes_version
  cluster_type                      = "enhanced"
  control_plane_is_public           = true
  assign_public_ip_to_control_plane = true
  control_plane_allowed_cidrs       = var.control_plane_allowed_cidrs

  # The HPA exercise requires the resource metrics API, independently of Prometheus.
  cluster_addons = {
    CertManager             = {}
    KubernetesMetricsServer = {}
  }

  create_vcn                  = true
  vcn_cidrs                   = [var.vcn_cidr]
  pods_cidr                   = var.pods_cidr
  services_cidr               = var.services_cidr
  cni_type                    = "npn"
  vcn_create_nat_gateway      = "always"
  vcn_create_service_gateway  = "always"
  vcn_create_internet_gateway = "always"
  create_bastion              = false
  create_operator             = false

  create_iam_resources = var.create_policies
  # Workload identity is an enhanced-cluster capability, not a module toggle.

  worker_pools = {
    workers = {
      mode                    = "node-pool"
      shape                   = var.node_shape
      ocpus                   = var.node_ocpus
      memory                  = var.node_memory_gb
      size                    = var.node_count
      boot_volume_vpus_per_gb = 10
    }
  }
}
