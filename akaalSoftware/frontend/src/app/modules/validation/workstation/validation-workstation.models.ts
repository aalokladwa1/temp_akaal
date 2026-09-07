export type ValidationExecutionState =
  | 'NOT_CONNECTED'
  | 'QUEUED'
  | 'RUNNING'
  | 'PAUSED'
  | 'INTERRUPTED'
  | 'RECOVERING'
  | 'BLOCKED'
  | 'COMPLETED';

export type ValidationVerdict =
  | 'NOT_EVALUATED'
  | 'PASSED'
  | 'FAILED'
  | 'WITHHELD';

export type WorkstationWorkspaceTab =
  | 'overview'
  | 'discrepancies'
  | 'repair'
  | 'evidence';

export type ProofTierLevel =
  | 'structural'
  | 'cardinality'
  | 'partition'
  | 'attribute';

export type ProofTierStatus =
  | 'NOT_EVALUATED'
  | 'PASSED'
  | 'FAILED'
  | 'EVALUATING'
  | 'SKIPPED';

export interface ProofTierItem {
  id: ProofTierLevel;
  name: string;
  tierNumber: number;
  description: string;
  status: ProofTierStatus;
  evaluatedCount: number | null;
  totalCount: number | null;
  discrepancyCount: number | null;
  details: string;
  note?: string;
}

export type DonutSemanticMode =
  | 'NOT_CONNECTED'
  | 'INDEPENDENT_VALIDATION'
  | 'MIGRATION_SYNC';

export type CanonicalComparisonMode =
  | 'SYNC'
  | 'ASYNC'
  | 'UNKNOWN';

export interface DonutViewModel {
  mode: DonutSemanticMode;
  canonicalComparisonMode?: CanonicalComparisonMode;
  centerPercentage: number | null;
  centerLabel: string;
  centerSubtext: string;
  centerSecondaryText?: string;
  ariaLabel?: string;
  sourceLabel: string;
  sourceType: string;
  sourceHost: string;
  sourceObjectCount: number | null;
  targetLabel: string;
  targetType: string;
  targetHost: string;
  targetObjectCount: number | null;
}

export interface CoverageRow {
  dimension: 'Objects' | 'Records' | 'Attributes';
  inScope: number | null;
  evaluated: number | null;
  remaining: number | null;
  differencesDetected: number | null;
  inconclusive: number | null;
}

export interface SemanticContext {
  samplingPolicy: string;
  tolerance: string;
  concurrency: string;
  failureThreshold: string;
}

export interface AttentionItem {
  id: string;
  severity: 'blocker' | 'warning' | 'info';
  category: 'difference' | 'missing_target' | 'correspondence' | 'baseline';
  title: string;
  description: string;
  timestamp?: string;
  location?: string;
}

export interface RemediationSummary {
  linkedMigrationId?: string;
  linkedMigrationName?: string;
  baselineId?: string;
  baselineHash?: string;
  baselineStatus?: 'VALID' | 'STALE' | 'NOT_AVAILABLE';
  autoRepairPolicy?: string;
  revalidationCount?: number;
  lastRevalidationTimestamp?: string;
}

export interface TechnicalDrawerData {
  canonicalValidationId: string;
  draftId?: string;
  enginePlacement: string;
  engineVersion: string;
  workerCount: number | null;
  maxMemoryLimit: string;
  capabilities: string[];
  evidenceHash?: string;
  signingKeyId?: string;
  evidenceUri?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface WorkstationViewModel {
  validationId: string;
  validationName: string;
  environment: string;
  activeTab: WorkstationWorkspaceTab;
  executionState: ValidationExecutionState;
  verdict: ValidationVerdict;
  source: { provider: string; label: string; host: string };
  target: { provider: string; label: string; host: string };
  elapsedFormatted?: string;
  throughputFormatted?: string;
  etaFormatted?: string;
  activeWorkers?: number;
  checkpointsCount?: number;
  donut: DonutViewModel;
  proofTiers: ProofTierItem[];
  coverage: CoverageRow[];
  semanticContext: SemanticContext;
  attentionItems: AttentionItem[];
  remediation: RemediationSummary;
  technicalDrawer: TechnicalDrawerData;
  isProductionDefault: boolean;
  drawerOpen: boolean;
}
