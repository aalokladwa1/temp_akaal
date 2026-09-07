// ============================================================================
// AKAAL CREATE MIGRATION — STEP 9: REVIEW, SCHEDULE & INITIALIZE
// PRESENTATION & INTEGRATION DATA MODELS
// ============================================================================

import { MigrationMode, PhysicalProviderId } from '../../../../core/models/migration-view.models';

// ----------------------------------------------------------------------------
// 1. MIGRATION IDENTITY & ROUTE
// ----------------------------------------------------------------------------
export interface MigrationIdentityPresentation {
  /** Canonical Migration ID originating from creation context (e.g. MIG-2026-0906-A1) [BACKEND-SUPPLIED] */
  migrationId: string;
  /** Human-readable migration draft title [BACKEND-SUPPLIED] */
  migrationName: string;
  /** Deployment target environment: Production, Non-Production, Staging, etc. [BACKEND-SUPPLIED] */
  environment: string;
  /** Canonical migration mode: M1_BULK through M7_DATA_ONLY [BACKEND-SUPPLIED] */
  mode: MigrationMode;
  /** Formatted title of execution mode (e.g. Bulk Migration + Continuous CDC) [PRESENTATION-DERIVED] */
  modeTitle: string;
  /** Source provider endpoint metadata [BACKEND-SUPPLIED] */
  source: {
    provider: PhysicalProviderId | string;
    host?: string;
    port?: number;
    database?: string;
    label: string;
  };
  /** Target provider endpoint metadata [BACKEND-SUPPLIED] */
  target: {
    provider: PhysicalProviderId | string;
    host?: string;
    port?: number;
    database?: string;
    label: string;
  };
  /** Governed plan revision number [BACKEND-SUPPLIED] */
  planRevision: number;
  /** Governed plan identifier [BACKEND-SUPPLIED] */
  planId: string;
  /** Cryptographic SHA-256 HMAC fingerprint of compiled plan [BACKEND-SUPPLIED] */
  planFingerprint: string;
}

// ----------------------------------------------------------------------------
// 2. MIGRATION REVIEW GROUPS (STEPS 1–8 COLLAPSED SUMMARY)
// ----------------------------------------------------------------------------
export interface ReviewFieldItem {
  label: string;
  value: string;
  detail?: string;
  badge?: string;
  badgeColor?: string;
}

export interface MigrationReviewGroup {
  id: 'SCOPE_DATA' | 'DATA_CONTROLS' | 'EXECUTION' | 'PLAN' | 'GOVERNANCE_READINESS';
  title: string;
  subtitle: string;
  upstreamStep: number;
  upstreamStepLabel: string;
  fields: ReviewFieldItem[];
}

// ----------------------------------------------------------------------------
// 3. BEFORE YOU START (DECISION-QUALITY INTELLIGENCE)
// ----------------------------------------------------------------------------
export type ScaleEvidenceClassification =
  | 'EXACT'
  | 'MEASURED'
  | 'CALCULATED'
  | 'SAMPLED'
  | 'ESTIMATED'
  | 'UNAVAILABLE';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNAVAILABLE';

export type StructuralRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'NONE';

export type ReversibilityClassification =
  | 'REVERSIBLE'
  | 'CONDITIONALLY_REVERSIBLE'
  | 'IRREVERSIBLE'
  | 'STAGE_SPECIFIC';

export interface BeforeYouStartPresentation {
  /** Data scale summary with evidence classification [BACKEND-SUPPLIED / ADAPTER] */
  dataScale: {
    objectCountLabel: string;
    volumeEstimateLabel: string;
    evidenceClassification: ScaleEvidenceClassification;
    evidenceExplanation: string;
  };
  /** Duration estimate range and confidence level [BACKEND-SUPPLIED / ADAPTER] */
  duration: {
    isAvailable: boolean;
    rangeDisplay?: string;
    confidenceLevel?: ConfidenceLevel;
    confidenceExplanation?: string;
  };
  /** Structural and residual risks from canonical analysis [BACKEND-SUPPLIED / ADAPTER] */
  structuralRisk: {
    level: StructuralRiskLevel;
    summary: string;
    residualRisks: string[];
    hasLossyConversions: boolean;
  };
  /** Downstream human intervention points / future approval barriers [BACKEND-SUPPLIED] */
  runtimeIntervention: {
    hasDownstreamBarriers: boolean;
    downstreamBarrierCount: number;
    description: string;
  };
  /** Consequence reversibility classification [BACKEND-SUPPLIED] */
  reversibility: {
    classification: ReversibilityClassification;
    summary: string;
    details: string;
  };
}

// ----------------------------------------------------------------------------
// 4. EXECUTION TIMING
// ----------------------------------------------------------------------------
export type TimingChoice = 'RUN_NOW' | 'SCHEDULE_LATER';

export interface ExecutionTimingState {
  choice: TimingChoice;
  scheduledDate: string;      // YYYY-MM-DD
  scheduledTime: string;      // HH:mm (24-hour)
  selectedTimezone: string;   // e.g. 'UTC', 'Asia/Kolkata', 'America/New_York'
  isAdvancedRecurring: boolean;
  recurrenceFrequency: 'DAILY' | 'WEEKLY' | 'MONTHLY';
  isRecurrencePermittedForMode: boolean;
  resolvedLocalDisplay: string;
  resolvedUtcDisplay: string;
  isValid: boolean;
  validationError?: string;
}

// ----------------------------------------------------------------------------
// 5. WHAT HAPPENS NEXT (CONSEQUENCE EXPLAINER)
// ----------------------------------------------------------------------------
export interface ConsequencePresentation {
  title: string;
  primaryActionDescription: string;
  subsequentSteps: string[];
  isProduction: boolean;
  productionNotice?: string;
  firstStageLabel?: string;
}

// ----------------------------------------------------------------------------
// 6. TECHNICAL DETAILS MODAL / OVERLAY
// ----------------------------------------------------------------------------
export interface TechnicalDetailsPresentation {
  migrationId: string;
  planId: string;
  planRevision: number;
  planFingerprint: string;
  policyBinding: string;
  governanceSealStatus: string;
  executionMode: string;
  sourceEndpoint: string;
  targetEndpoint: string;
  structuralRiskEvidence: string;
  scaleEvidence: string;
  scheduleIdentity?: string;
  executionAttemptId?: string;
  dispatchState: string;
}

// ----------------------------------------------------------------------------
// 7. LIFECYCLE & SUBMISSION STATE
// ----------------------------------------------------------------------------
export type Step9SubmitPhase =
  | 'IDLE'
  | 'INITIALIZING'
  | 'STARTING'
  | 'SCHEDULING'
  | 'SUCCESS'
  | 'ERROR';

export interface Step9OperationError {
  phase: 'INITIALIZATION' | 'START' | 'SCHEDULING' | 'IPC';
  title: string;
  message: string;
  isRetryable: boolean;
  recoveryGuidance?: string;
}
