/**
 * AKAAL Enterprise Migration Platform
 * Step 8: Governance & Readiness (Models & Presentation Contracts)
 *
 * Authority Invariant:
 * Canonical Backend Authorities / IPC -> Wails Bridge -> Angular Adapter/Store -> Presentation
 * Angular only maps and presents canonical truth; it does not mint governance authority.
 */

// ----------------------------------------------------------------------------
// 1. OVERALL READINESS PRESENTATION
// ----------------------------------------------------------------------------
export type OverallReadinessStatus = 'READY' | 'AWAITING_APPROVALS' | 'ACTION_REQUIRED' | 'NOT_READY';

export interface OverallReadinessPresentation {
  status: OverallReadinessStatus;
  statusLabel: string;
  summaryText: string;
  governanceSummary: {
    approvedCount: number;
    totalCount: number;
    isSatisfied: boolean;
  };
  readinessSummary: {
    passedCount: number;
    totalCount: number;
    warningCount: number;
    blockedCount: number;
  };
  requiredActionCount: number;
}

// ----------------------------------------------------------------------------
// 2. GOVERNANCE GATE PRESENTATION (STEP 7 BOUNDARIES -> STEP 8 FULFILLMENT)
// ----------------------------------------------------------------------------
export type GateApprovalStatus = 'APPROVED' | 'PENDING_APPROVAL' | 'REJECTED' | 'SATISFIED';

export interface GatePrecondition {
  id: string;
  label: string;
  satisfied: boolean;
  requirementDetail?: string;
}

export interface ActorAuthorizationContext {
  currentActorRole: string;
  currentActorName: string;
  isCurrentActorEligible: boolean;
  sodEnforced: boolean;
  sodExplanation?: string;
  isSoloOperatorPermitted: boolean;
}

export interface GovernanceGatePresentation {
  id: string;
  gateName: string;
  description: string;
  isMandatory: boolean;
  stagePlacementLabel: string;
  afterStageId?: string;
  beforeStageId?: string;
  signerPolicyLabel: string;
  signerPolicyCode: string;
  requiredSignatures: number;
  currentSignatures: number;
  status: GateApprovalStatus;
  approverRoles: string[];
  actorContext: ActorAuthorizationContext;
  preconditions: GatePrecondition[];
  rejectionAction: string;
  timeoutMinutes?: number;
  decisionComment?: string;
  decidedAt?: string;
  decidedBy?: string;
  decisionRole?: string;
}

// ----------------------------------------------------------------------------
// 3. TECHNICAL READINESS CHECK PRESENTATION (6 PRESENTATION GROUPS)
// ----------------------------------------------------------------------------
export type ReadinessCheckCategory =
  | 'CONNECTIONS_ACCESS'
  | 'SCHEMA_COMPATIBILITY'
  | 'CHANGE_CAPTURE'
  | 'CAPACITY_RESOURCES'
  | 'EXECUTION_REQUIREMENTS'
  | 'VALIDATION_REQUIREMENTS';

export type ReadinessCheckStatus = 'READY' | 'WARNING' | 'BLOCKED' | 'PENDING';

export interface ReadinessCheckPresentation {
  id: string;
  name: string;
  category: ReadinessCheckCategory;
  status: ReadinessCheckStatus;
  applicableModes: string[];
  observation: string;
  impact: string;
  affectedResources: string[];
  remediationGuidance?: string;
  upstreamStepOwner?: number;
  upstreamStepLabel?: string;
  lastEvaluatedAt: string;
  diagnosticDetails?: {
    probeResultCode: string;
    executionDurationMs: number;
    sanitizedDiagnosticText?: string;
  };
}

export interface ReadinessCategoryGroup {
  id: ReadinessCheckCategory;
  title: string;
  description: string;
  checks: ReadinessCheckPresentation[];
  passedCount: number;
  totalCount: number;
  hasBlockers: boolean;
  hasWarnings: boolean;
  isExpanded: boolean;
}

// ----------------------------------------------------------------------------
// 4. REQUIRED ACTIONS PRESENTATION
// ----------------------------------------------------------------------------
export type ActionSeverity = 'BLOCKER' | 'APPROVAL_REQUIRED' | 'ACKNOWLEDGEMENT_REQUIRED' | 'WARNING';

export interface RequiredActionPresentation {
  id: string;
  severity: ActionSeverity;
  title: string;
  description: string;
  actionLabel: string;
  upstreamStep?: number;
  gateId?: string;
  checkId?: string;
  ackId?: string;
}

// ----------------------------------------------------------------------------
// 5. POLICY ACKNOWLEDGEMENTS PRESENTATION
// ----------------------------------------------------------------------------
export interface PolicyAcknowledgementPresentation {
  id: string;
  title: string;
  riskAssessment: string;
  policyReference: string;
  isPermittedByPolicy: boolean;
  isAcknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  rationale?: string;
}

// ----------------------------------------------------------------------------
// 6. GOVERNED PLAN SNAPSHOT PRESENTATION
// ----------------------------------------------------------------------------
export interface GovernedPlanSnapshot {
  planId: string;
  revision: string;
  fingerprint: string;
  mode: string;
  sourceEngine: string;
  targetEngine: string;
  environment: string;
  governanceState: string;
  readinessState: string;
  sealedChecksum?: string;
  policyBindingVersion?: string;
}

// ----------------------------------------------------------------------------
// 7. GOVERNANCE ACTIVITY AUDIT LOG
// ----------------------------------------------------------------------------
export interface GovernanceActivityEvent {
  id: string;
  timestamp: string;
  eventType: 'EVALUATION' | 'APPROVAL' | 'REJECTION' | 'ACKNOWLEDGEMENT' | 'INVALIDATION';
  actorName: string;
  actorRole: string;
  summary: string;
  details?: string;
}
