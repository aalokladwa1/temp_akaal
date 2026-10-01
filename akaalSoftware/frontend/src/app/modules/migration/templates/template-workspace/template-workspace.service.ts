import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import {
  TemplateDetail,
  TemplateWorkspaceTab,
  TemplateVersionItem,
  VersionDiffResult,
  VersionDiffFieldChange,
  DiffChangeType
} from './template-workspace.models';
import { TEMPLATE_WORKSPACE_FIXTURES } from './template-workspace.fixtures';
import { CreateTemplateDraftState, INITIAL_CREATE_TEMPLATE_DRAFT } from '../create-template/create-template.models';
import { TemplateMigrationMode } from '../templates.models';
import { MigrationIpc } from '../../../../core/services/ipc/migration.ipc';
import { IpcService } from '../../../../core/services/ipc.service';

import { TemplatesService } from '../templates.service';

@Injectable({
  providedIn: 'root'
})
export class TemplateWorkspaceService {
  private migrationIpc?: MigrationIpc;
  private ipc?: IpcService;
  private templatesService?: TemplatesService;

  constructor(
    @Optional() migrationIpc?: MigrationIpc,
    @Optional() ipc?: IpcService,
    @Optional() templatesService?: TemplatesService
  ) {
    if (ipc) {
      this.ipc = ipc;
    } else {
      try { this.ipc = inject(IpcService, { optional: true }) || undefined; } catch { this.ipc = undefined; }
    }
    if (migrationIpc) {
      this.migrationIpc = migrationIpc;
    } else {
      try { this.migrationIpc = inject(MigrationIpc, { optional: true }) || (this.ipc ? new MigrationIpc(this.ipc) : undefined); } catch { this.migrationIpc = undefined; }
    }
    if (templatesService) {
      this.templatesService = templatesService;
    } else {
      try { this.templatesService = inject(TemplatesService, { optional: true }) || undefined; } catch { this.templatesService = undefined; }
    }
  }

  public templateId = signal<string>('');
  public template = signal<TemplateDetail | null>(null);
  public activeTab = signal<TemplateWorkspaceTab>('overview');
  public isLoading = signal<boolean>(false);
  public errorMessage = signal<string | null>(null);
  public copiedId = signal<boolean>(false);

  // Configuration Edit Presentation State
  public isEditingConfig = signal<boolean>(false);
  public editDraft = signal<CreateTemplateDraftState>(INITIAL_CREATE_TEMPLATE_DRAFT);
  public configSaveMessage = signal<string | null>(null);

  // Version Comparison State
  public selectedBaseVersion = signal<string>('v2.0.0');
  public selectedCompareVersion = signal<string>('v2.1.0');

  // Dialog Controls
  public isDeleteDialogOpen = signal<boolean>(false);
  public isDeprecateDialogOpen = signal<boolean>(false);
  public isArchiveDialogOpen = signal<boolean>(false);
  public isNewVersionDialogOpen = signal<boolean>(false);
  public newVersionSummary = signal<string>('');

  // Semantic Version Diff Computed Engine
  public diffResult = computed<VersionDiffResult>(() => {
    const tmpl = this.template();
    const baseV = this.selectedBaseVersion();
    const compV = this.selectedCompareVersion();

    if (!tmpl || !tmpl.versions || tmpl.versions.length < 2) {
      return {
        baseVersion: baseV,
        compareVersion: compV,
        changes: [],
        totalAdded: 0,
        totalModified: 0,
        totalRemoved: 0
      };
    }

    const v1 = tmpl.versions.find(v => v.versionLabel === baseV) || tmpl.versions[1];
    const v2 = tmpl.versions.find(v => v.versionLabel === compV) || tmpl.versions[0];

    const changes: VersionDiffFieldChange[] = [];

    // 1. Defaults comparison
    if (v1.configurationSnapshot?.migrationDefaults && v2.configurationSnapshot?.migrationDefaults) {
      const d1 = v1.configurationSnapshot.migrationDefaults;
      const d2 = v2.configurationSnapshot.migrationDefaults;

      if (d1.migrationNamePattern !== d2.migrationNamePattern) {
        changes.push({
          category: 'Defaults',
          fieldLabel: 'Naming Pattern',
          oldValue: d1.migrationNamePattern,
          newValue: d2.migrationNamePattern,
          changeType: 'MODIFIED'
        });
      }
      if (d1.executionPriority !== d2.executionPriority) {
        changes.push({
          category: 'Defaults',
          fieldLabel: 'Execution Priority',
          oldValue: d1.executionPriority,
          newValue: d2.executionPriority,
          changeType: 'MODIFIED'
        });
      }
    }

    // 2. Scope & Discovery comparison
    if (v1.configurationSnapshot?.scopeMapping && v2.configurationSnapshot?.scopeMapping) {
      const sm1 = v1.configurationSnapshot.scopeMapping;
      const sm2 = v2.configurationSnapshot.scopeMapping;

      const rules1Count = sm1.objectScopeRules?.length || 0;
      const rules2Count = sm2.objectScopeRules?.length || 0;
      if (rules1Count !== rules2Count) {
        changes.push({
          category: 'Scope & Discovery',
          fieldLabel: 'Object Scope Rules Count',
          oldValue: `${rules1Count} active rules`,
          newValue: `${rules2Count} active rules`,
          changeType: rules2Count > rules1Count ? 'ADDED' : 'REMOVED'
        });
      }

      const mask1Count = sm1.maskingRules?.length || 0;
      const mask2Count = sm2.maskingRules?.length || 0;
      if (mask1Count !== mask2Count) {
        changes.push({
          category: 'Data Privacy',
          fieldLabel: 'Masking Rules Count',
          oldValue: `${mask1Count} active rules`,
          newValue: `${mask2Count} active rules`,
          changeType: mask2Count > mask1Count ? 'ADDED' : 'REMOVED'
        });
      }
    }

    // 3. Performance & Enterprise Config
    if (v1.configurationSnapshot?.enterpriseConfig && v2.configurationSnapshot?.enterpriseConfig) {
      const ec1 = v1.configurationSnapshot.enterpriseConfig;
      const ec2 = v2.configurationSnapshot.enterpriseConfig;

      if (ec1.performance?.extractThreads !== ec2.performance?.extractThreads) {
        changes.push({
          category: 'Performance',
          fieldLabel: 'Extract Threads',
          oldValue: `${ec1.performance.extractThreads} workers`,
          newValue: `${ec2.performance.extractThreads} workers`,
          changeType: 'MODIFIED'
        });
      }
      if (ec1.performance?.batchSize !== ec2.performance?.batchSize) {
        changes.push({
          category: 'Performance',
          fieldLabel: 'Batch Size',
          oldValue: `${ec1.performance.batchSize} rows`,
          newValue: `${ec2.performance.batchSize} rows`,
          changeType: 'MODIFIED'
        });
      }
      if (ec1.performance?.bufferMemoryMb !== ec2.performance?.bufferMemoryMb) {
        changes.push({
          category: 'Performance',
          fieldLabel: 'Buffer Memory',
          oldValue: `${ec1.performance.bufferMemoryMb} MB`,
          newValue: `${ec2.performance.bufferMemoryMb} MB`,
          changeType: 'MODIFIED'
        });
      }
      if (ec1.checkpointRecovery?.commitIntervalRows !== ec2.checkpointRecovery?.commitIntervalRows) {
        changes.push({
          category: 'Fault Recovery',
          fieldLabel: 'Commit Frequency',
          oldValue: `${ec1.checkpointRecovery.commitIntervalRows} rows`,
          newValue: `${ec2.checkpointRecovery.commitIntervalRows} rows`,
          changeType: 'MODIFIED'
        });
      }
    }

    // 4. Governance comparison
    if (v1.configurationSnapshot?.governance && v2.configurationSnapshot?.governance) {
      const g1 = v1.configurationSnapshot.governance;
      const g2 = v2.configurationSnapshot.governance;

      if (g1.approvalAndPolicy?.requirePeerReview !== g2.approvalAndPolicy?.requirePeerReview) {
        changes.push({
          category: 'Governance',
          fieldLabel: 'Peer Review Mandate',
          oldValue: g1.approvalAndPolicy?.requirePeerReview ? 'Required' : 'Disabled',
          newValue: g2.approvalAndPolicy?.requirePeerReview ? 'Required' : 'Disabled',
          changeType: 'MODIFIED'
        });
      }
      if (g1.overridability?.mappingRules !== g2.overridability?.mappingRules) {
        changes.push({
          category: 'Governance',
          fieldLabel: 'Mapping Overridability',
          oldValue: g1.overridability?.mappingRules || 'LOCKED',
          newValue: g2.overridability?.mappingRules || 'LOCKED',
          changeType: 'MODIFIED'
        });
      }
    }

    let added = 0;
    let modified = 0;
    let removed = 0;

    changes.forEach(c => {
      if (c.changeType === 'ADDED') added++;
      else if (c.changeType === 'MODIFIED') modified++;
      else if (c.changeType === 'REMOVED') removed++;
    });

    return {
      baseVersion: v1.versionLabel,
      compareVersion: v2.versionLabel,
      changes,
      totalAdded: added,
      totalModified: modified,
      totalRemoved: removed
    };
  });

  public async loadTemplate(id: string): Promise<void> {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.templateId.set(id);

    if (this.migrationIpc && this.ipc && this.ipc.connectionState() === 'connected') {
      try {
        const res = await this.migrationIpc.getTemplate(id).catch(() => null);
        if (res && res.status === 'SUCCESS' && res.data) {
          const t = res.data;
          const cfg = t.configuration || {};
          const src = t.source_provider || cfg.definition?.sourceProvider || 'Oracle';
          const tgt = t.target_provider || cfg.definition?.targetProvider || 'PostgreSQL';

          const templateDetail: TemplateDetail = {
            id: t.id || t.template_id || id,
            name: t.name || 'Enterprise Template',
            description: t.description || 'Configured template specification',
            mode: (t.mode || 'M1_BULK') as TemplateMigrationMode,
            applicability: {
              sourceProviderName: src,
              targetProviderName: tgt
            },
            scope: (t.scope || cfg.definition?.scope || 'PROJECT'),
            versionLabel: t.version || t.versionLabel || 'v1.0.0',
            revisionNumber: 1,
            lifecycle: (t.status === 'DEPRECATED' ? 'DEPRECATED' : t.status === 'ARCHIVED' ? 'ARCHIVED' : 'PUBLISHED'),
            createdAt: t.created_at || new Date().toISOString(),
            updatedAt: t.updated_at || new Date().toISOString(),
            createdBy: t.author || 'Lead Architect',
            lastUpdatedBy: t.author || 'Lead Architect',
            configuration: t.configuration || INITIAL_CREATE_TEMPLATE_DRAFT,
            applicabilityDetails: {
              sourceDialect: src,
              sourceFamily: 'Relational Database',
              targetDialect: tgt,
              targetFamily: 'Relational Database',
              compatibility: {
                sourceProvider: src,
                targetProvider: tgt,
                status: 'VERIFIED',
                statusLabel: 'Verified Provider Pair'
              },
              requiredCapabilities: {
                sourcePrivileges: ['SELECT ANY TABLE / SELECT on migrated schemas'],
                targetPrivileges: ['CREATE SCHEMA, CREATE TABLE, INSERT, UPDATE, DELETE'],
                networkRequirements: ['Direct TCP connectivity']
              },
              requiredAtUse: {
                targetDatabaseRequired: true,
                scheduleRequired: false,
                secretBindingsRequired: true,
                workspaceSelectionRequired: true,
                notificationChannelsRequired: false
              },
              connectionExpectations: {
                tlsMandatory: true,
                zeroSecretsEnforced: true,
                logicalTaggingSupported: true,
                vaultReferencePattern: 'vault://*'
              },
              environmentConstraints: [],
              knownLimitations: []
            },
            versions: t.versions || [
              {
                versionLabel: t.version || 'v1.0.0',
                revisionNumber: 1,
                createdAt: t.updated_at || new Date().toISOString(),
                createdBy: t.author || 'Lead Architect',
                lifecycle: 'PUBLISHED',
                changeSummary: 'Initial release',
                isCurrent: true,
                configurationSnapshot: t.configuration || INITIAL_CREATE_TEMPLATE_DRAFT
              }
            ],
            usage: t.usage || {
              projects: [],
              migrations: [],
              isUsageKnown: true,
              referencedProjectCount: t.project_count || 0,
              migrationCount: t.migration_count || 0,
              lastUsedAt: null
            },
            activities: t.activities || [],
            p7bContext: t.p7bContext || {
              localityRequirements: [],
              sovereigntyConstraints: [],
              recoveryPreference: 'Checkpoint commit every 25,000 rows',
              zeroSecretsAttestation: true
            },
            p7cContext: t.p7cContext || {
              isAvailable: true,
              advisorySummary: 'Enterprise template specification configured.'
            },
            referenceProtection: t.referenceProtection || {
              isProtected: false,
              deletionPermitted: true,
              activeMigrationCount: 0
            }
          };

          this.template.set(templateDetail);
          this.editDraft.set(JSON.parse(JSON.stringify(templateDetail.configuration)));
          this.isLoading.set(false);
          return;
        }
      } catch {
        // Fall through to summary template lookup
      }
    }

    if (this.templatesService) {
      const summary = this.templatesService.templates().find(t => t.id === id);
      if (summary) {
        const templateDetail: TemplateDetail = {
          id: summary.id,
          name: summary.name,
          description: summary.description || '',
          mode: summary.mode as TemplateMigrationMode,
          applicability: {
            sourceProviderName: summary.applicability?.sourceProviderName || 'Oracle',
            targetProviderName: summary.applicability?.targetProviderName || 'PostgreSQL'
          },
          scope: summary.scope || 'PROJECT',
          versionLabel: summary.versionLabel || 'v1.0.0',
          revisionNumber: 1,
          lifecycle: summary.lifecycle || 'PUBLISHED',
          createdAt: summary.createdAt || new Date().toISOString(),
          updatedAt: summary.updatedAt || new Date().toISOString(),
          createdBy: 'Lead Architect',
          lastUpdatedBy: 'Lead Architect',
          configuration: INITIAL_CREATE_TEMPLATE_DRAFT,
          applicabilityDetails: {
            sourceDialect: summary.applicability?.sourceProviderName || 'Oracle',
            sourceFamily: 'Relational Database',
            targetDialect: summary.applicability?.targetProviderName || 'PostgreSQL',
            targetFamily: 'Relational Database',
            compatibility: {
              sourceProvider: summary.applicability?.sourceProviderName || 'Oracle',
              targetProvider: summary.applicability?.targetProviderName || 'PostgreSQL',
              status: 'VERIFIED',
              statusLabel: 'Verified Provider Pair'
            },
            requiredCapabilities: {
              sourcePrivileges: ['SELECT ANY TABLE / SELECT on migrated schemas'],
              targetPrivileges: ['CREATE SCHEMA, CREATE TABLE, INSERT, UPDATE, DELETE'],
              networkRequirements: ['Direct TCP connectivity']
            },
            requiredAtUse: {
              targetDatabaseRequired: true,
              scheduleRequired: false,
              secretBindingsRequired: true,
              workspaceSelectionRequired: true,
              notificationChannelsRequired: false
            },
            connectionExpectations: {
              tlsMandatory: true,
              zeroSecretsEnforced: true,
              logicalTaggingSupported: true,
              vaultReferencePattern: 'vault://*'
            },
            environmentConstraints: [],
            knownLimitations: []
          },
          versions: [
            {
              versionLabel: summary.versionLabel || 'v1.0.0',
              revisionNumber: 1,
              createdAt: summary.updatedAt || new Date().toISOString(),
              createdBy: 'Lead Architect',
              lifecycle: summary.lifecycle || 'PUBLISHED',
              changeSummary: 'Canonical template release',
              usageCount: 0,
              isCurrent: true,
              configurationSnapshot: INITIAL_CREATE_TEMPLATE_DRAFT
            }
          ],
          usage: {
            projects: [],
            migrations: [],
            isUsageKnown: true,
            referencedProjectCount: summary.usage?.referencedProjectCount || 0,
            migrationCount: summary.usage?.migrationCount || 0,
            lastUsedAt: summary.usage?.lastUsedAt || null
          },
          activities: [],
          p7bContext: {
            localityRequirements: [],
            sovereigntyConstraints: [],
            recoveryPreference: 'Checkpoint commit every 25,000 rows',
            zeroSecretsAttestation: true
          },
          p7cContext: {
            isAvailable: true,
            advisorySummary: 'Enterprise template specification configured.'
          },
          referenceProtection: {
            isProtected: false,
            deletionPermitted: true,
            activeMigrationCount: 0
          }
        };

        this.template.set(templateDetail);
        this.editDraft.set(JSON.parse(JSON.stringify(templateDetail.configuration)));
        this.isLoading.set(false);
        return;
      }
    }

    // Truthful NOT_FOUND state (Zero fake fixture fallback)
    this.template.set(null);
    this.errorMessage.set(`Template with ID "${id}" was not found or is inaccessible.`);
    this.isLoading.set(false);
  }

  /**
   * Explicit test-only fixture loader for unit/harness testing
   */
  public loadFixtureForTesting(id: string = 'tmpl-01'): void {
    const found = TEMPLATE_WORKSPACE_FIXTURES[id];
    if (found) {
      const clone = JSON.parse(JSON.stringify(found)) as TemplateDetail;
      clone.id = id;
      this.template.set(clone);
      this.editDraft.set(JSON.parse(JSON.stringify(clone.configuration)));
      if (clone.versions && clone.versions.length >= 2) {
        this.selectedBaseVersion.set(clone.versions[1].versionLabel);
        this.selectedCompareVersion.set(clone.versions[0].versionLabel);
      }
    }
  }

  public setActiveTab(tab: TemplateWorkspaceTab): void {
    this.activeTab.set(tab);
  }

  public copyTemplateId(): void {
    const tmpl = this.template();
    if (tmpl) {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(tmpl.id);
      }
      this.copiedId.set(true);
      setTimeout(() => this.copiedId.set(false), 2000);
    }
  }

  // =========================================================================
  // CONFIGURATION EDIT PRESENTATION MODE
  // =========================================================================

  public startEditingConfig(): void {
    const tmpl = this.template();
    if (tmpl) {
      this.editDraft.set(JSON.parse(JSON.stringify(tmpl.configuration)));
      this.isEditingConfig.set(true);
      this.configSaveMessage.set(null);
    }
  }

  public cancelEditingConfig(): void {
    const tmpl = this.template();
    if (tmpl) {
      this.editDraft.set(JSON.parse(JSON.stringify(tmpl.configuration)));
    }
    this.isEditingConfig.set(false);
    this.configSaveMessage.set(null);
  }

  public saveEditingConfig(): void {
    const tmpl = this.template();
    if (tmpl) {
      const updated = JSON.parse(JSON.stringify(tmpl)) as TemplateDetail;
      updated.configuration = JSON.parse(JSON.stringify(this.editDraft()));
      updated.updatedAt = new Date().toISOString();
      this.template.set(updated);
      this.isEditingConfig.set(false);
      this.configSaveMessage.set('Configuration draft updated in local workspace session.');
      setTimeout(() => this.configSaveMessage.set(null), 4000);
    }
  }

  public updateEditDraft(partial: Partial<CreateTemplateDraftState>): void {
    this.editDraft.update(curr => ({
      ...curr,
      ...partial
    }));
  }

  // =========================================================================
  // VERSION COMPARISON METHODS
  // =========================================================================

  public setDiffVersions(base: string, compare: string): void {
    this.selectedBaseVersion.set(base);
    this.selectedCompareVersion.set(compare);
  }

  // =========================================================================
  // LIFECYCLE & DIALOG MANAGEMENT
  // =========================================================================

  public openDeleteDialog(): void {
    this.isDeleteDialogOpen.set(true);
  }

  public closeDeleteDialog(): void {
    this.isDeleteDialogOpen.set(false);
  }

  public openDeprecateDialog(): void {
    this.isDeprecateDialogOpen.set(true);
  }

  public closeDeprecateDialog(): void {
    this.isDeprecateDialogOpen.set(false);
  }

  public openArchiveDialog(): void {
    this.isArchiveDialogOpen.set(true);
  }

  public closeArchiveDialog(): void {
    this.isArchiveDialogOpen.set(false);
  }

  public openNewVersionDialog(): void {
    this.newVersionSummary.set('');
    this.isNewVersionDialogOpen.set(true);
  }

  public closeNewVersionDialog(): void {
    this.isNewVersionDialogOpen.set(false);
  }

  public async applyDelete(): Promise<boolean> {
    const tmpl = this.template();
    if (tmpl) {
      if (this.migrationIpc && this.ipc && this.ipc.connectionState() === 'connected') {
        try {
          await this.migrationIpc.deleteTemplate(tmpl.id);
        } catch {
          // Continue
        }
      }
      this.template.set(null);
    }
    this.closeDeleteDialog();
    return true;
  }

  public applyDeprecate(): void {
    const tmpl = this.template();
    if (tmpl) {
      const updated = { ...tmpl, lifecycle: 'DEPRECATED' as const };
      this.template.set(updated);
      if (this.migrationIpc && this.ipc && this.ipc.connectionState() === 'connected') {
        this.migrationIpc.deprecateTemplate(tmpl.id).catch(() => null);
      }
    }
    this.closeDeprecateDialog();
  }

  public applyArchive(): void {
    const tmpl = this.template();
    if (tmpl) {
      const updated = { ...tmpl, lifecycle: 'ARCHIVED' as const };
      this.template.set(updated);
    }
    this.closeArchiveDialog();
  }
}
