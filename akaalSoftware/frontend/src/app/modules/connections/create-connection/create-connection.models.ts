/**
 * AKAAL Create Connection Domain & Presentation Models
 * Comprehensive 5-Step Wizard Contracts:
 * 1. Provider -> 2. Connection -> 3. Security & Network -> 4. Capabilities & Validation -> 5. Review & Create
 */

import {
  ConnectionFamily,
  ConnectionRoleApplicability,
  ConnectionVerificationState
} from '../connections.models';

export type CreateConnectionStepIndex = 1 | 2 | 3 | 4 | 5;

export interface CreateConnectionStepItem {
  index: CreateConnectionStepIndex;
  label: string;
  sublabel: string;
  description: string;
}

export type TlsMode =
  | 'DISABLED'
  | 'PREFERRED'
  | 'REQUIRED'
  | 'VERIFY_CA'
  | 'VERIFY_FULL';

export type MinTlsVersion = 'TLS_1_2' | 'TLS_1_3';

export type NetworkRouteType =
  | 'DIRECT'
  | 'DNS_HAPPY_EYEBALLS'
  | 'SSH_BASTION'
  | 'HTTP_PROXY'
  | 'SOCKS5_PROXY'
  | 'PRIVATE_ENDPOINT';

export type SshAuthMethod = 'PRIVATE_KEY' | 'PASSWORD';

export type ProxyAuthMethod = 'NONE' | 'USERNAME_PASSWORD';

export type ProbeStatus =
  | 'VERIFIED'
  | 'NOT_VERIFIED'
  | 'DENIED'
  | 'UNSUPPORTED'
  | 'UNKNOWN'
  | 'TESTING'
  | 'FAILED';

export interface ConnectivityFactItem {
  key: string;
  label: string;
  status: 'PASSED' | 'FAILED' | 'WARNING' | 'SKIPPED' | 'TESTING';
  value: string;
  detail?: string;
  latencyMs?: number;
}

export interface PermissionProbeItem {
  privilege: string; // e.g. 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE TABLE', 'ALTER', 'DROP'
  status: ProbeStatus;
  scope?: string;
  reason?: string;
}

export interface CapabilityProbeItem {
  capability: string; // e.g. 'wal_level=logical', 'binlog_format=ROW', 'ARCHIVELOG', 'Partition Pruning', 'Savepoints'
  status: ProbeStatus;
  category: 'CDC' | 'STORAGE' | 'TRANSACTION' | 'DISCOVERY' | 'VALIDATION';
  detail?: string;
}

export interface VerificationFacts {
  testedAt: string | null;
  overallStatus: 'PASSED' | 'FAILED' | 'PARTIAL' | 'UNTESTED';
  connectivity: ConnectivityFactItem[];
  permissions: PermissionProbeItem[];
  capabilities: CapabilityProbeItem[];
  sourceEligibility: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE' | 'UNKNOWN';
  targetEligibility: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE' | 'UNKNOWN';
  discoveryCapability: 'SUPPORTED' | 'PARTIAL' | 'UNAVAILABLE' | 'UNKNOWN';
  cdcCapability: {
    type: 'NATIVE_DATABASE_CDC' | 'STREAM_OFFSET_CONSUMPTION' | 'OBJECT_EVENT_NOTIFICATION' | 'POLLING_WATERMARK' | 'NONE';
    label: string;
    description: string;
  };
  validationCapability: {
    supported: boolean;
    rowHashChecksum: boolean;
    columnProfile: boolean;
    sampleReconciliation: boolean;
    nonMutatingGuaranteed: boolean;
  };
  limitations: string[];
  warnings: string[];
}

// Managed Cloud Resolver Types
export type ManagedCloudProviderId = 'AWS_MANAGED' | 'AZURE_MANAGED' | 'GCP_MANAGED' | 'OCI_MANAGED';

export interface ManagedCloudProfile {
  id: ManagedCloudProviderId;
  name: string;
  vendorName: string;
  icon: string;
  supportedResourceTypes: { label: string; value: string; physicalProviderId: string }[];
}

// Provider Catalog Manifest
export interface ProviderCatalogItem {
  id: string; // e.g. 'postgresql', 'oracle', 'kafka', 's3'
  name: string;
  family: ConnectionFamily;
  categoryLabel: string;
  vendorName: string;
  icon: string;
  roleApplicability: ConnectionRoleApplicability;
  supportsTls: boolean;
  supportsMtls: boolean;
  defaultPort?: number;
  isCustomExtension: boolean;
  customExtensionType?: 'ORACLE' | 'BIGQUERY' | 'SPANNER' | 'SALESFORCE' | 'SERVICENOW' | 'SAP_APPLICATION';
  authMethods: { label: string; value: string; desc?: string }[];
  defaultAuthMethod: string;
  supportedRoles: ('SOURCE' | 'TARGET' | 'REFERENCE' | 'VALIDATION')[];
  description: string;
}

// Wizard Draft State
export interface CreateConnectionDraft {
  // Step 1: Provider Selection
  selectedProviderId: string | null;
  isManagedCloud: boolean;
  managedCloudId: ManagedCloudProviderId | null;
  managedResourceType: string | null;
  isFileDataset: boolean;
  fileDatasetFormat: 'CSV' | 'JSONL' | 'PARQUET' | null;

  // Step 2: Connection Configuration
  // 2.1 Common Resource Identity
  name: string;
  description: string;
  environment: 'Production' | 'Staging' | 'Development' | 'Disaster Recovery';
  workspaceId: string;

  // 2.2 Generic / Dynamic Parameters Map
  parameters: Record<string, any>;

  // 2.3 Provider-Specific Extension States
  // Oracle
  oracleAddressingMode: 'HOST_SERVICE' | 'HOST_SID' | 'TNS_ENTRY' | 'ORACLE_WALLET';
  oracleHost: string;
  oraclePort: number;
  oracleServiceName: string;
  oracleSid: string;
  oracleTnsName: string;
  oracleTnsAdminPath: string;
  oracleDriverMode: 'THIN' | 'THICK';
  oracleClientLibPath: string;
  oraclePrivilegeMode: 'NORMAL' | 'SYSDBA' | 'SYSOPER';
  oracleWalletPath: string;

  // BigQuery
  bigqueryProjectId: string;
  bigqueryDataset: string;
  bigqueryLocation: string;
  bigqueryBillingProject: string;
  bigqueryUseStorageReadApi: boolean;
  bigqueryRequestTimeoutSec: number;

  // Spanner
  spannerProjectId: string;
  spannerInstanceId: string;
  spannerDatabaseId: string;
  spannerEmulatorHost: string;
  spannerChannelPoolSize: number;
  spannerPriority: 'HIGH' | 'MEDIUM' | 'LOW';

  // Salesforce
  salesforceInstanceUrl: string;
  salesforceAuthFlow: 'OAUTH' | 'JWT_BEARER' | 'USERNAME_PASSWORD';
  salesforceApiVersion: string;
  salesforceClientId: string;
  salesforceSubject: string;

  // ServiceNow
  servicenowInstanceUrl: string;
  servicenowAuthMode: 'BASIC' | 'OAUTH';
  servicenowPageSize: number;

  // SAP Application
  sapConnectionMode: 'RFC_BAPI' | 'ODATA';
  sapServerMode: 'APPLICATION_SERVER' | 'MESSAGE_SERVER';
  sapAppServerHost: string;
  sapSystemNumber: string;
  sapClient: string;
  sapMessageServerHost: string;
  sapGroup: string;
  sapSystemId: string;
  sapLanguage: string;
  sapSncEnabled: boolean;
  sapSncPartnerName: string;
  sapOdataServiceUrl: string;

  // Step 3: Security & Network
  authMethod: string;
  authUsername: string;
  authSecretRef: string; // Opaque reference, e.g. 'vault://...' or direct masked input
  authSecretValue: string; // Temporarily collected for probe, never stored/logged/rendered in plaintext
  authRoleArn: string;
  authPrincipal: string;
  authKeyId: string;
  authTenantId: string;

  // TLS & Certificates
  tlsMode: TlsMode;
  minTlsVersion: MinTlsVersion;
  caCertificateRef: string;
  serverNameOverride: string;
  allowSelfSigned: boolean;
  
  // mTLS
  clientCertRef: string;
  clientPrivateKeyRef: string;
  clientPrivateKeyPassphraseRef: string;

  // Network Routing
  networkRoute: NetworkRouteType;
  sshBastionHost: string;
  sshBastionPort: number;
  sshBastionUsername: string;
  sshBastionAuthMethod: SshAuthMethod;
  sshBastionKeyRef: string;
  sshBastionPasswordRef: string;
  sshHostKeyFingerprint: string;
  allowUnverifiedSshHost: boolean;

  proxyHost: string;
  proxyPort: number;
  proxyAuthMethod: ProxyAuthMethod;
  proxyUsername: string;
  proxyPasswordRef: string;

  privateEndpointUrl: string;
  fabricSite: string;
  fabricLocality: string;
  fabricTransitVpc: string;

  // Advanced Network
  dnsTimeoutMs: number;
  connectTimeoutMs: number;
  socketTimeoutMs: number;
  tcpKeepaliveEnabled: boolean;
  keepaliveIdleSec: number;
  keepaliveIntervalSec: number;
  keepaliveProbes: number;

  // Step 4: Verification State & Facts
  verificationFacts: VerificationFacts;
  isStaleVerification: boolean; // Set true when identity/endpoint/auth/TLS changes after test
  isTesting: boolean;
  isTestingPermissions: boolean;
  isTestingCapabilities: boolean;
}
