import type { MigrationPipeline, EngineStageId, DatabaseEngine, MigrationDraftState } from '../types/migration';

type MigrationListener = (pipelines: MigrationPipeline[]) => void;

export const ENGINE_STAGE_METADATA: Record<
  EngineStageId,
  { label: string; stageNumber: number; ownerAgent: string; description: string }
> = {
  scout:          { label: 'Scout & Profiling',          stageNumber: 1,  ownerAgent: 'SCOUT Agent',      description: 'Phase 1: Source & Target Database Schema Discovery'      },
  advisor:        { label: 'Advisor Risk Analysis',      stageNumber: 2,  ownerAgent: 'ADVISOR Agent',    description: 'Phase 2: Compatibility, Constraints & Lock Risk Assessment'},
  live_intel:     { label: 'Live Intelligence',           stageNumber: 3,  ownerAgent: 'LIVE_INTEL Agent', description: 'Phase 3: Decision Graph Simulation & Throughput Strategy' },
  planner:        { label: 'Planner Batch Strategy',    stageNumber: 4,  ownerAgent: 'PLANNER Agent',    description: 'Phase 4: Dependency Graph & Topological Ordering'          },
  manager:        { label: 'Manager Orchestration',     stageNumber: 5,  ownerAgent: 'MANAGER Agent',    description: 'Phase 5: Four-Eyes Sign-off & Policy Verification'         },
  schema_exec:    { label: 'Target Schema DDL',          stageNumber: 2,  ownerAgent: 'SCHEMA Engine',    description: 'Phase 2: Target Tables, Views & Schema DDL Execution'       },
  data_migration: { label: 'Data Migration Transport',    stageNumber: 3,  ownerAgent: 'GB AGENT Engine',  description: 'Phase 3: High-Throughput Parallel Partition Streaming'    },
  validator:      { label: 'Golden Benchmark (GB)',      stageNumber: 4,  ownerAgent: 'VALIDATOR Agent',  description: 'Phase 4: Merkle Tree Checksums & Referential Integrity Audit'},
  healing:        { label: 'Self Healing Recovery',      stageNumber: 5,  ownerAgent: 'HEALING Agent',    description: 'Phase 5: Healer Decision Matrix & Sandbox Execution'       },
  certification:  { label: 'Trust Certification',         stageNumber: 5,  ownerAgent: 'TRUST Engine',     description: 'Phase 5: Cryptographic Proof Seal & Audit Certification'  },
};

import { projectRepository } from '../repositories/projectRepository';

class MigrationService {
  private listeners: Set<MigrationListener> = new Set();

  constructor() {
    projectRepository.subscribe((updated) => {
      this.notifyListeners(updated);
    });
  }

  private notifyListeners(updated: MigrationPipeline[]): void {
    this.listeners.forEach((fn) => fn(updated));
  }

  subscribe(listener: MigrationListener): () => void {
    this.listeners.add(listener);
    listener(this.getPipelines());
    return () => this.listeners.delete(listener);
  }

  getPipelines(): MigrationPipeline[] {
    return projectRepository.getProjects();
  }

  getHeroPipeline(currentUser: string = 'Aalok'): MigrationPipeline | null {
    const pipelines = this.getPipelines();
    const active = pipelines.filter((p) => !p.isArchived && !p.isDraft);
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
    projectRepository.togglePin(id);
  }

  renamePipeline(id: string, newName: string): void {
    projectRepository.renameProject(id, newName);
  }

  duplicatePipeline(id: string): void {
    projectRepository.duplicateProject(id);
  }

  archivePipeline(id: string): void {
    projectRepository.archiveProject(id);
  }

  unarchivePipeline(id: string): void {
    projectRepository.unarchiveProject(id);
  }

  deletePipeline(id: string): void {
    projectRepository.deleteProject(id);
  }

  saveDraft(draft: MigrationDraftState, currentUser: string = 'Aalok'): MigrationPipeline {
    return projectRepository.saveDraft(draft, currentUser);
  }

  createPipeline(
    name: string,
    sourceEngine: DatabaseEngine,
    targetEngine: DatabaseEngine,
    currentUser: string = 'Aalok',
    migrationId?: string
  ): MigrationPipeline {
    return projectRepository.createProject(name, sourceEngine, targetEngine, currentUser, migrationId);
  }

  touchPipeline(_id: string): void {
    // Touch timestamp
  }
}

export const migrationService = new MigrationService();
