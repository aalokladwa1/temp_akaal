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
  activeSessionId?: string;
  sessionsCount?: number;
  recentSessions?: RuntimeSession[];
}

export type RuntimeSessionStatus =
  | 'initializing'
  | 'active'
  | 'paused'
  | 'approval_pending'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface EngineDecisionEvent {
  id: string;
  timestamp: string;
  stage: EngineStageId;
  subsystem: 'Planner' | 'Advisor' | 'Healing' | 'Certification' | 'Scout' | 'Schema';
  title: string;
  decision: string;
  reason: string;
  impactScore?: number;
  confidenceScore?: number;
  metadata?: Record<string, any>;
}

export interface RuntimeSession {
  sessionId: string;
  migrationId: string;
  executionNumber: number;
  status: RuntimeSessionStatus;
  startedAt: string;
  endedAt?: string;
  currentStage: EngineStageId;
  progressPercent: number;
  rowsTransferred: number;
  bytesTransferred: number;
  throughputMbps: number;
  activeWorkers: number;
  decisions: EngineDecisionEvent[];
  trustScore?: number;
  riskScore?: number;
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

export type GateId = 'GATE_1' | 'GATE_2' | 'GATE_3';

export interface GovernanceApproval {
  id: string;
  gate: GateId;
  gateTitle: string;
  migrationId: string;
  migrationName: string;
  projectName: string;
  requestedBy: string;
  requestedAt: string;
  expiresAt: string;
  status: 'pending' | 'approved' | 'rejected' | 'changes_requested' | 'delegated' | 'escalated' | 'expired';
  requiredRoles: TeamRole[];
  fourEyesConfirmed: boolean;
  riskScore?: number;
  summary: string;
  comments?: { author: string; timestamp: string; text: string }[];
  evidenceSummary?: string;
  decisionReason?: string;
  approver?: string;
  approvedAt?: string;
}

export interface ProjectConnection {
  id: string;
  projectId: string;
  name: string;
  engine: DatabaseEngine;
  endpoint: string;
  environment: 'Production' | 'Staging' | 'UAT' | 'Development';
  sslStatus: 'Enabled' | 'Disabled' | 'Enforced';
  vaultReference: string;
  latencyMs?: number;
  status: 'Healthy' | 'Testing' | 'Offline' | 'Unvalidated';
  lastValidatedAt?: string;
}

