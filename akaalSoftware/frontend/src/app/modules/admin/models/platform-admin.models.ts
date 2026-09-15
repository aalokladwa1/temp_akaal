/**
 * AKAAL Administration — 5.10 Platform Administration Models
 * Models for Platform Configuration, Nodes / Services Configuration, Deployment,
 * Versions, Updates / Upgrade Management, Maintenance, Licensing & Entitlements,
 * Backup / Restore, and Support / Diagnostics.
 */

export interface PlatformConfigCategory {
  id: string;
  group: 'SYSTEM' | 'SECURITY' | 'STORAGE' | 'IPC';
  key: string;
  label: string;
  value: string;
  description: string;
  isSensitive: boolean;
  isEditable: boolean;
}

export interface PlatformServiceNode {
  id: string;
  serviceName: string;
  desiredReplicas: number;
  startupMode: 'DAEMON' | 'ON_DEMAND';
  memoryLimitMb: number;
  cpuLimitMillicores: number;
  listenBinding: string;
  status: 'CONFIGURED' | 'MAINTENANCE';
}

export interface DeploymentConfig {
  id: string;
  targetEnvironment: string;
  orchestrator: 'KUBERNETES' | 'STANDALONE_DAEMON' | 'CONTAINERD';
  rolloutStrategy: 'ROLLING' | 'RECREATE';
  configVersion: string;
  lastDeployedAt: string;
  activeProfile: string;
}

export interface PlatformVersions {
  appVersion: string;
  backendVersion: string;
  schemaVersion: string;
  engineProtocolVersion: string;
  buildCommit: string;
  buildTimestamp: string;
}

export interface LicenseEntitlement {
  id: string;
  edition: 'ENTERPRISE_CORE' | 'SOVEREIGN_GOVERNMENT' | 'GLOBAL_FEDERATION';
  licenseKeyRef: string;
  licensedNodes: number;
  licensedCapacityTb: number;
  expiresAt: string;
  features: string[];
  status: 'ACTIVE' | 'EXPIRED';
}

export interface UpgradeReleaseInfo {
  id: string;
  targetVersion: string;
  releaseDate: string;
  severity: 'RECOMMENDED' | 'CRITICAL_SECURITY' | 'MAINTENANCE';
  releaseNotesUrl: string;
  readinessCheckPassed: boolean;
}

export interface MaintenanceWindow {
  id: string;
  title: string;
  scheduledStartTime: string;
  scheduledEndTime: string;
  allowJobDrain: boolean;
  scope: 'CLUSTER_WIDE' | 'SPECIFIC_NODES';
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED';
}

export interface BackupRecord {
  id: string;
  backupName: string;
  backupType: 'METADATA_STATE' | 'FULL_CONFIG_CATALOG';
  sizeBytes: number;
  locationRef: string;
  sha256Checksum: string;
  createdAt: string;
  status: 'AVAILABLE' | 'ARCHIVED';
}

export interface DiagnosticPackage {
  id: string;
  requestedAt: string;
  ticketRef: string;
  includesSanitizedLogs: boolean;
  includesConfigSnapshot: boolean;
  status: 'READY' | 'GENERATING';
  packageSize: string;
}
