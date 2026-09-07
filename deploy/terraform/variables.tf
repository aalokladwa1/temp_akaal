# P7B.21 -- input variables. No variable here has a default that enables broad/public
# access, and no variable is a secret (workload identity is established via cloud-native
# federation, e.g. AWS IRSA / GCP Workload Identity / Azure Workload Identity / OCI
# instance principal -- never a long-lived static credential passed through Terraform).

variable "environment_name" {
  type        = string
  description = "Logical environment name (matches akaalEngine.fabric.environment.Environment.display_name); used only for resource naming/tagging."
}

variable "enable_aws" {
  type    = bool
  default = false
}
variable "enable_azure" {
  type    = bool
  default = false
}
variable "enable_gcp" {
  type    = bool
  default = false
}
variable "enable_oci" {
  type    = bool
  default = false
}
variable "enable_kubernetes" {
  type    = bool
  default = false
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_oidc_provider_arn" {
  type        = string
  default     = ""
  description = "EKS cluster's OIDC provider ARN, required only when enable_aws && enable_kubernetes (IRSA trust binding). Never a credential."
}

variable "aws_worker_namespace" {
  type    = string
  default = "akaal-worker-fabric"
}

variable "gcp_project_id" {
  type    = string
  default = ""
}
variable "gcp_region" {
  type    = string
  default = "us-central1"
}

variable "oci_region" {
  type    = string
  default = ""
}
variable "oci_compartment_ocid" {
  type    = string
  default = ""
}

variable "kubeconfig_path" {
  type    = string
  default = "~/.kube/config"
}
variable "kubernetes_namespace" {
  type    = string
  default = "akaal-worker-fabric"
}

variable "tags" {
  type    = map(string)
  default = {}
}
