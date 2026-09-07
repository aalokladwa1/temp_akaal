# P7B.21 -- AKAAL execution-site prerequisites, per cloud. Every resource here is toggled
# by an explicit `enable_<cloud>` boolean (default false) -- this module never provisions
# infrastructure the caller did not explicitly request, and never provisions a "just to
# claim coverage" empty/meaningless resource. Each block below is genuinely load-bearing:
# the workload-identity binding an ExecutionSite of that cloud type actually needs
# (matching akaalEngine.fabric.workload_identity's per-cloud resolvers from P7B.3).

# ---------------------------------------------------------------------------------------
# AWS -- IRSA (IAM Roles for Service Accounts) worker identity, scoped minimally.
# ---------------------------------------------------------------------------------------

data "aws_iam_policy_document" "worker_assume_role" {
  count = var.enable_aws && var.enable_kubernetes ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.aws_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(var.aws_oidc_provider_arn, "/^.*oidc-provider\\//", "")}:sub"
      values   = ["system:serviceaccount:${var.aws_worker_namespace}:akaal-worker"]
    }
  }
}

resource "aws_iam_role" "worker" {
  count              = var.enable_aws && var.enable_kubernetes ? 1 : 0
  name               = "akaal-worker-${var.environment_name}"
  assume_role_policy = data.aws_iam_policy_document.worker_assume_role[0].json
  tags               = var.tags

  # No AWS-managed AdministratorAccess or similarly broad policy is attached here or
  # anywhere in this file -- only the scoped policy below.
}

# Minimal, explicit permission set: staging-bucket read/write only. A real deployment
# supplies its own bucket ARN(s); this module never defaults to "*" resources.
variable "aws_staging_bucket_arns" {
  type    = list(string)
  default = []
}

data "aws_iam_policy_document" "worker_permissions" {
  count = var.enable_aws && length(var.aws_staging_bucket_arns) > 0 ? 1 : 0

  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
    resources = var.aws_staging_bucket_arns
  }
}

resource "aws_iam_role_policy" "worker_permissions" {
  count  = var.enable_aws && var.enable_kubernetes && length(var.aws_staging_bucket_arns) > 0 ? 1 : 0
  name   = "akaal-worker-staging-access"
  role   = aws_iam_role.worker[0].id
  policy = data.aws_iam_policy_document.worker_permissions[0].json
}

# ---------------------------------------------------------------------------------------
# Azure -- User Assigned Managed Identity for federated workload identity.
# ---------------------------------------------------------------------------------------

resource "azurerm_user_assigned_identity" "worker" {
  count               = var.enable_azure ? 1 : 0
  name                = "akaal-worker-${var.environment_name}"
  resource_group_name = var.azure_resource_group_name
  location            = var.azure_location
  tags                = var.tags
}

variable "azure_resource_group_name" {
  type    = string
  default = ""
}
variable "azure_location" {
  type    = string
  default = "eastus"
}

resource "azurerm_federated_identity_credential" "worker" {
  count               = var.enable_azure && var.enable_kubernetes ? 1 : 0
  name                = "akaal-worker-federation"
  resource_group_name = var.azure_resource_group_name
  parent_id           = azurerm_user_assigned_identity.worker[0].id
  audience            = ["api://AzureADTokenExchange"]
  issuer               = var.azure_aks_oidc_issuer_url
  subject              = "system:serviceaccount:${var.kubernetes_namespace}:akaal-worker"
}

variable "azure_aks_oidc_issuer_url" {
  type    = string
  default = ""
}

# ---------------------------------------------------------------------------------------
# GCP -- Service Account + Workload Identity binding (never a downloaded JSON key).
# ---------------------------------------------------------------------------------------

resource "google_service_account" "worker" {
  count        = var.enable_gcp ? 1 : 0
  account_id   = "akaal-worker-${substr(var.environment_name, 0, 20)}"
  display_name = "AKAAL worker fabric (${var.environment_name})"
}

resource "google_service_account_iam_member" "worker_workload_identity" {
  count              = var.enable_gcp && var.enable_kubernetes ? 1 : 0
  service_account_id = google_service_account.worker[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.gcp_project_id}.svc.id.goog[${var.kubernetes_namespace}/akaal-worker]"
  # No project-level Owner/Editor role is ever granted here -- only the workload-identity
  # binding itself. Any additional data-access permission is the caller's explicit,
  # separate, minimally-scoped grant.
}

# ---------------------------------------------------------------------------------------
# OCI -- Dynamic Group + Policy for instance-principal workload identity.
# ---------------------------------------------------------------------------------------

resource "oci_identity_dynamic_group" "worker" {
  count          = var.enable_oci ? 1 : 0
  compartment_id = var.oci_tenancy_ocid
  name           = "akaal-worker-${var.environment_name}"
  description    = "AKAAL worker fabric instances for environment ${var.environment_name}"
  matching_rule  = "ALL {instance.compartment.id = '${var.oci_compartment_ocid}'}"
}

variable "oci_tenancy_ocid" {
  type    = string
  default = ""
}

resource "oci_identity_policy" "worker" {
  count          = var.enable_oci ? 1 : 0
  compartment_id = var.oci_compartment_ocid
  name           = "akaal-worker-${var.environment_name}-policy"
  description    = "Minimal object-storage access for AKAAL worker fabric staging."
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.worker[0].name} to manage objects in compartment id ${var.oci_compartment_ocid} where target.bucket.name = 'akaal-staging-${var.environment_name}'",
  ]
  # Deliberately NOT `Allow dynamic-group ... to manage all-resources in tenancy` --
  # scoped to one named staging bucket only.
}

# ---------------------------------------------------------------------------------------
# Kubernetes -- namespace + service account (RBAC itself is owned by the Helm chart,
# deploy/kubernetes/ -- this module only ensures the namespace/service-account identity
# prerequisites those manifests bind to actually exist ahead of a Helm install).
# ---------------------------------------------------------------------------------------

resource "kubernetes_namespace" "worker" {
  count = var.enable_kubernetes ? 1 : 0
  metadata {
    name   = var.kubernetes_namespace
    labels = merge(var.tags, { "akaal.io/component" = "worker-fabric" })
  }
}

resource "kubernetes_service_account" "worker" {
  count = var.enable_kubernetes ? 1 : 0
  metadata {
    name      = "akaal-worker"
    namespace = kubernetes_namespace.worker[0].metadata[0].name
    annotations = merge(
      var.enable_aws ? { "eks.amazonaws.com/role-arn" = aws_iam_role.worker[0].arn } : {},
      var.enable_azure ? { "azure.workload.identity/client-id" = azurerm_user_assigned_identity.worker[0].client_id } : {},
      var.enable_gcp ? { "iam.gke.io/gcp-service-account" = google_service_account.worker[0].email } : {},
    )
  }
  automount_service_account_token = true
}
