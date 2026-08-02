/**
 * AKAAL Enterprise Migration Module Data Types
 */

export type MigrationProjectStatus =
  | 'running'
  | 'planning'
  | 'completed'
  | 'paused'
  | 'failed'
  | 'archived';

export type AgentStage =
  | 'scout'
  | 'planner'
  | 'translator'
  | 'migration'
  | 'validator'
  | 'reporter';

export interface MigrationProject {
  id: string;
  name: string;
  sourceDb: string;
  targetDb: string;
  status: MigrationProjectStatus;
  progress: number; // 0 to 100
  lastActivity: string;
  lastOpenedTimestamp: number;
  createdAtTimestamp: number;
  owner: string;
  teamMemberCount: number;
  isPinned?: boolean;
  isShared?: boolean;
  assignedBy?: string;
  reviewStatus?: string;
  isArchived?: boolean;
  activeAgentStage?: AgentStage;
}

export type ProjectWorkspaceTab =
  | 'overview'
  | 'migration'
  | 'validation'
  | 'monitoring'
  | 'reports'
  | 'timeline'
  | 'team'
  | 'notes'
  | 'settings';
