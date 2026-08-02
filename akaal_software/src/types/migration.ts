/**
 * AKAAL Enterprise Migration Architecture Data Types
 * Definitive Engine-Aligned Model
 */

export type DatabaseEngine =
  | 'Oracle 19c'
  | 'PostgreSQL 16'
  | 'SQL Server 2019'
  | 'MySQL 8.0'
  | 'MongoDB 6.0'
  | 'IBM DB2 v11'
  | 'MariaDB'
  | 'CockroachDB'
  | 'Snowflake'
  | 'Redshift'
  | 'BigQuery'
  | 'SQLite';

export type EngineStageId =
  | 'scout'
  | 'advisor'
  | 'live_intel'
  | 'planner'
  | 'manager'
  | 'schema_exec'
  | 'data_migration'
  | 'validator'
  | 'healing'
  | 'certification';

export type PipelineHealthStatus =
  | 'healthy'
  | 'approval_required'
  | 'self_healing'
  | 'validation_failed'
  | 'completed'
  | 'draft';

export type DiscoveryProfileType = 'QUICK' | 'STANDARD' | 'DEEP' | 'COMPLIANCE';

export type TeamRole =
  | 'Owner'
  | 'Migration Engineer'
  | 'Validation Lead'
  | 'Approver'
  | 'Observer';

export interface MigrationDraftState {
  step: number;
  migName: string;
  migScope: string;
  strategy: string;
  sourceEngine: DatabaseEngine;
  sourceHost: string;
  sourcePort: string;
  sourceDbName: string;
  sourceUser: string;
  targetEngine: DatabaseEngine;
  targetHost: string;
  targetPort: string;
  targetDbName: string;
  targetUser: string;
  discoveryProfile: DiscoveryProfileType;
  includeSchemas: string;
  gbValidationLevel: string;
  requireFourEyes: boolean;
}

export interface MigrationPipeline {
  id: string;
  name: string;
  sourceEngine: DatabaseEngine;
  sourceEndpoint: string;
  targetEngine: DatabaseEngine;
  targetEndpoint: string;
  currentStage: EngineStageId;
  currentStageLabel: string;
  lastEvent: string;
  health: PipelineHealthStatus;
  healthLabel: string;
  progress: number; // 0 to 100%
  lastActivity: string;
  lastOpenedTimestamp: number;
  createdAtTimestamp: number;
  owner: string;
  assignedRole: TeamRole;
  teamMemberCount: number;
  isPinned?: boolean;
  isShared?: boolean;
  assignedBy?: string;
  approvalStatus?: 'None' | 'Pending Approval' | 'Approved' | 'Rejected';
  isArchived?: boolean;
  isDraft?: boolean;
  draftData?: MigrationDraftState;
  riskScore: number; // 0.0 - 1.0
  trustScore: number; // 0 - 100%
  discoveryProfile: DiscoveryProfileType;
  estimatedRows: number;
  estimatedDuration: string;
}

export type WorkspaceTabId =
  | 'overview'
  | 'lifecycle'
  | 'monitoring'
  | 'validation'
  | 'reports'
  | 'timeline'
  | 'team'
  | 'notes'
  | 'settings';
