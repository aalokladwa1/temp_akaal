import type { MigrationProject } from '../types/migration';

type MigrationListener = (projects: MigrationProject[]) => void;

const INITIAL_PROJECTS: MigrationProject[] = [
  {
    id: 'proj-001',
    name: 'Oracle ERP Migration',
    sourceDb: 'Oracle 19c',
    targetDb: 'PostgreSQL 16',
    status: 'running',
    progress: 87,
    lastActivity: 'Last active 18 minutes ago',
    lastOpenedTimestamp: Date.now() - 18 * 60 * 1000,
    createdAtTimestamp: Date.now() - 7 * 24 * 60 * 60 * 1000,
    owner: 'Aalok',
    teamMemberCount: 4,
    isPinned: true,
    isShared: false,
    activeAgentStage: 'migration',
  },
  {
    id: 'proj-002',
    name: 'Payroll Modernization',
    sourceDb: 'SQL Server 2019',
    targetDb: 'PostgreSQL 16',
    status: 'planning',
    progress: 25,
    lastActivity: 'Last opened yesterday',
    lastOpenedTimestamp: Date.now() - 24 * 60 * 60 * 1000,
    createdAtTimestamp: Date.now() - 5 * 24 * 60 * 60 * 1000,
    owner: 'Aalok',
    teamMemberCount: 2,
    isPinned: true,
    isShared: false,
    activeAgentStage: 'planner',
  },
  {
    id: 'proj-003',
    name: 'Oracle Financial Migration',
    sourceDb: 'Oracle 12c',
    targetDb: 'PostgreSQL 15',
    status: 'paused',
    progress: 54,
    lastActivity: 'Assigned by Aalok',
    lastOpenedTimestamp: Date.now() - 2 * 24 * 60 * 60 * 1000,
    createdAtTimestamp: Date.now() - 10 * 24 * 60 * 60 * 1000,
    owner: 'Sarah Jenkins',
    teamMemberCount: 6,
    isPinned: false,
    isShared: true,
    assignedBy: 'Aalok',
    reviewStatus: 'Waiting for Review',
    activeAgentStage: 'translator',
  },
  {
    id: 'proj-004',
    name: 'Legacy CRM Database',
    sourceDb: 'MySQL 5.7',
    targetDb: 'PostgreSQL 16',
    status: 'completed',
    progress: 100,
    lastActivity: 'Completed 3 days ago',
    lastOpenedTimestamp: Date.now() - 3 * 24 * 60 * 60 * 1000,
    createdAtTimestamp: Date.now() - 14 * 24 * 60 * 60 * 1000,
    owner: 'Aalok',
    teamMemberCount: 3,
    isPinned: false,
    isShared: false,
    activeAgentStage: 'reporter',
  },
  {
    id: 'proj-005',
    name: 'Archive Logs Vault',
    sourceDb: 'DB2 v11',
    targetDb: 'PostgreSQL 15',
    status: 'archived',
    progress: 100,
    lastActivity: 'Archived 1 month ago',
    lastOpenedTimestamp: Date.now() - 30 * 24 * 60 * 60 * 1000,
    createdAtTimestamp: Date.now() - 60 * 24 * 60 * 60 * 1000,
    owner: 'Aalok',
    teamMemberCount: 1,
    isPinned: false,
    isShared: false,
    isArchived: true,
    activeAgentStage: 'reporter',
  },
];

class MigrationService {
  private projects: MigrationProject[] = [...INITIAL_PROJECTS];
  private listeners: Set<MigrationListener> = new Set();
  private counter = INITIAL_PROJECTS.length;

  subscribe(listener: MigrationListener): () => void {
    this.listeners.add(listener);
    listener(this.getProjects());
    return () => this.listeners.delete(listener);
  }

  getProjects(): MigrationProject[] {
    return [...this.projects];
  }

  /**
   * Hero project selection priority logic:
   * 1. Running project assigned to current user
   * 2. Paused project assigned to current user
   * 3. Project awaiting current user's approval / review
   * 4. Most recently opened project
   * 5. Most recently created project
   */
  getContinueWorkingProject(currentUser: string = 'Aalok'): MigrationProject | null {
    const activeProjects = this.projects.filter((p) => !p.isArchived);
    if (activeProjects.length === 0) return null;

    // 1. Running project assigned to current user
    const runningUser = activeProjects.find(
      (p) => p.status === 'running' && p.owner.toLowerCase() === currentUser.toLowerCase()
    );
    if (runningUser) return runningUser;

    // 2. Paused project assigned to current user
    const pausedUser = activeProjects.find(
      (p) => p.status === 'paused' && p.owner.toLowerCase() === currentUser.toLowerCase()
    );
    if (pausedUser) return pausedUser;

    // 3. Project awaiting current user's review
    const reviewProject = activeProjects.find(
      (p) => p.reviewStatus && p.reviewStatus.includes('Review')
    );
    if (reviewProject) return reviewProject;

    // 4. Most recently opened project
    const sortedByOpened = [...activeProjects].sort(
      (a, b) => b.lastOpenedTimestamp - a.lastOpenedTimestamp
    );
    if (sortedByOpened.length > 0) return sortedByOpened[0];

    // 5. Most recently created project
    const sortedByCreated = [...activeProjects].sort(
      (a, b) => b.createdAtTimestamp - a.createdAtTimestamp
    );
    return sortedByCreated[0] || null;
  }

  togglePin(id: string): void {
    this.projects = this.projects.map((p) =>
      p.id === id ? { ...p, isPinned: !p.isPinned } : p
    );
    this.notify();
  }

  renameProject(id: string, newName: string): void {
    this.projects = this.projects.map((p) =>
      p.id === id ? { ...p, name: newName.trim(), lastOpenedTimestamp: Date.now() } : p
    );
    this.notify();
  }

  duplicateProject(id: string): void {
    const target = this.projects.find((p) => p.id === id);
    if (!target) return;

    this.counter++;
    const duplicate: MigrationProject = {
      ...target,
      id: `proj-${String(this.counter).padStart(3, '0')}`,
      name: `${target.name} (Copy)`,
      createdAtTimestamp: Date.now(),
      lastOpenedTimestamp: Date.now(),
      lastActivity: 'Created just now',
      isPinned: false,
    };

    this.projects = [duplicate, ...this.projects];
    this.notify();
  }

  archiveProject(id: string): void {
    this.projects = this.projects.map((p) =>
      p.id === id
        ? {
            ...p,
            isArchived: true,
            status: 'archived',
            isPinned: false,
            lastActivity: 'Archived just now',
          }
        : p
    );
    this.notify();
  }

  unarchiveProject(id: string): void {
    this.projects = this.projects.map((p) =>
      p.id === id
        ? {
            ...p,
            isArchived: false,
            status: 'planning',
            lastActivity: 'Restored from archive',
          }
        : p
    );
    this.notify();
  }

  deleteProject(id: string): void {
    this.projects = this.projects.filter((p) => p.id !== id);
    this.notify();
  }

  createProject(name: string, sourceDb: string, targetDb: string, owner: string = 'Aalok'): MigrationProject {
    this.counter++;
    const newProj: MigrationProject = {
      id: `proj-${String(this.counter).padStart(3, '0')}`,
      name: name.trim() || 'New Migration Project',
      sourceDb: sourceDb.trim() || 'Source DB',
      targetDb: targetDb.trim() || 'PostgreSQL 16',
      status: 'planning',
      progress: 0,
      lastActivity: 'Created just now',
      lastOpenedTimestamp: Date.now(),
      createdAtTimestamp: Date.now(),
      owner,
      teamMemberCount: 1,
      isPinned: false,
      isShared: false,
      isArchived: false,
      activeAgentStage: 'scout',
    };

    this.projects = [newProj, ...this.projects];
    this.notify();
    return newProj;
  }

  touchProject(id: string): void {
    this.projects = this.projects.map((p) =>
      p.id === id ? { ...p, lastOpenedTimestamp: Date.now() } : p
    );
    this.notify();
  }

  private notify(): void {
    const snapshot = this.getProjects();
    this.listeners.forEach((l) => l(snapshot));
  }
}

export const migrationService = new MigrationService();
