/**
 * AKAAL Enterprise Secrets Management — Domain Types
 * Stage 7.3
 */

// ─────────────────────────────────────────────
// Provider Types
// ─────────────────────────────────────────────

export type SecretProviderType =
  | 'env'
  | 'vault'
  | 'aws_secrets_manager'
  | 'azure_key_vault'
  | 'gcp_secret_manager'
  | 'kubernetes'
  | 'docker'
  | 'custom';

export interface SecretProviderConfig {
  type: SecretProviderType;
  enabled: boolean;
  priority: number; // Lower = higher priority in failover chain
  displayName: string;

  // HashiCorp Vault
  vault?: {
    address: string;
    token?: string;
    roleId?: string;
    secretId?: string;
    authMethod: 'token' | 'approle' | 'kubernetes' | 'aws';
    namespace?: string;
    mountPath: string;
    tlsSkipVerify?: boolean;
    caCert?: string;
    clientCert?: string;
    clientKey?: string;
  };

  // AWS Secrets Manager
  aws?: {
    region: string;
    accessKeyId?: string;
    secretAccessKey?: string;
    sessionToken?: string;
    roleArn?: string;
    endpoint?: string;
    prefix?: string;
  };

  // Azure Key Vault
  azure?: {
    vaultUrl: string;
    tenantId: string;
    clientId?: string;
    clientSecret?: string;
    useManagedIdentity?: boolean;
    prefix?: string;
  };

  // Google Secret Manager
  gcp?: {
    projectId: string;
    serviceAccountKey?: string; // JSON string
    impersonateServiceAccount?: string;
    prefix?: string;
  };

  // Kubernetes Secrets
  kubernetes?: {
    namespace: string;
    serviceAccountTokenPath?: string;
    caCertPath?: string;
    apiServer?: string;
    labelSelector?: string;
  };

  // Docker Secrets
  docker?: {
    secretsPath: string; // default: /run/secrets
  };

  // Custom Provider
  custom?: {
    endpoint: string;
    authHeader?: string;
    authToken?: string;
    tlsSkipVerify?: boolean;
    metadata?: Record<string, string>;
  };
}

export interface SecretProviderHealth {
  providerId: string;
  providerType: SecretProviderType;
  displayName: string;
  status: 'healthy' | 'degraded' | 'unreachable' | 'unauthenticated' | 'unconfigured' | 'disabled';
  latencyMs?: number;
  lastChecked: string;
  lastSuccess?: string;
  lastFailure?: string;
  failureReason?: string;
  retryCount: number;
  providerVersion?: string;
  authStatus: 'authenticated' | 'unauthenticated' | 'unknown';
  availability: number; // 0-100 percentage
}

// ─────────────────────────────────────────────
// Secret Types
// ─────────────────────────────────────────────

export type SecretType =
  | 'database_credential'
  | 'api_key'
  | 'oauth_client_secret'
  | 'oidc_secret'
  | 'saml_certificate'
  | 'jwt_signing_key'
  | 'encryption_key'
  | 'smtp_credential'
  | 'webhook_secret'
  | 'ssh_key'
  | 'tls_certificate'
  | 'application_secret';

export type SecretStatus = 'active' | 'inactive' | 'rotating' | 'deprecated' | 'deleted' | 'expired';

export type RotationTrigger = 'manual' | 'scheduled' | 'automatic' | 'emergency';

export interface SecretVersion {
  versionId: string;
  versionNumber: number;
  createdAt: string;
  createdBy: string;
  isActive: boolean;
  expiresAt?: string;
  checksum: string; // SHA-256 of the value, for integrity verification
  encryptedValue?: string; // Stored encrypted — raw value never in this field in prod
}

export interface SecretRotationConfig {
  enabled: boolean;
  trigger: RotationTrigger;
  intervalDays?: number;
  cronExpression?: string;
  gracePeriodHours: number; // Dual-active period for zero-downtime rotation
  notificationWebhook?: string;
  notificationEmail?: string;
  maxVersionHistory: number;
}

export interface SecretRecord {
  id: string;
  name: string;
  description: string;
  type: SecretType;
  status: SecretStatus;
  provider: SecretProviderType;
  providerPath: string; // The path/key in the provider

  // Metadata
  labels: Record<string, string>;
  tags: string[];
  owner: string;
  tenantId: string;
  organizationId: string;

  // Version control
  currentVersionId: string;
  versions: SecretVersion[];

  // Lifecycle
  createdAt: string;
  updatedAt: string;
  lastRotatedAt?: string;
  expiresAt?: string;
  nextRotationAt?: string;

  // Rotation config
  rotationConfig: SecretRotationConfig;
}

export interface SecretRotationRecord {
  id: string;
  secretId: string;
  secretName: string;
  trigger: RotationTrigger;
  status: 'pending' | 'in_progress' | 'success' | 'failed' | 'rolled_back';
  fromVersionId: string;
  toVersionId?: string;
  initiatedBy: string;
  initiatedAt: string;
  completedAt?: string;
  failureReason?: string;
  isEmergency: boolean;
  gracePeriodEndsAt?: string;
  notificationsSent: boolean;
}

export interface SecretCreateRequest {
  name: string;
  description?: string;
  type: SecretType;
  provider: SecretProviderType;
  providerPath: string;
  value: string; // The raw secret value — only used during creation
  labels?: Record<string, string>;
  tags?: string[];
  owner?: string;
  tenantId?: string;
  organizationId?: string;
  expiresAt?: string;
  rotationConfig?: Partial<SecretRotationConfig>;
}

export interface SecretUpdateRequest {
  id: string;
  description?: string;
  labels?: Record<string, string>;
  tags?: string[];
  expiresAt?: string;
  rotationConfig?: Partial<SecretRotationConfig>;
}

export interface SecretListFilter {
  type?: SecretType;
  status?: SecretStatus;
  provider?: SecretProviderType;
  owner?: string;
  tenantId?: string;
  search?: string;
  tags?: string[];
}
