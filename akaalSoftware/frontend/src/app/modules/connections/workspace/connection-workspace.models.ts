/**
 * AKAAL Connection Workspace Domain & Presentation Models (Part C)
 * Governs full 6-tab Workspace: Overview, Configuration, Capabilities, Usage, Activity, Settings.
 * Preserves canonical verification semantics: Configured != Reachable != Authenticated != Permitted != Capable != Ready.
 */

import {
  ConnectionFamily,
  ConnectionRoleApplicability,
  ConnectionVerificationState,
  ConnectionFabricContext,
  ConnectionIntelligenceAdvisory
} from '../connections.models';

export type ConnectionWorkspaceTab =
  | 'overview'
  | 'configuration'
  | 'capabilities'
  | 'usage'
  | 'activity'
  | 'settings';

export type ProofLevel =
  | 'IMPLEMENTED'
  | 'UNIT_PROVEN'
  | 'INTEGRATION_PROVEN'
  | 'LIVE_PROVEN'
  | 'EXTERNAL_DEFERRED';

export type ActivityCategory =
  | 'ALL'
  | 'CONFIG'
  | 'TEST'
  | 'SECURITY'
  | 'USAGE'
  | 'LIFECYCLE';

export interface ActivityEvent {
  id: string;
  timestamp: string;
  category: ActivityCategory;
  title: string;
  description: string;
  actor: string;
  icon: string;
  stateBadge?: {
    label: string;
    type: 'success' | 'warning' | 'info' | 'neutral' | 'danger';
  };
}

export interface ConnectivityProbeResult {
  step: string;
  name: string;
  status: 'VERIFIED' | 'FAILED' | 'NOT_CHECKED' | 'NOT_APPLICABLE' | 'STALE';
  latencyMs?: number;
  details: string;
}

export interface PermissionCheckResult {
  permission: string;
  scope: string;
  status: 'VERIFIED' | 'FAILED' | 'NOT_CHECKED';
  details: string;
}

export interface CapabilitiesDetail {
  connectivityProbes: ConnectivityProbeResult[];
  permissionChecks: PermissionCheckResult[];
  
  sourceCapability: {
    supported: boolean;
    status: 'VERIFIED' | 'UNVERIFIED' | 'UNSUPPORTED' | 'CONDITIONAL';
    throughputRating: string;
    details: string;
  };

  targetCapability: {
    supported: boolean;
    status: 'VERIFIED' | 'UNVERIFIED' | 'UNSUPPORTED' | 'CONDITIONAL';
    acidCompliant: boolean;
    details: string;
  };

  discoveryCapability: {
    supported: boolean;
    status: 'VERIFIED' | 'UNVERIFIED' | 'UNSUPPORTED';
    supportedObjectTypes: string[];
    details: string;
  };

  cdcCapability: {
    type: 'LOGICAL_DECODING' | 'LOGMINER' | 'BINLOG' | 'CHANGE_STREAMS' | 'STREAM_OFFSET' | 'POLLING_QUERY' | 'NONE';
    label: string;
    status: 'VERIFIED' | 'UNVERIFIED' | 'UNSUPPORTED' | 'POLLING_ONLY';
    details: string;
  };

  validationCapability: {
    supported: boolean;
    status: 'VERIFIED' | 'UNVERIFIED' | 'UNSUPPORTED';
    supportedLevels: string[]; // e.g. ["L1 Row Count", "L2 Schema Parity", "L3 Partition Hash", "L4 Full Cell"]
    details: string;
  };

  providerLimitations: string[];
  proofLevel: ProofLevel;
  lastCheckedAt: string | null;
  configChangedSinceTest: boolean;
}

export interface ProjectUsageItem {
  id: string;
  key: string;
  name: string;
  environment: string;
  status: 'ACTIVE' | 'PLANNING' | 'COMPLETED' | 'ARCHIVED';
  associatedAt: string;
}

export interface MigrationUsageItem {
  id: string;
  name: string;
  projectKey: string;
  role: 'Source' | 'Target' | 'Reference';
  mode: string; // e.g. 'M1 Bulk', 'M2 Bulk+CDC', 'M7 Data Only'
  state: 'EXECUTING' | 'COMPLETED' | 'DRAFT' | 'PAUSED' | 'FAILED';
  lastRunAt: string;
}

export interface ValidationUsageItem {
  id: string;
  name: string;
  projectKey: string;
  role: 'Source Reference' | 'Target Assertion' | 'Dual Scope';
  verdict: 'PASSED' | 'FAILED' | 'WITHHELD' | 'NOT_EVALUATED';
  state: 'COMPLETED' | 'RUNNING' | 'QUEUED';
  lastRunAt: string;
}

export interface UsageDetail {
  projects: ProjectUsageItem[];
  migrations: MigrationUsageItem[];
  validations: ValidationUsageItem[];
  activeStreamsCount: number;
  scheduledExecutionsCount: number;
  referenceProtection: {
    canDelete: boolean;
    blockReason?: string;
    isReferenced: boolean;
  };
}

export interface EndpointConfigSpec {
  host?: string;
  port?: number;
  database?: string;
  schema?: string;
  serviceName?: string;
  sid?: string;
  tnsString?: string;
  driverMode?: string;
  bootstrapServers?: string;
  securityProtocol?: string;
  bucketName?: string;
  region?: string;
  endpointUrl?: string;
  prefix?: string;
  projectId?: string;
  datasetId?: string;
  location?: string;
  instanceUrl?: string;
  apiVersion?: string;
  filePath?: string;
  format?: string;
  replicaSet?: string;
  customParams?: Record<string, any>;
}

export interface AuthConfigSpec {
  authMethod: string;
  username?: string;
  secretRef?: string;
  secretSource?: 'Vault' | 'AWS Secrets Manager' | 'Azure KeyVault' | 'K8s Secret' | 'Environment Variable' | 'Direct Configured';
  roleArn?: string;
  principal?: string;
  keyId?: string;
  tenantId?: string;
  isConfigured: boolean;
}

export interface TlsConfigSpec {
  mode: 'DISABLED' | 'PREFERRED' | 'REQUIRED' | 'VERIFY_CA' | 'VERIFY_FULL';
  minVersion: 'TLS_1_2' | 'TLS_1_3';
  caCertRef?: string;
  serverNameOverride?: string;
  clientCertRef?: string;
  isMtlsEnabled: boolean;
}

export interface RouteConfigSpec {
  type: 'DIRECT' | 'HAPPY_EYEBALLS' | 'SSH_BASTION' | 'HTTP_PROXY' | 'SOCKS5_PROXY' | 'PRIVATE_ENDPOINT';
  sshHost?: string;
  sshPort?: number;
  sshUsername?: string;
  sshKeyRef?: string;
  proxyHost?: string;
  proxyPort?: number;
  proxyAuthMethod?: string;
  privateEndpointUrl?: string;
  fabricSite?: string;
  fabricTransitVpc?: string;
}

export interface AdvancedSettingsSpec {
  dnsTimeoutMs: number;
  connectTimeoutMs: number;
  socketTimeoutMs: number;
  tcpKeepaliveEnabled: boolean;
  keepaliveIdleSec: number;
  keepaliveIntervalSec: number;
  sessionParams?: Record<string, string>;
}

export interface DetailedConnectionRecord {
  id: string;
  name: string;
  description: string;
  providerId: string;
  providerName: string;
  family: ConnectionFamily;
  environment: 'Production' | 'Staging' | 'Development' | 'Disaster Recovery';
  workspaceId: string;
  workspaceName: string;
  organizationId: string;
  organizationName: string;
  
  // Managed Cloud origin context (if applicable)
  managedCloudId?: string;
  managedCloudName?: string;
  managedResourceType?: string;

  // Endpoint display summary
  endpointDisplay: string;
  safeRouteInfo: string;
  authMethodDisplay: string;
  roleApplicability: ConnectionRoleApplicability;
  
  // Verification State
  verificationState: ConnectionVerificationState;
  lastVerifiedAt: string | null;
  lastVerifiedDetails: string;
  verificationFailureReason?: string;
  configChangedSinceTest: boolean;

  // Lifecycle
  lifecycleState: 'ACTIVE' | 'DISABLED' | 'ARCHIVED';
  disabledAt?: string;
  archivedAt?: string;

  // Fabric & Platform Context
  fabric: ConnectionFabricContext;
  advisory?: ConnectionIntelligenceAdvisory;
  tags: string[];
  createdAt: string;
  updatedAt: string;

  // 6 Tab Specific Data Structures
  endpointConfig: EndpointConfigSpec;
  authConfig: AuthConfigSpec;
  tlsConfig: TlsConfigSpec;
  routeConfig: RouteConfigSpec;
  advancedSettings: AdvancedSettingsSpec;
  capabilities: CapabilitiesDetail;
  usage: UsageDetail;
  activities: ActivityEvent[];
}
