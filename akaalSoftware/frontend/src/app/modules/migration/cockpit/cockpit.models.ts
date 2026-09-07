/**
 * AKAAL Enterprise Migration Platform
 * Cockpit / Mission Control — Canonical Presentation & Domain Models
 *
 * Governing Law:
 * Frontend projects canonical runtime truth provided by akaalEngine / akaalPipeline / akaalIPC.
 * Semantic invention and authority duplication are strictly prohibited.
 */

import { MigrationMode, PhysicalProviderId } from '../../../core/models/migration-view.models';
import { PlanStageType, ApprovalBarrierConfig } from '../create/steps/step7-plan.models';

// ----------------------------------------------------------------------------
// 1. LIFECYCLE & OPERATIONAL HEALTH STATES
// ----------------------------------------------------------------------------
export type CockpitLifecycleState =
  | 'INITIALIZED'
  | 'RUNNING'
  | 'PAUSED'
  | 'WAITING_FOR_APPROVAL'
  | 'RECOVERING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type EngineHealthState = 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'UNKNOWN';

// ----------------------------------------------------------------------------
// 2. MIGRATION IDENTITY & METADATA
// ----------------------------------------------------------------------------
export interface CockpitEndpointDescriptor {
  provider: PhysicalProviderId | string;
  host?: string;
  port?: number;
  database?: string;
  label: string;
}

export interface CockpitIdentity {
  migrationId: string;
  migrationName: string;
  environment: string;
  mode: MigrationMode;
  modeTitle: string;
  source: CockpitEndpointDescriptor;
  target: CockpitEndpointDescriptor;
  planRevision: number;
  planFingerprint: string;
  activeAttempt: number;
  lifecycleState: CockpitLifecycleState;
  lifecycleLabel: string;
  startedAt?: string;
  elapsedTimeString: string;
}

// ----------------------------------------------------------------------------
// 3. OPERATIONAL PULSE & GLANCEABLE STATUS
// ----------------------------------------------------------------------------
export interface OperationalPulseMetric {
  id: string;
  label: string;
  value: string;
  unit?: string;
  status: 'NORMAL' | 'SUCCESS' | 'WARNING' | 'CRITICAL' | 'MUTED';
  detail?: string;
  sparkline?: number[];
}

export interface CockpitStatusPulse {
  stateHeading: string;
  stateBadgeColor: string;
  phaseSubtitle: string;
  activeTaskDescription: string;
  metrics: OperationalPulseMetric[];
}

// ----------------------------------------------------------------------------
// 4. WORKLOAD PROGRESS (DISTINCT FROM PLAN PROGRESS)
// ----------------------------------------------------------------------------
export interface WorkloadProgressState {
  isContinuous: boolean;
  isUnknown: boolean;
  units: 'rows' | 'bytes' | 'objects' | 'records' | 'diffs';
  processed: number;
  total: number;
  percentage: number;
  processedFormatted: string;
  totalFormatted: string;
  currentRateFormatted: string;
  etaFormatted?: string;
  elapsedFormatted: string;
  phaseDescription: string;
}

// ----------------------------------------------------------------------------
// 5. LIVE EXECUTION PLAN / RUNTIME DAG
// ----------------------------------------------------------------------------
export type RuntimeDagNodeState =
  | 'COMPLETED'
  | 'ACTIVE'
  | 'RUNNING_PARALLEL'
  | 'WAITING'
  | 'APPROVAL_BARRIER'
  | 'FAILED'
  | 'RECOVERING'
  | 'SKIPPED'
  | 'UPCOMING';

export interface RuntimeDagNode {
  id: string;
  order: number;
  label: string;
  subtitle: string;
  category: string;
  stageType: PlanStageType | string;
  runtimeState: RuntimeDagNodeState;
  progressPercent?: number;
  throughputFormatted?: string;
  workerAllocation?: number;
  elapsedDuration?: string;
  isContinuous?: boolean;
  isBarrier?: boolean;
  barrierConfig?: ApprovalBarrierConfig;
  failureMessage?: string;
  incomingNodeIds: string[];
  outgoingNodeIds: string[];
}

export interface RuntimeDagEdge {
  id: string;
  source: string;
  target: string;
  isActive: boolean;
  isCompleted: boolean;
}

export interface RuntimeDagTopology {
  nodes: RuntimeDagNode[];
  edges: RuntimeDagEdge[];
  activeNodeIds: string[];
  completedNodeIds: string[];
  waitingBarrierNodeIds: string[];
}

// ----------------------------------------------------------------------------
// 6. ENGINE HEALTH & EXPLAINABLE SUBSYSTEMS (COLLECTION-ORIENTED)
// ----------------------------------------------------------------------------
export interface SubsystemHealthEntry {
  id: string;
  name: string;
  category: string;
  status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'UNKNOWN' | 'NOT_APPLICABLE';
  reason?: string;
  evidence?: string;
  latencyMs?: number;
  throughputMetrics?: string;
  isCausal: boolean;
}

export interface EngineHealthSummary {
  overallStatus: EngineHealthState;
  statusLabel: string;
  summaryNarrative: string;
  subsystems: SubsystemHealthEntry[];
  primaryDegradedReason?: string;
  primaryDegradedEvidence?: string;
}

// ----------------------------------------------------------------------------
// 7. OPERATOR INTERVENTION
// ----------------------------------------------------------------------------
export interface OperatorIntervention {
  type: 'APPROVAL_BARRIER' | 'EXECUTION_FAILURE' | 'HEALTH_DEGRADED' | 'MANUAL_HOLD';
  title: string;
  description: string;
  durabilityStatus: string;
  barrierGateName?: string;
  barrierId?: string;
  requiredSignatures?: number;
  currentSignatures?: number;
  separationOfDutiesEnforced?: boolean;
  recoveryGuidance?: string;
  isResolved: boolean;
  validActions: CanonicalPermittedAction[];
}

// ----------------------------------------------------------------------------
// 8. CURRENT PHYSICAL ACTIVITY
// ----------------------------------------------------------------------------
export interface CurrentActivitySnapshot {
  activeStageName: string;
  activeEntityName: string;
  entityType: string;
  partitionChunkInfo: string;
  activeWorkerCount: number;
  totalWorkerCount: number;
  throughputRowsSec: number;
  throughputBytesSec: number;
  elapsedSec: number;
  checkpointContext: string;
  isStalled: boolean;
}

// ----------------------------------------------------------------------------
// 9. DYNAMIC WORKBENCH OPERATIONAL DOMAINS
// ----------------------------------------------------------------------------
export interface TableProgressItem {
  tableName: string;
  schemaName: string;
  rowsTotal: number;
  rowsProcessed: number;
  percentComplete: number;
  throughputRowsSec: number;
  activeWorkers: number;
  state: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'RETRYING';
  retries: number;
}

export interface WorkerTelemetryItem {
  workerId: string;
  threadId: number;
  siteName: string;
  status: 'ACTIVE' | 'IDLE' | 'UNHEALTHY' | 'DRAINING';
  assignedEntity: string;
  partitionId?: number;
  throughputRowsSec: number;
  memoryMb: number;
  heartbeatAgeMs: number;
  consecutiveRetries: number;
}

export interface ExecutionSiteItem {
  siteId: string;
  siteName: string;
  siteTypeDescriptor: string; // Extensible descriptor (e.g. "Local Host", "Remote Agent", "K8s Worker Pool")
  livenessState: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
  workerCapacity: number;
  workersAllocated: number;
  latencyMs: number;
  isDrainPending: boolean;
}

export interface SchemaObjectExecutionItem {
  objectName: string;
  objectType: string;
  order: number;
  status: 'PENDING' | 'APPLYING' | 'SUCCEEDED' | 'FAILED' | 'SKIPPED';
  executionTimeMs?: number;
  errorMessage?: string;
}

export interface DynamicWorkbenchData {
  mode: MigrationMode;
  availableDomains: string[];
  activeDomainId: string;

  // Domain 1: Data Movement (M1, M2, M7)
  dataMovement?: {
    totalTables: number;
    completedTables: number;
    activeTablesCount: number;
    overallRowsSec: number;
    overallBytesSec: number;
    tableProgressList: TableProgressItem[];
  };

  // Domain 2: CDC & Convergence (M2, M3)
  cdcConvergence?: {
    captureScn: string;
    applyLsn: string;
    lagMs: number;
    backlogBytes: number;
    applyTxSec: number;
    bufferCapacityMb: number;
    bufferUsedMb: number;
    convergenceStatus: 'CONVERGED' | 'CONVERGING' | 'FALLING_BEHIND' | 'STALLED';
    dlqCount: number;
  };

  // Domain 3: Workers Pool (Universal)
  workersPool?: {
    totalWorkers: number;
    activeWorkers: number;
    idleWorkers: number;
    unhealthyWorkers: number;
    workersList: WorkerTelemetryItem[];
  };

  // Domain 4: Execution Sites (Universal)
  executionSites?: {
    sitesList: ExecutionSiteItem[];
  };

  // Domain 5: Checkpoint & Recovery (Universal)
  checkpointRecovery?: {
    lastCheckpointTimestamp: string;
    lastCheckpointScn: string;
    freshnessSeconds: number;
    resumePosition: string;
    activeAttempt: number;
    recoveryStrategy: string;
    isDurable: boolean;
  };

  // Domain 6: Validation & Integrity (M1, M2, M7 where present)
  validationIntegrity?: {
    validationMode: string;
    rowCountMatchRate: number;
    checksumMatchRate: number;
    discrepanciesCount: number;
    discrepancySample: { entity: string; issue: string; impact: string }[];
  };

  // Domain 7: Schema Execution (M6 Schema Only)
  schemaExecution?: {
    totalObjects: number;
    completedObjects: number;
    failedObjects: number;
    currentDdl: string;
    objectStream: SchemaObjectExecutionItem[];
  };

  // Domain 8: Incremental Polling (M4 Incremental)
  incrementalPolling?: {
    watermarkColumn: string;
    currentWatermarkValue: string;
    pollIntervalSec: number;
    lastPollDurationMs: number;
    recordsLastCycle: number;
    nextPollScheduled: string;
    cycleState: 'IDLE' | 'QUERYING' | 'APPLYING';
  };

  // Domain 9: State Synchronization (M5 State Sync)
  stateSync?: {
    comparisonCycle: number;
    divergenceCount: number;
    correctionsApplied: number;
    unresolvedDiffs: number;
    convergenceTrend: string;
    lastReconciliationTimestamp: string;
  };

  // Domain 10: Retry & Throttling
  retryThrottling?: {
    retryQueueLength: number;
    activeBackoffSec: number;
    sourcePressure: 'LOW' | 'MODERATE' | 'HIGH';
    targetPressure: 'LOW' | 'MODERATE' | 'HIGH';
    bufferPressure: 'LOW' | 'MODERATE' | 'HIGH';
  };
}

// ----------------------------------------------------------------------------
// 10. PREVIOUS / NOW / NEXT EXECUTION CONTEXT
// ----------------------------------------------------------------------------
export interface ExecutionContextNarrative {
  previousCompleted: {
    stageName: string;
    summary: string;
    completedAt: string;
  };
  currentNow: {
    stageName: string;
    summary: string;
    activeSince: string;
  };
  nextPlanned: {
    stageName: string;
    summary: string;
    isBlocked: boolean;
    dependencyNotice?: string;
  };
}

// ----------------------------------------------------------------------------
// 11. CHRONOLOGICAL ACTIVITY & LOGS DOCK
// ----------------------------------------------------------------------------
export interface CockpitActivityEvent {
  id: string;
  timestamp: string;
  category: 'LIFECYCLE' | 'STAGE' | 'WORKER' | 'CHECKPOINT' | 'CDC' | 'BARRIER' | 'HEALTH' | 'ERROR';
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';
  message: string;
  sourceComponent?: string;
  metadata?: Record<string, any>;
}

// ----------------------------------------------------------------------------
// 12. CANONICAL PERMITTED ACTIONS
// ----------------------------------------------------------------------------
export interface CanonicalPermittedAction {
  id: string;
  label: string;
  icon: string;
  isPrimary: boolean;
  isDestructive: boolean;
  confirmationRequired: boolean;
  confirmationTitle?: string;
  confirmationMessage?: string;
  confirmationImpacts?: string[];
  disabled?: boolean;
  disabledReason?: string;
}
