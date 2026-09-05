import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { DiscoveryScopeService } from '../../../../core/services/discovery-scope.service';
import { DiscoveryDepthTier, MigrationMode, PhysicalProviderId } from '../../../../core/models/migration-view.models';

describe('Step 4 — Discovery & Scope Master Contract Verification Suite', () => {
  let ms: MigrationUiService;
  let svc: DiscoveryScopeService;

  beforeEach(() => {
    ms = new MigrationUiService();
    svc = new DiscoveryScopeService(ms);
    ms.resetWizardDraft();
  });

  // ==========================================================================
  // 1. LIFECYCLE STATE MACHINE (Section 1, 10, 14, 15, 21, 22, 23, 25, 65)
  // ==========================================================================
  describe('Lifecycle State Machine', () => {
    it('initial entry with no prior discovery must start in DEPTH_SELECTION', () => {
      svc.syncInitialStateFromDraft();
      expect(svc.lifecycleState()).toBe('DEPTH_SELECTION');
      expect(ms.wizardDraft().discoveryHash).toBeUndefined();
    });

    it('operator can choose between all 4 canonical depth tiers (QUICK, STANDARD, DEEP, COMPLIANCE)', () => {
      const tiers: DiscoveryDepthTier[] = ['QUICK', 'STANDARD', 'DEEP', 'COMPLIANCE'];
      for (const tier of tiers) {
        svc.currentDepth.set(tier);
        expect(svc.currentDepth()).toBe(tier);
      }
    });

    it('starting discovery transitions state to DISCOVERING and begins stage progression', () => {
      svc.startDiscovery('STANDARD');
      expect(svc.lifecycleState()).toBe('DISCOVERING');
      expect(svc.currentDepth()).toBe('STANDARD');
      expect(svc.discoveryStages().length).toBe(5);
      expect(svc.discoveryStages()[0].id).toBe('identity');
      expect(svc.discoveryStages()[0].status).toBe('RUNNING');
    });

    it('cancellation transitions truthfully and returns to DEPTH_SELECTION without fake results', async () => {
      svc.startDiscovery('STANDARD');
      expect(svc.lifecycleState()).toBe('DISCOVERING');

      svc.cancelDiscovery();
      expect(svc.isCancelling()).toBe(true);

      // Wait for cancellation acknowledgment
      await new Promise(r => setTimeout(r, 250));
      expect(svc.isCancelled()).toBe(true);
      expect(svc.lifecycleState()).toBe('DEPTH_SELECTION');
    });

    it('successful discovery completion transitions to SCOPE_WORKBENCH and populates estate', async () => {
      svc.startDiscovery('STANDARD');
      // Wait for async stage completion
      await new Promise(r => setTimeout(r, 1300));

      expect(svc.lifecycleState()).toBe('SCOPE_WORKBENCH');
      expect(ms.wizardDraft().discoveryHash).toBe('7f9a2b8e');
      expect(svc.rootNodes().length).toBeGreaterThan(0);
      expect(ms.wizardDraft().selectedTopologyNodes.length).toBeGreaterThan(0);
    });

    it('failure state does not dump operator into empty workbench and allows retry', () => {
      svc.lifecycleState.set('FAILURE');
      svc.errorMessage.set('Insufficient privileges to inspect required source metadata.');
      expect(svc.lifecycleState()).toBe('FAILURE');

      // Retry discovery
      svc.retryDiscovery();
      expect(svc.lifecycleState()).toBe('DISCOVERING');
    });

    it('change depth returns to DEPTH_SELECTION and invalidates previous scope hash', () => {
      svc.lifecycleState.set('SCOPE_WORKBENCH');
      ms.updateDraft({ discoveryHash: '7f9a2b8e', isScopeLocked: true });

      svc.returnToDepthSelection();
      expect(svc.lifecycleState()).toBe('DEPTH_SELECTION');
      expect(ms.wizardDraft().discoveryHash).toBeUndefined();
      expect(ms.wizardDraft().isScopeLocked).toBe(false);
    });

    it('re-entry into Step 4 restores SCOPE_WORKBENCH if discovery hash exists', () => {
      ms.updateDraft({ discoveryHash: '7f9a2b8e', sourceProvider: 'Oracle' });
      svc.rootNodes.set([]); // Clear in-memory
      svc.syncInitialStateFromDraft();

      expect(svc.lifecycleState()).toBe('SCOPE_WORKBENCH');
      expect(svc.rootNodes().length).toBeGreaterThan(0);
    });

    it('metadata drift detection displays warning and invalidates readiness until refreshed', () => {
      svc.lifecycleState.set('SCOPE_WORKBENCH');
      ms.updateDraft({ isScopeLocked: true, isScopeFrozen: true });

      svc.setDriftDetected(true);
      expect(svc.isDriftDetected()).toBe(true);
      expect(ms.wizardDraft().isScopeLocked).toBe(false);
      expect(ms.wizardDraft().isScopeFrozen).toBe(false);

      // Refresh discovery after drift
      svc.refreshDiscoveryAfterDrift();
      expect(svc.isDriftDetected()).toBe(false);
      expect(svc.lifecycleState()).toBe('DISCOVERING');
    });
  });

  // ==========================================================================
  // 2. PROVIDER-NEUTRAL HIERARCHY & TERMINOLOGY (Section 35, 36, 37)
  // ==========================================================================
  describe('Provider-Neutral Hierarchy & Native Terminology', () => {
    it('relational provider (Oracle) generates 4-level instance/schema/group/leaf hierarchy', () => {
      svc.generateDiscoveredEstate('Oracle', 'STANDARD', 'M1_BULK');
      const roots = svc.rootNodes();
      expect(roots[0].type).toBe('INSTANCE');
      expect(roots[0].children?.[0].type).toBe('SCHEMA');
      expect(roots[0].children?.[0].name).toBe('CORE_BANKING');

      const labels = svc.getHierarchyFilterLabels();
      expect(labels.level1Label).toBe('Instance');
      expect(labels.level2Label).toBe('Schema');
      expect(labels.primaryObjectLabel).toBe('Tables');
    });

    it('NoSQL document provider (MongoDB) generates cluster/database/collections hierarchy without fake schema layer', () => {
      svc.generateDiscoveredEstate('MongoDB', 'STANDARD', 'M1_BULK');
      const roots = svc.rootNodes();
      expect(roots[0].type).toBe('INSTANCE'); // cluster
      expect(roots[0].children?.[0].type).toBe('DATABASE');
      expect(roots[0].children?.[0].children?.[0].type).toBe('COLLECTION');

      const labels = svc.getHierarchyFilterLabels();
      expect(labels.level1Label).toBe('Cluster');
      expect(labels.level2Label).toBe('Database');
      expect(labels.primaryObjectLabel).toBe('Collections');
    });

    it('streaming provider (Kafka) generates cluster/topic/partitions hierarchy without table semantics', () => {
      svc.generateDiscoveredEstate('Apache Kafka', 'STANDARD', 'M3_CDC');
      const roots = svc.rootNodes();
      expect(roots[0].type).toBe('INSTANCE');
      expect(roots[0].children?.[0].type).toBe('TOPIC');
      expect(roots[0].children?.[0].children?.[0].type).toBe('PARTITION');

      const labels = svc.getHierarchyFilterLabels();
      expect(labels.level1Label).toBe('Cluster');
      expect(labels.level2Label).toBe('Topic');
      expect(labels.primaryObjectLabel).toBe('Partitions');
    });

    it('object storage provider (S3) generates endpoint/bucket/prefix/objects hierarchy', () => {
      svc.generateDiscoveredEstate('Amazon S3', 'STANDARD', 'M1_BULK');
      const roots = svc.rootNodes();
      expect(roots[0].type).toBe('INSTANCE');
      expect(roots[0].children?.[0].type).toBe('BUCKET');
      expect(roots[0].children?.[0].children?.[0].type).toBe('PREFIX');
      expect(roots[0].children?.[0].children?.[0].children?.[0].type).toBe('OBJECT');

      const labels = svc.getHierarchyFilterLabels();
      expect(labels.level1Label).toBe('Endpoint');
      expect(labels.level2Label).toBe('Bucket');
      expect(labels.primaryObjectLabel).toBe('Objects');
    });
  });

  // ==========================================================================
  // 3. SELECTION, ELIGIBILITY, TRI-STATE, SKIP & INCLUDE (Section 42-50)
  // ==========================================================================
  describe('Scope Selection & Tri-State Engine', () => {
    beforeEach(() => {
      svc.generateDiscoveredEstate('Oracle', 'STANDARD', 'M2_BULK_CDC');
    });

    it('toggling leaf node updates selection and recomputes parent tri-state', () => {
      const accNode = svc.nodeMap.get('tbl-accounts')!;
      expect(accNode.isSelected).toBe(true);

      // Deselect leaf
      svc.toggleNodeSelection('tbl-accounts');
      expect(accNode.isSelected).toBe(false);

      // Parent group should now be indeterminate (some selected, some not)
      const groupNode = svc.nodeMap.get('grp-tables-core')!;
      expect(svc.isNodeIndeterminate(groupNode)).toBe(true);
      expect(svc.isNodeFullySelected(groupNode)).toBe(false);
    });

    it('toggling parent container node cascades selection to all migratable descendants', () => {
      const groupNode = svc.nodeMap.get('grp-tables-core')!;
      expect(svc.isNodeFullySelected(groupNode)).toBe(true);

      // Deselect entire table group
      svc.toggleNodeSelection('grp-tables-core');
      expect(svc.isNodeFullySelected(groupNode)).toBe(false);
      expect(svc.nodeMap.get('tbl-accounts')!.isSelected).toBe(false);
      expect(svc.nodeMap.get('tbl-customers')!.isSelected).toBe(false);
      expect(svc.nodeMap.get('tbl-transactions')!.isSelected).toBe(false);

      // Re-select entire group
      svc.toggleNodeSelection('grp-tables-core');
      expect(svc.isNodeFullySelected(groupNode)).toBe(true);
      expect(svc.nodeMap.get('tbl-accounts')!.isSelected).toBe(true);
      expect(svc.nodeMap.get('tbl-customers')!.isSelected).toBe(true);
      expect(svc.nodeMap.get('tbl-transactions')!.isSelected).toBe(true);
    });

    it('filtering does not erase hidden selections', () => {
      // Initially 5 objects selected
      const initialSelected = svc.getMigratableLeafNodes().filter(n => n.isSelected).length;
      expect(initialSelected).toBeGreaterThan(0);

      // Apply search filter matching only ACCOUNTS
      svc.searchQuery.set('ACCOUNTS');

      // Selections in the estate must remain intact
      const stillSelected = svc.getMigratableLeafNodes().filter(n => n.isSelected).length;
      expect(stillSelected).toBe(initialSelected);
    });

    it('collapsing nodes does not erase selections', () => {
      const initialSelected = svc.getMigratableLeafNodes().filter(n => n.isSelected).length;
      svc.collapseAll();
      expect(svc.expandedNodeIds().size).toBe(0);

      const stillSelected = svc.getMigratableLeafNodes().filter(n => n.isSelected).length;
      expect(stillSelected).toBe(initialSelected);
    });

    it('Skip excludes blocked resource from scope without overriding the underlying blocker', () => {
      const txNode = svc.nodeMap.get('tbl-transactions')!;
      expect(txNode.status).toBe('BLOCKED');
      expect(txNode.isSelected).toBe(true);

      // Initially has 1 selected blocker
      expect(svc.computeSelectedBlockerCount()).toBe(1);

      // Operator clicks Skip
      svc.skipBlockedResource('tbl-transactions');

      // Resource is now EXCLUDED (isSelected = false)
      expect(txNode.isSelected).toBe(false);
      // Status is still BLOCKED on physical object, but it is no longer selected
      expect(txNode.status).toBe('BLOCKED');
      // Selected blockers count is now 0!
      expect(svc.computeSelectedBlockerCount()).toBe(0);
    });

    it('Include explicitly adds referenced dependency to scope', () => {
      const auditNode = svc.nodeMap.get('tbl-audit-events')!;
      expect(auditNode.isDependencyReference).toBe(true);
      expect(auditNode.isSelected).toBe(false);

      // Operator clicks + Include
      svc.includeDependencyResource('tbl-audit-events');
      expect(auditNode.isSelected).toBe(true);
    });

    it('bulk selection actions (selectAll, deselectAll, selectVisible, deselectVisible, selectNamespace) work correctly', () => {
      // Deselect all
      svc.deselectAll();
      expect(svc.getMigratableLeafNodes().filter(n => n.isSelected).length).toBe(0);

      // Select all
      svc.selectAll();
      expect(svc.getMigratableLeafNodes().filter(n => !n.isSelected).length).toBe(0);

      // Select specific namespace
      svc.deselectAll();
      svc.selectNamespace('CORE_BANKING');
      const coreLeaves = svc.getMigratableLeafNodes().filter(n => n.namespace === 'CORE_BANKING');
      expect(coreLeaves.every(n => n.isSelected)).toBe(true);
    });
  });

  // ==========================================================================
  // 4. SUMMARY METRICS & MODE AWARENESS (Section 26, 27, 28, 54)
  // ==========================================================================
  describe('Summary Metrics & Mode-Aware Presentation', () => {
    it('accurately calculates schemas, objects, tables, and volume in bulk mode', () => {
      ms.updateWizardMode('M1_BULK');
      svc.generateDiscoveredEstate('Oracle', 'STANDARD', 'M1_BULK');

      const m = svc.computeSummaryMetrics();
      expect(m.schemasTotal).toBe(2); // CORE_BANKING, AUDIT_ARCHIVE
      expect(m.schemasSelected).toBe(1); // CORE_BANKING selected by default
      expect(m.objectsSelected).toBe(5);
      expect(m.isVolumeApplicable).toBe(true);
      expect(m.volumeSelectedBytes).toBeGreaterThan(0);
      expect(m.volumeFormatted).toContain('GB');
    });

    it('suppresses volume in M6_SCHEMA_ONLY mode', () => {
      ms.updateWizardMode('M6_SCHEMA_ONLY');
      svc.generateDiscoveredEstate('Oracle', 'STANDARD', 'M6_SCHEMA_ONLY');

      const m = svc.computeSummaryMetrics();
      expect(m.isVolumeApplicable).toBe(false);
      expect(m.volumeFormatted).toBe('— (Inapplicable)');
    });

    it('M2_BULK_CDC and M3_CDC accurately identify CDC blockers on unlogged/non-PK objects', () => {
      ms.updateWizardMode('M2_BULK_CDC');
      svc.generateDiscoveredEstate('Oracle', 'STANDARD', 'M2_BULK_CDC');

      const txNode = svc.nodeMap.get('tbl-transactions')!;
      expect(txNode.status).toBe('BLOCKED');
      expect(txNode.statusReason).toContain('CDC eligibility');
    });
  });

  // ==========================================================================
  // 5. SCOPE READINESS & CANONICAL LOCKING (Section 59, 60, 61, 62)
  // ==========================================================================
  describe('Scope Readiness & Canonical Locking', () => {
    beforeEach(() => {
      ms.updateWizardMode('M2_BULK_CDC');
      svc.generateDiscoveredEstate('Oracle', 'STANDARD', 'M2_BULK_CDC');
    });

    it('readiness is blocked when a selected resource is BLOCKED', () => {
      expect(svc.computeSelectedBlockerCount()).toBe(1);
      // MigrationUiService canLockScope should return false
      ms.updateDraft({ hasCdcBlockers: true });
      expect(ms.canLockScope()).toBe(false);
    });

    it('readiness is blocked when 0 objects are selected', () => {
      svc.deselectAll();
      ms.updateDraft({ selectedTopologyNodes: [] });
      expect(ms.canLockScope()).toBe(false);
      expect(ms.isStepValid(4)).toBe(false);
    });

    it('readiness passes once blocked resource is skipped (excluded)', () => {
      // Skip the blocked transaction table
      svc.skipBlockedResource('tbl-transactions');
      expect(svc.computeSelectedBlockerCount()).toBe(0);

      const readySelected = svc.getMigratableLeafNodes().filter(n => n.isSelected).map(n => n.id);
      ms.updateDraft({
        selectedTopologyNodes: readySelected,
        hasCdcBlockers: false,
        unresolvedFkCount: 0
      });

      expect(ms.canLockScope()).toBe(true);
      expect(ms.isStepValid(4)).toBe(true);
    });

    it('locking scope freezes selections and produces internal hash without claiming canonical evidence authority', () => {
      svc.skipBlockedResource('tbl-transactions');
      const readySelected = svc.getMigratableLeafNodes().filter(n => n.isSelected).map(n => n.id);
      ms.updateDraft({
        selectedTopologyNodes: readySelected,
        hasCdcBlockers: false,
        discoveryHash: '7f9a2b8e'
      });

      expect(ms.canLockScope()).toBe(true);
      ms.lockScope();

      expect(ms.wizardDraft().isScopeLocked).toBe(true);
      expect(ms.wizardDraft().isScopeFrozen).toBe(true);
      expect(ms.wizardDraft().scopeFingerprint).toBeDefined();

      // Unlock scope re-enables editing
      ms.unlockScope();
      expect(ms.wizardDraft().isScopeLocked).toBe(false);
      expect(ms.wizardDraft().isScopeFrozen).toBe(false);
    });

    it('ignoreFkWarnings does NOT bypass canonical CDC or incremental blockers', () => {
      // Both CDC blocker and ignoreFkWarnings present
      ms.updateDraft({
        hasCdcBlockers: true,
        unresolvedFkCount: 2,
        ignoreFkWarnings: true
      });
      // ignoreFkWarnings resolves FK advisory only; canonical CDC blocker must still prevent locking
      expect(ms.canLockScope()).toBe(false);
    });

    it('row count displays reflect backend CountAccuracy levels truthfully and unknown is never 0', () => {
      const accountsNode = svc.nodeMap.get('tbl-accounts')!;
      const displayEstimate = svc.getRowCountDisplay(accountsNode);
      expect(displayEstimate.text).toBe('~18.6M');
      expect(displayEstimate.tooltip).toBe('Catalog estimate');

      const viewNode = svc.nodeMap.get('view-account-balances')!;
      const displayUnavailable = svc.getRowCountDisplay(viewNode);
      expect(displayUnavailable.text).toBe('—');
      expect(displayUnavailable.tooltip).toBe('Row count unavailable');
      expect(displayUnavailable.text).not.toBe('0');

      // Test EXACT_ROW_COUNT
      const exactNode = { ...accountsNode, countAccuracy: 'EXACT_ROW_COUNT' as const };
      const displayExact = svc.getRowCountDisplay(exactNode);
      expect(displayExact.text).toBe('18.6M');
      expect(displayExact.tooltip).toBe('Exact row count');

      // Test STATISTICAL_SAMPLE
      const sampleNode = { ...accountsNode, estimatedRows: 1420000, countAccuracy: 'STATISTICAL_SAMPLE' as const };
      const displaySample = svc.getRowCountDisplay(sampleNode);
      expect(displaySample.text).toBe('~1.4M');
      expect(displaySample.tooltip).toBe('Statistical sample estimate');
    });
  });
});
