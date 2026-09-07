/**
 * Projects & Initiatives Domain & View Models
 *
 * Product Laws:
 * 1. Initiative = Portfolio/Program grouping of Projects contributing to a broader migration objective.
 * 2. Project = Governed operational scope around a body of migration and validation work.
 * 3. Shell Context = Organization -> Workspace -> Environment is owned by the shell (ContextService).
 * 4. Zero-Fake Policy = Non-canonical data is typed as nullable/optional; availability states are explicitly tracked.
 */

export type EntityAvailabilityState =
  | 'READY'
  | 'LOADING'
  | 'EMPTY'
  | 'UNAVAILABLE'
  | 'NOT_CONNECTED'
  | 'UNAUTHORIZED'
  | 'PARTIAL'
  | 'ERROR';

export type EntityAccessState = 'GRANTED' | 'READ_ONLY' | 'PERMISSION_REQUIRED';

/**
 * Project Discovery Model (Part A Discovery Table/List)
 */
export interface ProjectDiscoveryItem {
  // 1. Canonical Entity Properties
  id: string;
  key: string;
  name: string;
  description?: string;
  workspaceId: string;
  environmentName?: string;
  isProduction?: boolean;

  // 2. Program Association (Initiative Reference)
  initiativeId?: string;
  initiativeName?: string;
  initiativeKey?: string;

  // 3. Factual Status (Repository-native / Opaque Presentation String)
  status?: string;

  // 4. Backend-Provided Aggregate Projections (Strictly nullable when not connected / unavailable)
  migrationCount?: number | null;
  validationCount?: number | null;
  activeWorkloadsCount?: number | null;
  attentionCount?: number | null;

  // 5. Audit & Activity Timestamps
  lastActivityAt?: string;
  createdAt?: string;
  updatedAt?: string;

  // 6. Access & Availability Meta
  availability: EntityAvailabilityState;
  accessState: EntityAccessState;
}

/**
 * Initiative Discovery Model (Part A Initiative Discovery)
 * Deliberately lightweight: Grouping mechanism, NOT a project management engine.
 */
export interface InitiativeDiscoveryItem {
  // 1. Core Identity & Narrative
  id: string;
  key: string;
  name: string;
  objective?: string;
  description?: string;

  // 2. Factual Status
  status?: string;

  // 3. Project Association Summary (Where available from backend projection)
  associatedProjectIds: string[];
  associatedProjectCount: number;
  associatedProjectsSummary?: { id: string; key: string; name: string }[];

  // 4. Activity & Timestamps
  lastActivityAt?: string;
  createdAt?: string;
  updatedAt?: string;

  // 5. Backend Availability & Access State
  // Canonical Initiative backend authority is currently absent pre-P7D; tracked explicitly.
  backendAvailability: EntityAvailabilityState;
  accessState: EntityAccessState;
}

/**
 * Attention / Current Work Event Projection (Truthful, non-fabricated)
 */
export interface PortfolioAttentionItem {
  id: string;
  title: string;
  description: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  occurredAt: string;
  category: 'BLOCKED_OPERATION' | 'VALIDATION_FINDING' | 'PENDING_APPROVAL' | 'RESOURCE_UNAVAILABLE';
  projectId?: string;
  projectName?: string;
  migrationId?: string;
  migrationName?: string;
  actionLabel?: string;
  actionRoute?: string;
}

/**
 * Portfolio Summary Counters (Only displayed when canonical aggregate truth exists)
 */
export interface ProjectsPortfolioSummary {
  totalProjects: number | null;
  activeProjects: number | null;
  totalInitiatives: number | null;
  activeInitiatives: number | null;
  attentionCount: number | null;
}

/**
 * Project Discovery Filters & Sorting State
 */
export interface ProjectFilterState {
  searchQuery: string;
  statusFilter: string; // 'ALL' or specific status
  initiativeFilter: string; // 'ALL' or specific initiativeId
  sortBy: 'NAME' | 'RECENT' | 'STATUS';
  sortDirection: 'ASC' | 'DESC';
}

/**
 * Initiative Discovery Filters & Sorting State
 */
export interface InitiativeFilterState {
  searchQuery: string;
  statusFilter: string; // 'ALL' or specific status
  sortBy: 'NAME' | 'RECENT' | 'PROJECTS';
  sortDirection: 'ASC' | 'DESC';
}

/**
 * ============================================================================
 * PART B: INITIATIVE WORKSPACE & CREATION MODELS
 * ============================================================================
 */

export type InitiativeTabType = 'overview' | 'projects' | 'activity' | 'settings';

/**
 * Full Initiative Workspace Detail
 */
export interface InitiativeWorkspaceDetail {
  id: string;
  key: string;
  name: string;
  objective?: string;
  description?: string;
  status?: string;

  // Associated Project IDs
  associatedProjectIds: string[];

  // Factual Aggregates (Nullable when not canonically supplied)
  totalProjectsCount: number;
  activeProjectsCount?: number | null;
  workloadsCount?: number | null;
  attentionCount?: number | null;

  // Timestamps
  createdAt?: string;
  updatedAt?: string;
  lastActivityAt?: string;

  // Access & Backend Capability Meta
  backendAvailability: EntityAvailabilityState;
  accessState: EntityAccessState;
}

/**
 * Initiative Chronological Activity Item
 * Operational context — NOT immutable security audit.
 */
export interface InitiativeActivityItem {
  id: string;
  initiativeId?: string;
  projectId?: string;
  title: string;
  description: string;
  category: 'METADATA' | 'ASSOCIATION' | 'MILESTONE' | 'GOVERNANCE' | 'EXECUTION' | 'VALIDATION';
  severity: 'SUCCESS' | 'WARNING' | 'INFO' | 'ERROR';
  occurredAt: string;
  actorName?: string;
  subjectName?: string;
  subjectType?: 'PROJECT' | 'INITIATIVE' | 'MIGRATION' | 'VALIDATION' | 'RESOURCE';
  actionType?: 'REVIEW' | 'VIEW' | 'MANAGE' | 'EXECUTE';
  actionRoute?: string;
}

/**
 * Create Initiative Draft Form State
 */
export interface InitiativeDraftState {
  name: string;
  objective: string;
  selectedProjectIds: string[];
}

/**
 * Project Association Intent Actions
 */
export type ProjectAssociationActionType = 'ADD' | 'REMOVE' | 'REASSIGN';

export interface ProjectAssociationIntent {
  action: ProjectAssociationActionType;
  projectId: string;
  projectName: string;
  targetInitiativeId?: string;
  targetInitiativeName?: string;
}

/**
 * ============================================================================
 * PART C: PROJECT CREATION & PROJECT WORKSPACE MODELS
 * ============================================================================
 */

export type ProjectWorkspaceTabType =
  | 'overview'
  | 'migrations'
  | 'validations'
  | 'resources'
  | 'activity'
  | 'access'
  | 'governance'
  | 'settings';

export type ProjectRoleType = 'PROJECT_ADMIN' | 'OPERATOR' | 'VIEWER';

export interface ProjectPrincipal {
  id: string;
  name: string;
  email: string;
  type: 'USER' | 'GROUP' | 'SERVICE_ACCOUNT';
  role: ProjectRoleType;
}

export interface ProjectResourceIntent {
  connectionId: string;
  connectionName: string;
  provider: string;
  category: string;
  environment: string;
  host?: string;
}

export interface ProjectDraftState {
  name: string;
  key: string;
  description: string;
  initiativeId: string | null; // null = Standalone Project
  accessAssignments: ProjectPrincipal[];
  selectedResourceIds: string[];
}

export interface ProjectCurrentWorkSummary {
  totalMigrations: number;
  activeMigrations: number;
  completedMigrations: number;
  totalValidations: number;
  passedValidations: number;
  discrepancyValidations: number;
}

export interface ProjectUpcomingEvent {
  id: string;
  title: string;
  description: string;
  scheduledAt: string;
  type: 'CUTOVER_WINDOW' | 'SCHEMA_FREEZE' | 'MAINTENANCE' | 'SYNC_BATCH';
}

export interface ProjectWorkspaceDetail {
  id: string;
  key: string;
  name: string;
  description?: string;
  workspaceId: string;
  environmentName: string;
  isProduction: boolean;
  initiativeId?: string;
  initiativeName?: string;
  initiativeKey?: string;
  status: string;
  currentWork?: ProjectCurrentWorkSummary;
  upcomingEvents?: ProjectUpcomingEvent[];
  recentActivities?: InitiativeActivityItem[];
  createdAt?: string;
  updatedAt?: string;
  lastActivityAt?: string;
  availability: EntityAvailabilityState;
  accessState: EntityAccessState;
}

/**
 * ============================================================================
 * PART D: PROJECT WORK (MIGRATIONS + VALIDATIONS + RESOURCES) MODELS
 * ============================================================================
 */

export interface ProjectMigrationItem {
  id: string;
  key: string;
  name: string;
  projectId: string;
  projectName?: string;
  sourceProvider: string;
  sourceLabel?: string;
  targetProvider: string;
  targetLabel?: string;
  mode: 'OFFLINE_BULK' | 'ONLINE_CDC' | 'DUAL_RUN' | 'SCHEMA_ONLY' | string;
  lifecycleState: 'PLANNING' | 'READY' | 'RUNNING' | 'ATTENTION' | 'COMPLETED' | 'PAUSED' | 'FAILED' | string;
  currentPhase: string;
  lastActivityAt: string;
  attentionRequired?: boolean;
  attentionText?: string;
  availability: EntityAvailabilityState;
}

export interface ProjectMigrationFilterState {
  searchQuery: string;
  stateFilter: string;
  modeFilter: string;
  sortBy: 'NAME' | 'STATE' | 'RECENT';
  sortDirection: 'ASC' | 'DESC';
}

export interface ProjectValidationItem {
  id: string;
  key: string;
  name: string;
  projectId: string;
  projectName?: string;
  migrationId?: string;
  migrationName?: string;
  scopeName: string;
  sourceProvider: string;
  sourceLabel?: string;
  targetProvider: string;
  targetLabel?: string;
  strategy: 'Structural' | 'Cardinality' | 'Partition Fingerprint' | 'Complete Attribute' | string;
  state: 'ACTIVE' | 'RUNNING' | 'ATTENTION' | 'SCHEDULED' | 'COMPLETED' | 'FAILED' | string;
  outcome: 'Validated' | 'Discrepancies Found' | 'Execution Failed' | 'Running' | 'Scheduled' | string;
  discrepancyCount?: number;
  lastRunAt?: string;
  nextRunAt?: string;
  availability: EntityAvailabilityState;
}

export interface ProjectValidationFilterState {
  searchQuery: string;
  stateFilter: string;
  strategyFilter: string;
  sortBy: 'NAME' | 'STATE' | 'RECENT';
  sortDirection: 'ASC' | 'DESC';
}

export type ProjectResourceAvailabilityState =
  | 'AVAILABLE'
  | 'BOUND'
  | 'UNAVAILABLE'
  | 'UNAUTHORIZED'
  | 'UNSUPPORTED'
  | 'CAPABILITY_UNKNOWN';

export interface ProjectResourceItem {
  id: string;
  connectionId: string;
  connectionName: string;
  provider: string;
  category: 'RELATIONAL' | 'WAREHOUSE' | 'STREAMING' | 'OBJECT_STORE' | string;
  environment: string;
  isProduction: boolean;
  host?: string;
  isBoundToProject: boolean;
  availabilityState: ProjectResourceAvailabilityState;
  capabilityText?: string;
  lastVerifiedAt?: string;
  assignedProjectIds: string[];
  availability: EntityAvailabilityState;
}

export interface ProjectResourceFilterState {
  searchQuery: string;
  categoryFilter: string;
  associationFilter: 'ALL' | 'BOUND' | 'AVAILABLE';
  availabilityFilter: string;
  sortBy: 'NAME' | 'PROVIDER' | 'STATUS';
  sortDirection: 'ASC' | 'DESC';
}

/**
 * ============================================================================
 * PART E: PROJECT CONTROL (ACTIVITY + ACCESS + GOVERNANCE + SETTINGS) MODELS
 * ============================================================================
 */

// 1. ACTIVITY MODELS (Operational context — NOT canonical audit / Evidence #12)
export type ProjectActivityCategory =
  | 'ALL'
  | 'METADATA'
  | 'MIGRATION'
  | 'VALIDATION'
  | 'RESOURCE'
  | 'ACCESS'
  | 'GOVERNANCE'
  | 'SYSTEM';

export interface ProjectActivityItem {
  id: string;
  projectId: string;
  title: string;
  description: string;
  category: ProjectActivityCategory;
  severity: 'SUCCESS' | 'WARNING' | 'INFO' | 'ERROR';
  occurredAt: string;
  actorName: string;
  actorType?: 'USER' | 'SYSTEM' | 'SERVICE_ACCOUNT';
  subjectName?: string;
  subjectType?: 'PROJECT' | 'MIGRATION' | 'VALIDATION' | 'RESOURCE' | 'ACCESS' | 'GOVERNANCE';
  actionType?: 'REVIEW' | 'VIEW' | 'MANAGE' | 'EXECUTE' | 'NAVIGATE';
  actionRoute?: string;
  availability: EntityAvailabilityState;
}

export interface ProjectActivityFilterState {
  searchQuery: string;
  categoryFilter: string;
  sortBy: 'RECENT' | 'CATEGORY' | 'ACTOR';
  sortDirection: 'ASC' | 'DESC';
}

// 2. ACCESS MODELS (Project-scoped grants & inherited WS grants — NOT Administration)
export interface ProjectAccessGrantItem {
  id: string;
  projectId: string;
  principalId: string;
  principalName: string;
  principalEmail: string;
  principalType: 'USER' | 'GROUP' | 'SERVICE_ACCOUNT';
  role: ProjectRoleType;
  accessSource: 'DIRECT_PROJECT' | 'INHERITED_WORKSPACE';
  scopeDescription: string;
  grantedAt: string;
  expiresAt?: string;
  status: 'ACTIVE' | 'EXPIRED' | 'SUSPENDED';
  availability: EntityAvailabilityState;
}

export interface ProjectAccessFilterState {
  searchQuery: string;
  typeFilter: string;
  roleFilter: string;
  sourceFilter: string;
  sortBy: 'NAME' | 'ROLE' | 'SOURCE' | 'STATUS';
  sortDirection: 'ASC' | 'DESC';
}

// 3. GOVERNANCE MODELS (Contextualizing governed operations — NOT approval engine)
export interface ProjectGovernanceItem {
  id: string;
  projectId: string;
  title: string;
  description: string;
  category: 'PENDING_APPROVAL' | 'POLICY_REQUIREMENT' | 'RESOLVED_DECISION' | 'EXCEPTION_WAIVER';
  protectedOperation: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'ACTIVE' | 'WAIVED';
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  requestedAt: string;
  requestedBy?: string;
  resolvedAt?: string;
  resolvedBy?: string;
  policyReference?: string;
  actionLabel?: string;
  actionRoute?: string;
  availability: EntityAvailabilityState;
}

export interface ProjectGovernanceFilterState {
  searchQuery: string;
  categoryFilter: string;
  statusFilter: string;
  sortBy: 'RECENT' | 'CATEGORY' | 'STATUS';
  sortDirection: 'ASC' | 'DESC';
}

// 4. SETTINGS MODELS (Project metadata, defaults, lifecycle — NOT platform administration)
export interface ProjectSettingsState {
  name: string;
  key: string;
  description: string;
  initiativeId: string | null;
  defaultMigrationMode: 'ONLINE_CDC' | 'OFFLINE_BULK' | 'DUAL_RUN' | 'SCHEMA_ONLY';
  defaultValidationStrategy: 'Structural' | 'Cardinality' | 'Partition Fingerprint' | 'Complete Attribute';
  technicalLeadName: string;
  technicalLeadEmail: string;
  status: 'ACTIVE' | 'PLANNING' | 'ARCHIVED';
  isProduction: boolean;
}

/**
 * ============================================================================
 * PART F: CROSS-CUTTING PRODUCT BEHAVIOR MODELS
 * ============================================================================
 */

export type MigrationMoveState =
  | 'MOVE_AVAILABLE'
  | 'CONTROLLED_ACTION_REQUIRED'
  | 'UNAVAILABLE_ACTIVE'
  | 'UNAVAILABLE_UNAUTHORIZED'
  | 'BACKEND_NOT_CONNECTED'
  | 'PENDING'
  | 'FAILED'
  | 'STALE_CONFLICT';

export interface ProjectMigrationMoveIntent {
  migrationId: string;
  sourceProjectId: string;
  destinationProjectId: string;
  reason?: string;
}

export type ActionAuthorizationState =
  | 'PERMITTED'
  | 'DENIED'
  | 'PERMISSION_REQUIRED'
  | 'UNAVAILABLE'
  | 'NOT_CONNECTED'
  | 'PENDING'
  | 'FAILED'
  | 'STALE_CONFLICT';




