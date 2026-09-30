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

    if (this.rootNodes().length > 0) {
      this.lifecycleState.set('SCOPE_WORKBENCH');
    } else {
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

  private runStageProgression(depth: DiscoveryDepthTier): void {
    try {
      if (this.isCancelled()) return;
      const draft = this.ms.wizardDraft();
      this.lifecycleState.set('DISCOVERING');
      const migId = draft.migrationId || 'mig-draft';

      this.ipc.invoke('pipeline', 'migration.discover', {
        migration_id: migId,
        depth: depth,
        connection_id: draft.sourceConnectionId,
        source_connection_id: draft.sourceConnectionId,
        provider_id: draft.sourceProvider,
        source_provider: draft.sourceProvider,
        host: draft.sourceHost,
        port: draft.sourcePort,
        database: draft.sourceDatabase,
        service_name: draft.sourceDatabase,
        username: draft.sourceUsername,
        password: draft.sourceSecretRef || (draft.sourceParams ? (draft.sourceParams as any)['password'] : undefined),
        secret_ref: draft.sourceSecretRef || (draft.sourceParams ? (draft.sourceParams as any)['password'] : undefined),
      }).then((resp) => {
        if (this.timerInterval) clearInterval(this.timerInterval);
        if (this.isCancelled()) return;
        if (resp && resp.status === 'SUCCESS' && resp.data) {
          const data = resp.data;
          this.updateStage('identity', 'COMPLETED', 0, undefined, 'Connected and authenticated');
          this.updateStage('namespace', 'COMPLETED', 0, undefined, 'Catalog namespaces identified');
          this.applyDiscoveredEstateFromBackend(data, draft.sourceProvider, depth, draft.mode);
          const realCount = this.getMigratableLeafNodes().length;
          this.updateStage('inventory', 'COMPLETED', 0, realCount, `${realCount.toLocaleString()} resources discovered`);
          this.updateStage('structure', 'COMPLETED', 0, undefined, 'Columns, keys, and constraints extracted');
          this.updateStage('capability', 'COMPLETED', 0, undefined, 'CDC and eligibility verified');
          const initialSelected = this.getMigratableLeafNodes().filter(n => n.isSelected).map(n => n.id);
          this.ms.updateDraft({
            discoveryDepth: depth === 'SHALLOW' || depth === 'FULL_WITH_SAMPLING' ? 'STANDARD' : depth,
            discoveryDepthTier: depth,
            discoveryHash: data.snapshot_fingerprint || `disc-${migId}`,
            selectedTopologyNodes: initialSelected,
            isScopeSaved: true,
            hasCdcBlockers: this.computeSelectedBlockerCount() > 0
          });
          this.lifecycleState.set('SCOPE_WORKBENCH');
        } else {
          const rawErr = resp?.error;
          const errMsg = (rawErr && typeof rawErr === 'object' && 'message' in rawErr)
            ? (rawErr as any).message
            : (typeof rawErr === 'string' ? rawErr : 'Physical discovery returned an unsuccessful response.');
          this.errorMessage.set(typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg));
          this.lifecycleState.set('FAILURE');
        }
      }).catch((err: any) => {
        if (this.timerInterval) clearInterval(this.timerInterval);
        if (this.isCancelled()) return;
        this.errorMessage.set(err?.message || 'Source discovery failed to communicate with discovery authority.');
        this.lifecycleState.set('FAILURE');
      });
    } catch (err: any) {
      if (this.timerInterval) clearInterval(this.timerInterval);
      this.errorMessage.set(err?.message || 'Source discovery encountered an unexpected interruption.');
      this.lifecycleState.set('FAILURE');
    }
  }

  public applyDiscoveredEstateFromBackend(
    data: any,
    provider: PhysicalProviderId,
    depth: DiscoveryDepthTier,
    mode: MigrationMode
  ): void {
    this.currentEstateProvider.set(provider);
    this.nodeMap.clear();

    const tables = Array.isArray(data.tables) ? data.tables : [];
    const collections = Array.isArray(data.collections) ? data.collections : [];
    const topics = Array.isArray(data.topics) ? data.topics : [];

    let nodes: DiscoveredResourceNode[] = [];

    if (collections.length > 0) {
      const dbs = new Map<string, any[]>();
      for (const col of collections) {
        const dbName = col.database || 'default_db';
        if (!dbs.has(dbName)) dbs.set(dbName, []);
        dbs.get(dbName)!.push(col);
      }
      const dbNodes: DiscoveredResourceNode[] = [];
      dbs.forEach((cols, dbName) => {
        dbNodes.push({
          id: `db-${dbName}`,
          name: dbName,
          type: 'DATABASE',
          typeLabel: 'Database',
          namespace: dbName,
          status: 'READY',
          isSelected: true,
          isMigratable: false,
          children: cols.map(c => ({
            id: `col-${c.name}`,
            name: c.name,
            type: 'COLLECTION',
            typeLabel: 'Collection',
            namespace: dbName,
            status: 'READY',
            isSelected: true,
            isMigratable: true,
          }))
        });
      });
      nodes = [{
        id: 'cluster-root',
        name: `${provider} Cluster`,
        type: 'INSTANCE',
        typeLabel: 'Cluster',
        status: 'READY',
        isSelected: true,
        isMigratable: false,
        children: dbNodes
      }];
    } else if (topics.length > 0) {
      nodes = [{
        id: 'streaming-root',
        name: `${provider} Cluster`,
        type: 'INSTANCE',
        typeLabel: 'Cluster',
        status: 'READY',
        isSelected: true,
        isMigratable: false,
        children: [{
          id: 'grp-topics',
          name: `Topics (${topics.length})`,
          type: 'OBJECT_GROUP',
          typeLabel: 'Group',
          status: 'READY',
          isSelected: true,
          isMigratable: false,
          children: topics.map((t: any) => ({
            id: `top-${t.name}`,
            name: t.name,
            type: 'TOPIC',
            typeLabel: 'Topic',
            status: 'READY',
            isSelected: true,
            isMigratable: true,
          }))
        }]
      }];
    } else if (tables.length > 0) {
      const schemas = new Map<string, any[]>();
      for (const tbl of tables) {
        const sName = tbl.schema || 'public';
        if (!schemas.has(sName)) schemas.set(sName, []);
        schemas.get(sName)!.push(tbl);
      }
      const schemaNodes: DiscoveredResourceNode[] = [];
      schemas.forEach((tbls, sName) => {
        schemaNodes.push({
          id: `schema-${sName}`,
          name: sName,
          type: 'SCHEMA',
          typeLabel: 'Schema',
          namespace: sName,
          status: 'READY',
          isSelected: true,
          isMigratable: false,
          children: [{
            id: `grp-tables-${sName}`,
            name: `Tables (${tbls.length})`,
            type: 'OBJECT_GROUP',
            typeLabel: 'Group',
            namespace: sName,
            status: 'READY',
            isSelected: true,
            isMigratable: false,
            children: tbls.map(t => ({
              id: `tbl-${t.name}`,
              name: t.name,
              type: 'TABLE',
              typeLabel: 'Table',
              namespace: sName,
              estimatedRows: t.estimatedRows || t.rows || null,
              countAccuracy: t.countAccuracy || 'CATALOG_ESTIMATE',
              estimatedSizeBytes: t.estimatedSizeBytes || t.size || null,
              status: t.status || 'READY',
              statusReason: t.statusReason,
              secondaryTraits: t.secondaryTraits || (t.primary_keys ? [`PK: ${t.primary_keys.join(', ')}`] : undefined),
              isDependencyReference: t.isDependencyReference || false,
              isSelected: t.isDependencyReference ? false : (t.isSelected !== undefined ? t.isSelected : true),
              isMigratable: true,
            }))
          }]
        });
      });
      nodes = [{
        id: 'instance-root',
        name: `${provider} Instance`,
        type: 'INSTANCE',
        typeLabel: 'Instance',
        status: 'READY',
        isSelected: true,
        isMigratable: false,
        children: schemaNodes
      }];
    } else if (Array.isArray(data.buckets) && data.buckets.length > 0) {
      const bucketNodes: DiscoveredResourceNode[] = [];
      for (const b of data.buckets) {
        const bName = typeof b === 'string' ? b : (b.name || 'bucket');
        const bObjs = Array.isArray(b.objects) ? b.objects : [];
        bucketNodes.push({
          id: `bucket-${bName}`,
          name: bName,
          type: 'BUCKET',
          typeLabel: 'Bucket',
          namespace: bName,
          status: 'READY',
          isSelected: true,
          isMigratable: false,
          children: bObjs.map((o: any) => ({
            id: `obj-${(o.name || o).replace(/[^a-zA-Z0-9_-]/g, '_')}`,
            name: o.name || o,
            type: 'OBJECT',
            typeLabel: 'Object',
            namespace: bName,
            estimatedRows: o.estimatedRows || null,
            countAccuracy: 'STATISTICAL_SAMPLE',
            estimatedSizeBytes: o.estimatedSizeBytes || null,
            status: 'READY',
            isSelected: true,
            isMigratable: true
          }))
        });
      }
      nodes = [{
        id: 'storage-root',
        name: `${provider} Endpoint`,
        type: 'INSTANCE',
        typeLabel: 'Endpoint',
        status: 'READY',
        isSelected: true,
        isMigratable: false,
        children: bucketNodes
      }];
    } else {
      nodes = [{
        id: 'instance-root',
        name: `${provider} Instance`,
        type: 'INSTANCE',
        typeLabel: 'Instance',
        status: 'READY',
        isSelected: false,
        isMigratable: false,
        children: []
      }];
    }

    this.rootNodes.set(nodes);
    this.indexNodes(nodes);

    const initialExpanded = new Set<string>();
    nodes.forEach(root => {
      initialExpanded.add(root.id);
      root.children?.forEach(c => {
        initialExpanded.add(c.id);
        c.children?.forEach(g => initialExpanded.add(g.id));
      });
    });
    this.expandedNodeIds.set(initialExpanded);
    this.reconcileAllParentStates();
  }

  public cancelDiscovery(): void {
    this.isCancelling.set(false);
    this.isCancelled.set(true);
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.lifecycleState.set('DEPTH_SELECTION');
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

    // Fail-closed / no synthetic data manufactured in production
    const nodes: DiscoveredResourceNode[] = [{
      id: 'instance-root',
      name: `${provider} Instance`,
      type: 'INSTANCE',
      typeLabel: 'Instance',
      status: 'READY',
      isSelected: false,
      isMigratable: false,
      children: []
    }];

    this.rootNodes.set(nodes);
    this.indexNodes(nodes);
    this.expandedNodeIds.set(new Set(['instance-root']));
    this.reconcileAllParentStates();
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
