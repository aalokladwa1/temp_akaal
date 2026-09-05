import { Injectable, inject, signal, computed, WritableSignal } from '@angular/core';
import { MigrationUiService } from './migration-ui.service';
import { Step6ConfigurationAdapterService } from './step6-configuration-adapter.service';
import {
  ConfigurationDepth,
  StandardProfileId,
  ValidationDepthOption,
  AdvancedGroupId,
  AdvancedFieldDescriptor,
  Step6ConfigurationDraft,
  Step6SummaryMetrics,
  CustomActionItem,
  StandardProfileOption
} from '../../modules/migration/create/steps/step6-configuration.models';
import { MigrationMode, PhysicalProviderId } from '../models/migration-view.models';

@Injectable({
  providedIn: 'root'
})
export class Step6ConfigurationStoreService {
  private ms: MigrationUiService;
  private adapter: Step6ConfigurationAdapterService;

  // Upstream context computed signals
  public currentMode = computed<MigrationMode>(() => this.ms.wizardDraft().mode || 'M2_BULK_CDC');
  public sourceProvider = computed<PhysicalProviderId>(() => this.ms.wizardDraft().sourceProvider || 'Oracle');
  public targetProvider = computed<PhysicalProviderId>(() => this.ms.wizardDraft().targetProvider || 'PostgreSQL');
  public environment = computed<string>(() => this.ms.wizardDraft().environment || 'Production');
  public scopedObjectsCount = computed<number>(() => (this.ms.wizardDraft().selectedTopologyNodes || []).length || 303);

  // Core Draft Signal
  public draft: WritableSignal<Step6ConfigurationDraft>;

  // Advanced Mode Navigation & Search Signals
  public activeAdvancedGroupId = signal<AdvancedGroupId>('EXECUTION_RESOURCES');
  public advancedSearchQuery = signal<string>('');

  // Dialog & Modal State Signals
  public showSwitchToStandardModal = signal<boolean>(false);
  public pendingMaterialField = signal<{ field: AdvancedFieldDescriptor; pendingValue: any } | null>(null);
  public showCustomActionsModal = signal<boolean>(false);
  public editingAction = signal<CustomActionItem | null>(null);

  // Standard Profiles
  public standardProfiles = computed<StandardProfileOption[]>(() =>
    this.adapter.getStandardProfiles(this.currentMode(), this.sourceProvider(), this.targetProvider())
  );

  public selectedProfileOption = computed<StandardProfileOption>(() => {
    const p = this.draft().profile;
    return this.standardProfiles().find(opt => opt.id === p) || this.standardProfiles()[1];
  });

  // Validation Options
  public validationOptions = computed(() =>
    this.adapter.getValidationOptions(this.currentMode())
  );

  // Advanced Field Descriptors
  public advancedFields = computed<AdvancedFieldDescriptor[]>(() =>
    this.adapter.getAdvancedFieldDescriptors(
      this.currentMode(),
      this.sourceProvider(),
      this.targetProvider(),
      this.environment(),
      this.draft().advancedOverrides
    )
  );

  // Advanced Groups with Override Counts
  public advancedGroups = computed(() => {
    const allGroups = this.adapter.advancedGroups;
    const allFields = this.advancedFields();

    return allGroups.map(group => {
      const groupFields = allFields.filter(f => f.groupId === group.id);
      const overrideCount = groupFields.filter(f => f.isOverridden).length;
      return {
        ...group,
        overrideCount,
        fieldCount: groupFields.length
      };
    });
  });

  // Filtered Advanced Fields (by Search Query or Active Group)
  public filteredAdvancedFields = computed<AdvancedFieldDescriptor[]>(() => {
    const q = this.advancedSearchQuery().trim().toLowerCase();
    const all = this.advancedFields();

    if (q) {
      return all.filter(f =>
        f.label.toLowerCase().includes(q) ||
        f.description.toLowerCase().includes(q) ||
        (f.subGroup && f.subGroup.toLowerCase().includes(q)) ||
        (f.providerName && f.providerName.toLowerCase().includes(q))
      );
    }

    return all.filter(f => f.groupId === this.activeAdvancedGroupId());
  });

  // Override Counts & Customization Badge
  public totalOverridesCount = computed<number>(() =>
    Object.keys(this.draft().advancedOverrides).length
  );

  public isCustomized = computed<boolean>(() =>
    this.totalOverridesCount() > 0
  );

  // Human Readable Mode Display Label (Step 1 Match)
  public modeDisplayTitle = computed<string>(() => {
    switch (this.currentMode()) {
      case 'M1_BULK': return 'Bulk Migration';
      case 'M2_BULK_CDC': return 'Bulk + CDC';
      case 'M3_CDC': return 'CDC Replication';
      case 'M4_INCREMENTAL': return 'Incremental Polling';
      case 'M5_STATE_SYNC': return 'State Synchronization';
      case 'M6_SCHEMA_ONLY': return 'Schema Only';
      case 'M7_DATA_ONLY': return 'Data Only';
      default: return 'Bulk + CDC';
    }
  });

  // Summary Metrics
  public summaryMetrics = computed<Step6SummaryMetrics>(() => {
    const d = this.draft();
    const prof = this.selectedProfileOption();
    const bw = d.bandwidthPolicy === 'LIMITED' ? `${d.bandwidthLimitValue} ${d.bandwidthLimitUnit} limit` : 'Automatic bandwidth';
    const rec = d.recoveryPolicy === 'RESUME_CHECKPOINT' ? 'Durable checkpoint recovery' : 'Pause on recovery';
    const quar = d.failedRecordsPolicy === 'QUARANTINE_CONTINUE' ? 'Quarantine enabled' : 'Stop on error';
    const valOpt = this.validationOptions().find(v => v.id === d.validationDepth);
    const val = valOpt ? `${valOpt.title} validation` : 'Fast Full validation';
    const win = d.executionWindowChoice === 'RESTRICTED' ? `Restricted window (${d.executionWindowStart}-${d.executionWindowEnd})` : 'No execution-window restriction';
    const isProd = this.environment() === 'Production';

    return {
      profileLabel: prof.title,
      bandwidthSummary: bw,
      recoverySummary: rec,
      quarantineSummary: quar,
      modeSummary: this.modeDisplayTitle(),
      validationSummary: val,
      windowSummary: win,
      inheritedPoliciesCount: isProd ? 2 : 1,
      customOverridesCount: this.totalOverridesCount(),
      isCustomized: this.isCustomized()
    };
  });

  // Validity / Readiness Gate
  public isStep6Valid = computed<boolean>(() => {
    const d = this.draft();
    if (d.bandwidthPolicy === 'LIMITED' && (d.bandwidthLimitValue <= 0 || isNaN(d.bandwidthLimitValue))) {
      return false;
    }
    if (d.executionWindowChoice === 'RESTRICTED' && (!d.executionWindowStart || !d.executionWindowEnd)) {
      return false;
    }
    // Custom actions must have valid SQL
    for (const action of d.customActions) {
      if (action.isEnabled && !action.sql.trim()) {
        return false;
      }
    }
    return true;
  });

  constructor(ms?: MigrationUiService, adapter?: Step6ConfigurationAdapterService) {
    try {
      this.ms = ms || inject(MigrationUiService);
    } catch {
      this.ms = ms || new MigrationUiService();
    }
    try {
      this.adapter = adapter || inject(Step6ConfigurationAdapterService);
    } catch {
      this.adapter = adapter || new Step6ConfigurationAdapterService();
    }
    this.draft = signal<Step6ConfigurationDraft>(
      this.adapter.createDefaultDraft(
        this.currentMode(),
        this.sourceProvider(),
        this.targetProvider(),
        this.environment()
      )
    );
    this.syncDraftReadiness();
  }

  // Depth Switching (Standard <-> Advanced)
  public setDepth(depth: ConfigurationDepth): void {
    if (depth === 'STANDARD' && this.draft().depth === 'ADVANCED' && this.totalOverridesCount() > 0) {
      this.showSwitchToStandardModal.set(true);
      return;
    }

    this.draft.update(d => ({ ...d, depth }));
    this.syncDraftReadiness();
  }

  public keepOverridesAndSwitchToStandard(): void {
    this.draft.update(d => ({ ...d, depth: 'STANDARD' }));
    this.showSwitchToStandardModal.set(false);
    this.syncDraftReadiness();
  }

  public resetOverridesAndSwitchToStandard(): void {
    this.draft.update(d => ({
      ...d,
      depth: 'STANDARD',
      advancedOverrides: {}
    }));
    this.showSwitchToStandardModal.set(false);
    this.syncDraftReadiness();
  }

  public cancelSwitchToStandard(): void {
    this.showSwitchToStandardModal.set(false);
  }

  // Profile Selection
  public selectProfile(profile: StandardProfileId): void {
    this.draft.update(d => ({
      ...d,
      profile,
      resourceImpact: profile === 'PROTECTIVE' ? 'CONSERVATIVE' : (profile === 'HIGH_THROUGHPUT' ? 'MAXIMUM' : 'BALANCED')
    }));
    this.syncDraftReadiness();
  }

  // Update Partial Draft
  public patchDraft(patch: Partial<Step6ConfigurationDraft>): void {
    this.draft.update(d => ({ ...d, ...patch }));
    this.syncDraftReadiness();
  }

  // Advanced Field Override Updates
  public setAdvancedField(fieldId: string, value: any): void {
    const field = this.advancedFields().find(f => f.id === fieldId);
    if (!field) return;

    if (field.isPolicyLocked) return;

    // Check for Material Invalidation Warning
    if (field.isMaterialChange && field.effectiveValue !== value) {
      this.pendingMaterialField.set({ field, pendingValue: value });
      return;
    }

    this.applyAdvancedFieldValue(fieldId, value);
  }

  public confirmMaterialChange(): void {
    const pending = this.pendingMaterialField();
    if (!pending) return;

    this.applyAdvancedFieldValue(pending.field.id, pending.pendingValue);
    this.pendingMaterialField.set(null);
  }

  public cancelMaterialChange(): void {
    this.pendingMaterialField.set(null);
  }

  private applyAdvancedFieldValue(fieldId: string, value: any): void {
    this.draft.update(d => {
      const overrides = { ...d.advancedOverrides, [fieldId]: value };
      return {
        ...d,
        advancedOverrides: overrides
      };
    });
    this.syncDraftReadiness();
  }

  public resetAdvancedField(fieldId: string): void {
    this.draft.update(d => {
      const overrides = { ...d.advancedOverrides };
      delete overrides[fieldId];
      return {
        ...d,
        advancedOverrides: overrides
      };
    });
    this.syncDraftReadiness();
  }

  public resetAllOverrides(): void {
    this.draft.update(d => ({
      ...d,
      advancedOverrides: {}
    }));
    this.syncDraftReadiness();
  }

  // Custom SQL Actions Management
  public openAddCustomAction(hook: 'PRE_MIGRATION' | 'POST_SCHEMA' | 'POST_BULK' | 'POST_CUTOVER' = 'PRE_MIGRATION'): void {
    const hookLabel = this.getHookLabel(hook);
    this.editingAction.set({
      id: `act-${Date.now()}`,
      hook,
      hookLabel,
      name: `Custom ${hookLabel} Script`,
      sql: `-- SQL statements executed during ${hookLabel}\n-- Example: ALTER SESSION SET CURRENT_SCHEMA = target_schema;\n`,
      timeoutSec: 120,
      onFailure: 'ABORT_MIGRATION',
      isEnabled: true
    });
    this.showCustomActionsModal.set(true);
  }

  public openEditCustomAction(action: CustomActionItem): void {
    this.editingAction.set({ ...action });
    this.showCustomActionsModal.set(true);
  }

  public closeCustomActionModal(): void {
    this.showCustomActionsModal.set(false);
    this.editingAction.set(null);
  }

  public saveCustomAction(action: CustomActionItem): void {
    this.draft.update(d => {
      const existing = d.customActions.findIndex(a => a.id === action.id);
      let updated: CustomActionItem[];
      if (existing >= 0) {
        updated = [...d.customActions];
        updated[existing] = action;
      } else {
        updated = [...d.customActions, action];
      }
      return { ...d, customActions: updated };
    });
    this.closeCustomActionModal();
    this.syncDraftReadiness();
  }

  public deleteCustomAction(actionId: string): void {
    this.draft.update(d => ({
      ...d,
      customActions: d.customActions.filter(a => a.id !== actionId)
    }));
    this.syncDraftReadiness();
  }

  public toggleCustomAction(actionId: string): void {
    this.draft.update(d => ({
      ...d,
      customActions: d.customActions.map(a => a.id === actionId ? { ...a, isEnabled: !a.isEnabled } : a)
    }));
    this.syncDraftReadiness();
  }

  public getHookLabel(hook: string): string {
    switch (hook) {
      case 'PRE_MIGRATION': return 'Pre-migration';
      case 'POST_SCHEMA': return 'Post-schema DDL';
      case 'POST_BULK': return 'Post-bulk Data Load';
      case 'POST_CUTOVER': return 'Post-cutover';
      default: return 'Custom Execution Hook';
    }
  }

  // Synchronize readiness state with MigrationUiService
  public syncDraftReadiness(): void {
    const isValid = this.isStep6Valid();
    this.ms.updateDraft({
      isDirty: true
    });
  }
}
