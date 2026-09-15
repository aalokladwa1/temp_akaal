/**
 * AKAAL Administration — 5.4 Identity & Security Domain Models
 */

export type AuthPolicyTier = 'CRITICAL_GOV' | 'ENTERPRISE_HIGH' | 'STANDARD';
export type SsoProtocol = 'OIDC' | 'SAML_2_0';
export type SsoProviderType = 'OKTA' | 'AZURE_AD' | 'GOOGLE_WORKSPACE' | 'PING_IDENTITY' | 'KEYCLOAK' | 'GENERIC_SAML' | 'GENERIC_OIDC';
export type DirectoryType = 'ACTIVE_DIRECTORY' | 'OPEN_LDAP' | 'AZURE_ENTRA_SCIM' | 'OKTA_SCIM' | 'CUSTOM_SCIM';
export type WorkloadType = 'KUBERNETES_SERVICE_ACCOUNT' | 'AWS_IAM_ROLE' | 'GCP_WORKLOAD_IDENTITY' | 'SPIFFE_SVID' | 'MTLS_WORKLOAD';
export type CertType = 'ROOT_CA' | 'INTERMEDIATE_CA' | 'SERVER_TLS' | 'CLIENT_MTLS' | 'SIGNING_CERT';
export type KeyAlgorithm = 'AES_256_GCM' | 'RSA_4096' | 'ECDSA_P384' | 'ED25519';

export interface AuthPolicy {
  id: string;
  name: string;
  tier: AuthPolicyTier;
  description: string;
  minPasswordLength: number;
  requireSpecialChars: boolean;
  requireNumbers: boolean;
  requireUppercase: boolean;
  passwordMaxAgeDays: number;
  lockoutThresholdAttempts: number;
  lockoutDurationMinutes: number;
  sessionIdleTimeoutMinutes: number;
  sessionAbsoluteTimeoutHours: number;
  mfaEnforcement: 'ENFORCED_ALL' | 'ENFORCED_PRIVILEGED_ONLY' | 'OPTIONAL';
  ipAllowlist: string[];
  adaptiveRiskBasedAuth: boolean;
  status: 'ACTIVE' | 'DRAFT' | 'ARCHIVED';
  assignedPrincipalsCount: number;
  updatedAt: string;
}

export interface MfaConfig {
  id: string;
  enforceFido2WebAuthn: boolean;
  enforceTotp: boolean;
  allowHardwareSecurityKeys: boolean;
  allowSmsOtpWithWarning: boolean;
  allowEmailOtpWithWarning: boolean;
  rememberDeviceDays: number;
  gracePeriodDays: number;
  backupCodesCount: number;
  totalEnrolledUsers: number;
  totalHardwareKeysRegistered: number;
  fido2AdoptionRatePercent: number;
}

export interface SsoProvider {
  id: string;
  name: string;
  protocol: SsoProtocol;
  providerType: SsoProviderType;
  entityIdOrIssuer: string;
  singleSignOnUrl: string;
  clientId: string;
  metadataUrl?: string;
  signingCertificateThumbprint: string;
  jitProvisioningEnabled: boolean;
  defaultRoleAssign: string;
  attributeMapping: {
    email: string;
    fullName: string;
    groups: string;
    department: string;
  };
  status: 'ACTIVE' | 'TESTING' | 'DISABLED';
  lastAuthEvent?: string;
  activeUsersCount: number;
  createdAt: string;
}

export interface LdapConfig {
  id: string;
  name: string;
  directoryType: 'ACTIVE_DIRECTORY' | 'OPEN_LDAP';
  serverUrl: string;
  port: number;
  useTls: boolean;
  bindDn: string;
  baseDn: string;
  userSearchFilter: string;
  groupSearchFilter: string;
  syncIntervalMinutes: number;
  groupRoleMappingsCount: number;
  status: 'CONNECTED' | 'DISCONNECTED' | 'SYNC_IN_PROGRESS' | 'ERROR';
  lastSyncTimestamp: string;
  syncedUsersCount: number;
  syncedGroupsCount: number;
}

export interface ScimEndpoint {
  id: string;
  name: string;
  providerType: 'AZURE_ENTRA_SCIM' | 'OKTA_SCIM' | 'CUSTOM_SCIM';
  endpointUrl: string;
  tokenSecretHint: string;
  tokenExpiryDate: string;
  inboundProvisioning: boolean;
  outboundProvisioning: boolean;
  syncUsers: boolean;
  syncGroups: boolean;
  deprovisionAction: 'SUSPEND' | 'DELETE' | 'TRANSFER';
  status: 'ACTIVE' | 'DEGRADED' | 'INACTIVE';
  lastWebhookTimestamp: string;
  provisionedUsersCount: number;
}

export interface IdentityFederationTrust {
  id: string;
  trustDomain: string;
  partnerTenantName: string;
  partnerTenantId: string;
  trustProtocol: 'SAML_2_0_FEDERATION' | 'OIDC_EXCHANGE' | 'SPIFFE_FEDERATION';
  allowedClaimScopes: string[];
  status: 'ESTABLISHED' | 'PENDING_EXCHANGE' | 'REVOKED';
  expiresAt: string;
  crossTenantPrincipalsCount: number;
}

export interface WorkloadIdentityEntry {
  id: string;
  name: string;
  type: WorkloadType;
  identityIdentifier: string; // e.g., spiffe://akaal.enterprise/ns/prod/sa/migration-worker
  trustDomain: string;
  associatedNamespaceOrCluster: string;
  tokenTtlMinutes: number;
  mfaOrAttestationMethod: string;
  status: 'ACTIVE' | 'ROTATING' | 'REVOKED';
  lastAttestedAt: string;
  activeWorkloadsCount: number;
}

export interface SpiffeServerConfig {
  id: string;
  trustDomain: string;
  spireServerEndpoint: string;
  caKeyAlgorithm: KeyAlgorithm;
  svidDefaultTtlHours: number;
  svidMaxTtlHours: number;
  federatedTrustDomains: string[];
  attestationPlugins: string[];
  status: 'HEALTHY' | 'SYNCING' | 'OFFLINE';
  activeSvidsCount: number;
  agentsConnectedCount: number;
}

export interface X509CertificateRecord {
  id: string;
  commonName: string;
  type: CertType;
  issuerName: string;
  serialNumber: string;
  validFrom: string;
  validTo: string;
  daysRemaining: number;
  algorithm: KeyAlgorithm;
  autoRenewEnabled: boolean;
  boundServicesCount: number;
  status: 'VALID' | 'EXPIRING_SOON' | 'EXPIRED' | 'REVOKED';
}

export interface VaultSecretEngineConfig {
  id: string;
  engineName: string;
  engineType: 'KV_V2' | 'DATABASE_DYNAMIC' | 'PKI' | 'TRANSIT' | 'AWS_IAM';
  mountPath: string;
  vaultClusterUrl: string;
  authMethod: 'APP_ROLE' | 'KUBERNETES_AUTH' | 'AWS_IAM_AUTH';
  leaseTtlHours: number;
  maxLeaseTtlHours: number;
  managedSecretsCount: number;
  status: 'CONNECTED' | 'DEGRADED' | 'LOCKED';
  lastRotatedAt: string;
}

export interface KmsMasterKey {
  id: string;
  keyAlias: string;
  keyArnOrId: string;
  algorithm: KeyAlgorithm;
  keyOrigin: 'CUSTOMER_MANAGED_CMK' | 'BYOK_EXTERNAL_HSM' | 'CLOUD_PROVIDER_MANAGED';
  hsmModuleModel?: string;
  rotationIntervalDays: number;
  nextScheduledRotation: string;
  encryptedVolumesCount: number;
  status: 'ENABLED' | 'ROTATING' | 'DISABLED' | 'PENDING_DELETION';
}

export interface SecretRotationRule {
  id: string;
  name: string;
  targetType: 'DATABASE_CREDENTIALS' | 'SERVICE_ACCOUNT_API_KEY' | 'TLS_CERTIFICATE' | 'KMS_WRAPPING_KEY' | 'SSH_KEYPAIR';
  targetResourceName: string;
  rotationFrequencyDays: number;
  lastRotationTimestamp: string;
  nextRotationTimestamp: string;
  automatedExecution: boolean;
  lastRotationStatus: 'SUCCESS' | 'FAILED' | 'PENDING';
  auditLogId: string;
}
