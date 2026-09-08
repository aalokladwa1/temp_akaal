/**
 * AKAAL Connection Workspace Service (Part C)
 * Governs state, verification probes, configuration editing, staleness lifecycle, and tabs.
 * Preserves canonical verification semantics: Configured != Reachable != Authenticated != Permitted != Capable != Ready.
 */

import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import { Router } from '@angular/router';
import {
  DetailedConnectionRecord,
  ConnectionWorkspaceTab,
  ActivityEvent,
  ActivityCategory
} from './connection-workspace.models';
import { DETAILED_CONNECTION_FIXTURES } from './connection-workspace.fixtures';
import { ConnectionsService } from '../connections.service';

@Injectable({
  providedIn: 'root'
})
export class ConnectionWorkspaceService {
  private router?: Router;
  private connectionsService?: ConnectionsService;

  constructor(
    @Optional() router?: Router,
    @Optional() connectionsService?: ConnectionsService
  ) {
    if (router) this.router = router;
    if (connectionsService) this.connectionsService = connectionsService;
    else {
      try {
        this.router = inject(Router);
      } catch {}
      try {
        this.connectionsService = inject(ConnectionsService);
      } catch {}
    }
  }

  // Active Connection Store
  public connection = signal<DetailedConnectionRecord | null>(DETAILED_CONNECTION_FIXTURES['conn-ora-rac-01']);
  public activeTab = signal<ConnectionWorkspaceTab>('overview');
  public isLoading = signal<boolean>(false);
  public errorMessage = signal<string | null>(null);

  // Configuration Edit State
  public isEditingConfig = signal<boolean>(false);
  public configDraft = signal<any>({});
  public isSavingConfig = signal<boolean>(false);
  public configNotice = signal<string | null>(null);

  // Interactive Verification / Probe State
  public isRunningTest = signal<boolean>(false);
  public isRunningPermissionProbe = signal<boolean>(false);
  public isRunningCapabilityProbe = signal<boolean>(false);
  public testResultMessage = signal<string | null>(null);

  // Activity Tab Filter State
  public activityCategoryFilter = signal<ActivityCategory>('ALL');

  // Copy Feedback
  public copiedId = signal<boolean>(false);

  // Delete & Danger Dialog
  public isDeleteDialogOpen = signal<boolean>(false);
  public isArchiveDialogOpen = signal<boolean>(false);
  public isDisableDialogOpen = signal<boolean>(false);

  // ==========================================================================
  // COMPUTED SIGNALS
  // ==========================================================================

  public filteredActivities = computed<ActivityEvent[]>(() => {
    const conn = this.connection();
    if (!conn) return [];
    const cat = this.activityCategoryFilter();
    if (cat === 'ALL') return conn.activities;
    return conn.activities.filter(a => a.category === cat);
  });

  public isVerificationStale = computed<boolean>(() => {
    const conn = this.connection();
    if (!conn) return false;
    return (
      conn.configChangedSinceTest ||
      conn.verificationState === 'CONFIG_CHANGED_SINCE_TEST' ||
      conn.verificationState === 'VERIFIED_STALE'
    );
  });

  // ==========================================================================
  // NAVIGATION & LIFECYCLE
  // ==========================================================================

  public loadConnection(id: string, initialTab: ConnectionWorkspaceTab = 'overview'): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.activeTab.set(initialTab);

    // Search detailed fixtures first
    let found = DETAILED_CONNECTION_FIXTURES[id];

    // Fallback: If not found in detailed fixtures, construct from summary connection
    if (!found && this.connectionsService) {
      const summary = this.connectionsService.connections().find(c => c.id === id);
      if (summary) {
        found = {
          ...DETAILED_CONNECTION_FIXTURES['conn-ora-rac-01'],
          id: summary.id,
          name: summary.name,
          description: summary.description || '',
          providerId: summary.providerId,
          providerName: summary.providerName,
          family: summary.family,
          environment: summary.environment,
          workspaceId: summary.workspaceId,
          workspaceName: summary.workspaceName || 'Default Workspace',
          endpointDisplay: summary.endpointDisplay,
          safeRouteInfo: summary.safeRouteInfo || 'Direct',
          authMethodDisplay: summary.authMethodDisplay,
          roleApplicability: summary.roleApplicability,
          verificationState: summary.verificationState,
          lastVerifiedAt: summary.lastVerifiedAt,
          lastVerifiedDetails: summary.lastVerifiedDetails || '',
          configChangedSinceTest: !!summary.configChangedSinceTest,
          tags: summary.tags || []
        };
      }
    }

    if (found) {
      this.connection.set(JSON.parse(JSON.stringify(found)));
      this.isLoading.set(false);
    } else {
      // Default to Oracle RAC fixture for resilient demo viewing
      this.connection.set(JSON.parse(JSON.stringify(DETAILED_CONNECTION_FIXTURES['conn-ora-rac-01'])));
      this.isLoading.set(false);
    }
  }

  public setActiveTab(tab: ConnectionWorkspaceTab): void {
    this.activeTab.set(tab);
    if (this.router && this.connection()) {
      const connId = this.connection()!.id;
      // Keep URL synced cleanly
      this.router.navigate(['/connections', connId, tab], { replaceUrl: true });
    }
  }

  public copyConnectionId(): void {
    const conn = this.connection();
    if (!conn) return;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(conn.id);
    }
    this.copiedId.set(true);
    setTimeout(() => this.copiedId.set(false), 2000);
  }

  // ==========================================================================
  // CONFIGURATION EDITING & STALENESS LIFECYCLE
  // ==========================================================================

  public startEditingConfig(): void {
    const conn = this.connection();
    if (!conn) return;
    this.configDraft.set({
      host: conn.endpointConfig.host || '',
      port: conn.endpointConfig.port || 5432,
      database: conn.endpointConfig.database || '',
      schema: conn.endpointConfig.schema || '',
      serviceName: conn.endpointConfig.serviceName || '',
      sid: conn.endpointConfig.sid || '',
      bootstrapServers: conn.endpointConfig.bootstrapServers || '',
      bucketName: conn.endpointConfig.bucketName || '',
      region: conn.endpointConfig.region || '',
      projectId: conn.endpointConfig.projectId || '',
      datasetId: conn.endpointConfig.datasetId || '',
      instanceUrl: conn.endpointConfig.instanceUrl || '',
      filePath: conn.endpointConfig.filePath || '',
      authMethod: conn.authConfig.authMethod,
      username: conn.authConfig.username || '',
      secretRef: conn.authConfig.secretRef || '',
      tlsMode: conn.tlsConfig.mode,
      minTlsVersion: conn.tlsConfig.minVersion,
      routeType: conn.routeConfig.type,
      sshHost: conn.routeConfig.sshHost || '',
      sshPort: conn.routeConfig.sshPort || 22,
      proxyHost: conn.routeConfig.proxyHost || '',
      proxyPort: conn.routeConfig.proxyPort || 8080,
      dnsTimeoutMs: conn.advancedSettings.dnsTimeoutMs,
      connectTimeoutMs: conn.advancedSettings.connectTimeoutMs,
      socketTimeoutMs: conn.advancedSettings.socketTimeoutMs
    });
    this.isEditingConfig.set(true);
  }

  public cancelEditingConfig(): void {
    this.isEditingConfig.set(false);
    this.configDraft.set({});
  }

  public saveConfigChanges(): void {
    const conn = this.connection();
    if (!conn) return;

    const draft = this.configDraft();
    const nowIso = new Date().toISOString();

    // Check if material endpoint / security fields changed
    const materialChange =
      draft.host !== conn.endpointConfig.host ||
      draft.port !== conn.endpointConfig.port ||
      draft.database !== conn.endpointConfig.database ||
      draft.serviceName !== conn.endpointConfig.serviceName ||
      draft.bootstrapServers !== conn.endpointConfig.bootstrapServers ||
      draft.bucketName !== conn.endpointConfig.bucketName ||
      draft.authMethod !== conn.authConfig.authMethod ||
      draft.username !== conn.authConfig.username ||
      draft.tlsMode !== conn.tlsConfig.mode ||
      draft.routeType !== conn.routeConfig.type;

    this.connection.update(curr => {
      if (!curr) return null;
      const updated: DetailedConnectionRecord = {
        ...curr,
        endpointConfig: {
          ...curr.endpointConfig,
          host: draft.host,
          port: draft.port,
          database: draft.database,
          schema: draft.schema,
          serviceName: draft.serviceName,
          bootstrapServers: draft.bootstrapServers,
          bucketName: draft.bucketName,
          region: draft.region,
          projectId: draft.projectId,
          datasetId: draft.datasetId,
          instanceUrl: draft.instanceUrl,
          filePath: draft.filePath
        },
        authConfig: {
          ...curr.authConfig,
          authMethod: draft.authMethod,
          username: draft.username,
          secretRef: draft.secretRef
        },
        tlsConfig: {
          ...curr.tlsConfig,
          mode: draft.tlsMode,
          minVersion: draft.minTlsVersion
        },
        routeConfig: {
          ...curr.routeConfig,
          type: draft.routeType,
          sshHost: draft.sshHost,
          sshPort: draft.sshPort,
          proxyHost: draft.proxyHost,
          proxyPort: draft.proxyPort
        },
        advancedSettings: {
          ...curr.advancedSettings,
          dnsTimeoutMs: draft.dnsTimeoutMs,
          connectTimeoutMs: draft.connectTimeoutMs,
          socketTimeoutMs: draft.socketTimeoutMs
        },
        // Staleness semantics
        verificationState: materialChange ? 'CONFIG_CHANGED_SINCE_TEST' : curr.verificationState,
        configChangedSinceTest: materialChange ? true : curr.configChangedSinceTest,
        lastVerifiedDetails: materialChange
          ? 'Configuration modified after last verification probe. Retest required.'
          : curr.lastVerifiedDetails,
        updatedAt: nowIso,
        activities: [
          {
            id: 'act-' + Date.now(),
            timestamp: nowIso,
            category: 'CONFIG',
            title: 'Configuration Updated',
            description: materialChange
              ? 'Endpoint/security parameters updated. Prior verification marked stale.'
              : 'Connection configuration parameters updated.',
            actor: 'admin-operator@corp.internal',
            icon: 'sliders',
            stateBadge: materialChange ? { label: 'Needs Retest', type: 'warning' } : { label: 'Updated', type: 'neutral' }
          },
          ...curr.activities
        ]
      };
      return updated;
    });

    this.isSavingConfig.set(false);
    this.isEditingConfig.set(false);
    this.configNotice.set(
      materialChange
        ? 'Configuration saved. Previous verification is now stale. Retest connection to verify new parameters.'
        : 'Configuration saved successfully.'
    );
    setTimeout(() => this.configNotice.set(null), 5000);
  }

  // ==========================================================================
  // INTERACTIVE TEST PROBES (Point-in-Time Factual Verification)
  // ==========================================================================

  public testConnection(): void {
    const conn = this.connection();
    if (!conn) return;

    this.isRunningTest.set(true);
    this.testResultMessage.set(null);

    // Set state to TESTING
    this.connection.update(c => {
      if (!c) return null;
      return {
        ...c,
        verificationState: 'TESTING',
        lastVerifiedDetails: 'Dispatching connectivity probe...'
      };
    });

    setTimeout(() => {
      const nowIso = new Date().toISOString();
      this.connection.update(c => {
        if (!c) return null;
        return {
          ...c,
          verificationState: 'VERIFIED_RECENT',
          lastVerifiedAt: nowIso,
          configChangedSinceTest: false,
          lastVerifiedDetails: 'Point-in-time probe verified in 1.4ms · TLS 1.3 · Authentication & catalog read passed',
          updatedAt: nowIso,
          capabilities: {
            ...c.capabilities,
            lastCheckedAt: nowIso,
            configChangedSinceTest: false,
            connectivityProbes: c.capabilities.connectivityProbes.map(p => ({
              ...p,
              status: 'VERIFIED'
            }))
          },
          activities: [
            {
              id: 'act-' + Date.now(),
              timestamp: nowIso,
              category: 'TEST',
              title: 'Connection Test Passed',
              description: 'Point-in-time verification probe verified DNS, TLS 1.3 handshake, and authentication.',
              actor: 'system-probe-scheduler',
              icon: 'shield-check',
              stateBadge: { label: 'Verified', type: 'success' }
            },
            ...c.activities
          ]
        };
      });

      this.isRunningTest.set(false);
      this.testResultMessage.set('Connection probe verified successfully.');
      setTimeout(() => this.testResultMessage.set(null), 4000);
    }, 600);
  }

  public runPermissionProbe(): void {
    this.isRunningPermissionProbe.set(true);
    setTimeout(() => {
      const nowIso = new Date().toISOString();
      this.connection.update(c => {
        if (!c) return null;
        return {
          ...c,
          capabilities: {
            ...c.capabilities,
            permissionChecks: c.capabilities.permissionChecks.map(p => ({
              ...p,
              status: 'VERIFIED'
            }))
          },
          activities: [
            {
              id: 'act-' + Date.now(),
              timestamp: nowIso,
              category: 'SECURITY',
              title: 'Permission Probe Completed',
              description: 'Introspected and verified database table and schema privileges.',
              actor: 'system-permission-probe',
              icon: 'shield-check',
              stateBadge: { label: 'Permitted', type: 'success' }
            },
            ...c.activities
          ]
        };
      });
      this.isRunningPermissionProbe.set(false);
    }, 500);
  }

  public runCapabilityProbe(): void {
    this.isRunningCapabilityProbe.set(true);
    setTimeout(() => {
      const nowIso = new Date().toISOString();
      this.connection.update(c => {
        if (!c) return null;
        return {
          ...c,
          capabilities: {
            ...c.capabilities,
            sourceCapability: { ...c.capabilities.sourceCapability, status: 'VERIFIED' },
            targetCapability: { ...c.capabilities.targetCapability, status: 'VERIFIED' },
            discoveryCapability: { ...c.capabilities.discoveryCapability, status: 'VERIFIED' },
            cdcCapability: { ...c.capabilities.cdcCapability, status: 'VERIFIED' }
          },
          activities: [
            {
              id: 'act-' + Date.now(),
              timestamp: nowIso,
              category: 'TEST',
              title: 'Capability Probe Completed',
              description: 'Attested engine discovery depth and synchronization capabilities.',
              actor: 'system-capability-probe',
              icon: 'activity',
              stateBadge: { label: 'Capable', type: 'info' }
            },
            ...c.activities
          ]
        };
      });
      this.isRunningCapabilityProbe.set(false);
    }, 500);
  }

  // ==========================================================================
  // SETTINGS & LIFECYCLE
  // ==========================================================================

  public saveMetadata(name: string, description: string, tags: string[]): void {
    const nowIso = new Date().toISOString();
    this.connection.update(c => {
      if (!c) return null;
      return {
        ...c,
        name,
        description,
        tags,
        updatedAt: nowIso,
        activities: [
          {
            id: 'act-' + Date.now(),
            timestamp: nowIso,
            category: 'CONFIG',
            title: 'General Metadata Updated',
            description: `Updated connection display name and description.`,
            actor: 'admin-operator@corp.internal',
            icon: 'sliders',
            stateBadge: { label: 'Updated', type: 'neutral' }
          },
          ...c.activities
        ]
      };
    });
  }

  public toggleDisableConnection(): void {
    const conn = this.connection();
    if (!conn) return;
    const nowIso = new Date().toISOString();
    const isDisabling = conn.lifecycleState === 'ACTIVE';

    this.connection.update(c => {
      if (!c) return null;
      return {
        ...c,
        lifecycleState: isDisabling ? 'DISABLED' : 'ACTIVE',
        disabledAt: isDisabling ? nowIso : undefined,
        updatedAt: nowIso,
        activities: [
          {
            id: 'act-' + Date.now(),
            timestamp: nowIso,
            category: 'LIFECYCLE',
            title: isDisabling ? 'Connection Disabled' : 'Connection Enabled',
            description: isDisabling
              ? 'Connection profile disabled for new workflow assignments.'
              : 'Connection profile re-enabled for active use.',
            actor: 'admin-operator@corp.internal',
            icon: isDisabling ? 'pause-circle' : 'play-circle',
            stateBadge: isDisabling ? { label: 'Disabled', type: 'warning' } : { label: 'Active', type: 'success' }
          },
          ...c.activities
        ]
      };
    });
    this.isDisableDialogOpen.set(false);
  }

  public archiveConnection(): void {
    const conn = this.connection();
    if (!conn) return;
    const nowIso = new Date().toISOString();

    this.connection.update(c => {
      if (!c) return null;
      return {
        ...c,
        lifecycleState: 'ARCHIVED',
        archivedAt: nowIso,
        updatedAt: nowIso,
        activities: [
          {
            id: 'act-' + Date.now(),
            timestamp: nowIso,
            category: 'LIFECYCLE',
            title: 'Connection Archived',
            description: 'Connection archived. Removed from active pickers while preserving historical references.',
            actor: 'admin-operator@corp.internal',
            icon: 'archive',
            stateBadge: { label: 'Archived', type: 'neutral' }
          },
          ...c.activities
        ]
      };
    });
    this.isArchiveDialogOpen.set(false);
  }

  public deleteConnection(): void {
    const conn = this.connection();
    if (!conn) return;

    if (!conn.usage.referenceProtection.canDelete) {
      alert('Cannot delete connection with active references.');
      return;
    }

    if (this.connectionsService) {
      this.connectionsService.connections.update(list => list.filter(c => c.id !== conn.id));
    }
    this.isDeleteDialogOpen.set(false);
    if (this.router) {
      this.router.navigate(['/connections']);
    }
  }
}
