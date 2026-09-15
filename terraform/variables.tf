variable "tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID."
}
variable "user_ocid" {
  type        = string
  description = "OCI user OCID for Terraform authentication."
}
variable "fingerprint" {
  type        = string
  description = "OCI API signing-key fingerprint."
}
variable "private_key_path" {
  type        = string
  description = "Absolute path to OCI API signing key."
}
variable "region" {
  type        = string
  description = "OCI region, for example us-ashburn-1."
}
variable "compartment_ocid" {
  type        = string
  description = "Compartment OCID for this lab."
}

variable "cluster_name" {
  type        = string
  description = "OKE cluster display name."
  default     = "oke-monitoring-lab"
}
variable "kubernetes_version" {
  type        = string
  description = "An OKE-supported version for the selected region."
  default     = "v1.32.1"
}
variable "vcn_cidr" {
  type        = string
  description = "CIDR for the new lab VCN."
  default     = "10.0.0.0/16"
}
variable "pods_cidr" {
  type        = string
  description = "Non-overlapping Pod CIDR."
  default     = "10.244.0.0/16"
}
variable "services_cidr" {
  type        = string
  description = "Non-overlapping Service CIDR."
  default     = "10.96.0.0/16"
}
variable "node_shape" {
  type        = string
  description = "Available flexible worker-node shape."
  default     = "VM.Standard.E4.Flex"
}
variable "node_ocpus" {
  type        = number
  description = "OCPUs per worker."
  default     = 1
}
variable "node_memory_gb" {
  type        = number
  description = "Memory GB per worker."
  default     = 16
}
variable "node_count" {
  type        = number
  description = "Fixed worker count."
  default     = 2
}
variable "create_policies" {
  type        = bool
  description = "Let the module create documented OKE IAM policies."
  default     = true
}
