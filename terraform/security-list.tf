# Move the existing managed default list rather than creating a second owner.
# Keep this migration for previously provisioned GitLab/Luna state.
moved {
  from = module.oke.module.vcn[0].oci_core_default_security_list.lockdown[0]
  to   = oci_core_default_security_list.lab
}

data "oci_core_vcn" "lab" {
  vcn_id = module.oke.vcn_id
}

# Lab-only broad private access, explicitly requested for Luna connectivity.
# Applies to every subnet associated with this default list. NSG rules remain
# intact; these additive allows are not restricted by a narrower NSG allowlist.
resource "oci_core_default_security_list" "lab" {
  manage_default_resource_id = data.oci_core_vcn.lab.default_security_list_id

  ingress_security_rules {
    description = "Lab private access from 10.0.0.0/8"
    protocol    = "all"
    source      = "10.0.0.0/8"
    source_type = "CIDR_BLOCK"
    stateless   = false
  }

  egress_security_rules {
    description      = "Lab outbound access"
    protocol         = "all"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    stateless        = false
  }

  lifecycle {
    ignore_changes = [defined_tags]
  }
}
