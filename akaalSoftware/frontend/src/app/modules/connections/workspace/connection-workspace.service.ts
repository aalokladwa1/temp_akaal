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
import { EntityAvailabilityState } from '../connections.models';
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

  // Active Connection Store (Neutral truthful startup: B-2.2-01)
  public connection = signal<DetailedConnectionRecord | null>(null);
  public availabilityState = signal<EntityAvailabilityState>('NOT_CONNECTED');
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
      this.availabilityState.set('READY');
      this.isLoading.set(false);
    } else {
      // Truthful NOT_FOUND state (Zero fake Oracle fallback: B-2.2-02)
      this.connection.set(null);
      this.availabilityState.set('NOT_FOUND');
      this.isLoading.set(false);
    }
  }

  /**
   * Explicit test-only fixture loader for test suites & Playwright harnesses (§53)
   */
  public loadFixtureForTesting(id: string = 'conn-ora-rac-01', tab?: ConnectionWorkspaceTab): void {
    const found = DETAILED_CONNECTION_FIXTURES[id] || DETAILED_CONNECTION_FIXTURES['conn-ora-rac-01'];
    this.connection.set(JSON.parse(JSON.stringify(found)));
    this.availabilityState.set('READY');
    this.errorMessage.set(null);
    this.isLoading.set(false);
    if (tab) {
      this.activeTab.set(tab);
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

    this.isSavingConfig.set(true);
    setTimeout(() => {
      this.isSavingConfig.set(false);
      this.configNotice.set('Configuration saving is unavailable while connection service is disconnected.');
      setTimeout(() => this.configNotice.set(null), 5000);
    }, 300);
  }

  // ==========================================================================
  // INTERACTIVE TEST PROBES (Fail-closed before live backend wiring: B-2.2-06)
  // ==========================================================================

  public testConnection(): void {
    const conn = this.connection();
    if (!conn) return;

    this.isRunningTest.set(true);
    this.testResultMessage.set(null);

    setTimeout(() => {
      this.isRunningTest.set(false);
      this.testResultMessage.set('Live connection testing is unavailable while connection service is disconnected.');
      setTimeout(() => this.testResultMessage.set(null), 5000);
    }, 300);
  }

  public runPermissionProbe(): void {
    this.isRunningPermissionProbe.set(true);
    setTimeout(() => {
      this.isRunningPermissionProbe.set(false);
      this.testResultMessage.set('Live permission introspection is unavailable while connection service is disconnected.');
      setTimeout(() => this.testResultMessage.set(null), 5000);
    }, 300);
  }

  public runCapabilityProbe(): void {
    this.isRunningCapabilityProbe.set(true);
    setTimeout(() => {
      this.isRunningCapabilityProbe.set(false);
      this.testResultMessage.set('Live capability attestation is unavailable while connection service is disconnected.');
      setTimeout(() => this.testResultMessage.set(null), 5000);
    }, 300);
  }

  // ==========================================================================
  // SETTINGS & LIFECYCLE (Fail-closed before durable persistence wiring: B-2.2-07)
  // ==========================================================================

  public saveMetadata(name: string, description: string, tags: string[]): void {
    this.configNotice.set('Connection renaming is unavailable while connection service is disconnected.');
    setTimeout(() => this.configNotice.set(null), 5000);
  }

  public toggleDisableConnection(): void {
    this.isDisableDialogOpen.set(false);
    this.configNotice.set('Connection lifecycle changes are unavailable while connection service is disconnected.');
    setTimeout(() => this.configNotice.set(null), 5000);
  }

  public archiveConnection(): void {
    this.isArchiveDialogOpen.set(false);
    this.configNotice.set('Connection archiving is unavailable while connection service is disconnected.');
    setTimeout(() => this.configNotice.set(null), 5000);
  }

  public deleteConnection(): void {
    const conn = this.connection();
    if (!conn) return;

    this.isDeleteDialogOpen.set(false);
    this.configNotice.set('Connection deletion is unavailable while connection service is disconnected.');
    setTimeout(() => this.configNotice.set(null), 5000);
  }
}
