# P7B.21 -- outputs are identity REFERENCES only (ARNs, client IDs, resource names) --
# never a secret, token, or key. None of these needs `sensitive = true` because none of
# them is sensitive; a reviewer should treat any *_secret/*_key/*_password output added
# here in the future as a defect, not a naming choice.

output "aws_worker_role_arn" {
  value       = var.enable_aws && var.enable_kubernetes ? aws_iam_role.worker[0].arn : null
  description = "IAM role ARN for IRSA binding -- a reference, never a credential."
}

output "azure_worker_identity_client_id" {
  value = var.enable_azure ? azurerm_user_assigned_identity.worker[0].client_id : null
}

output "gcp_worker_service_account_email" {
  value = var.enable_gcp ? google_service_account.worker[0].email : null
}

output "oci_worker_dynamic_group_id" {
  value = var.enable_oci ? oci_identity_dynamic_group.worker[0].id : null
}

output "kubernetes_namespace" {
  value = var.enable_kubernetes ? kubernetes_namespace.worker[0].metadata[0].name : null
}
