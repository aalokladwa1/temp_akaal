import { Injectable, signal, computed } from '@angular/core';
import { MigrationDevFixturesAdapter } from '../fixtures/migration-dev-fixtures.adapter';
import {
  MigrationPortfolioItem,
  MigrationAttentionItem,
  PortfolioSummaryCounters,
  ActivityEventItem,
  ProjectItem,
  ConnectionItem,
  MigrationTemplateItem,
  ExecutionPlanViewModel,
  DagNodeViewModel,
  ConfigDomainGroup,
  MigrationMode,
  PhysicalProviderId,
  BasicConfigurationView,
  BasicPerformancePreset,
  TopologyNode,
  SelectedScopeRule,
  TableMappingItem,
  CodeTranspilerItem,
  SourceVerificationResult,
  TargetVerificationResult,
  CollisionPolicyType,
  DiscoveryDepthTier,
  ScopeCompoundRule,
  NetworkRouteType
} from '../models/migration-view.models';

export interface WizardDraftState {
  name: string;
  description: string;
  environment: string;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';
  criticalityTier: 'TIER_1' | 'TIER_2' | 'TIER_3';
  downtimeRequirement: 'ZERO_DOWNTIME' | 'MAINTENANCE_WINDOW' | null;
  tags: string[];
  owner: string;
  projectId?: string;
  mode: MigrationMode;

  sourceConnectionMode: 'SAVED' | 'NEW';
  sourceConnectionId?: string;
  sourceProvider: PhysicalProviderId;
  sourceHost: string;
  sourcePort: number;
  sourceDatabase: string;
  sourceUsername: string;
  sourceSecretRef: string;
  sourceTls: boolean;
  sourceNetworkRoute: NetworkRouteType;
  sourceBastionHost?: string;
  sourceParams?: Record<string, any>;
  sourceSaveToVault?: boolean;
  sourceVerified?: boolean;
  sourceVerificationResult?: SourceVerificationResult;

  targetConnectionMode: 'SAVED' | 'NEW';
  targetConnectionId?: string;
  targetProvider: PhysicalProviderId;
  targetHost: string;
  targetPort: number;
  targetDatabase: string;
  targetUsername: string;
  targetSecretRef: string;
  targetTls: boolean;
  targetNetworkRoute: NetworkRouteType;
  targetBastionHost?: string;
  targetParams?: Record<string, any>;
  targetSaveToVault?: boolean;
  targetVerified?: boolean;
  targetVerificationResult?: TargetVerificationResult;
  collisionPolicy?: CollisionPolicyType;
  productionCollisionAcknowledged?: boolean;
  targetSchema?: string;
  targetAutoCreateSchema?: boolean;
  targetIngestionEngine?: string;

  discoveryDepth: 'QUICK' | 'STANDARD' | 'DEEP' | 'COMPLIANCE';
  discoveryDepthTier?: DiscoveryDepthTier;
  discoveryHash?: string;
  selectedTopologyNodes: string[];
  scopeRules: SelectedScopeRule[];
  compoundRules?: ScopeCompoundRule[];
  includeParentDependencies?: boolean;
  includeDownstreamDependencies?: boolean;
  unresolvedFkCount?: number;
  ignoreFkWarnings?: boolean;
  isScopeSaved?: boolean;
  isScopeFrozen?: boolean;
  isScopeLocked?: boolean;
  hasCdcBlockers?: boolean;
  hasIncrementalBlockers?: boolean;
  scopeFingerprint?: string;
  hasStep5Blockers?: boolean;
  step5BlockerCount?: number;
  step5GovernanceCount?: number;

  activeStudioTab: 'MAPPING' | 'TRANSPILER';
  tableMapping: TableMappingItem;
  codeTranspilerItems: CodeTranspilerItem[];
  selectedTranspilerItemId?: string;

  isAdvancedConfigMode: boolean;
  basicView: BasicConfigurationView;
  configOverrides: Record<string, any>;
  hasInvalidatedConfig: boolean;

  planStale: boolean;
  planVersion: number;
  customBarriersCount: number;

  readinessPassed: boolean;
  requiresQuorumApproval: boolean;

  scheduleChoice: 'RUN_NOW' | 'SCHEDULE' | 'DRAFT';
  scheduledTime?: string;

  currentStep: number;
  completedSteps: Set<number>;
  isDirty: boolean;
  lastAutoSaved?: string;
}

@Injectable({
  providedIn: 'root'
})
export class MigrationUiService {
  private fixtures: MigrationDevFixturesAdapter = new MigrationDevFixturesAdapter();

  // Zero Fake Data by default
  public portfolioMigrations = signal<MigrationPortfolioItem[]>([]);
  public attentionItems = signal<MigrationAttentionItem[]>([]);
  public activityEvents = signal<ActivityEventItem[]>([]);
  public projects = signal<ProjectItem[]>([]);
  public connections = signal<ConnectionItem[]>([]);
  public templates = signal<MigrationTemplateItem[]>([]);

  // 4 Primary Lightweight Status Metrics (2.1 B)
  public summaryCounters = computed<PortfolioSummaryCounters>(() => {
    const list = this.portfolioMigrations();
    return {
      total: list.length,
      active: list.filter(m => m.lifecycleState === 'ACTIVE' || m.lifecycleState === 'RUNNING' || m.lifecycleState === 'GOVERNANCE_PENDING').length,
      scheduled: list.filter(m => m.lifecycleState === 'INITIALIZED').length,
      attentionRequired: list.filter(m => m.attentionCount > 0 || m.requiresApproval).length,
      completed: list.filter(m => m.lifecycleState === 'COMPLETED').length,
      failedInterrupted: list.filter(m => m.lifecycleState === 'FAILED' || m.lifecycleState === 'CANCELLED' || m.lifecycleState === 'INTERRUPTED').length,
      archived: list.filter(m => m.lifecycleState === 'ARCHIVED').length
    };
  });

  // Fleet Filtering
  public filterSearch = signal<string>('');
  public filterStatusMetric = signal<string>('ALL'); // ALL, ACTIVE, ATTENTION, SCHEDULED, COMPLETED
  public filterMode = signal<string>('ALL');
  public filterEnvironment = signal<string>('ALL');

  public filteredMigrations = computed<MigrationPortfolioItem[]>(() => {
    let list = this.portfolioMigrations();
    const q = this.filterSearch().trim().toLowerCase();
    const metric = this.filterStatusMetric();
    const md = this.filterMode();
    const env = this.filterEnvironment();

    if (q) {
      list = list.filter(m =>
        m.name.toLowerCase().includes(q) ||
        m.sourceEngine.toLowerCase().includes(q) ||
        m.targetEngine.toLowerCase().includes(q) ||
        (m.projectName && m.projectName.toLowerCase().includes(q))
      );
    }

    if (metric !== 'ALL') {
      if (metric === 'ACTIVE') list = list.filter(m => m.lifecycleState === 'ACTIVE' || m.lifecycleState === 'RUNNING' || m.lifecycleState === 'GOVERNANCE_PENDING');
      else if (metric === 'ATTENTION') list = list.filter(m => m.attentionCount > 0 || m.requiresApproval);
      else if (metric === 'SCHEDULED') list = list.filter(m => m.lifecycleState === 'INITIALIZED');
      else if (metric === 'COMPLETED') list = list.filter(m => m.lifecycleState === 'COMPLETED');
    }

    if (md !== 'ALL') {
      list = list.filter(m => m.mode === md);
    }

    if (env !== 'ALL') {
      list = list.filter(m => m.environment.toLowerCase() === env.toLowerCase());
    }

    return list;
  });

  // Selected Migration for Cockpit (2.5)
  public selectedMigrationId = signal<string>('mig-002');
  public activeMigration = computed<MigrationPortfolioItem | null>(() => {
    const id = this.selectedMigrationId();
    return this.portfolioMigrations().find(m => m.id === id) || this.portfolioMigrations()[0] || null;
  });

  public activeExecutionPlan = computed<ExecutionPlanViewModel>(() => {
    const mig = this.activeMigration();
    return this.fixtures.getExecutionPlanForMode(mig ? mig.mode : 'M2_BULK_CDC');
  });

  // 9-Step Creation Wizard State (2.2)
  public wizardDraft = signal<WizardDraftState>(this.createDefaultWizardDraft());

  public wizardConfigDomains = computed<ConfigDomainGroup[]>(() => {
    const draft = this.wizardDraft();
    return this.fixtures.getDynamicConfigDomains(draft.mode || 'M1_BULK');
  });

  // Save Lifecycle Signal
  public saveStatus = signal<'SAVED' | 'SAVING' | 'ERROR' | 'DIRTY'>('SAVED');
  public lastSavedTimestamp = signal<string>('Just now');

  // Downstream Invalidation Warnings
  public invalidationNotice = signal<string | null>(null);

  // Custom Barriers Map for Execution Plan
  public draftCustomBarriers = signal<DagNodeViewModel[]>([]);

  // Computed Execution Plan incorporating custom operator-authored Approval Barriers
  public wizardExecutionPlan = computed<ExecutionPlanViewModel>(() => {
    const draft = this.wizardDraft();
    const basePlan = this.fixtures.getExecutionPlanForMode(draft.mode || 'M1_BULK');
    const customBarriers = this.draftCustomBarriers();

    // Adjust pre-existing barrier defaults based on environment
    const isProd = draft.environment === 'Production';
    const mappedNodes: DagNodeViewModel[] = basePlan.nodes.map(n => {
      if (n.isBarrier) {
        return {
          ...n,
          barrierType: isProd ? ('MANDATORY_FOUR_EYES' as const) : ('MAKER_CHECKER' as const),
          requiredSignatures: isProd ? 2 : 1,
          approverRoles: isProd ? ['Lead DBA', 'Security Officer'] : ['Lead DBA']
        };
      }
      return n;
    });

    if (customBarriers.length === 0) {
      return {
        ...basePlan,
        nodes: mappedNodes
      };
    }

    // Merge custom barriers into base plan and connect them
    const nodes = [...mappedNodes];
    const edges = [...basePlan.edges];

    for (const b of customBarriers) {
      if (!nodes.some(n => n.id === b.id)) {
        nodes.push(b);
        if (nodes.length >= 3) {
          const prevNode = nodes[nodes.length - 3];
          const nextNode = nodes[nodes.length - 2];
          edges.push({ id: `e_${prevNode.id}_${b.id}`, source: prevNode.id, target: b.id });
          edges.push({ id: `e_${b.id}_${nextNode.id}`, source: b.id, target: nextNode.id });
        }
      }
    }

    return {
      ...basePlan,
      nodes,
      edges,
      version: basePlan.version + customBarriers.length
    };
  });

  // Global Destructive Action Confirmation Modal State
  public isDestructiveConfirmModalOpen = signal<boolean>(false);
  public dropConfirmationInput = signal<string>('');

  public openDestructiveModal(): void {
    this.dropConfirmationInput.set('');
    this.isDestructiveConfirmModalOpen.set(true);
  }

  public closeDestructiveModal(): void {
    this.isDestructiveConfirmModalOpen.set(false);
    this.dropConfirmationInput.set('');
  }

  public confirmDestructiveAction(): void {
    if (this.dropConfirmationInput().trim() === 'DROP TARGET TABLES') {
      this.updateDraft({
        collisionPolicy: 'DROP_AND_RECREATE',
        productionCollisionAcknowledged: true
      });
      this.closeDestructiveModal();
    }
  }

  public cancelDestructiveAction(): void {
    this.closeDestructiveModal();
    this.updateDraft({
      collisionPolicy: 'FAIL_ON_COLLISION',
      productionCollisionAcknowledged: false
    });
  }

  constructor(fixtures?: MigrationDevFixturesAdapter) {
    if (fixtures) {
      this.fixtures = fixtures;
    }
  }

  public loadDemoFixtures(): void {
    this.portfolioMigrations.set(this.fixtures.getPortfolioMigrations());
    this.attentionItems.set(this.fixtures.getAttentionItems());
    this.activityEvents.set(this.fixtures.getActivityEvents());
    this.projects.set(this.fixtures.getProjects());
    this.connections.set(this.fixtures.getConnections());
    this.templates.set(this.fixtures.getTemplates());
  }

  public createDefaultWizardDraft(): WizardDraftState {
    return {
      name: '',
      description: '',
      environment: '' as any,
      priority: 'NORMAL',
      criticalityTier: 'TIER_2',
      downtimeRequirement: null,
      tags: [],
      owner: 'Aalok Ladwa',
      mode: '' as any,

      sourceConnectionMode: '' as any,
      sourceConnectionId: '',
      sourceProvider: '' as any,
      sourceHost: '',
      sourcePort: 0,
      sourceDatabase: '',
      sourceUsername: '',
      sourceSecretRef: '',
      sourceTls: true,
      sourceNetworkRoute: 'DIRECT',
      sourceVerified: false,
      sourceSaveToVault: false,
      sourceParams: {},

      targetConnectionMode: '' as any,
      targetConnectionId: '',
      targetProvider: '' as any,
      targetHost: '',
      targetPort: 0,
      targetDatabase: '',
      targetUsername: '',
      targetSecretRef: '',
      targetTls: true,
      targetNetworkRoute: 'DIRECT',
      targetBastionHost: '',
      targetParams: {},
      targetSaveToVault: false,
      targetVerified: false,
      collisionPolicy: 'FAIL_ON_COLLISION',
      productionCollisionAcknowledged: false,
      targetSchema: '',
      targetAutoCreateSchema: true,
      targetIngestionEngine: '',

      discoveryDepth: 'STANDARD',
      discoveryDepthTier: undefined,
      discoveryHash: undefined,
      selectedTopologyNodes: [],
      scopeRules: [],
      isScopeSaved: true,

      activeStudioTab: 'MAPPING',
      tableMapping: this.fixtures.getTableMapping(),
      codeTranspilerItems: this.fixtures.getCodeTranspilerItems(),
      selectedTranspilerItemId: 'sct-1',

      isAdvancedConfigMode: false,
      basicView: {
        performancePreset: 'BALANCED',
        derivedMinWorkers: 4,
        derivedMaxWorkers: 16,
        derivedBatchMb: 16,
        durabilityLevel: 'STANDARD',
        spillHeadroomGb: 10,
        cdcLagObjectiveMs: 500,
        validationDepth: 'STANDARD'
      },
      configOverrides: {},
      hasInvalidatedConfig: false,

      planStale: false,
      planVersion: 1,
      customBarriersCount: 0,

      readinessPassed: false,
      requiresQuorumApproval: true,

      scheduleChoice: 'RUN_NOW',
      currentStep: 1,
      completedSteps: new Set([1]),
      isDirty: false,
      lastAutoSaved: 'Just now'
    };
  }

  // Upstream-to-Downstream Invalidation: Mode Change
  public updateWizardMode(newMode: MigrationMode): void {
    const prev = this.wizardDraft();
    if (prev.mode !== newMode) {
      this.wizardDraft.update(d => ({
        ...d,
        mode: newMode,
        hasInvalidatedConfig: true,
        planStale: true,
        isDirty: true,
        planVersion: d.planVersion + 1
      }));
      this.invalidationNotice.set(`Execution mode updated to ${newMode}. Configuration and dynamic DAG plan were refreshed.`);
      this.triggerAutoSave();
    }
  }

  // Upstream-to-Downstream Invalidation: Source Provider Change
  public updateSourceProvider(newProvider: PhysicalProviderId): void {
    const prev = this.wizardDraft();
    if (prev.sourceProvider !== newProvider) {
      this.wizardDraft.update(d => ({
        ...d,
        sourceProvider: newProvider,
        sourceConnectionId: undefined,
        selectedTopologyNodes: [],
        hasInvalidatedConfig: true,
        planStale: true,
        isDirty: true
      }));
      this.invalidationNotice.set(`Source engine changed to ${newProvider}. Target compatibility, scope discovery, mapping, and DAG plan were refreshed.`);
      this.triggerAutoSave();
    }
  }

  // Upstream-to-Downstream Invalidation: Target Provider Change
  public updateTargetProvider(newProvider: PhysicalProviderId): void {
    const prev = this.wizardDraft();
    if (prev.targetProvider !== newProvider) {
      this.wizardDraft.update(d => ({
        ...d,
        targetProvider: newProvider,
        targetConnectionId: undefined,
        hasInvalidatedConfig: true,
        planStale: true,
        isDirty: true
      }));
      this.invalidationNotice.set(`Target engine changed to ${newProvider}. Route compatibility matrix and DDL mapping were refreshed.`);
      this.triggerAutoSave();
    }
  }

  public updateDraft(partial: Partial<WizardDraftState>): void {
    this.wizardDraft.update(d => ({
      ...d,
      ...partial,
      isDirty: true
    }));
    this.triggerAutoSave();
  }

  // Real Auto-Save Lifecycle
  public triggerAutoSave(): void {
    this.saveStatus.set('SAVING');
    setTimeout(() => {
      const nowStr = new Date().toLocaleTimeString();
      this.saveStatus.set('SAVED');
      this.lastSavedTimestamp.set(`Saved at ${nowStr}`);
      this.wizardDraft.update(d => ({
        ...d,
        isDirty: false,
        lastAutoSaved: `Saved at ${nowStr}`
      }));
    }, 400);
  }

  // Drag and Drop Approval Barrier Inserter
  public insertApprovalBarrier(
    position: 'BEFORE' | 'AFTER' | 'BETWEEN',
    targetNodeId: string,
    edgeId?: string
  ): void {
    const barrierId = `barr-custom-${Date.now().toString().slice(-4)}`;
    const newBarrier: DagNodeViewModel = {
      id: barrierId,
      label: `Approval Barrier (${position === 'BETWEEN' ? 'Inter-Stage' : position})`,
      type: 'APPROVAL_BARRIER',
      state: 'BARRIER_WAITING',
      progressPercent: 0,
      isBarrier: true,
      barrierType: 'MANDATORY_FOUR_EYES',
      approverRoles: ['SecOps Lead', 'Lead DBA'],
      requiredSignatures: 2,
      currentSignatures: 0,
      isApproved: false
    };

    this.draftCustomBarriers.update(list => [...list, newBarrier]);
    this.wizardDraft.update(d => ({
      ...d,
      customBarriersCount: d.customBarriersCount + 1,
      isDirty: true
    }));
    this.triggerAutoSave();
  }

  public removeApprovalBarrier(barrierId: string): void {
    this.draftCustomBarriers.update(list => list.filter(b => b.id !== barrierId));
    this.wizardDraft.update(d => ({
      ...d,
      customBarriersCount: Math.max(0, d.customBarriersCount - 1),
      isDirty: true
    }));
    this.triggerAutoSave();
  }

  public updateBarrierConfig(barrierId: string, patch: Partial<DagNodeViewModel>): void {
    this.draftCustomBarriers.update(list =>
      list.map(b => (b.id === barrierId ? { ...b, ...patch } : b))
    );
    this.triggerAutoSave();
  }

  public resetWizardDraft(): void {
    this.draftCustomBarriers.set([]);
    this.invalidationNotice.set(null);
    this.wizardDraft.set(this.createDefaultWizardDraft());
    this.triggerAutoSave();
  }

  // Provider-Aware Topology Generator
  public getTopologyTreeForProvider(provider: PhysicalProviderId): TopologyNode[] {
    switch (provider) {
      case 'Oracle':
        return [
          {
            id: 'instance-cdb',
            label: 'ORCL_CDB (Container Instance)',
            type: 'DATABASE',
            objectCount: 1,
            isSelected: true,
            children: [
              {
                id: 'pdb-orclpdb',
                label: 'ORCLPDB (Pluggable DB)',
                type: 'DATABASE',
                objectCount: 1,
                isSelected: true,
                children: [
                  {
                    id: 'schema-sct',
                    label: 'SCT_DEMO',
                    type: 'SCHEMA',
                    objectCount: 24,
                    estimatedRows: 52400000,
                    estimatedSizeBytes: 42949672960,
                    isSelected: true,
                    children: [
                      {
                        id: 'grp-tables',
                        label: 'Tables (18)',
                        type: 'OBJECT_GROUP',
                        objectCount: 18,
                        isSelected: true,
                        children: [
                          { id: 'tbl-cust', label: 'CUSTOMERS (14.2M rows • 8.6 GB)', type: 'TABLE', estimatedRows: 14200000, estimatedSizeBytes: 8589934592, isSelected: true },
                          { id: 'tbl-acc', label: 'ACCOUNTS (18.6M rows • 12.8 GB)', type: 'TABLE', estimatedRows: 18600000, estimatedSizeBytes: 12884901888, isSelected: true },
                          { id: 'tbl-tx', label: 'TRANSACTIONS (16.8M rows • 17.1 GB)', type: 'TABLE', estimatedRows: 16800000, estimatedSizeBytes: 17179869184, isSelected: true },
                          { id: 'tbl-audit', label: 'AUDIT_LOGS (2.8M rows • 4.3 GB)', type: 'TABLE', estimatedRows: 2800000, estimatedSizeBytes: 4294967296, isSelected: true }
                        ]
                      },
                      {
                        id: 'grp-procs',
                        label: 'Procedures & Packages (6)',
                        type: 'OBJECT_GROUP',
                        objectCount: 6,
                        isSelected: true,
                        children: [
                          { id: 'proc-settle', label: 'P_SETTLE_ACCOUNTS', type: 'OBJECT_GROUP', isSelected: true },
                          { id: 'proc-sub', label: 'P_SUBTYPE_003', type: 'OBJECT_GROUP', isSelected: true },
                          { id: 'fn-calc', label: 'FN_CALCULATE_FEE', type: 'OBJECT_GROUP', isSelected: true }
                        ]
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ];

      case 'MongoDB':
        return [
          {
            id: 'mongo-cluster',
            label: 'rs0 (Replica Set Deployment)',
            type: 'DATABASE',
            objectCount: 1,
            isSelected: true,
            children: [
              {
                id: 'db-inventory',
                label: 'inventory_db',
                type: 'DATABASE',
                objectCount: 5,
                isSelected: true,
                children: [
                  { id: 'coll-orders', label: 'orders (Collection • 8.4M docs)', type: 'COLLECTION', estimatedRows: 8400000, isSelected: true },
                  { id: 'coll-products', label: 'products (Collection • 250k docs)', type: 'COLLECTION', estimatedRows: 250000, isSelected: true },
                  { id: 'coll-users', label: 'users (Collection • 1.2M docs)', type: 'COLLECTION', estimatedRows: 1200000, isSelected: true }
                ]
              }
            ]
          }
        ];

      case 'Apache Kafka':
        return [
          {
            id: 'kafka-cluster',
            label: 'kafka-prod-cluster',
            type: 'DATABASE',
            objectCount: 1,
            isSelected: true,
            children: [
              {
                id: 'topic-orders',
                label: 'orders-cdc-stream (Topic • 12 Partitions)',
                type: 'TOPIC',
                objectCount: 12,
                isSelected: true,
                children: [
                  { id: 'p0', label: 'Partition 0..3 (Hot Key Partition)', type: 'PATH', isSelected: true },
                  { id: 'p4', label: 'Partition 4..7 (Standard Partition)', type: 'PATH', isSelected: true },
                  { id: 'p8', label: 'Partition 8..11 (Standard Partition)', type: 'PATH', isSelected: true }
                ]
              }
            ]
          }
        ];

      case 'Amazon S3':
        return [
          {
            id: 's3-bucket',
            label: 'corp-migration-datalake (S3 Bucket)',
            type: 'BUCKET',
            objectCount: 1,
            isSelected: true,
            children: [
              {
                id: 's3-prefix-raw',
                label: 'raw/databases/oracle_dump/ (Prefix)',
                type: 'PATH',
                objectCount: 64,
                estimatedSizeBytes: 34359738368,
                isSelected: true,
                children: [
                  { id: 's3-obj-1', label: 'customers_part001.parquet (512 MB)', type: 'PATH', isSelected: true },
                  { id: 's3-obj-2', label: 'accounts_part001.parquet (1.2 GB)', type: 'PATH', isSelected: true },
                  { id: 's3-obj-3', label: 'transactions_part001.parquet (2.4 GB)', type: 'PATH', isSelected: true }
                ]
              }
            ]
          }
        ];

      case 'Apache HDFS':
        return [
          {
            id: 'hdfs-root',
            label: 'hdfs://namenode1:9000 (HDFS Root)',
            type: 'DATABASE',
            isSelected: true,
            children: [
              {
                id: 'hdfs-dir-user',
                label: '/user/akaal/migration (Directory)',
                type: 'PATH',
                isSelected: true,
                children: [
                  { id: 'hdfs-f1', label: 'part-m-00000.avro (2.1 GB)', type: 'PATH', isSelected: true },
                  { id: 'hdfs-f2', label: 'part-m-00001.avro (1.8 GB)', type: 'PATH', isSelected: true }
                ]
              }
            ]
          }
        ];

      default: // PostgreSQL, MySQL, SQL Server, etc.
        return [
          {
            id: 'db-app',
            label: 'app_production',
            type: 'DATABASE',
            objectCount: 1,
            isSelected: true,
            children: [
              {
                id: 'schema-public',
                label: 'public',
                type: 'SCHEMA',
                objectCount: 12,
                estimatedRows: 12500000,
                estimatedSizeBytes: 10737418240,
                isSelected: true,
                children: [
                  { id: 'tbl-users', label: 'users (500k rows • 250 MB)', type: 'TABLE', estimatedRows: 500000, isSelected: true },
                  { id: 'tbl-orders', label: 'orders (2.5M rows • 1.8 GB)', type: 'TABLE', estimatedRows: 2500000, isSelected: true },
                  { id: 'tbl-payments', label: 'payments (9.5M rows • 8.6 GB)', type: 'TABLE', estimatedRows: 9500000, isSelected: true }
                ]
              }
            ]
          }
        ];
    }
  }

  // Step Validation Guard
  public isStepValid(stepNum: number): boolean {
    const d = this.wizardDraft();
    switch (stepNum) {
      case 1: {
        const name = (d.name || '').trim();
        const isNameValid = name.length >= 3 && name.length <= 64 && /^[a-zA-Z0-9_ -]+$/.test(name);
        const isEnvValid = ['Production', 'Non-Production', 'Staging', 'Development', 'QA', 'Sandbox', 'Disaster Recovery'].includes(d.environment);
        const isModeValid = ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'].includes(d.mode);
        return isNameValid && isEnvValid && isModeValid;
      }
      case 2: {
        const isVerified = !!d.sourceVerified && !d.sourceVerificationResult?.hasBlockingIssues;
        if (d.sourceConnectionMode === 'SAVED') {
          return !!d.sourceConnectionId && isVerified;
        } else {
          return !!d.sourceProvider && isVerified;
        }
      }
      case 3: {
        const isVerified =
          !!d.targetVerified &&
          !d.targetVerificationResult?.hasBlockingIssues &&
          !d.targetVerificationResult?.compatibility?.isBlocked;
        const isConnSelected =
          d.targetConnectionMode === 'SAVED'
            ? !!d.targetConnectionId
            : !!d.targetProvider;
        const isProd = d.environment === 'Production';
        const hasConflicts = (d.targetVerificationResult?.targetContents?.conflictingObjectsCount || 0) > 0;
        const isDestructive =
          d.collisionPolicy === 'DROP_AND_RECREATE' ||
          d.collisionPolicy === 'TRUNCATE_EXISTING' ||
          d.collisionPolicy === 'TRUNCATE_AND_LOAD';
        const isAckSatisfied =
          !(isProd && hasConflicts && isDestructive) || !!d.productionCollisionAcknowledged;

        // Self-targeting guard
        const isSameEndpoint =
          !!d.sourceHost &&
          !!d.targetHost &&
          d.sourceHost.toLowerCase().trim() === d.targetHost.toLowerCase().trim() &&
          (d.sourceDatabase || '').toLowerCase().trim() === (d.targetDatabase || '').toLowerCase().trim();
        const hasDifferentSchema = !!d.targetSchema && d.targetSchema.trim() !== '' && d.targetSchema.trim() !== (d.sourceDatabase || '').trim();
        const isSelfTargetBlocked = isSameEndpoint && !hasDifferentSchema;

        return isConnSelected && isVerified && isAckSatisfied && !isSelfTargetBlocked;
      }
      case 4: {
        if (d.isScopeFrozen !== undefined) {
          return d.isScopeFrozen;
        }
        if (d.isScopeSaved !== undefined && !d.isScopeSaved) {
          return false;
        }
        const hasNodes = (d.selectedTopologyNodes || []).length > 0;
        const fkResolved = (d.unresolvedFkCount || 0) === 0 || !!d.ignoreFkWarnings;
        return hasNodes && fkResolved;
      }
      case 5: {
        const hasScope = (d.selectedTopologyNodes || []).length > 0;
        return hasScope && !d.hasStep5Blockers;
      }
      case 6:
        return true;
      case 7:
        return true;
      case 8:
        return true;
      case 9:
        return true;
      default:
        return true;
    }
  }

  public loadTemplateIntoDraft(template: MigrationTemplateItem): void {
    this.wizardDraft.update(d => ({
      ...d,
      name: `${template.title} Instance`,
      description: template.description,
      mode: template.compatibleModes[0],
      sourceProvider: template.sourceTypes[0],
      targetProvider: template.targetTypes[0],
      basicView: {
        ...d.basicView,
        performancePreset: template.defaultConfigPreset,
        derivedMaxWorkers: template.recommendedWorkers
      },
      isDirty: true,
      currentStep: 1
    }));
    this.triggerAutoSave();
  }

  public launchDraftMigration(): string {
    const draft = this.wizardDraft();
    const newId = `mig-${Date.now().toString().slice(-4)}`;
    const newMigration: MigrationPortfolioItem = {
      id: newId,
      name: draft.name || `${draft.sourceProvider} to ${draft.targetProvider} Migration`,
      sourceEngine: draft.sourceProvider,
      sourceInstance: `${draft.sourceHost || 'source-db.internal'}:${draft.sourcePort}`,
      targetEngine: draft.targetProvider,
      targetInstance: `${draft.targetHost || 'target-db.internal'}:${draft.targetPort}`,
      mode: draft.mode,
      environment: draft.environment,
      lifecycleState: 'RUNNING',
      currentStage: 'Worker Partitions Initializing',
      progressPercent: 0,
      health: 'HEALTHY',
      attentionCount: 0,
      requiresApproval: draft.customBarriersCount > 0,
      planVersion: `v${draft.planVersion}.0`,
      planFingerprint: 'Pending canonical compilation',
      etaString: 'Calculating',
      updatedAt: new Date().toISOString()
    };

    this.portfolioMigrations.update(list => [newMigration, ...list]);
    this.selectedMigrationId.set(newId);
    return newId;
  }

  public canLockScope(): boolean {
    const d = this.wizardDraft();
    const hasNodes = (d.selectedTopologyNodes || []).length > 0;
    const fkResolved = (d.unresolvedFkCount || 0) === 0 || !!d.ignoreFkWarnings;
    const isCdc = d.mode === 'M2_BULK_CDC' || d.mode === 'M3_CDC';
    const cdcResolved = !isCdc || !d.hasCdcBlockers;
    const isIncremental = d.mode === 'M4_INCREMENTAL';
    const incResolved = !isIncremental || !d.hasIncrementalBlockers;
    return hasNodes && fkResolved && cdcResolved && incResolved;
  }

  public lockScope(): void {
    if (!this.canLockScope()) return;
    const d = this.wizardDraft();
    const snapshotHash = d.discoveryHash || '7f9a2b8e';
    const scopeData = (d.selectedTopologyNodes || []).slice().sort().join(',');
    let hash = 0;
    for (let i = 0; i < scopeData.length; i++) {
      hash = (hash << 5) - hash + scopeData.charCodeAt(i);
      hash |= 0;
    }
    const hex = Math.abs(hash).toString(16).padStart(8, '0');
    const fingerprint = `${hex}a3f89b1c`.slice(0, 16);

    this.updateDraft({
      isScopeLocked: true,
      isScopeFrozen: true,
      isScopeSaved: true,
      scopeFingerprint: fingerprint
    });
  }

  public unlockScope(): void {
    this.updateDraft({
      isScopeLocked: false,
      isScopeFrozen: false,
      isScopeSaved: false
    });
  }
}
