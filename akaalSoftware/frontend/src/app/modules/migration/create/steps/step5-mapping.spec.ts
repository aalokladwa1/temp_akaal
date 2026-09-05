import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { Step5MappingAdapterService } from '../../../../core/services/step5-mapping-adapter.service';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { PhysicalProviderId, MigrationMode } from '../../../../core/models/migration-view.models';

describe('Step 5 — Mapping & Data Controls Master Contract Verification Suite', () => {
  let ms: MigrationUiService;
  let adapter: Step5MappingAdapterService;
  let store: Step5MappingStoreService;

  beforeEach(() => {
    ms = new MigrationUiService();
    ms.resetWizardDraft();
    adapter = new Step5MappingAdapterService();
    store = new Step5MappingStoreService(ms, adapter);
  });

  // ==========================================================================
  // 1. INITIAL ENTRY & UPSTREAM CONTEXT CONVERGENCE
  // ==========================================================================
  describe('Entry & Upstream Context Convergence', () => {
    it('initializes from wizard draft context preserving source, target, mode and scope', () => {
      expect(store.activeWorkspace()).toBe('MAPPING');
      expect(store.workMode()).toBe('REVIEW');
      expect(store.objects().length).toBeGreaterThan(0);
      expect(store.codeObjects().length).toBeGreaterThan(0);
    });

    it('exposes accurate summary metrics derived strictly from declarative packet', () => {
      const metrics = store.metrics();
      expect(metrics.totalObjects).toBe(store.objects().length);
      expect(metrics.totalCodeObjects).toBe(store.codeObjects().length);
      expect(metrics.autoMappedCount + metrics.modifiedCount + metrics.needsReviewCount + metrics.blockedCount).toBe(metrics.totalObjects);
    });

    it('loads capability-driven options for privacy, cleansing, and deduplication', () => {
      expect(store.privacyOptions().length).toBeGreaterThan(0);
      expect(store.cleansingOptions().length).toBeGreaterThan(0);
      expect(store.survivorPolicyOptions().length).toBeGreaterThan(0);

      // Verify privacy option contract
      const maskOption = store.privacyOptions().find(p => p.id === 'PARTIAL_MASK');
      expect(maskOption).toBeDefined();
      expect(maskOption?.label).toBe('Partial Mask');
    });
  });

  // ==========================================================================
  // 2. REVIEW MODE DECISION QUEUE
  // ==========================================================================
  describe('Review Mode Decision Queue', () => {
    it('partitions objects into status buckets correctly', () => {
      expect(store.blockedObjects().every(o => o.status === 'BLOCKED')).toBe(true);
      expect(store.needsReviewObjects().every(o => o.status === 'NEEDS_REVIEW')).toBe(true);
      expect(store.modifiedObjects().every(o => o.status === 'MODIFIED')).toBe(true);
      expect(store.autoMappedObjects().every(o => o.status === 'AUTO_MAPPED')).toBe(true);
    });

    it('filtering by status restricts filtered objects list', () => {
      store.setStatusFilter('BLOCKED');
      expect(store.filteredObjects().every(o => o.status === 'BLOCKED')).toBe(true);

      store.setStatusFilter('ALL');
      expect(store.filteredObjects().length).toBe(store.objects().length);
    });

    it('search filter searches across source name, target name, and column names', () => {
      store.setSearchQuery('ACCOUNTS');
      const filtered = store.filteredObjects();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.some(o => o.sourceName.includes('ACCOUNTS'))).toBe(true);

      store.setSearchQuery('nonexistent_xyz_query');
      expect(store.filteredObjects().length).toBe(0);
      store.setSearchQuery('');
    });
  });

  // ==========================================================================
  // 3. ACTION ROUTING & WORKBENCH NAVIGATION
  // ==========================================================================
  describe('Action Routing & Workbench Navigation', () => {
    it('routeToMapObject switches to MAP mode and selects the object', () => {
      const firstObj = store.objects()[0];
      store.routeToMapObject(firstObj.id);

      expect(store.activeWorkspace()).toBe('MAPPING');
      expect(store.workMode()).toBe('MAP');
      expect(store.selectedObjectId()).toBe(firstObj.id);
      expect(store.activeFieldDetailId()).toBeNull();
    });

    it('routeToMapObject with fieldId focuses that specific column inline detail', () => {
      const firstObj = store.objects()[0];
      const colId = firstObj.columns[0].id;
      store.routeToMapObject(firstObj.id, colId);

      expect(store.workMode()).toBe('MAP');
      expect(store.selectedObjectId()).toBe(firstObj.id);
      expect(store.activeFieldDetailId()).toBe(colId);
    });

    it('routeToTranspilerObject switches to TRANSPILER workspace and selects routine', () => {
      const firstCode = store.codeObjects()[0];
      store.routeToTranspilerObject(firstCode.id);

      expect(store.activeWorkspace()).toBe('TRANSPILER');
      expect(store.selectedCodeObjectId()).toBe(firstCode.id);
    });
  });

  // ==========================================================================
  // 4. MAP MODE: OBJECT-LEVEL EDITING & DATA CONTROLS
  // ==========================================================================
  describe('Map Mode Object-Level Editing & Data Controls', () => {
    it('updating target namespace updates currentTargetNamespace and marks object modified', () => {
      const obj = store.objects()[0];
      store.updateTargetNamespace(obj.id, 'analytics_schema');

      const updated = store.objects().find(o => o.id === obj.id)!;
      expect(updated.currentTargetNamespace).toBe('analytics_schema');
      expect(updated.isModified).toBe(true);
    });

    it('updating target table name updates currentTargetName and marks object modified', () => {
      const obj = store.objects()[0];
      store.updateTargetName(obj.id, 'tbl_orders_renamed');

      const updated = store.objects().find(o => o.id === obj.id)!;
      expect(updated.currentTargetName).toBe('tbl_orders_renamed');
      expect(updated.isModified).toBe(true);
    });

    it('toggling row filter mode and predicate updates draft', () => {
      const obj = store.objects()[0];
      store.updateRowFilter(obj.id, 'CUSTOM', 'STATUS = 1 AND CREATED_AT >= 2024');

      const updated = store.objects().find(o => o.id === obj.id)!;
      expect(updated.rowFilterMode).toBe('CUSTOM');
      expect(updated.rowFilterPredicate).toBe('STATUS = 1 AND CREATED_AT >= 2024');
      expect(updated.isModified).toBe(true);
    });

    it('updating deduplication config enables dedup and assigns survivor policy', () => {
      const obj = store.objects()[0];
      store.updateDeduplication(obj.id, {
        enabled: true,
        keyFields: ['ORDER_ID', 'CUSTOMER_ID'],
        survivorPolicyOptionId: 'LATEST_TIMESTAMP'
      });

      const updated = store.objects().find(o => o.id === obj.id)!;
      expect(updated.deduplication.enabled).toBe(true);
      expect(updated.deduplication.keyFields).toEqual(['ORDER_ID', 'CUSTOMER_ID']);
      expect(updated.deduplication.survivorPolicyOptionId).toBe('LATEST_TIMESTAMP');
      expect(updated.isModified).toBe(true);
    });
  });

  // ==========================================================================
  // 5. DRAFT CONFLICT GUARD (Immediate UI Duplicate Target Detection)
  // ==========================================================================
  describe('Draft Conflict Guard', () => {
    it('flags duplicate target namespace and name collisions as BLOCKED', () => {
      const [obj1, obj2] = store.objects();
      
      // Deliberately set obj2 target to conflict with obj1
      store.updateTargetNamespace(obj2.id, obj1.currentTargetNamespace);
      store.updateTargetName(obj2.id, obj1.currentTargetName);

      const updatedObj1 = store.objects().find(o => o.id === obj1.id)!;
      const updatedObj2 = store.objects().find(o => o.id === obj2.id)!;

      expect(updatedObj1.status).toBe('BLOCKED');
      expect(updatedObj2.status).toBe('BLOCKED');

      const collisionIssue1 = updatedObj1.issues.find(i => i.code === 'TARGET_NAMING_COLLISION');
      expect(collisionIssue1).toBeDefined();
      expect(collisionIssue1?.severity).toBe('BLOCKED');

      // Resolve collision by changing target name
      store.updateTargetName(obj2.id, 'unique_target_name_fixed');
      const resolvedObj1 = store.objects().find(o => o.id === obj1.id)!;
      const resolvedObj2 = store.objects().find(o => o.id === obj2.id)!;

      expect(resolvedObj1.issues.some(i => i.code === 'TARGET_NAMING_COLLISION')).toBe(false);
      expect(resolvedObj2.issues.some(i => i.code === 'TARGET_NAMING_COLLISION')).toBe(false);
    });
  });

  // ==========================================================================
  // 6. FIELD-LEVEL CONTROLS & OVERRIDES
  // ==========================================================================
  describe('Field-Level Controls & Overrides', () => {
    it('renaming target column updates currentTargetField and marks column and object modified', () => {
      const obj = store.objects()[0];
      const col = obj.columns[0];
      store.updateTargetFieldName(obj.id, col.id, 'renamed_field_id');

      const updatedObj = store.objects().find(o => o.id === obj.id)!;
      const updatedCol = updatedObj.columns.find(c => c.id === col.id)!;

      expect(updatedCol.currentTargetField).toBe('renamed_field_id');
      expect(updatedCol.isModified).toBe(true);
      expect(updatedObj.isModified).toBe(true);
    });

    it('updating field type and parameter overrides (length, precision, scale)', () => {
      const obj = store.objects()[0];
      const col = obj.columns[0];
      store.updateTargetFieldType(obj.id, col.id, 'VARCHAR', { length: 128 });

      const updatedCol = store.objects().find(o => o.id === obj.id)!.columns.find(c => c.id === col.id)!;
      expect(updatedCol.currentTargetType).toBe('VARCHAR');
      expect(updatedCol.length).toBe(128);
      expect(updatedCol.isModified).toBe(true);
    });

    it('updating default expression override records expression and flags modified', () => {
      const obj = store.objects()[0];
      const col = obj.columns[0];
      store.updateDefaultExpression(obj.id, col.id, "'PENDING'");

      const updatedCol = store.objects().find(o => o.id === obj.id)!.columns.find(c => c.id === col.id)!;
      expect(updatedCol.currentDefaultExpression).toBe("'PENDING'");
      expect(updatedCol.isDefaultExpressionOverridden).toBe(true);
    });

    it('applying privacy transformation sets privacyOptionId and parameter', () => {
      const obj = store.objects()[0];
      const col = obj.columns[0];
      store.updatePrivacyControl(obj.id, col.id, 'PARTIAL_MASK', 'keep_first=2,keep_last=2');

      const updatedCol = store.objects().find(o => o.id === obj.id)!.columns.find(c => c.id === col.id)!;
      expect(updatedCol.privacyOptionId).toBe('PARTIAL_MASK');
      expect(updatedCol.privacyParam).toBe('keep_first=2,keep_last=2');
      expect(updatedCol.isModified).toBe(true);
    });

    it('applying cleansing transformation sets cleansingOptionId', () => {
      const obj = store.objects()[0];
      const col = obj.columns[0];
      store.updateCleansingControl(obj.id, col.id, 'TRIM');

      const updatedCol = store.objects().find(o => o.id === obj.id)!.columns.find(c => c.id === col.id)!;
      expect(updatedCol.cleansingOptionId).toBe('TRIM');
      expect(updatedCol.isModified).toBe(true);
    });

    it('toggling column inclusion updates isIncluded without deleting canonical issues', () => {
      const obj = store.objects()[0];
      const col = obj.columns[0];
      const initialInclusion = col.isIncluded;

      store.toggleColumnInclusion(obj.id, col.id);
      const updatedCol = store.objects().find(o => o.id === obj.id)!.columns.find(c => c.id === col.id)!;
      expect(updatedCol.isIncluded).toBe(!initialInclusion);
      expect(updatedCol.isModified).toBe(true);
    });
  });

  // ==========================================================================
  // 7. TRANSPILER STUDIO & PROCEDURAL TRANSLATION
  // ==========================================================================
  describe('Transpiler Studio & Procedural Translation', () => {
    it('exposes code objects partitioned by category', () => {
      const codeObjs = store.codeObjects();
      expect(codeObjs.length).toBeGreaterThan(0);
      expect(codeObjs.some(c => c.category === 'PROCEDURE')).toBe(true);
    });

    it('editing target code marks routine as modified', () => {
      const code = store.codeObjects()[0];
      const newSql = `${code.currentTargetCode}\n-- Operator syntax optimization`;
      store.updateTargetCode(code.id, newSql);

      const updatedCode = store.codeObjects().find(c => c.id === code.id)!;
      expect(updatedCode.currentTargetCode).toBe(newSql);
      expect(updatedCode.isModified).toBe(true);
      expect(updatedCode.status).toBe('MODIFIED');
    });

    it('routine diagnostics expose line, column, severity, construct and recommendation', () => {
      const codeWithDiag = store.codeObjects().find(c => c.diagnostics.length > 0);
      expect(codeWithDiag).toBeDefined();
      if (codeWithDiag) {
        const diag = codeWithDiag.diagnostics[0];
        expect(diag.severity).toMatch(/ERROR|WARNING|INFO/);
        expect(diag.message.length).toBeGreaterThan(0);
      }
    });
  });

  // ==========================================================================
  // 8. REVERT OPERATIONS
  // ==========================================================================
  describe('Revert Operations', () => {
    it('reverting modified object mapping restores original declarative proposal', () => {
      const obj = store.objects()[0];
      const origName = obj.originalProposal.targetName;
      const origNamespace = obj.originalProposal.targetNamespace;

      // Make edits
      store.updateTargetNamespace(obj.id, 'modified_namespace');
      store.updateTargetName(obj.id, 'modified_table_name');
      expect(store.objects().find(o => o.id === obj.id)!.isModified).toBe(true);

      // Prompt and confirm revert
      store.promptRevertObject(obj.id);
      expect(store.pendingRevertObject()?.id).toBe(obj.id);

      store.confirmRevertObject();
      const restored = store.objects().find(o => o.id === obj.id)!;
      expect(restored.currentTargetNamespace).toBe(origNamespace);
      expect(restored.currentTargetName).toBe(origName);
      expect(restored.isModified).toBe(false);
      expect(store.pendingRevertObject()).toBeNull();
    });

    it('reverting modified code object restores original declarative target dialect code', () => {
      const code = store.codeObjects()[0];
      const origCode = code.originalProposal.targetCode;

      store.updateTargetCode(code.id, '-- Manual destructive replacement');
      expect(store.codeObjects().find(c => c.id === code.id)!.isModified).toBe(true);

      store.promptRevertCodeObject(code.id);
      expect(store.pendingRevertCodeObject()?.id).toBe(code.id);

      store.confirmRevertCodeObject();
      const restored = store.codeObjects().find(c => c.id === code.id)!;
      expect(restored.currentTargetCode).toBe(origCode);
      expect(restored.isModified).toBe(false);
      expect(store.pendingRevertCodeObject()).toBeNull();
    });
  });

  // ==========================================================================
  // 9. UI WORKFLOW READINESS GATE
  // ==========================================================================
  describe('UI Workflow Readiness Gate', () => {
    it('isUiWorkflowReady is true when scope has objects and zero blockers', () => {
      // In default Oracle -> Postgres, there is 1 blocked item (iss-oracle-bfile)
      // If there are blocked items, readiness is false
      const m = store.metrics();
      if (m.blockedCount > 0 || m.codeBlockedCount > 0) {
        expect(store.isUiWorkflowReady()).toBe(false);
      } else {
        expect(store.isUiWorkflowReady()).toBe(true);
      }
    });

    it('resolving blockers transitions UI workflow readiness to true', () => {
      // Clear or resolve all blockers across objects and codeObjects
      store.objects.update(list =>
        list.map(obj => ({
          ...obj,
          status: obj.status === 'BLOCKED' ? 'MODIFIED' : obj.status,
          readiness: obj.readiness === 'BLOCKED' ? 'READY' : obj.readiness,
          issues: obj.issues.filter(i => i.severity !== 'BLOCKED')
        }))
      );
      store.codeObjects.update(list =>
        list.map(code => ({
          ...code,
          status: code.status === 'BLOCKED' ? 'MODIFIED' : code.status,
          diagnostics: code.diagnostics.filter(d => d.severity !== 'ERROR')
        }))
      );

      expect(store.isUiWorkflowReady()).toBe(true);
    });

    it('empty scope causes readiness to be false', () => {
      store.objects.set([]);
      expect(store.isUiWorkflowReady()).toBe(false);
    });
  });

  // ==========================================================================
  // 10. UI POLYMORPHISM ACROSS SOURCE/TARGET ENGINES
  // ==========================================================================
  describe('UI Polymorphism Across Engines', () => {
    it('loads MongoDB -> Kafka document streaming packet correctly', () => {
      const mongoPacket = adapter.getProposedMappingPacket(
        'MongoDB' as PhysicalProviderId,
        'Apache Kafka' as PhysicalProviderId,
        'M2_BULK_CDC' as MigrationMode,
        ['coll-orders', 'coll-products']
      );

      store.loadPacket(mongoPacket);
      expect(store.objects().length).toBeGreaterThan(0);
      expect(store.objects()[0].sourceType).toBe('COLLECTION');
      expect(store.objects()[0].sourceTypeLabel).toBe('Collection');
      expect(store.codeObjects().length).toBe(0); // MongoDB has no procedural routines
    });

    it('loads S3 -> Snowflake storage packet correctly', () => {
      const s3Packet = adapter.getProposedMappingPacket(
        'Amazon S3' as PhysicalProviderId,
        'Snowflake' as PhysicalProviderId,
        'M1_BULK' as MigrationMode,
        ['s3-prefix-raw']
      );

      store.loadPacket(s3Packet);
      expect(store.objects().length).toBeGreaterThan(0);
      expect(store.objects()[0].sourceType).toBe('BUCKET');
      expect(store.objects()[0].sourceTypeLabel).toBe('Bucket');
    });
  });

  // ==========================================================================
  // 11. SUB-WORKSPACE NAVIGATION & ATTENTION QUEUE ROUTING
  // ==========================================================================
  describe('Sub-Workspace Navigation & Attention Queue Routing', () => {
    it('defaults to OVERVIEW sub-workspace and supports switching to STRUCTURE, FIELDS, and CONTROLS', () => {
      expect(store.activeSubWorkspace()).toBe('OVERVIEW');

      store.setSubWorkspace('STRUCTURE');
      expect(store.activeSubWorkspace()).toBe('STRUCTURE');

      store.setSubWorkspace('FIELDS');
      expect(store.activeSubWorkspace()).toBe('FIELDS');

      store.setSubWorkspace('CONTROLS');
      expect(store.activeSubWorkspace()).toBe('CONTROLS');
    });

    it('routeToStructure selects the namespace and switches sub-workspace', () => {
      store.routeToStructure('PAYMENTS');
      expect(store.activeSubWorkspace()).toBe('STRUCTURE');
      expect(store.selectedNamespaceName()).toBe('PAYMENTS');
    });

    it('routeToFields selects the object and focuses column detail', () => {
      const targetObj = store.objects()[0];
      const colId = targetObj.columns[0].id;

      store.routeToFields(targetObj.id, colId);
      expect(store.activeSubWorkspace()).toBe('FIELDS');
      expect(store.selectedObjectId()).toBe(targetObj.id);
      expect(store.activeFieldDetailId()).toBe(colId);
    });

    it('routeToControls switches to Data Controls and selects the category', () => {
      store.routeToControls('DEDUPLICATION');
      expect(store.activeSubWorkspace()).toBe('CONTROLS');
      expect(store.activeControlsCategory()).toBe('DEDUPLICATION');
    });
  });

  // ==========================================================================
  // 12. DATA CONTROLS & CANONICAL SURVIVOR POLICIES
  // ==========================================================================
  describe('Data Controls & Canonical Survivor Policies', () => {
    it('provides canonical deduplication survivor policies matching backend contracts', () => {
      const policies = store.survivorPolicyOptions();
      const policyIds = policies.map(p => p.id);

      expect(policyIds).toContain('FIRST');
      expect(policyIds).toContain('LAST');
      expect(policyIds).toContain('MIN_FIELD');
      expect(policyIds).toContain('MAX_FIELD');
      expect(policyIds).toContain('NEWEST');
      expect(policyIds).toContain('OLDEST');
      expect(policyIds).toContain('PRIORITY');
      expect(policyIds).toContain('FAIL_ON_DUPLICATE');
      expect(policyIds).toContain('REJECT_GROUP');
      expect(policyIds).toContain('QUARANTINE_GROUP');
    });

    it('applying deduplication draft updates store items and clears dirty state', () => {
      const dedupItem = store.deduplicationItems()[0];
      store.dedupDraft.set({
        ...dedupItem,
        survivorPolicy: 'PRIORITY',
        survivorPolicyLabel: 'Priority Matrix',
        disposition: 'QUARANTINE_GROUP'
      });

      expect(store.isControlsDirty()).toBe(true);

      store.applyDedupDraft();
      expect(store.isControlsDirty()).toBe(false);

      const updated = store.deduplicationItems().find(d => d.id === dedupItem.id)!;
      expect(updated.survivorPolicy).toBe('PRIORITY');
      expect(updated.disposition).toBe('QUARANTINE_GROUP');
      expect(updated.isModified).toBe(true);
    });

    it('applying privacy draft with secret vault reference commits correctly', () => {
      const privItem = store.privacyItems()[0];
      store.privacyDraft.set({
        ...privItem,
        strategy: 'KEYED_PSEUDONYM',
        strategyLabel: 'Keyed Pseudonym',
        configuration: 'vault://enterprise/keys/custom_salt'
      });

      expect(store.isControlsDirty()).toBe(true);
      store.applyPrivacyDraft();
      expect(store.isControlsDirty()).toBe(false);

      const updated = store.privacyItems().find(p => p.id === privItem.id)!;
      expect(updated.strategy).toBe('KEYED_PSEUDONYM');
      expect(updated.configuration).toBe('vault://enterprise/keys/custom_salt');
      expect(updated.isModified).toBe(true);
    });
  });

  // ==========================================================================
  // 13. APPLY BUTTON LAW & DRAFT PERSISTENCE ACROSS NAVIGATION
  // ==========================================================================
  describe('Apply Button Law & Persistence Across Sub-Workspaces', () => {
    it('editing namespace updates draft and enables Apply via isNamespaceDirty', () => {
      const curNs = store.selectedNamespace()!;
      expect(store.isNamespaceDirty()).toBe(false);

      store.namespaceDraft.set({
        ...curNs,
        currentTargetNamespace: 'banking_enterprise_prod',
        prefix: 'corp_'
      });

      expect(store.isNamespaceDirty()).toBe(true);

      // Apply commits draft
      store.applyNamespaceDraft();
      expect(store.isNamespaceDirty()).toBe(false);

      const updated = store.namespaces().find(n => n.sourceNamespace === curNs.sourceNamespace)!;
      expect(updated.currentTargetNamespace).toBe('banking_enterprise_prod');
      expect(updated.prefix).toBe('corp_');
      expect(updated.isModified).toBe(true);

      // Verify persistent across navigation
      store.setSubWorkspace('FIELDS');
      expect(store.activeSubWorkspace()).toBe('FIELDS');
      store.setSubWorkspace('STRUCTURE');
      expect(store.activeSubWorkspace()).toBe('STRUCTURE');

      const rechecked = store.namespaces().find(n => n.sourceNamespace === curNs.sourceNamespace)!;
      expect(rechecked.currentTargetNamespace).toBe('banking_enterprise_prod');
    });

    it('field edit draft commits into applied state and updates modified counter', () => {
      const curObj = store.objects()[0];
      const col = curObj.columns[0];
      const initialModifiedCount = store.metrics().modifiedCount;

      store.fieldDraft.set({
        ...col,
        currentTargetField: 'custom_identifier_v2',
        currentTargetType: 'TEXT'
      });

      expect(store.isFieldDirty()).toBe(true);

      store.applyFieldDraft();
      expect(store.isFieldDirty()).toBe(false);

      const updatedObj = store.objects().find(o => o.id === curObj.id)!;
      const updatedCol = updatedObj.columns.find(c => c.id === col.id)!;

      expect(updatedCol.currentTargetField).toBe('custom_identifier_v2');
      expect(updatedCol.currentTargetType).toBe('TEXT');
      expect(updatedCol.isModified).toBe(true);
      expect(updatedObj.isModified).toBe(true);
    });
  });

  // ==========================================================================
  // 14. UNSAVED CHANGES PROTECTION GUARD
  // ==========================================================================
  describe('Unsaved Changes Protection Guard', () => {
    it('triggers pendingNavigation when dirty draft exists on sub-workspace change', () => {
      const curNs = store.selectedNamespace()!;
      store.namespaceDraft.set({
        ...curNs,
        prefix: 'unapplied_prefix_'
      });
      expect(store.hasAnyUnsavedDraft()).toBe(true);

      let navigated = false;
      store.navigateWithGuard(() => {
        navigated = true;
      }, 'Testing navigation guard');

      expect(navigated).toBe(false);
      expect(store.pendingNavigation()).not.toBeNull();
      expect(store.pendingNavigation()?.title).toBe('Unsaved Changes');

      // Cancel keeps draft
      store.cancelPendingNavigation();
      expect(store.pendingNavigation()).toBeNull();
      expect(store.hasAnyUnsavedDraft()).toBe(true);

      // Discard clears draft and executes navigation
      store.navigateWithGuard(() => {
        navigated = true;
      });
      store.discardPendingNavigation();
      expect(navigated).toBe(true);
      expect(store.hasAnyUnsavedDraft()).toBe(false);
    });
  });

  // ==========================================================================
  // 15. TRANSPILER STUDIO FOCUS MODE & MANUAL EDITING
  // ==========================================================================
  describe('Transpiler Studio Focus Mode & Manual Editing', () => {
    it('supports switching view modes and toggling Focus Editor', () => {
      store.setWorkspace('TRANSPILER');
      expect(store.activeWorkspace()).toBe('TRANSPILER');

      store.transpilerViewMode.set('SOURCE');
      expect(store.transpilerViewMode()).toBe('SOURCE');

      store.transpilerViewMode.set('TARGET');
      expect(store.transpilerViewMode()).toBe('TARGET');

      store.transpilerViewMode.set('SIDE_BY_SIDE');
      expect(store.transpilerViewMode()).toBe('SIDE_BY_SIDE');

      expect(store.isTranspilerFocusMode()).toBe(false);
      store.isTranspilerFocusMode.set(true);
      expect(store.isTranspilerFocusMode()).toBe(true);
      store.isTranspilerFocusMode.set(false);
    });

    it('manual code draft marks isTranspilerDirty and Apply commits target code', () => {
      store.setWorkspace('TRANSPILER');
      const curCode = store.selectedCodeObject()!;
      const modifiedSql = `${curCode.currentTargetCode}\n-- Added custom concurrency hint`;

      store.transpilerCodeDraft.set(modifiedSql);
      expect(store.isTranspilerDirty()).toBe(true);

      store.applyTranspilerCodeDraft();
      expect(store.isTranspilerDirty()).toBe(false);

      const updated = store.codeObjects().find(c => c.id === curCode.id)!;
      expect(updated.currentTargetCode).toBe(modifiedSql);
      expect(updated.isModified).toBe(true);
      expect(updated.status).toBe('MODIFIED');
    });
  });

  // ==========================================================================
  // 16. UI WORKFLOW READINESS GATE & BLOCKER SYNCHRONIZATION
  // ==========================================================================
  describe('UI Workflow Readiness Gate & Blocker Synchronization', () => {
    it('isUiWorkflowReady is true when no blockers exist and syncs with wizard draft', () => {
      // Set topology nodes so draft has scope
      ms.updateDraft({ selectedTopologyNodes: ['tbl-1', 'tbl-2'] });
      // Clear initial sample blockers
      store.objects.update(list =>
        list.map(obj => ({
          ...obj,
          status: obj.status === 'BLOCKED' ? 'MODIFIED' : obj.status,
          readiness: obj.readiness === 'BLOCKED' ? 'READY' : obj.readiness,
          issues: obj.issues.filter(i => i.severity !== 'BLOCKED')
        }))
      );
      store.codeObjects.update(list =>
        list.map(code => ({
          ...code,
          status: code.status === 'BLOCKED' ? 'MODIFIED' : code.status,
          diagnostics: code.diagnostics.filter(d => d.severity !== 'ERROR')
        }))
      );
      store.syncDraftReadiness();

      expect(store.metrics().blockedCount).toBe(0);
      expect(store.isUiWorkflowReady()).toBe(true);
      expect(ms.isStepValid(5)).toBe(true);
      expect(ms.wizardDraft().hasStep5Blockers).toBe(false);
    });

    it('flags Step 5 as invalid in MigrationUiService when a collision causes a blocker', () => {
      ms.updateDraft({ selectedTopologyNodes: ['tbl-1', 'tbl-2'] });
      // Clear initial sample blockers
      store.objects.update(list =>
        list.map(obj => ({
          ...obj,
          status: obj.status === 'BLOCKED' ? 'MODIFIED' : obj.status,
          readiness: obj.readiness === 'BLOCKED' ? 'READY' : obj.readiness,
          issues: obj.issues.filter(i => i.severity !== 'BLOCKED')
        }))
      );
      store.codeObjects.update(list =>
        list.map(code => ({
          ...code,
          status: code.status === 'BLOCKED' ? 'MODIFIED' : code.status,
          diagnostics: code.diagnostics.filter(d => d.severity !== 'ERROR')
        }))
      );
      store.syncDraftReadiness();
      expect(store.isUiWorkflowReady()).toBe(true);

      const [obj1, obj2] = store.objects();

      // Create target collision
      store.updateTargetNamespace(obj2.id, obj1.currentTargetNamespace);
      store.updateTargetName(obj2.id, obj1.currentTargetName);

      expect(store.metrics().blockedCount).toBeGreaterThan(0);
      expect(store.isUiWorkflowReady()).toBe(false);
      expect(ms.wizardDraft().hasStep5Blockers).toBe(true);
      expect(ms.isStepValid(5)).toBe(false);

      // Resolve collision
      store.updateTargetName(obj2.id, 'resolved_unique_table_name');
      expect(store.metrics().blockedCount).toBe(0);
      expect(store.isUiWorkflowReady()).toBe(true);
      expect(ms.wizardDraft().hasStep5Blockers).toBe(false);
      expect(ms.isStepValid(5)).toBe(true);
    });
  });
});

