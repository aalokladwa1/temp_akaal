import type { MigrationPipeline, DatabaseEngine, MigrationDraftState } from '../types/migration';
import { ipcService } from '../services/ipcService';

type ProjectChangeListener = (projects: MigrationPipeline[]) => void;

class ProjectRepository {
  private projects: MigrationPipeline[] = [];
  private listeners: Set<ProjectChangeListener> = new Set();

  public getProjects(): MigrationPipeline[] {
    return [...this.projects];
  }

  public subscribe(listener: ProjectChangeListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    const copy = [...this.projects];
    this.listeners.forEach((fn) => fn(copy));
  }

  public createProject(
    name: string,
    sourceEngine: DatabaseEngine,
    targetEngine: DatabaseEngine,
    currentUser: string = 'Aalok'
  ): MigrationPipeline {
    const newProject: MigrationPipeline = {
      id: `proj-${Date.now()}`,
      name,
      sourceEngine,
      sourceEndpoint: `src-${sourceEngine.toLowerCase().replace(/\s+/g, '-')}.internal`,
      targetEngine,
      targetEndpoint: `tgt-${targetEngine.toLowerCase().replace(/\s+/g, '-')}.internal`,
      currentStage: 'scout',
      currentStageLabel: 'Scout & Schema Discovery',
      lastEvent: 'Project Workspace Initialized',
      health: 'healthy',
      healthLabel: 'Healthy',
      progress: 0,
      lastActivity: 'Just created',
      lastOpenedTimestamp: Date.now(),
      createdAtTimestamp: Date.now(),
      owner: currentUser,
      assignedRole: 'Owner',
      teamMemberCount: 1,
      isPinned: false,
      isShared: false,
      approvalStatus: 'None',
      riskScore: 0.0,
      trustScore: 100,
      discoveryProfile: 'STANDARD',
      estimatedRows: 0,
      estimatedDuration: 'Pending Scout',
    };

    // Forward capability to Engine Bridge via IPC
    ipcService.invokeEngineCapability('create_project', JSON.stringify({
      project_name: name,
      source_engine: sourceEngine,
      target_engine: targetEngine,
    })).catch(() => {});

    this.projects = [newProject, ...this.projects];
    this.notify();
    return newProject;
  }

  public saveDraft(draft: MigrationDraftState, currentUser: string = 'Aalok'): MigrationPipeline {
    const draftId = `draft-${Date.now()}`;
    const draftProject: MigrationPipeline = {
      id: draftId,
      name: draft.migName || 'Untitled Migration Draft',
      sourceEngine: draft.sourceEngine,
      sourceEndpoint: `${draft.sourceHost || 'localhost'}:${draft.sourcePort}/${draft.sourceDbName}`,
      targetEngine: draft.targetEngine,
      targetEndpoint: `${draft.targetHost || 'localhost'}:${draft.targetPort}/${draft.targetDbName}`,
      currentStage: 'scout',
      currentStageLabel: 'Draft Configuration',
      lastEvent: 'Draft Configuration Saved',
      health: 'draft',
      healthLabel: 'Draft',
      progress: 0,
      lastActivity: 'Draft Saved',
      lastOpenedTimestamp: Date.now(),
      createdAtTimestamp: Date.now(),
      owner: currentUser,
      assignedRole: 'Owner',
      teamMemberCount: 1,
      isDraft: true,
      draftData: draft,
      riskScore: 0.0,
      trustScore: 100,
      discoveryProfile: draft.discoveryProfile || 'STANDARD',
      estimatedRows: 0,
      estimatedDuration: 'Draft Configuration',
    };

    this.projects = [draftProject, ...this.projects];
    this.notify();
    return draftProject;
  }

  public togglePin(id: string): void {
    this.projects = this.projects.map((p) => (p.id === id ? { ...p, isPinned: !p.isPinned } : p));
    this.notify();
  }

  public renameProject(id: string, newName: string): void {
    this.projects = this.projects.map((p) => (p.id === id ? { ...p, name: newName } : p));
    this.notify();
  }

  public duplicateProject(id: string): void {
    const existing = this.projects.find((p) => p.id === id);
    if (!existing) return;
    const duplicated: MigrationPipeline = {
      ...existing,
      id: `proj-${Date.now()}_copy`,
      name: `${existing.name} (Copy)`,
      createdAtTimestamp: Date.now(),
      lastOpenedTimestamp: Date.now(),
      lastActivity: 'Duplicated',
    };
    this.projects = [duplicated, ...this.projects];
    this.notify();
  }

  public archiveProject(id: string): void {
    this.projects = this.projects.map((p) => (p.id === id ? { ...p, isArchived: true } : p));
    this.notify();
  }

  public unarchiveProject(id: string): void {
    this.projects = this.projects.map((p) => (p.id === id ? { ...p, isArchived: false } : p));
    this.notify();
  }

  public deleteProject(id: string): void {
    this.projects = this.projects.filter((p) => p.id !== id);
    this.notify();
  }

  public setProjectsFromIPC(incoming: MigrationPipeline[]): void {
    this.projects = incoming;
    this.notify();
  }
}

export const projectRepository = new ProjectRepository();
