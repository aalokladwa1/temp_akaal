export type ExecutionMode = 
  | 'M1_BULK' 
  | 'M2_BULK_CDC' 
  | 'M3_CDC_CONTINUOUS' 
  | 'M4_INCREMENTAL' 
  | 'M5_STATE_SYNC' 
  | 'M6_SCHEMA_ONLY' 
  | 'M7_DATA_ONLY' 
  | 'M8_VALIDATION_ONLY';

export type LifecycleState = 
  | 'RUNNING' 
  | 'PAUSED' 
  | 'BLOCKED' 
  | 'COMPLETED' 
  | 'FAILED' 
  | 'QUEUED' 
  | 'VALIDATING' 
  | 'CATCHING_UP'
  | 'UNKNOWN';

export interface ActiveMigration {
  id: string;
  name: string;
  sourceEngine: string;
  targetEngine: string;
  sourceEndpoint: string;
  targetEndpoint: string;
  mode: ExecutionMode;
  state: LifecycleState;
  
  // Capability-aware properties:
  // For Bulk / Staged (M1, M2, M7):
  progressPercent?: number | null; // e.g. 73.5 (ONLY for bulk/finite operations)
  processedRows?: number | null;
  totalRows?: number | null;
  throughputRowsSec?: number | null;
  throughputMbSec?: number | null;
  etaSeconds?: number | null;
  
  // For CDC / Continuous Replication (M2 catchup, M3 live):
  cdcLagMs?: number | null;       // e.g. 2.1 ms
  cdcBacklogEvents?: number | null;
  cdcCurrentSsn?: string | null;
  
  // For Incremental / State Sync / Validation (M4, M5, M8):
  lastWatermark?: string | null;
  reconciliationState?: string | null;
  
  hasWarning?: boolean;
  warningMessage?: string | null;
  startedAt?: string | null;
}

export type AttentionSeverity = 'critical' | 'blocked' | 'failed' | 'approval_required' | 'warning' | 'info';

export interface AttentionItem {
  id: string;
  migrationId?: string | null;
  title: string;
  description: string;
  severity: AttentionSeverity;
  category: 'approval' | 'backlog' | 'capacity' | 'connector' | 'error' | 'validation';
  actionLabel?: string | null;
  timestamp?: string | null;
}

export interface SubsystemStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unavailable' | 'unknown';
  detail?: string | null;
  metric?: string | null;
}

export interface PendingApproval {
  id: string;
  migrationName: string;
  operation: string;
  boundary: string;
  requester: string;
  requestedAt: string;
  quorum: string; // e.g. '2 of 3 Required'
  severity: 'critical' | 'normal';
}

export interface CapacityMetric {
  resource: string;
  used: number | null;
  total: number | null;
  unit: string;
  percent: number | null;
  status: 'normal' | 'elevated' | 'critical' | 'unavailable';
}

export interface AlertIncident {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  subject: string;
  context: string;
  age: string;
  isActionable: boolean;
}

export interface FleetClusterSummary {
  clusterState: 'healthy' | 'degraded' | 'unconfigured' | 'unavailable';
  nodeCount: number | null;
  activeWorkers: number | null;
  totalCapacityCores: number | null;
  detail: string;
}

export interface SecurityComplianceSummary {
  posture: 'enforced' | 'partial' | 'unconfigured' | 'unavailable';
  mTLSEnabled: boolean | null;
  vaultEncryption: boolean | null;
  auditLedgerActive: boolean | null;
  detail: string;
}

export interface OperationalEvent {
  id: string;
  migrationName?: string | null;
  type: 'started' | 'completed' | 'paused' | 'approval_granted' | 'validation_passed' | 'warning_raised';
  description: string;
  operator: string;
  timestamp: string;
}

export interface DashboardSummary {
  runningCount: number | null;
  scheduledCount: number | null;
  attentionCount: number | null;
  completedTodayCount: number | null;
  activeMigrations: ActiveMigration[];
  attentionItems: AttentionItem[];
  subsystems: SubsystemStatus[];
  pendingApprovals: PendingApproval[];
  capacityMetrics: CapacityMetric[];
  incidents: AlertIncident[];
  fleet: FleetClusterSummary | null;
  security: SecurityComplianceSummary | null;
  recentEvents: OperationalEvent[];
}
