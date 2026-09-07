# P7B.21 -- AKAAL Terraform-First IaC: provider configuration.
#
# TERRAFORM PROVISIONS INFRASTRUCTURE. IT DOES NOT OWN MIGRATION TRUTH.
# This module never creates/reads Migration/ExecutionPlan/checkpoint/CDC-offset/
# validation/approval state. It provisions only the identity/network prerequisites an
# akaalEngine.fabric.execution_site.ExecutionSite needs to exist -- workload identity,
# namespace/RBAC scaffolding, and (optionally) network security group references. It
# never provisions the AKAAL runtime itself, and never embeds a plaintext secret/token
# anywhere (verified by tests/unit/engine_fabric/test_p7b21_terraform_static.py's
# regex sweep of every .tf file in this directory).

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
  }

  # State can contain sensitive values in plaintext even when a resource attribute is
  # marked `sensitive = true` in configuration -- Terraform's `sensitive` flag only
  # redacts CLI/plan output, it does NOT encrypt state. A remote backend with
  # encryption-at-rest and access control is required for any real deployment; this
  # module does not configure one by default (environment-specific), and this comment
  # exists precisely so that omission is never mistaken for "state is safe by default".
}

provider "aws" {
  region = var.aws_region
  # No default credentials, no hardcoded access keys -- authentication is resolved via
  # the standard AWS provider credential chain (environment/instance-profile/IRSA),
  # never a value in this repository.
}

provider "azurerm" {
  features {}
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "oci" {
  # Authenticated via the standard OCI provider config chain (instance principal /
  # config file / environment) -- no tenancy/user OCID or key material is hardcoded here.
  region = var.oci_region
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}
