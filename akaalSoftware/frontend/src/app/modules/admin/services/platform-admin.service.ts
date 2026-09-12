/**
 * AKAAL Administration — 5.10 Platform Administration Service
 * Authoritative presentation service for Platform Configuration, Nodes / Services,
 * Deployment, Versions, Upgrades, Maintenance, Licensing, Backup/Restore, and Diagnostics.
 */

import { Injectable, signal } from '@angular/core';
import {
  PlatformConfigCategory,
  PlatformServiceNode,
  DeploymentConfig,
  PlatformVersions,
  LicenseEntitlement,
  UpgradeReleaseInfo,
  MaintenanceWindow,
  BackupRecord,
  DiagnosticPackage
} from '../models/platform-admin.models';

@Injectable({
  providedIn: 'root'
})
export class PlatformAdminService {
  // Platform Configuration Settings
  public platformConfigs = signal<PlatformConfigCategory[]>([
    {
      id: 'cfg-sys-01',
      group: 'SYSTEM',
      key: 'system.max_concurrent_worker_threads',
      label: 'Max Concurrent Worker Threads',
      value: '64',
      description: 'Global compute limit for concurrent pipeline worker threads per node.',
      isSensitive: false,
      isEditable: true
    },
    {
      id: 'cfg-sys-02',
      group: 'SYSTEM',
      key: 'system.default_session_timeout_seconds',
      label: 'Default Session Timeout Seconds',
      value: '3600',
      description: 'Maximum idle duration for control plane interactive administrative sessions.',
      isSensitive: false,
      isEditable: true
    },
    {
      id: 'cfg-sec-01',
      group: 'SECURITY',
      key: 'security.tls_minimum_protocol_version',
      label: 'TLS Minimum Protocol Version',
      value: 'TLSv1.3',
      description: 'Strict transport layer security enforcement across all ingress and egress channels.',
      isSensitive: false,
      isEditable: false
    },
    {
      id: 'cfg-ipc-01',
      group: 'IPC',
      key: 'ipc.named_pipe_path',
      label: 'Named Pipe IPC Socket Path',
      value: '\\\\.\\pipe\\akaal_ipc',
      description: 'Local boundary pipe for transport-neutral communication between Wails GUI and Engine.',
      isSensitive: false,
      isEditable: false
    }
  ]);

  // Nodes & Services Configuration
  public serviceNodes = signal<PlatformServiceNode[]>([
    {
      id: 'node-eng-01',
      serviceName: 'akaalEngine Core Execution Daemon',
      desiredReplicas: 3,
      startupMode: 'DAEMON',
      memoryLimitMb: 8192,
      cpuLimitMillicores: 4000,
      listenBinding: '127.0.0.1:50051',
      status: 'CONFIGURED'
    },
    {
      id: 'node-pipe-01',
      serviceName: 'akaalPipeline Orchestration Engine',
      desiredReplicas: 2,
      startupMode: 'DAEMON',
      memoryLimitMb: 4096,
      cpuLimitMillicores: 2000,
      listenBinding: '127.0.0.1:50052',
      status: 'CONFIGURED'
    },
    {
      id: 'node-cdc-01',
      serviceName: 'akaalEngine CDC Replication Buffer',
      desiredReplicas: 2,
      startupMode: 'DAEMON',
      memoryLimitMb: 16384,
      cpuLimitMillicores: 8000,
      listenBinding: '127.0.0.1:50053',
      status: 'CONFIGURED'
    }
  ]);

  // Deployment Configuration
  public deploymentConfig = signal<DeploymentConfig>({
    id: 'dep-01',
    targetEnvironment: 'Enterprise Production Cluster',
    orchestrator: 'KUBERNETES',
    rolloutStrategy: 'ROLLING',
    configVersion: 'v2.6.4-prod',
    lastDeployedAt: '2026-02-18 04:00 UTC',
    activeProfile: 'sovereign-production-profile'
  });

  // Canonical Versions
  public versions = signal<PlatformVersions>({
    appVersion: '2.4.0',
    backendVersion: '1.9.2',
    schemaVersion: '2026.02.01',
    engineProtocolVersion: 'v2.4',
    buildCommit: '9c4f881b',
    buildTimestamp: '2026-02-19 12:00:00 UTC'
  });

  // Commercial Licensing & Entitlements
  public licensing = signal<LicenseEntitlement>({
    id: 'lic-corp-01',
    edition: 'ENTERPRISE_CORE',
    licenseKeyRef: 'vault://secret/license/akaal-ent-key',
    licensedNodes: 32,
    licensedCapacityTb: 500,
    expiresAt: '2027-12-31',
    features: [
      'Multi-Tenant Organization Hierarchy',
      'Real-Time CDC Ingestion',
      'Data Masking & Format-Preserving Encryption',
      'Dual-Custody Maker-Checker Governance',
      'Cross-Cloud Federation'
    ],
    status: 'ACTIVE'
  });

  // Updates & Upgrades Management
  public upgradeInfo = signal<UpgradeReleaseInfo>({
    id: 'upg-2.4.1',
    targetVersion: '2.4.1',
    releaseDate: '2026-03-01',
    severity: 'RECOMMENDED',
    releaseNotesUrl: 'https://docs.akaaltech.internal/releases/v2.4.1',
    readinessCheckPassed: true
  });

  // Maintenance Windows
  public maintenanceWindows = signal<MaintenanceWindow[]>([
    {
      id: 'maint-01',
      title: 'Q1 Quarterly Database Kernel Patching Window',
      scheduledStartTime: '2026-03-15 02:00 UTC',
      scheduledEndTime: '2026-03-15 06:00 UTC',
      allowJobDrain: true,
      scope: 'CLUSTER_WIDE',
      status: 'SCHEDULED'
    }
  ]);

  // Backups
  public backups = signal<BackupRecord[]>([
    {
      id: 'bak-01',
      backupName: 'akaal-control-plane-metadata-20260218.snap',
      backupType: 'METADATA_STATE',
      sizeBytes: 14892010,
      locationRef: 's3://akaal-cold-backups/metadata/20260218.snap',
      sha256Checksum: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
      createdAt: '2026-02-18 01:00 UTC',
      status: 'AVAILABLE'
    }
  ]);

  // Diagnostic Packages
  public diagnostics = signal<DiagnosticPackage[]>([
    {
      id: 'diag-01',
      requestedAt: '2026-02-19 10:15 UTC',
      ticketRef: 'SUP-99120',
      includesSanitizedLogs: true,
      includesConfigSnapshot: true,
      status: 'READY',
      packageSize: '18.4 MB'
    }
  ]);

  public updateConfigValue(id: string, newValue: string): void {
    this.platformConfigs.update(list =>
      list.map(c => (c.id === id ? { ...c, value: newValue } : c))
    );
  }

  public createMaintenanceWindow(window: Omit<MaintenanceWindow, 'id' | 'status'>): void {
    const newRecord: MaintenanceWindow = {
      ...window,
      id: `maint-${Date.now()}`,
      status: 'SCHEDULED'
    };
    this.maintenanceWindows.update(list => [newRecord, ...list]);
  }

  public requestDiagnostics(ticketRef: string): void {
    const pkg: DiagnosticPackage = {
      id: `diag-${Date.now()}`,
      requestedAt: 'Just now',
      ticketRef,
      includesSanitizedLogs: true,
      includesConfigSnapshot: true,
      status: 'READY',
      packageSize: '12.1 MB'
    };
    this.diagnostics.update(list => [pkg, ...list]);
  }
}
