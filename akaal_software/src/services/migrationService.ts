import type { MigrationPipeline, EngineStageId, DatabaseEngine, MigrationDraftState } from '../types/migration';

type MigrationListener = (pipelines: MigrationPipeline[]) => void;

export const ENGINE_STAGE_METADATA: Record<
  EngineStageId,
  { label: string; stageNumber: number; ownerAgent: string; description: string }
> = {
  scout:          { label: 'Scout & Profiling',          stageNumber: 1,  ownerAgent: 'SCOUT Agent',      description: 'Stage 1: Source & Target Database Schema Discovery'      },
  advisor:        { label: 'Advisor Risk Analysis',      stageNumber: 2,  ownerAgent: 'ADVISOR Agent',    description: 'Stage 2: Compatibility, Constraints & Lock Risk Assessment'},
  live_intel:     { label: 'Live Intelligence',           stageNumber: 3,  ownerAgent: 'LIVE_INTEL Agent', description: 'Stage 3: Decision Graph Simulation & Throughput Strategy' },
  planner:        { label: 'Planner Batch Strategy',    stageNumber: 4,  ownerAgent: 'PLANNER Agent',    description: 'Stage 4: Dependency Graph & Topological Ordering'          },
  manager:        { label: 'Manager Orchestration',     stageNumber: 5,  ownerAgent: 'MANAGER Agent',    description: 'Stage 5: Four-Eyes Sign-off & Policy Verification'         },
  schema_exec:    { label: 'Target Schema DDL',          stageNumber: 6,  ownerAgent: 'SCHEMA Engine',    description: 'Stage 6: Target Tables, Views & Indexes Execution'         },
  data_migration: { label: 'Data Migration Transport',    stageNumber: 7,  ownerAgent: 'GB AGENT Engine',  description: 'Stage 7: High-Throughput Parallel Partition Streaming'    },
  validator:      { label: 'Golden Benchmark (GB)',      stageNumber: 8,  ownerAgent: 'VALIDATOR Agent',  description: 'Stage 8: Column Checksums & Referential Integrity Audit'   },
  healing:        { label: 'Self Healing Recovery',      stageNumber: 9,  ownerAgent: 'HEALING Agent',    description: 'Stage 9: Healer Decision Matrix & Sandbox Execution'       },
  certification:  { label: 'Trust Certification',         stageNumber: 10, ownerAgent: 'TRUST Engine',     description: 'Stage 10: Cryptographic Proof Seal & Audit Certification'  },
};

const INITIAL_PIPELINES: MigrationPipeline[] = [
  {
    id: 'pipe-001',
    name: 'Oracle ERP Core Migration',
    sourceEngine: 'Oracle 19c',
    sourceEndpoint: 'db-oracle.enterprise.internal:1521/ORCL',
    targetEngine: 'PostgreSQL 16',
    targetEndpoint: 'pg-cluster.enterprise.internal:5432/app_target_db',
    currentStage: 'data_migration',
    currentStageLabel: 'Data Migration Transport',
    lastEvent: 'Batch #42 streamed (150,000 rows transferred)',
    health: 'healthy',
    healthLabel: 'Healthy',
    progress: 87,
    lastActivity: 'Active 18 minutes ago',
    lastOpenedTimestamp: Date.now() - 18 * 60 * 1000,
    createdAtTimestamp: Date.now() - 7 * 24 * 60 * 60 * 1000,
    owner: 'Aalok',
    assignedRole: 'Owner',
    teamMemberCount: 4,
    isPinned: true,
    isShared: false,
    approvalStatus: 'Approved',
    riskScore: 0.15,
    trustScore: 98,
    discoveryProfile: 'STANDARD',
    estimatedRows: 1_250_000_000,
    estimatedDuration: '4h 15m',
  },
  {
    id: 'pipe-002',
    name: 'Payroll Modernization Stream',
    sourceEngine: 'SQL Server 2019',
    sourceEndpoint: 'sql-payroll.corp.internal:1433/PayrollDB',
    targetEngine: 'PostgreSQL 16',
    targetEndpoint: 'pg-payroll.corp.internal:5432/payroll_pg',
    currentStage: 'manager',
    currentStageLabel: 'Four-Eyes Approval Required',
    lastEvent: 'Planning completed — Four-Eyes Manager sign-off required',
    health: 'approval_required',
    healthLabel: 'Approval Required',
    progress: 45,
    lastActivity: 'Awaiting Approver Sign-off',
    lastOpenedTimestamp: Date.now() - 2 * 60 * 60 * 1000,
    createdAtTimestamp: Date.now() - 5 * 24 * 60 * 60 * 1000,
    owner: 'Aalok',
    assignedRole: 'Approver',
    teamMemberCount: 3,
    isPinned: true,
    isShared: false,
    approvalStatus: 'Pending Approval',
    riskScore: 0.42,
    trustScore: 85,
    discoveryProfile: 'DEEP',
    estimatedRows: 480_000_000,
    estimatedDuration: '2h 30m',
  },
  {
    id: 'pipe-003',
    name: 'Oracle Financial Core Pipeline',
    sourceEngine: 'Oracle 19c',
    sourceEndpoint: 'fin-oracle.internal:1521/FINDB',
    targetEngine: 'PostgreSQL 16',
    targetEndpoint: 'pg-fin.internal:5432/fin_target',
    currentStage: 'healing',
    currentStageLabel: 'Self-Healing Active',
    lastEvent: 'FK Constraint Conflict detected — Healer executing sandbox retry',
    health: 'self_healing',
    healthLabel: 'Self-Healing',
    progress: 62,
    lastActivity: 'Assigned by Aalok',
    lastOpenedTimestamp: Date.now() - 5 * 60 * 1000,
    createdAtTimestamp: Date.now() - 10 * 24 * 60 * 60 * 1000,
    owner: 'Sarah Jenkins',
    assignedRole: 'Validation Lead',
    teamMemberCount: 6,
    isPinned: false,
    isShared: true,
    assignedBy: 'Aalok',
    approvalStatus: 'Approved',
    riskScore: 0.35,
    trustScore: 91,
    discoveryProfile: 'COMPLIANCE',
    estimatedRows: 890_000_000,
    estimatedDuration: '3h 45m',
  },
  {
    id: 'pipe-004',
    name: 'Legacy CRM Database Pipeline',
    sourceEngine: 'MySQL 8.0',
    sourceEndpoint: 'crm-mysql.internal:3306/crm_prod',
    targetEngine: 'PostgreSQL 16',
    targetEndpoint: 'pg-crm.internal:5432/crm_pg',
    currentStage: 'certification',
    currentStageLabel: 'Trust Certified',
    lastEvent: 'Cryptographic Proof Seal generated (SHA-256 Verified)',
    health: 'completed',
    healthLabel: 'Certified',
    progress: 100,
    lastActivity: 'Certified 3 days ago',
    lastOpenedTimestamp: Date.now() - 3 * 24 * 60 * 60 * 1000,
    createdAtTimestamp: Date.now() - 14 * 24 * 60 * 60 * 1000,
    owner: 'Aalok',
    assignedRole: 'Owner',
    teamMemberCount: 3,
    isPinned: false,
    isShared: false,
    approvalStatus: 'Approved',
    riskScore: 0.05,
    trustScore: 100,
    discoveryProfile: 'STANDARD',
    estimatedRows: 120_000_000,
    estimatedDuration: '1h 10m',
  },
];

class MigrationService {
  private pipelines: MigrationPipeline[] = [...INITIAL_PIPELINES];
  private listeners: Set<MigrationListener> = new Set();
  private counter = INITIAL_PIPELINES.length;

  subscribe(listener: MigrationListener): () => void {
    this.listeners.add(listener);
    listener(this.getPipelines());
    return () => this.listeners.delete(listener);
  }

  getPipelines(): MigrationPipeline[] {
    return [...this.pipelines];
  }

  getHeroPipeline(currentUser: string = 'Aalok'): MigrationPipeline | null {
    const active = this.pipelines.filter((p) => !p.isArchived && !p.isDraft);
    if (active.length === 0) return null;

    const userLower = (currentUser || '').toLowerCase();
    const approval = active.find(
      (p) =>
        (p.health === 'approval_required' || p.currentStage === 'manager') &&
        (p.owner || '').toLowerCase() === userLower
    );
    if (approval) return approval;

    const healing = active.find((p) => p.health === 'self_healing' || p.currentStage === 'healing');
    if (healing) return healing;

    const running = active.find((p) => p.currentStage === 'data_migration');
    if (running) return running;

    const sorted = [...active].sort((a, b) => b.lastOpenedTimestamp - a.lastOpenedTimestamp);
    return sorted[0] || null;
  }

  togglePin(id: string): void {
    this.pipelines = this.pipelines.map((p) =>
      p.id === id ? { ...p, isPinned: !p.isPinned } : p
    );
    this.notify();
  }

  renamePipeline(id: string, newName: string): void {
    this.pipelines = this.pipelines.map((p) =>
      p.id === id ? { ...p, name: newName.trim(), lastOpenedTimestamp: Date.now() } : p
    );
    this.notify();
  }

  duplicatePipeline(id: string): void {
    const target = this.pipelines.find((p) => p.id === id);
    if (!target) return;

    this.counter++;
    const duplicate: MigrationPipeline = {
      ...target,
      id: `pipe-${String(this.counter).padStart(3, '0')}`,
      name: `${target.name} (Copy)`,
      createdAtTimestamp: Date.now(),
      lastOpenedTimestamp: Date.now(),
      lastActivity: 'Created just now',
      isPinned: false,
    };

    this.projectsNotify([duplicate, ...this.pipelines]);
  }

  archivePipeline(id: string): void {
    this.pipelines = this.pipelines.map((p) =>
      p.id === id
        ? {
            ...p,
            isArchived: true,
            currentStage: 'certification',
            currentStageLabel: 'Archived',
            lastActivity: 'Archived just now',
            isPinned: false,
          }
        : p
    );
    this.notify();
  }

  unarchivePipeline(id: string): void {
    this.pipelines = this.pipelines.map((p) =>
      p.id === id
        ? {
            ...p,
            isArchived: false,
            currentStage: 'scout',
            currentStageLabel: 'Scout & Profiling',
            lastActivity: 'Restored from archive',
          }
        : p
    );
    this.notify();
  }

  deletePipeline(id: string): void {
    this.pipelines = this.pipelines.filter((p) => p.id !== id);
    this.notify();
  }

  saveDraft(draft: MigrationDraftState, owner: string = 'Aalok'): MigrationPipeline {
    this.counter++;
    const draftPipeline: MigrationPipeline = {
      id: `pipe-draft-${String(this.counter).padStart(3, '0')}`,
      name: draft.migName.trim() || `${draft.sourceEngine} → ${draft.targetEngine} Setup (Draft)`,
      sourceEngine: draft.sourceEngine,
      sourceEndpoint: `${draft.sourceHost}:${draft.sourcePort}/${draft.sourceDbName}`,
      targetEngine: draft.targetEngine,
      targetEndpoint: `${draft.targetHost}:${draft.targetPort}/${draft.targetDbName}`,
      currentStage: 'scout',
      currentStageLabel: 'Setup Configuration Draft',
      lastEvent: `Saved draft at Step ${draft.step} of 5`,
      health: 'draft',
      healthLabel: 'Draft Saved',
      progress: Math.round((draft.step / 5) * 100),
      lastActivity: 'Draft saved just now',
      lastOpenedTimestamp: Date.now(),
      createdAtTimestamp: Date.now(),
      owner,
      assignedRole: 'Owner',
      teamMemberCount: 1,
      isPinned: false,
      isShared: false,
      isArchived: false,
      isDraft: true,
      draftData: draft,
      riskScore: 0.10,
      trustScore: 100,
      discoveryProfile: draft.discoveryProfile,
      estimatedRows: 250_000_000,
      estimatedDuration: '1h 45m',
    };

    this.projectsNotify([draftPipeline, ...this.pipelines]);
    return draftPipeline;
  }

  createPipeline(
    name: string,
    sourceEngine: DatabaseEngine,
    targetEngine: DatabaseEngine,
    owner: string = 'Aalok'
  ): MigrationPipeline {
    this.counter++;
    const newPipeline: MigrationPipeline = {
      id: `pipe-${String(this.counter).padStart(3, '0')}`,
      name: name.trim() || `${sourceEngine} → ${targetEngine} Pipeline`,
      sourceEngine,
      sourceEndpoint: 'db-source.internal:1521/SRCDB',
      targetEngine,
      targetEndpoint: 'pg-target.internal:5432/TGTDB',
      currentStage: 'scout',
      currentStageLabel: 'Scout & Profiling',
      lastEvent: 'Migration pipeline initialized — Scout discovery active',
      health: 'healthy',
      healthLabel: 'Healthy',
      progress: 5,
      lastActivity: 'Created just now',
      lastOpenedTimestamp: Date.now(),
      createdAtTimestamp: Date.now(),
      owner,
      assignedRole: 'Owner',
      teamMemberCount: 1,
      isPinned: false,
      isShared: false,
      isArchived: false,
      isDraft: false,
      riskScore: 0.10,
      trustScore: 100,
      discoveryProfile: 'STANDARD',
      estimatedRows: 250_000_000,
      estimatedDuration: '1h 45m',
    };

    this.projectsNotify([newPipeline, ...this.pipelines]);
    return newPipeline;
  }

  touchPipeline(id: string): void {
    this.pipelines = this.pipelines.map((p) =>
      p.id === id ? { ...p, lastOpenedTimestamp: Date.now() } : p
    );
    this.notify();
  }

  private projectsNotify(newPipelines: MigrationPipeline[]): void {
    this.pipelines = newPipelines;
    this.notify();
  }

  private notify(): void {
    const snapshot = this.getPipelines();
    this.listeners.forEach((l) => l(snapshot));
  }
}

export const migrationService = new MigrationService();
