import { Injectable, inject, signal, computed } from '@angular/core';
import { MigrationUiService } from './migration-ui.service';
import { IpcService } from './ipc.service';
import { PhysicalProviderId, DiscoveryDepthTier, MigrationMode } from '../models/migration-view.models';
import {
  DiscoveredResourceNode,
  DiscoveredNodeType,
  DiscoveryStageEvent,
  ScopeSummaryMetrics,
  Step4LifecycleState,
  HierarchyFilterLabels,
  CountAccuracy
} from '../../modules/migration/create/steps/step4-scope.models';

@Injectable({
  providedIn: 'root'
})
export class DiscoveryScopeService {
  private ms: MigrationUiService;
  private ipc: IpcService;

  // Lifecycle & Mode
  public lifecycleState = signal<Step4LifecycleState>('DEPTH_SELECTION');
  public currentDepth = signal<DiscoveryDepthTier>('STANDARD');
  public currentEstateProvider = signal<PhysicalProviderId | null>(null);
  public isCancelled = signal<boolean>(false);
  public isCancelling = signal<boolean>(false);
  public isDriftDetected = signal<boolean>(false);
  public errorMessage = signal<string | null>(null);

  // Discovery Job Progress & Elapsed Time
  public elapsedSeconds = signal<number>(0);
  public discoveryStages = signal<DiscoveryStageEvent[]>([]);
  private timerInterval?: any;

  // Discovered Tree Hierarchy Data
  public rootNodes = signal<DiscoveredResourceNode[]>([]);
  public nodeMap = new Map<string, DiscoveredResourceNode>();
  public expandedNodeIds = signal<Set<string>>(new Set<string>());

  // Filtering signals
  public searchQuery = signal<string>('');
  public selectedLevel1Filter = signal<string>('ALL');
  public selectedLevel2Filter = signal<string>('ALL');
  public selectedTypeFilter = signal<string>('ALL');

  constructor(ms?: MigrationUiService, ipc?: IpcService) {
    try {
      this.ms = ms || inject(MigrationUiService);
    } catch {
      this.ms = ms || new MigrationUiService();
    }
    try {
      this.ipc = ipc || inject(IpcService);
    } catch {
      this.ipc = ipc || new IpcService();
    }
    this.syncInitialStateFromDraft();
  }

  /**
   * Initializes or restores Step 4 state based on draft data
   */
  public syncInitialStateFromDraft(): void {
    const draft = this.ms.wizardDraft();
    if (draft.discoveryDepthTier) {
      this.currentDepth.set(draft.discoveryDepthTier);
    }

    if (draft.discoveryHash && this.rootNodes().length === 0) {
      // Restore previously discovered state
      this.generateDiscoveredEstate(draft.sourceProvider, this.currentDepth(), draft.mode);
      this.lifecycleState.set('SCOPE_WORKBENCH');
    } else if (this.rootNodes().length === 0) {
      this.lifecycleState.set('DEPTH_SELECTION');
    }
  }

  // ==========================================================================
  // DISCOVERY LIFECYCLE CONTROLLER
  // ==========================================================================

  public startDiscovery(depth: DiscoveryDepthTier): void {
    this.currentDepth.set(depth);
    this.lifecycleState.set('DISCOVERING');
    this.isCancelled.set(false);
    this.isCancelling.set(false);
    this.errorMessage.set(null);
    this.elapsedSeconds.set(0);

    const initialStages: DiscoveryStageEvent[] = [
      { id: 'identity', label: 'Source identity', status: 'RUNNING' },
      { id: 'namespace', label: 'Namespace discovery', status: 'PENDING' },
      { id: 'inventory', label: 'Object inventory', status: 'PENDING' },
      { id: 'structure', label: 'Structural metadata', status: 'PENDING' },
      { id: 'capability', label: 'Capability analysis', status: 'PENDING' }
    ];
    this.discoveryStages.set(initialStages);

    const startTime = Date.now();
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds.set(Number(((Date.now() - startTime) / 1000).toFixed(1)));
    }, 100);

    // Run stage-aware progression
    this.runStageProgression(depth);
  }

  private async runStageProgression(depth: DiscoveryDepthTier): Promise<void> {
    try {
      // Stage 1: Identity
      await this.delay(200);
      if (this.isCancelled()) return;
      this.updateStage('identity', 'COMPLETED', 120, undefined, 'Connected and authenticated');
      this.updateStage('namespace', 'RUNNING');

      // Stage 2: Namespace
      await this.delay(250);
      if (this.isCancelled()) return;
      this.updateStage('namespace', 'COMPLETED', 240, undefined, 'Catalog namespaces identified');
      this.updateStage('inventory', 'RUNNING');

      // Stage 3: Inventory
      await this.delay(300);
      if (this.isCancelled()) return;
      const count = depth === 'QUICK' ? 420 : depth === 'STANDARD' ? 1420 : 3890;
      this.updateStage('inventory', 'COMPLETED', 310, count, `${count.toLocaleString()} resources discovered`);
      this.updateStage('structure', 'RUNNING');

      // Stage 4: Structure
      await this.delay(250);
      if (this.isCancelled()) return;
      this.updateStage('structure', 'COMPLETED', 280, undefined, 'Columns, keys, and constraints extracted');
      this.updateStage('capability', 'RUNNING');

      // Stage 5: Capability
      await this.delay(200);
      if (this.isCancelled()) return;
      this.updateStage('capability', 'COMPLETED', 150, undefined, 'CDC and eligibility verified');

      // Complete discovery
      if (this.timerInterval) clearInterval(this.timerInterval);
      const draft = this.ms.wizardDraft();
      this.generateDiscoveredEstate(draft.sourceProvider, depth, draft.mode);

      const snapshotHash = '7f9a2b8e';
      const initialSelected = this.getMigratableLeafNodes()
        .filter(n => n.isSelected)
        .map(n => n.id);

      this.ms.updateDraft({
        discoveryDepth: depth === 'SHALLOW' || depth === 'FULL_WITH_SAMPLING' ? 'STANDARD' : depth,
        discoveryDepthTier: depth,
        discoveryHash: snapshotHash,
        selectedTopologyNodes: initialSelected,
        isScopeSaved: true,
        hasCdcBlockers: this.computeSelectedBlockerCount() > 0
      });

      this.lifecycleState.set('SCOPE_WORKBENCH');
    } catch (err: any) {
      if (this.timerInterval) clearInterval(this.timerInterval);
      this.errorMessage.set(err?.message || 'Source discovery encountered an unexpected interruption.');
      this.lifecycleState.set('FAILURE');
    }
  }

  public cancelDiscovery(): void {
    if (this.lifecycleState() !== 'DISCOVERING') return;
    this.isCancelling.set(true);
    setTimeout(() => {
      this.isCancelled.set(true);
      this.isCancelling.set(false);
      if (this.timerInterval) clearInterval(this.timerInterval);
      this.lifecycleState.set('DEPTH_SELECTION');
    }, 200);
  }

  public retryDiscovery(): void {
    this.startDiscovery(this.currentDepth());
  }

  public returnToDepthSelection(): void {
    this.lifecycleState.set('DEPTH_SELECTION');
    this.ms.updateDraft({
      discoveryHash: undefined,
      isScopeLocked: false,
      isScopeFrozen: false
    });
  }

  public setDriftDetected(val: boolean): void {
    this.isDriftDetected.set(val);
    if (val) {
      this.ms.updateDraft({ isScopeFrozen: false, isScopeLocked: false });
    }
  }

  public refreshDiscoveryAfterDrift(): void {
    this.isDriftDetected.set(false);
    this.startDiscovery(this.currentDepth());
  }

  private updateStage(
    stageId: string,
    status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED',
    durationMs?: number,
    itemsCount?: number,
    detail?: string
  ): void {
    this.discoveryStages.update(stages =>
      stages.map(s => (s.id === stageId ? { ...s, status, durationMs, itemsCount, detail } : s))
    );
  }

  // ==========================================================================
  // DISCOVERED ESTATE GENERATOR (PROVIDER-NEUTRAL FOR 28 PHYSICAL CONNECTORS)
  // ==========================================================================

  public generateDiscoveredEstate(
    provider: PhysicalProviderId,
    depth: DiscoveryDepthTier,
    mode: MigrationMode
  ): void {
    this.currentEstateProvider.set(provider);
    this.nodeMap.clear();
    const isCdcMode = mode === 'M2_BULK_CDC' || mode === 'M3_CDC';

    let nodes: DiscoveredResourceNode[] = [];

    switch (provider) {
      case 'MongoDB':
        nodes = this.createMongoHierarchy(depth, isCdcMode);
        break;
      case 'Apache Kafka':
      case 'Amazon Kinesis':
      case 'Azure Event Hubs':
      case 'Google Cloud Pub/Sub':
        nodes = this.createStreamingHierarchy(provider, depth);
        break;
      case 'Amazon S3':
      case 'Google Cloud Storage':
      case 'Azure Blob Storage':
      case 'MinIO':
      case 'Apache HDFS':
        nodes = this.createStorageHierarchy(provider, depth);
        break;
      default:
        // Relational default (Oracle, PostgreSQL, MySQL, SQL Server, IBM Db2, etc.)
        nodes = this.createRelationalHierarchy(provider, depth, isCdcMode);
        break;
    }

    this.rootNodes.set(nodes);
    this.indexNodes(nodes);

    // By default expand down to object groups so leaf resources are immediately visible
    const initialExpanded = new Set<string>();
    nodes.forEach(root => {
      initialExpanded.add(root.id);
      root.children?.forEach(c => {
        initialExpanded.add(c.id);
        c.children?.forEach(g => initialExpanded.add(g.id));
      });
    });
    this.expandedNodeIds.set(initialExpanded);

    // Initial parent tri-state reconciliation
    this.reconcileAllParentStates();
  }

  private createRelationalHierarchy(
    provider: PhysicalProviderId,
    depth: DiscoveryDepthTier,
    isCdcMode: boolean
  ): DiscoveredResourceNode[] {
    const isOracle = provider === 'Oracle';
    const rootLabel = isOracle ? 'RAC-PROD-01' : `${provider.toLowerCase()}_production`;

    return [
      {
        id: 'inst-prod-01',
        name: rootLabel,
        type: 'INSTANCE',
        typeLabel: 'Instance',
        status: 'READY',
        isSelected: true,
        isMigratable: false,
        children: [
          {
            id: 'schema-core-banking',
            name: 'CORE_BANKING',
            type: 'SCHEMA',
            typeLabel: 'Schema',
            namespace: 'CORE_BANKING',
            status: 'READY',
            isSelected: true,
            isMigratable: false,
            children: [
              {
                id: 'grp-tables-core',
                name: 'Tables (3)',
                type: 'OBJECT_GROUP',
                typeLabel: 'Group',
                namespace: 'CORE_BANKING',
                status: 'READY',
                isSelected: true,
                isMigratable: false,
                children: [
                  {
                    id: 'tbl-accounts',
                    name: 'ACCOUNTS',
                    type: 'TABLE',
                    typeLabel: 'Table',
                    namespace: 'CORE_BANKING',
                    estimatedRows: 18600000,
                    countAccuracy: 'CATALOG_ESTIMATE',
                    estimatedSizeBytes: 13743895347, // 12.8 GB
                    status: 'READY',
                    secondaryTraits: ['Partitioned', 'PK: ACC_ID'],
                    isSelected: true,
                    isMigratable: true
                  },
                  {
                    id: 'tbl-customers',
                    name: 'CUSTOMERS',
                    type: 'TABLE',
                    typeLabel: 'Table',
                    namespace: 'CORE_BANKING',
                    estimatedRows: 14200000,
                    countAccuracy: 'CATALOG_ESTIMATE',
                    estimatedSizeBytes: 9234169856, // 8.6 GB
                    status: 'READY',
                    secondaryTraits: ['Identity', 'PK: CUST_ID'],
                    isSelected: true,
                    isMigratable: true
                  },
                  {
                    id: 'tbl-transactions',
                    name: 'TRANSACTIONS',
                    type: 'TABLE',
                    typeLabel: 'Table',
                    namespace: 'CORE_BANKING',
                    estimatedRows: 42700000,
                    countAccuracy: 'CATALOG_ESTIMATE',
                    estimatedSizeBytes: 32857423872, // 30.6 GB
                    status: isCdcMode ? 'BLOCKED' : 'READY',
                    statusReason: isCdcMode
                      ? 'CDC eligibility requirement not satisfied (missing supplemental logging for LOB column)'
                      : undefined,
                    secondaryTraits: ['LOB', 'Partitioned'],
                    isSelected: true,
                    isMigratable: true
                  }
                ]
              },
              {
                id: 'grp-views-core',
                name: 'Views (1)',
                type: 'OBJECT_GROUP',
                typeLabel: 'Group',
                namespace: 'CORE_BANKING',
                status: 'READY',
                isSelected: true,
                isMigratable: false,
                children: [
                  {
                    id: 'view-account-balances',
                    name: 'V_ACCOUNT_BALANCES',
                    type: 'VIEW',
                    typeLabel: 'View',
                    namespace: 'CORE_BANKING',
                    estimatedRows: null,
                    countAccuracy: 'UNAVAILABLE',
                    estimatedSizeBytes: null,
                    status: 'READY',
                    secondaryTraits: ['Mat-View'],
                    isSelected: true,
                    isMigratable: true
                  }
                ]
              },
              {
                id: 'grp-procs-core',
                name: 'Procedures (1)',
                type: 'OBJECT_GROUP',
                typeLabel: 'Group',
                namespace: 'CORE_BANKING',
                status: 'READY',
                isSelected: true,
                isMigratable: false,
                children: [
                  {
                    id: 'proc-close-account',
                    name: 'P_CLOSE_ACCOUNT',
                    type: 'PROCEDURE',
                    typeLabel: 'Proc',
                    namespace: 'CORE_BANKING',
                    estimatedRows: null,
                    countAccuracy: 'UNAVAILABLE',
                    estimatedSizeBytes: 46080, // 45 KB
                    status: 'READY',
                    isSelected: true,
                    isMigratable: true
                  }
                ]
              }
            ]
          },
          {
            id: 'schema-audit-archive',
            name: 'AUDIT_ARCHIVE',
            type: 'SCHEMA',
            typeLabel: 'Schema',
            namespace: 'AUDIT_ARCHIVE',
            status: 'READY',
            isSelected: false,
            isMigratable: false,
            children: [
              {
                id: 'grp-tables-audit',
                name: 'Tables (1)',
                type: 'OBJECT_GROUP',
                typeLabel: 'Group',
                namespace: 'AUDIT_ARCHIVE',
                status: 'READY',
                isSelected: false,
                isMigratable: false,
                children: [
                  {
                    id: 'tbl-audit-events',
                    name: 'AUDIT_EVENTS',
                    type: 'TABLE',
                    typeLabel: 'Table',
                    namespace: 'AUDIT_ARCHIVE',
                    estimatedRows: 9100000,
                    countAccuracy: 'CATALOG_ESTIMATE',
                    estimatedSizeBytes: 4402341478, // 4.1 GB
                    status: 'READY',
                    statusReason: 'Referenced by selected resource (ACCOUNTS.AUDIT_REF)',
                    secondaryTraits: ['Partitioned', 'External'],
                    isSelected: false,
                    isDependencyReference: true,
                    isMigratable: true
                  }
                ]
              }
            ]
          }
        ]
      }
    ];
  }

  private createMongoHierarchy(depth: DiscoveryDepthTier, isCdcMode: boolean): DiscoveredResourceNode[] {
    return [
      {
        id: 'mongo-cluster-01',
        name: 'rs0.internal:27017',
        type: 'INSTANCE',
        typeLabel: 'Cluster',
        status: 'READY',
        isSelected: true,
        isMigratable: false,
        children: [
          {
            id: 'mongo-db-inventory',
            name: 'inventory_db',
            type: 'DATABASE',
            typeLabel: 'Database',
            namespace: 'inventory_db',
            status: 'READY',
            isSelected: true,
            isMigratable: false,
            children: [
              {
                id: 'coll-orders',
                name: 'orders',
                type: 'COLLECTION',
                typeLabel: 'Collection',
                namespace: 'inventory_db',
                estimatedRows: 8400000,
                countAccuracy: 'CATALOG_ESTIMATE',
                estimatedSizeBytes: 5583457484, // 5.2 GB
                status: 'READY',
                secondaryTraits: ['Sharded', 'Indexes: 4'],
                isSelected: true,
                isMigratable: true
              },
              {
                id: 'coll-products',
                name: 'products',
                type: 'COLLECTION',
                typeLabel: 'Collection',
                namespace: 'inventory_db',
                estimatedRows: 250000,
                countAccuracy: 'EXACT_ROW_COUNT',
                estimatedSizeBytes: 440401920, // 420 MB
                status: 'READY',
                secondaryTraits: ['Indexes: 2'],
                isSelected: true,
                isMigratable: true
              },
              {
                id: 'coll-change-log',
                name: 'oplog_tail_archive',
                type: 'COLLECTION',
                typeLabel: 'Collection',
                namespace: 'inventory_db',
                estimatedRows: 15600000,
                countAccuracy: 'CATALOG_ESTIMATE',
                estimatedSizeBytes: 13315582361, // 12.4 GB
                status: isCdcMode ? 'BLOCKED' : 'READY',
                statusReason: isCdcMode ? 'Oplog retention exceeded or capped collection unsupported in CDC' : undefined,
                secondaryTraits: ['Capped'],
                isSelected: true,
                isMigratable: true
              }
            ]
          }
        ]
      }
    ];
  }

  private createStreamingHierarchy(provider: PhysicalProviderId, depth: DiscoveryDepthTier): DiscoveredResourceNode[] {
    return [
      {
        id: 'kafka-cluster-01',
        name: `${provider.toLowerCase()}-prod-cluster`,
        type: 'INSTANCE',
        typeLabel: 'Cluster',
        status: 'READY',
        isSelected: true,
        isMigratable: false,
        children: [
          {
            id: 'topic-orders-cdc',
            name: 'orders-cdc-stream',
            type: 'TOPIC',
            typeLabel: 'Topic',
            namespace: 'orders-cdc-stream',
            estimatedRows: 12500000,
            countAccuracy: 'CATALOG_ESTIMATE',
            estimatedSizeBytes: 10737418240, // 10 GB
            status: 'READY',
            secondaryTraits: ['12 Partitions', 'Avro'],
            isSelected: true,
            isMigratable: true,
            children: [
              {
                id: 'part-0-3',
                name: 'Partitions 0..3',
                type: 'PARTITION',
                typeLabel: 'Partition',
                estimatedRows: null,
                countAccuracy: 'UNAVAILABLE',
                status: 'READY',
                isSelected: true,
                isMigratable: true
              },
              {
                id: 'part-4-7',
                name: 'Partitions 4..7',
                type: 'PARTITION',
                typeLabel: 'Partition',
                estimatedRows: null,
                countAccuracy: 'UNAVAILABLE',
                status: 'READY',
                isSelected: true,
                isMigratable: true
              }
            ]
          },
          {
            id: 'topic-payments-cdc',
            name: 'payments-cdc-stream',
            type: 'TOPIC',
            typeLabel: 'Topic',
            namespace: 'payments-cdc-stream',
            estimatedRows: 8200000,
            countAccuracy: 'CATALOG_ESTIMATE',
            estimatedSizeBytes: 6442450944, // 6 GB
            status: 'READY',
            secondaryTraits: ['8 Partitions', 'JSON'],
            isSelected: true,
            isMigratable: true
          }
        ]
      }
    ];
  }

  private createStorageHierarchy(provider: PhysicalProviderId, depth: DiscoveryDepthTier): DiscoveredResourceNode[] {
    return [
      {
        id: 'storage-endpoint-01',
        name: 'us-east-1.storage.internal',
        type: 'INSTANCE',
        typeLabel: 'Endpoint',
        status: 'READY',
        isSelected: true,
        isMigratable: false,
        children: [
          {
            id: 'bucket-datalake',
            name: 'corp-migration-datalake',
            type: 'BUCKET',
            typeLabel: 'Bucket',
            namespace: 'corp-migration-datalake',
            status: 'READY',
            isSelected: true,
            isMigratable: false,
            children: [
              {
                id: 'prefix-raw-dump',
                name: 'raw/databases/oracle_dump/',
                type: 'PREFIX',
                typeLabel: 'Prefix',
                status: 'READY',
                isSelected: true,
                isMigratable: false,
                children: [
                  {
                    id: 'obj-customers-parquet',
                    name: 'customers_part001.parquet',
                    type: 'OBJECT',
                    typeLabel: 'Object',
                    estimatedRows: 1420000,
                    countAccuracy: 'STATISTICAL_SAMPLE',
                    estimatedSizeBytes: 536870912, // 512 MB
                    status: 'READY',
                    secondaryTraits: ['Parquet', 'Snappy'],
                    isSelected: true,
                    isMigratable: true
                  },
                  {
                    id: 'obj-accounts-parquet',
                    name: 'accounts_part001.parquet',
                    type: 'OBJECT',
                    typeLabel: 'Object',
                    estimatedRows: 1860000,
                    countAccuracy: 'STATISTICAL_SAMPLE',
                    estimatedSizeBytes: 1288490188, // 1.2 GB
                    status: 'READY',
                    secondaryTraits: ['Parquet', 'Snappy'],
                    isSelected: true,
                    isMigratable: true
                  }
                ]
              }
            ]
          }
        ]
      }
    ];
  }

  private indexNodes(nodes: DiscoveredResourceNode[], parentId?: string): void {
    nodes.forEach(n => {
      n.parentId = parentId;
      this.nodeMap.set(n.id, n);
      if (n.children && n.children.length > 0) {
        this.indexNodes(n.children, n.id);
      }
    });
  }

  // ==========================================================================
  // TREE SELECTION & TRI-STATE ENGINE
  // ==========================================================================

  public toggleNodeSelection(nodeId: string): void {
    const node = this.nodeMap.get(nodeId);
    if (!node) return;

    const newSelected = !this.isNodeFullySelected(node);
    this.applySelectionRecursive(node, newSelected);
    this.reconcileAllParentStates();
    this.notifyDraftUpdated();
  }

  private applySelectionRecursive(node: DiscoveredResourceNode, selected: boolean): void {
    node.isSelected = selected;
    if (node.children) {
      node.children.forEach(c => this.applySelectionRecursive(c, selected));
    }
  }

  public isNodeFullySelected(node: DiscoveredResourceNode): boolean {
    if (!node.children || node.children.length === 0) {
      return !!node.isSelected;
    }
    const migratableLeaves = this.getMigratableDescendants(node);
    if (migratableLeaves.length === 0) return !!node.isSelected;
    return migratableLeaves.every(l => l.isSelected);
  }

  public isNodeIndeterminate(node: DiscoveredResourceNode): boolean {
    if (!node.children || node.children.length === 0) return false;
    const migratableLeaves = this.getMigratableDescendants(node);
    if (migratableLeaves.length === 0) return false;
    const selectedCount = migratableLeaves.filter(l => l.isSelected).length;
    return selectedCount > 0 && selectedCount < migratableLeaves.length;
  }

  private reconcileAllParentStates(): void {
    // Post-order evaluation from root
    this.rootNodes().forEach(r => this.reconcileNodeState(r));
  }

  private reconcileNodeState(node: DiscoveredResourceNode): void {
    if (node.children && node.children.length > 0) {
      node.children.forEach(c => this.reconcileNodeState(c));
      const migratableLeaves = this.getMigratableDescendants(node);
      if (migratableLeaves.length > 0) {
        node.isSelected = migratableLeaves.some(l => l.isSelected);
      }
    }
  }

  public getMigratableDescendants(node: DiscoveredResourceNode): DiscoveredResourceNode[] {
    const results: DiscoveredResourceNode[] = [];
    const traverse = (n: DiscoveredResourceNode) => {
      if (n.isMigratable) {
        results.push(n);
      }
      if (n.children) {
        n.children.forEach(traverse);
      }
    };
    traverse(node);
    return results;
  }

  public getMigratableLeafNodes(): DiscoveredResourceNode[] {
    const list: DiscoveredResourceNode[] = [];
    this.nodeMap.forEach(n => {
      if (n.isMigratable) list.push(n);
    });
    return list;
  }

  // Skip & Include actions
  public skipBlockedResource(nodeId: string): void {
    const node = this.nodeMap.get(nodeId);
    if (!node) return;

    // Skip means: EXCLUDE from migration scope (isSelected = false)
    node.isSelected = false;
    this.reconcileAllParentStates();
    this.notifyDraftUpdated();
  }

  public includeDependencyResource(nodeId: string): void {
    const node = this.nodeMap.get(nodeId);
    if (!node) return;

    // Include means: explicitly select in scope
    node.isSelected = true;
    this.reconcileAllParentStates();
    this.notifyDraftUpdated();
  }

  // Bulk Selection Operations
  public selectAll(): void {
    this.rootNodes().forEach(r => this.applySelectionRecursive(r, true));
    this.reconcileAllParentStates();
    this.notifyDraftUpdated();
  }

  public deselectAll(): void {
    this.rootNodes().forEach(r => this.applySelectionRecursive(r, false));
    this.reconcileAllParentStates();
    this.notifyDraftUpdated();
  }

  public selectVisible(visibleIds: string[]): void {
    visibleIds.forEach(id => {
      const node = this.nodeMap.get(id);
      if (node && node.isMigratable) {
        node.isSelected = true;
      }
    });
    this.reconcileAllParentStates();
    this.notifyDraftUpdated();
  }

  public deselectVisible(visibleIds: string[]): void {
    visibleIds.forEach(id => {
      const node = this.nodeMap.get(id);
      if (node && node.isMigratable) {
        node.isSelected = false;
      }
    });
    this.reconcileAllParentStates();
    this.notifyDraftUpdated();
  }

  public selectNamespace(namespace: string): void {
    this.getMigratableLeafNodes().forEach(n => {
      if (n.namespace === namespace) {
        n.isSelected = true;
      }
    });
    this.reconcileAllParentStates();
    this.notifyDraftUpdated();
  }

  // Expand / Collapse Operations
  public toggleNodeExpansion(nodeId: string): void {
    this.expandedNodeIds.update(set => {
      const copy = new Set(set);
      if (copy.has(nodeId)) copy.delete(nodeId);
      else copy.add(nodeId);
      return copy;
    });
  }

  public expandAll(): void {
    const all = new Set<string>();
    this.nodeMap.forEach(n => {
      if (n.children && n.children.length > 0) all.add(n.id);
    });
    this.expandedNodeIds.set(all);
  }

  public collapseAll(): void {
    this.expandedNodeIds.set(new Set<string>());
  }

  public expandVisible(visibleIds: string[]): void {
    this.expandedNodeIds.update(set => {
      const copy = new Set(set);
      visibleIds.forEach(id => {
        const node = this.nodeMap.get(id);
        if (node && node.children && node.children.length > 0) copy.add(id);
      });
      return copy;
    });
  }

  // ==========================================================================
  // METRICS & COMPUTED PROPERTIES
  // ==========================================================================

  public computeSummaryMetrics(): ScopeSummaryMetrics {
    const leaves = this.getMigratableLeafNodes();
    const selectedLeaves = leaves.filter(l => l.isSelected);

    // Schemas calculation
    const allSchemas = new Set<string>();
    const selectedSchemas = new Set<string>();
    leaves.forEach(l => {
      if (l.namespace) {
        allSchemas.add(l.namespace);
        if (l.isSelected) selectedSchemas.add(l.namespace);
      }
    });

    // Volume calculation
    let totalBytes = 0;
    selectedLeaves.forEach(l => {
      if (typeof l.estimatedSizeBytes === 'number') {
        totalBytes += l.estimatedSizeBytes;
      }
    });

    const isSchemaOnly = this.ms.wizardDraft().mode === 'M6_SCHEMA_ONLY';
    const volumeFormatted = isSchemaOnly
      ? '— (Inapplicable)'
      : this.formatBytes(totalBytes);

    const primaryType = this.getPrimaryObjectTypeLabel();
    const primarySelected = selectedLeaves.filter(
      l => l.type === 'TABLE' || l.type === 'COLLECTION' || l.type === 'TOPIC' || l.type === 'OBJECT'
    ).length;

    const selectedBlockers = selectedLeaves.filter(l => l.status === 'BLOCKED').length;
    const selectedAdvisories = selectedLeaves.filter(l => l.status === 'ADVISORY').length;
    const excludedReferenced = leaves.filter(l => !l.isSelected && l.isDependencyReference).length;

    return {
      schemasSelected: selectedSchemas.size,
      schemasTotal: allSchemas.size,
      objectsSelected: selectedLeaves.length,
      objectsTotal: leaves.length,
      primaryTypeLabel: primaryType,
      primarySelected,
      volumeSelectedBytes: totalBytes,
      volumeFormatted,
      isVolumeApplicable: !isSchemaOnly,
      selectedBlockersCount: selectedBlockers,
      selectedAdvisoriesCount: selectedAdvisories,
      excludedReferencedCount: excludedReferenced
    };
  }

  public computeSelectedBlockerCount(): number {
    return this.getMigratableLeafNodes().filter(l => l.isSelected && l.status === 'BLOCKED').length;
  }

  public getPrimaryObjectTypeLabel(provider?: PhysicalProviderId): string {
    const p = provider || this.currentEstateProvider() || this.ms.wizardDraft().sourceProvider;
    switch (p) {
      case 'MongoDB':
        return 'Collections';
      case 'Apache Kafka':
      case 'Amazon Kinesis':
      case 'Azure Event Hubs':
      case 'Google Cloud Pub/Sub':
        return 'Topics';
      case 'Amazon S3':
      case 'Google Cloud Storage':
      case 'Azure Blob Storage':
      case 'MinIO':
      case 'Apache HDFS':
        return 'Objects';
      default:
        return 'Tables';
    }
  }

  public getHierarchyFilterLabels(provider?: PhysicalProviderId): HierarchyFilterLabels {
    const p = provider || this.currentEstateProvider() || this.ms.wizardDraft().sourceProvider;
    switch (p) {
      case 'MongoDB':
        return { level1Label: 'Cluster', level2Label: 'Database', primaryObjectLabel: 'Collections' };
      case 'Apache Kafka':
      case 'Amazon Kinesis':
      case 'Azure Event Hubs':
      case 'Google Cloud Pub/Sub':
        return { level1Label: 'Cluster', level2Label: 'Topic', primaryObjectLabel: 'Partitions' };
      case 'Amazon S3':
      case 'Google Cloud Storage':
      case 'Azure Blob Storage':
      case 'MinIO':
      case 'Apache HDFS':
        return { level1Label: 'Endpoint', level2Label: 'Bucket', primaryObjectLabel: 'Objects' };
      default:
        return { level1Label: 'Instance', level2Label: 'Schema', primaryObjectLabel: 'Tables' };
    }
  }

  public getAvailableTypesInCurrentEstate(): string[] {
    const types = new Set<string>();
    this.nodeMap.forEach(n => {
      if (n.typeLabel) types.add(n.typeLabel);
    });
    return Array.from(types).sort();
  }

  public getLevel1FilterOptions(): string[] {
    const list = new Set<string>();
    this.rootNodes().forEach(r => list.add(r.name));
    return Array.from(list);
  }

  public getLevel2FilterOptions(): string[] {
    const list = new Set<string>();
    this.rootNodes().forEach(r => {
      r.children?.forEach(c => list.add(c.name));
    });
    return Array.from(list);
  }

  private notifyDraftUpdated(): void {
    const selectedNodes = this.getMigratableLeafNodes()
      .filter(l => l.isSelected)
      .map(l => l.id);

    const blockerCount = this.computeSelectedBlockerCount();

    this.ms.updateDraft({
      selectedTopologyNodes: selectedNodes,
      hasCdcBlockers: blockerCount > 0,
      isScopeSaved: true
    });
  }

  public formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }

  public formatNumber(num: number | null | undefined): string {
    if (num === null || num === undefined) return '—';
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  }

  public getRowCountDisplay(node: DiscoveredResourceNode): { text: string; tooltip: string } {
    if (node.estimatedRows === null || node.estimatedRows === undefined || node.countAccuracy === 'UNAVAILABLE') {
      return { text: '—', tooltip: 'Row count unavailable' };
    }
    const formatted = this.formatNumber(node.estimatedRows);
    switch (node.countAccuracy) {
      case 'EXACT_ROW_COUNT':
        return { text: formatted, tooltip: 'Exact row count' };
      case 'STATISTICAL_SAMPLE':
        return { text: `~${formatted}`, tooltip: 'Statistical sample estimate' };
      case 'CATALOG_ESTIMATE':
      default:
        return { text: `~${formatted}`, tooltip: 'Catalog estimate' };
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
