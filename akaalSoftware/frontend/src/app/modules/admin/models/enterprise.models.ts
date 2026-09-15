/**
 * AKAAL Administration — 5.1 Enterprise Domain Models
 * Canonical DTOs conforming to natural product language and zero-fake backend integration.
 */

export interface EnterpriseSettings {
  id: string;
  legalEntityName: string;
  enterpriseIdentifier: string;
  primaryDomain: string;
  secondaryDomains: string[];
  rootOrgId: string;
  rootOrgName: string;
  globalComplianceTier: 'FINANCIAL_STRICT_SOC2_PCI' | 'HEALTHCARE_HIPAA' | 'GOV_CLOUD_FEDRAMP' | 'ENTERPRISE_STANDARD';
  kmsKeyArn: string;
  securityBaseline: {
    mfaEnforced: boolean;
    sessionTimeoutMinutes: number;
    fourEyesQuorumThreshold: number;
    auditLogRetentionDays: number;
    ipAllowlistEnforced: boolean;
  };
  maintenanceWindow: {
    preferredDay: string;
    startUtc: string;
    durationHours: number;
    timeZone: string;
  };
  emergencyBreakGlass: {
    primaryContact: string;
    emergencyEmail: string;
    escalationPhone: string;
    vaultEscrowReference: string;
  };
  updatedAt: string;
  updatedBy: string;
}

export type OrgLifecycleStatus = 'ACTIVE' | 'SUSPENDED' | 'PROVISIONING' | 'MAINTENANCE_LOCK';
export type OrgTier = 'GLOBAL_PARENT' | 'REGIONAL_SUBSIDIARY' | 'BUSINESS_UNIT' | 'SANDBOX_TENANT';

export interface AdminOrganization {
  id: string;
  name: string;
  code: string;
  description: string;
  tier: OrgTier;
  status: OrgLifecycleStatus;
  primaryContactName: string;
  primaryContactEmail: string;
  workspacesCount: number;
  activeUsersCount: number;
  defaultRegion: string;
  costCenterCode: string;
  createdAt: string;
  updatedAt: string;
}

export type WorkspaceTier = 'ENTERPRISE_PRODUCTION' | 'HIGH_THROUGHPUT_REPLICATION' | 'STAGING_VALIDATION' | 'DEVELOPMENT_SANDBOX';

export interface AdminWorkspace {
  id: string;
  orgId: string;
  orgName: string;
  name: string;
  code: string;
  description: string;
  tier: WorkspaceTier;
  status: 'ACTIVE' | 'ARCHIVED' | 'MAINTENANCE';
  residencyRegion: string;
  environmentCount: number;
  activeMemberCount: number;
  activeInitiativesCount: number;
  ownerName: string;
  ownerEmail: string;
  storageQuotaGb: number;
  storageUsedGb: number;
  createdAt: string;
  updatedAt: string;
}

export type EnvironmentTier = 'PRODUCTION' | 'STAGING' | 'UAT' | 'DEVELOPMENT' | 'SANDBOX';

export interface AdminEnvironment {
  id: string;
  workspaceId: string;
  workspaceName: string;
  orgId: string;
  name: string;
  tier: EnvironmentTier;
  isProduction: boolean;
  isolationBarrierStatus: 'STRICT_ENFORCED' | 'STANDARD_ISOLATED' | 'SHARED_DEVELOPMENT';
  dataMaskingEnforced: boolean;
  maintenanceLock: boolean;
  activeConnectionsCount: number;
  lastDeploymentAt: string;
  createdAt: string;
}

export interface ProjectBoundary {
  id: string;
  name: string;
  code: string;
  workspaceId: string;
  workspaceName: string;
  leadOwnerName: string;
  isolationPolicy: 'STRICT_ISOLATED' | 'CROSS_TENANT_READ' | 'FEDERATED_PEER';
  boundConnectionsCount: number;
  crossBoundaryAllowed: boolean;
  dataClassification: 'RESTRICTED_CONFIDENTIAL' | 'CONFIDENTIAL' | 'INTERNAL' | 'PUBLIC';
  tags: string[];
  createdAt: string;
}

export interface ResourceOwnership {
  id: string;
  resourceType: 'ORGANIZATION' | 'WORKSPACE' | 'PROJECT_BOUNDARY' | 'DATA_PIPELINE';
  resourceId: string;
  resourceName: string;
  primaryOwnerName: string;
  primaryOwnerEmail: string;
  secondaryOwnerName: string;
  secondaryOwnerEmail: string;
  assignedTeam: string;
  escalationContact: string;
  lastTransferDate: string;
  transferPending: boolean;
  pendingTransferTo?: string;
}

export interface QuotaAllocation {
  id: string;
  scopeType: 'ORGANIZATION' | 'WORKSPACE';
  scopeId: string;
  scopeName: string;
  concurrentMigrationsLimit: number;
  concurrentMigrationsUsed: number;
  bandwidthMbpsLimit: number;
  bandwidthMbpsUsed: number;
  maxActiveConnectionsLimit: number;
  activeConnectionsUsed: number;
  storageQuotaGb: number;
  storageUsedGb: number;
  peakThroughputCapIops: number;
  rateLimitReqPerSec: number;
  lastUpdated: string;
}

export interface AdminMetadataTag {
  id: string;
  key: string;
  valueSchema: string;
  category: 'COST_CENTER' | 'DATA_GOVERNANCE' | 'SECURITY_CLASSIFICATION' | 'OPERATIONAL_TIER';
  isMandatory: boolean;
  allowedValues?: string[];
  appliedResourceCount: number;
  description: string;
  createdAt: string;
}
