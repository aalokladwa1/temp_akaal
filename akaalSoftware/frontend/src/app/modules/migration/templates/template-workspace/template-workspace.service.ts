import { Injectable, signal, computed } from '@angular/core';
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

@Injectable({
  providedIn: 'root'
})
export class TemplateWorkspaceService {
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

  public loadTemplate(id: string): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.templateId.set(id);

    // Simulated calm resolution from fixtures or fallback
    setTimeout(() => {
      const found = TEMPLATE_WORKSPACE_FIXTURES[id] || TEMPLATE_WORKSPACE_FIXTURES['tmpl-ora-pg-m2'];
      if (found) {
        // Clone to protect fixture immutability
        const clone = JSON.parse(JSON.stringify(found)) as TemplateDetail;
        clone.id = id;
        this.template.set(clone);
        this.editDraft.set(JSON.parse(JSON.stringify(clone.configuration)));
        
        if (clone.versions && clone.versions.length >= 2) {
          this.selectedBaseVersion.set(clone.versions[1].versionLabel);
          this.selectedCompareVersion.set(clone.versions[0].versionLabel);
        }
      } else {
        this.errorMessage.set(`Template with ID "${id}" could not be located.`);
      }
      this.isLoading.set(false);
    }, 150);
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

  public applyDeprecate(): void {
    const tmpl = this.template();
    if (tmpl) {
      const updated = { ...tmpl, lifecycle: 'DEPRECATED' as const };
      this.template.set(updated);
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
