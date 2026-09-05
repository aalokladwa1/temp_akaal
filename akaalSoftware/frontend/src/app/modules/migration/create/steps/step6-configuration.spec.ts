import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { Step6ConfigurationAdapterService } from '../../../../core/services/step6-configuration-adapter.service';
import { Step6ConfigurationStoreService } from '../../../../core/services/step6-configuration-store.service';
import { PhysicalProviderId, MigrationMode } from '../../../../core/models/migration-view.models';

describe('Step 6 — Enterprise Configuration Center Master Contract Verification Suite', () => {
  let ms: MigrationUiService;
  let adapter: Step6ConfigurationAdapterService;
  let store: Step6ConfigurationStoreService;

  beforeEach(() => {
    ms = new MigrationUiService();
    ms.resetWizardDraft();
    adapter = new Step6ConfigurationAdapterService();
    store = new Step6ConfigurationStoreService(ms, adapter);
  });

  // ==========================================================================
  // 1. ENTRY & UPSTREAM CONTEXT CONVERGENCE
  // ==========================================================================
  describe('Entry & Upstream Context Convergence', () => {
    it('initializes from wizard draft context preserving source, target, mode and environment', () => {
      expect(store.currentMode()).toBe('M2_BULK_CDC');
      expect(store.sourceProvider()).toBe('Oracle');
      expect(store.targetProvider()).toBe('PostgreSQL');
      expect(store.draft().depth).toBe('STANDARD');
      expect(store.draft().profile).toBe('BALANCED');
    });

    it('exposes canonical mode display titles matching Step 1 names (no MX_type raw codes)', () => {
      const modeTitles: Record<MigrationMode, string> = {
        'M1_BULK': 'Bulk Migration',
        'M2_BULK_CDC': 'Bulk + CDC',
        'M3_CDC': 'CDC Replication',
        'M4_INCREMENTAL': 'Incremental Polling',
        'M5_STATE_SYNC': 'State Synchronization',
        'M6_SCHEMA_ONLY': 'Schema Only',
        'M7_DATA_ONLY': 'Data Only'
      };

      for (const [mode, expectedTitle] of Object.entries(modeTitles)) {
        ms.updateDraft({ mode: mode as MigrationMode });
        expect(store.modeDisplayTitle()).toBe(expectedTitle);
        expect(store.modeDisplayTitle().startsWith('M')).toBe(false);
      }
    });

    it('derives accurate summary metrics from the active configuration draft', () => {
      const metrics = store.summaryMetrics();
      expect(metrics.profileLabel).toBe('Balanced');
      expect(metrics.bandwidthSummary).toBe('Automatic bandwidth');
      expect(metrics.recoverySummary).toBe('Durable checkpoint recovery');
      expect(metrics.quarantineSummary).toBe('Quarantine enabled');
      expect(metrics.customOverridesCount).toBe(0);
      expect(metrics.isCustomized).toBe(false);
    });
  });

  // ==========================================================================
  // 2. STANDARD EXECUTION PROFILES
  // ==========================================================================
  describe('Standard Execution Profiles', () => {
    it('provides exactly 3 standard execution profiles (Protective, Balanced, High Throughput)', () => {
      const profiles = store.standardProfiles();
      expect(profiles.length).toBe(3);
      expect(profiles.map(p => p.id)).toEqual(['PROTECTIVE', 'BALANCED', 'HIGH_THROUGHPUT']);
      
      const balanced = profiles.find(p => p.id === 'BALANCED');
      expect(balanced?.badge).toBe('Recommended');
      expect(balanced?.workers).toBe(4);
    });

    it('updates draft profile and aligns resourceImpact when selecting a standard profile', () => {
      store.selectProfile('PROTECTIVE');
      expect(store.draft().profile).toBe('PROTECTIVE');
      expect(store.draft().resourceImpact).toBe('CONSERVATIVE');
      expect(store.selectedProfileOption().workers).toBe(2);

      store.selectProfile('HIGH_THROUGHPUT');
      expect(store.draft().profile).toBe('HIGH_THROUGHPUT');
      expect(store.draft().resourceImpact).toBe('MAXIMUM');
      expect(store.selectedProfileOption().workers).toBe(8);
    });
  });

  // ==========================================================================
  // 3. TRANSFER & RESOURCE POLICY
  // ==========================================================================
  describe('Transfer & Resource Policy', () => {
    it('supports unlimited and rate-limited bandwidth policy configurations', () => {
      expect(store.draft().bandwidthPolicy).toBe('UNLIMITED');

      store.patchDraft({
        bandwidthPolicy: 'LIMITED',
        bandwidthLimitValue: 250,
        bandwidthLimitUnit: 'MB/s'
      });

      expect(store.draft().bandwidthPolicy).toBe('LIMITED');
      expect(store.draft().bandwidthLimitValue).toBe(250);
      expect(store.draft().bandwidthLimitUnit).toBe('MB/s');
      expect(store.summaryMetrics().bandwidthSummary).toBe('250 MB/s limit');
    });

    it('supports LOB handling and resource impact policies', () => {
      store.patchDraft({ lobPolicy: 'STREAMING' });
      expect(store.draft().lobPolicy).toBe('STREAMING');

      store.patchDraft({ lobPolicy: 'INLINE' });
      expect(store.draft().lobPolicy).toBe('INLINE');
    });
  });

  // ==========================================================================
  // 4. RESILIENCE & RECOVERY POLICIES
  // ==========================================================================
  describe('Resilience & Recovery Policies', () => {
    it('supports checkpoint recovery and operator pause recovery policies', () => {
      expect(store.draft().recoveryPolicy).toBe('RESUME_CHECKPOINT');
      expect(store.summaryMetrics().recoverySummary).toBe('Durable checkpoint recovery');

      store.patchDraft({ recoveryPolicy: 'PAUSE_OPERATOR' });
      expect(store.draft().recoveryPolicy).toBe('PAUSE_OPERATOR');
      expect(store.summaryMetrics().recoverySummary).toBe('Pause on recovery');
    });

    it('supports quarantine and stop on error policies for failed records', () => {
      expect(store.draft().failedRecordsPolicy).toBe('QUARANTINE_CONTINUE');
      expect(store.summaryMetrics().quarantineSummary).toBe('Quarantine enabled');

      store.patchDraft({ failedRecordsPolicy: 'STOP_WORK' });
      expect(store.draft().failedRecordsPolicy).toBe('STOP_WORK');
      expect(store.summaryMetrics().quarantineSummary).toBe('Stop on error');
    });
  });

  // ==========================================================================
  // 5. DYNAMIC MODE-SPECIFIC CONTRACTS (M1 - M7)
  // ==========================================================================
  describe('Dynamic Mode-Specific Contracts (M1 - M7)', () => {
    it('maintains structured configurations for all migration modes', () => {
      const draft = store.draft();

      // M1 Bulk
      expect(draft.modeM1.chunkSizeRows).toBe(50000);
      expect(draft.modeM1.directLoad).toBe(true);

      // M2 Bulk + CDC
      expect(draft.modeM2.catchupLagTargetSec).toBe(2);
      expect(draft.modeM2.cutoverMaxLagSec).toBe(5);
      expect(draft.modeM2.conflictPolicy).toBe('LATEST_WINS');

      // M3 CDC
      expect(draft.modeM3.startPosition).toBe('IMMEDIATE');
      expect(draft.modeM3.batchWindowMs).toBe(500);

      // M4 Incremental
      expect(draft.modeM4.pollingIntervalSec).toBe(60);
      expect(draft.modeM4.watermarkColumn).toBe('UPDATED_AT');

      // M5 State Sync
      expect(draft.modeM5.reconciliationMode).toBe('ONE_WAY_ALIGN');
      expect(draft.modeM5.stateTolerancePercent).toBe(0);

      // M6 Schema Only
      expect(draft.modeM6.transactionalDdl).toBe(true);
      expect(draft.modeM6.fkIndexTiming).toBe('DEFERRED');

      // M7 Data Only
      expect(draft.modeM7.targetReadiness).toBe('TRUNCATE');
      expect(draft.modeM7.requireSchemaAttestation).toBe(true);
    });

    it('patches mode-specific parameters accurately', () => {
      store.patchDraft({
        modeM2: {
          ...store.draft().modeM2,
          catchupLagTargetSec: 10,
          conflictPolicy: 'SOURCE_WINS'
        }
      });

      expect(store.draft().modeM2.catchupLagTargetSec).toBe(10);
      expect(store.draft().modeM2.conflictPolicy).toBe('SOURCE_WINS');
    });
  });

  // ==========================================================================
  // 6. VALIDATION & ASSURANCE CONFIGURATION
  // ==========================================================================
  describe('Validation & Assurance Configuration', () => {
    it('provides data validation options for data-bearing modes', () => {
      ms.updateDraft({ mode: 'M2_BULK_CDC' });
      const options = store.validationOptions();
      expect(options.length).toBe(4);
      expect(options.map(o => o.id)).toContain('FAST_FULL');
      expect(options.map(o => o.id)).toContain('EXACT_FULL');
      expect(options.map(o => o.id)).toContain('DETERMINISTIC_SAMPLE');
    });

    it('provides structural validation options for Schema Only mode (M6)', () => {
      ms.updateDraft({ mode: 'M6_SCHEMA_ONLY' });
      const options = store.validationOptions();
      expect(options.length).toBe(2);
      expect(options.map(o => o.id)).toContain('STRUCTURE_ONLY');
      expect(options.map(o => o.id)).toContain('FAST_FULL');
    });
  });

  // ==========================================================================
  // 7. EXECUTION CONSTRAINTS & CUSTOM SQL ACTIONS
  // ==========================================================================
  describe('Execution Constraints & Custom SQL Actions', () => {
    it('configures execution window choices (Anytime vs Restricted)', () => {
      expect(store.draft().executionWindowChoice).toBe('ANYTIME');
      expect(store.summaryMetrics().windowSummary).toBe('No execution-window restriction');

      store.patchDraft({
        executionWindowChoice: 'RESTRICTED',
        executionWindowStart: '22:00',
        executionWindowEnd: '04:00'
      });

      expect(store.draft().executionWindowChoice).toBe('RESTRICTED');
      expect(store.summaryMetrics().windowSummary).toBe('Restricted window (22:00-04:00)');
    });

    it('supports adding, editing, toggling, and deleting Custom SQL Actions', () => {
      // 1. Open Add Custom Action
      store.openAddCustomAction('PRE_MIGRATION');
      expect(store.showCustomActionsModal()).toBe(true);
      expect(store.editingAction()?.hook).toBe('PRE_MIGRATION');
      expect(store.editingAction()?.hookLabel).toBe('Pre-migration');

      // 2. Save Custom Action
      const newAction = {
        ...store.editingAction()!,
        name: 'Set Session Schema',
        sql: 'ALTER SESSION SET CURRENT_SCHEMA = MIGRATION_TARGET;'
      };
      store.saveCustomAction(newAction);

      expect(store.showCustomActionsModal()).toBe(false);
      expect(store.draft().customActions.length).toBe(1);
      expect(store.draft().customActions[0].name).toBe('Set Session Schema');

      // 3. Toggle Action
      const actionId = store.draft().customActions[0].id;
      store.toggleCustomAction(actionId);
      expect(store.draft().customActions[0].isEnabled).toBe(false);

      store.toggleCustomAction(actionId);
      expect(store.draft().customActions[0].isEnabled).toBe(true);

      // 4. Edit Custom Action
      store.openEditCustomAction(store.draft().customActions[0]);
      expect(store.showCustomActionsModal()).toBe(true);
      store.saveCustomAction({ ...store.editingAction()!, name: 'Updated Action Name' });
      expect(store.draft().customActions[0].name).toBe('Updated Action Name');

      // 5. Delete Custom Action
      store.deleteCustomAction(actionId);
      expect(store.draft().customActions.length).toBe(0);
    });

    it('maps all 4 canonical custom action hooks properly', () => {
      expect(store.getHookLabel('PRE_MIGRATION')).toBe('Pre-migration');
      expect(store.getHookLabel('POST_SCHEMA')).toBe('Post-schema DDL');
      expect(store.getHookLabel('POST_BULK')).toBe('Post-bulk Data Load');
      expect(store.getHookLabel('POST_CUTOVER')).toBe('Post-cutover');
    });
  });

  // ==========================================================================
  // 8. ADVANCED 2-PANE WORKBENCH & SEARCH
  // ==========================================================================
  describe('Advanced 2-Pane Workbench & Search', () => {
    it('exposes all 8 canonical advanced navigation groups', () => {
      const groups = store.advancedGroups();
      expect(groups.length).toBe(8);
      const groupIds = groups.map(g => g.id);
      expect(groupIds).toEqual([
        'EXECUTION_RESOURCES',
        'TRANSFER_BATCHING',
        'RESILIENCE_RECOVERY',
        'MODE_CONFIG',
        'VALIDATION_RECON',
        'SCHEMA_ACTIONS',
        'OBSERVABILITY_WINDOWS',
        'PROVIDER_OPTIONS'
      ]);
    });

    it('filters advanced fields by active navigation group', () => {
      store.activeAdvancedGroupId.set('EXECUTION_RESOURCES');
      const fields = store.filteredAdvancedFields();
      expect(fields.length).toBeGreaterThan(0);
      expect(fields.every(f => f.groupId === 'EXECUTION_RESOURCES')).toBe(true);

      store.activeAdvancedGroupId.set('TRANSFER_BATCHING');
      const batchingFields = store.filteredAdvancedFields();
      expect(batchingFields.length).toBeGreaterThan(0);
      expect(batchingFields.every(f => f.groupId === 'TRANSFER_BATCHING')).toBe(true);
    });

    it('filters advanced fields globally across all groups when search query is entered', () => {
      store.advancedSearchQuery.set('buffer');
      const searchResults = store.filteredAdvancedFields();
      expect(searchResults.length).toBeGreaterThan(0);
      expect(searchResults.some(f => f.label.toLowerCase().includes('buffer') || f.description.toLowerCase().includes('buffer'))).toBe(true);
    });
  });

  // ==========================================================================
  // 9. ADVANCED OVERRIDES MANAGEMENT
  // ==========================================================================
  describe('Advanced Overrides Management', () => {
    it('tracks active overrides and updates provenance to USER_OVERRIDE', () => {
      expect(store.totalOverridesCount()).toBe(0);
      expect(store.isCustomized()).toBe(false);

      // Apply override to an un-locked, non-material field
      store.setAdvancedField('source_max_connections', 12);
      expect(store.totalOverridesCount()).toBe(1);
      expect(store.isCustomized()).toBe(true);
      expect(store.draft().advancedOverrides['source_max_connections']).toBe(12);

      const field = store.advancedFields().find(f => f.id === 'source_max_connections');
      expect(field?.isOverridden).toBe(true);
      expect(field?.provenance).toBe('USER_OVERRIDE');
      expect(field?.effectiveValue).toBe(12);
    });

    it('resets an individual field override and restores preset provenance', () => {
      store.setAdvancedField('source_max_connections', 12);
      expect(store.totalOverridesCount()).toBe(1);

      store.resetAdvancedField('source_max_connections');
      expect(store.totalOverridesCount()).toBe(0);
      expect(store.isCustomized()).toBe(false);

      const field = store.advancedFields().find(f => f.id === 'source_max_connections');
      expect(field?.isOverridden).toBe(false);
      expect(field?.provenance).toBe('PRESET');
      expect(field?.effectiveValue).toBe(6);
    });

    it('resets all overrides simultaneously', () => {
      store.setAdvancedField('source_max_connections', 12);
      store.setAdvancedField('target_max_connections', 16);
      expect(store.totalOverridesCount()).toBe(2);

      store.resetAllOverrides();
      expect(store.totalOverridesCount()).toBe(0);
      expect(store.isCustomized()).toBe(false);
    });
  });

  // ==========================================================================
  // 10. POLICY LOCKS & MATERIAL INVALIDATION PROTECTION
  // ==========================================================================
  describe('Policy Locks & Material Invalidation Protection', () => {
    it('prevents modifying policy-locked parameters in Production environment', () => {
      ms.updateDraft({ environment: 'Production' });
      const lockedField = store.advancedFields().find(f => f.isPolicyLocked);
      expect(lockedField).toBeDefined();

      const fieldId = lockedField!.id;

      // Attempt to override locked field
      store.setAdvancedField(fieldId, 'MODIFIED_ILLEGAL_VALUE');
      expect(store.draft().advancedOverrides[fieldId]).toBeUndefined();
      expect(store.totalOverridesCount()).toBe(0);
    });

    it('intercepts material parameter changes with confirmation modal', () => {
      const materialField = store.advancedFields().find(f => f.isMaterialChange);
      expect(materialField).toBeDefined();

      const fieldId = materialField!.id;
      const newValue = materialField!.type === 'number' ? 999 : 'CUSTOM_VAL';

      // Attempt change on material field
      store.setAdvancedField(fieldId, newValue);

      // Verification: Pending modal is opened, value is not yet in overrides
      expect(store.pendingMaterialField()).not.toBeNull();
      expect(store.pendingMaterialField()?.field.id).toBe(fieldId);
      expect(store.draft().advancedOverrides[fieldId]).toBeUndefined();

      // Cancel material change
      store.cancelMaterialChange();
      expect(store.pendingMaterialField()).toBeNull();
      expect(store.draft().advancedOverrides[fieldId]).toBeUndefined();

      // Trigger change again and confirm
      store.setAdvancedField(fieldId, newValue);
      store.confirmMaterialChange();
      expect(store.pendingMaterialField()).toBeNull();
      expect(store.draft().advancedOverrides[fieldId]).toBe(newValue);
    });
  });

  // ==========================================================================
  // 11. DEPTH SWITCHING GUARDRAILS
  // ==========================================================================
  describe('Depth Switching Guardrails', () => {
    it('allows switching freely from Standard to Advanced', () => {
      expect(store.draft().depth).toBe('STANDARD');
      store.setDepth('ADVANCED');
      expect(store.draft().depth).toBe('ADVANCED');
      expect(store.showSwitchToStandardModal()).toBe(false);
    });

    it('allows switching from Advanced to Standard directly if no overrides exist', () => {
      store.setDepth('ADVANCED');
      expect(store.totalOverridesCount()).toBe(0);

      store.setDepth('STANDARD');
      expect(store.draft().depth).toBe('STANDARD');
      expect(store.showSwitchToStandardModal()).toBe(false);
    });

    it('protects custom overrides with a modal when switching from Advanced to Standard', () => {
      store.setDepth('ADVANCED');
      store.setAdvancedField('source_max_connections', 16);
      expect(store.totalOverridesCount()).toBe(1);

      // Attempt to switch to standard
      store.setDepth('STANDARD');

      // Verification: Modal opens, depth remains Advanced until user chooses
      expect(store.showSwitchToStandardModal()).toBe(true);
      expect(store.draft().depth).toBe('ADVANCED');

      // Option A: Keep Overrides & Switch
      store.keepOverridesAndSwitchToStandard();
      expect(store.showSwitchToStandardModal()).toBe(false);
      expect(store.draft().depth).toBe('STANDARD');
      expect(store.totalOverridesCount()).toBe(1);

      // Switch back to Advanced
      store.setDepth('ADVANCED');

      // Attempt switch to Standard again
      store.setDepth('STANDARD');
      expect(store.showSwitchToStandardModal()).toBe(true);

      // Option B: Reset Overrides & Switch
      store.resetOverridesAndSwitchToStandard();
      expect(store.showSwitchToStandardModal()).toBe(false);
      expect(store.draft().depth).toBe('STANDARD');
      expect(store.totalOverridesCount()).toBe(0);
    });
  });

  // ==========================================================================
  // 12. READINESS GATE & WIZARD INTEGRATION
  // ==========================================================================
  describe('Readiness Gate & Wizard Integration', () => {
    it('validates default configuration draft as valid for Step 6', () => {
      expect(store.isStep6Valid()).toBe(true);
    });

    it('invalidates Step 6 if bandwidth limit is non-positive when LIMITED is selected', () => {
      store.patchDraft({
        bandwidthPolicy: 'LIMITED',
        bandwidthLimitValue: 0
      });
      expect(store.isStep6Valid()).toBe(false);

      store.patchDraft({
        bandwidthLimitValue: 100
      });
      expect(store.isStep6Valid()).toBe(true);
    });

    it('invalidates Step 6 if execution window is RESTRICTED without start/end times', () => {
      store.patchDraft({
        executionWindowChoice: 'RESTRICTED',
        executionWindowStart: '',
        executionWindowEnd: '04:00'
      });
      expect(store.isStep6Valid()).toBe(false);

      store.patchDraft({
        executionWindowStart: '22:00',
        executionWindowEnd: '04:00'
      });
      expect(store.isStep6Valid()).toBe(true);
    });

    it('invalidates Step 6 if an enabled custom SQL action has blank SQL', () => {
      store.openAddCustomAction('PRE_MIGRATION');
      const action = {
        ...store.editingAction()!,
        sql: '   '
      };
      store.saveCustomAction(action);

      expect(store.isStep6Valid()).toBe(false);

      // Disabling the action restores readiness
      store.toggleCustomAction(action.id);
      expect(store.isStep6Valid()).toBe(true);
    });
  });
});
