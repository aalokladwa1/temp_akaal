/**
 * validation-results.models.ts
 * =====================================
 * Type definitions and contracts for Workspace 4: Results & Evidence.
 * 
 * Strict Architectural Laws:
 * 1. Independent State Dimensions: Verdict (Validation #11), ComparisonMode (SYNC/ASYNC),
 *    TemporalModel (Consistent-State/Continuous), ExecutionState, and Baseline are decoupled.
 * 2. Evidence #12 = Provenance / Content Integrity Digest (sha256:...). Digest !== Digital Signature.
 * 3. No Frontend-Invented Severity (Critical/High/Medium/Low).
 * 4. No Fake Parity Percentages or Compliance Certificates.
 */

export type FinalValidationVerdict =
  | 'NOT_EVALUATED'
  | 'PASSED'
  | 'FAILED'
  | 'WITHHELD';

export type ComparisonMode =
  | 'SYNC'
  | 'ASYNC'
  | 'UNKNOWN';

export type TemporalModel =
  | 'CONSISTENT_STATE'
  | 'CONTINUOUS'
  | 'UNSPECIFIED';

export type ValidationExecutionState =
  | 'NOT_CONNECTED'
  | 'QUEUED'
  | 'RUNNING'
  | 'PAUSED'
  | 'INTERRUPTED'
  | 'RECOVERING'
  | 'BLOCKED'
  | 'COMPLETED';

export type BaselineState =
  | 'VALID'
  | 'STALE'
  | 'NOT_AVAILABLE';

export type AssuranceTierLevel =
  | 'STRUCTURAL'
  | 'CARDINALITY'
  | 'PARTITION_FINGERPRINT'
  | 'COMPLETE_ATTRIBUTE';

export type AssuranceTierStatus =
  | 'NOT_EVALUATED'
  | 'PASSED'
  | 'FAILED'
  | 'SKIPPED';

export interface AssuranceTierResult {
  level: AssuranceTierLevel;
  tierNumber: number;
  title: string;
  description: string;
  status: AssuranceTierStatus;
  evaluatedScopeSummary: string;
  details: string;
  note?: string;
}

export interface EndpointIdentity {
  provider: string;
  label: string;
  host: string;
  objectCount?: number | null;
}

export interface UnresolvedFindingsSummary {
  totalCount: number;
  affectedObjectsCount: number;
  affectedCategories: string[];
  sampleObjects?: string[];
  discrepanciesTabTarget: string;
}

export interface RemediationLineageRecord {
  hasRemediationHistory: boolean;
  initialValidation?: {
    runId: string;
    verdict: FinalValidationVerdict;
    timestamp: string;
    discrepancyCount: number;
  };
  controlledRemediation?: {
    repairPlanId: string;
    strategy: string;
    executedAt: string;
    status: 'COMPLETED' | 'FAILED' | 'PENDING';
    operationsCount: number;
  };
  revalidation?: {
    runId: string;
    verdict: FinalValidationVerdict;
    completedAt: string;
    remainingDiscrepancies: number;
    notes?: string;
  };
}

export interface ValidationRunRecord {
  runId: string;
  trigger: 'MANUAL' | 'SCHEDULED' | 'REVALIDATION';
  startedAt: string;
  completedAt?: string;
  durationFormatted: string;
  verdict: FinalValidationVerdict;
  comparisonMode: ComparisonMode;
  evaluatedObjectsCount: number | null;
  unresolvedCount: number | null;
  operator?: string;
}

export interface EvidenceIntegrityRecord {
  evidenceAvailable: boolean;
  evidenceBundleId?: string;
  contentDigest?: string; // e.g. sha256:d8e8fca234...
  digestAlgorithm?: string; // SHA-256
  generatedAt?: string;
  bundleSizeBytes?: number;
  bundleSizeFormatted?: string;
  integrityNote?: string;
  storageLocation?: string; // Strictly exposed in technical drawer only
}

export interface AuditTimelineEventRecord {
  id: string;
  timestamp: string;
  actor?: string;
  category: 'VALIDATION' | 'REMEDIATION' | 'EVIDENCE' | 'SYSTEM';
  title: string;
  description: string;
}

export interface ArtifactReference {
  id: string;
  name: string;
  format: string;
  description: string;
  ready: boolean;
}

export interface ArtifactsSummary {
  generationAvailable: boolean;
  availabilityNotice?: string;
  artifacts: ArtifactReference[];
}

export interface TechnicalProvenanceDrawerData {
  canonicalValidationId: string;
  planId?: string;
  planFingerprint?: string;
  enginePlacement?: string;
  engineVersion?: string;
  workerCount?: number | null;
  p7bFabric?: {
    site?: string;
    region?: string;
    placementNode?: string;
    failoverReady?: boolean;
  };
  contentDigest?: string;
  checkpointReference?: string;
  storageLocation?: string;
}

export type ResultsViewStatus =
  | 'READY'
  | 'NOT_EVALUATED'
  | 'WITHHELD'
  | 'UNAVAILABLE'
  | 'LOADING'
  | 'ERROR';

export interface ResultsWorkspaceState {
  viewStatus: ResultsViewStatus;
  errorMessage?: string;
  isProductionDefault: boolean;
  activeScenarioId?: string;
  isTechnicalDrawerOpen: boolean;

  // Independent Core Dimensions
  validationId: string;
  validationName: string;
  verdict: FinalValidationVerdict;
  comparisonMode: ComparisonMode;
  temporalModel: TemporalModel;
  executionState: ValidationExecutionState;
  baselineState: BaselineState;
  completedAt?: string;
  durationFormatted?: string;
  operator?: string;
  verdictSummaryNote?: string;

  // Visual Sections
  source: EndpointIdentity;
  target: EndpointIdentity;
  assuranceTiers: AssuranceTierResult[];
  unresolvedFindings?: UnresolvedFindingsSummary | null;
  remediationLineage: RemediationLineageRecord;
  runs: ValidationRunRecord[];
  selectedRunId?: string;
  evidence: EvidenceIntegrityRecord;
  auditTimeline: AuditTimelineEventRecord[];
  artifacts: ArtifactsSummary;
  technicalDetails: TechnicalProvenanceDrawerData;
}
