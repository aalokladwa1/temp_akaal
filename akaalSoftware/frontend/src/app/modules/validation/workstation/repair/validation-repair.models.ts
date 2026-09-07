/**
 * validation-repair.models.ts
 * =====================================
 * Canonical models and UI view contracts for the Controlled Repair & Revalidation workspace.
 * 
 * Absolute Laws:
 * 1. M8 Validation is strictly read-only and non-mutating.
 * 2. Controlled Repair is a separate governed mutating path.
 * 3. Pre-P7D production default must remain truthful (UNAVAILABLE / NOT_CONNECTED).
 * 4. Selection != Eligibility. Approval != Authorization. Repair Success != Validation Passed.
 * 5. UNKNOWN commit outcome remains UNKNOWN absent provider-native verification.
 * 6. Mandatory return to Validation #11 for revalidation.
 */

export type RepairProposalDimension =
  | 'UNAVAILABLE'
  | 'DRAFT'
  | 'READY_FOR_EVALUATION'
  | 'ESTABLISHED';

export type RepairEligibilityDimension =
  | 'NOT_EVALUATED'
  | 'ELIGIBLE'
  | 'INELIGIBLE'
  | 'UNAVAILABLE';

export type GovernanceDimension =
  | 'NOT_EVALUATED'
  | 'NO_APPROVAL_REQUIRED'
  | 'APPROVAL_REQUIRED'
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'UNAVAILABLE';

export type ExecutionDimension =
  | 'NOT_STARTED'
  | 'SCHEDULED'
  | 'RUNNING'
  | 'INTERRUPTED'
  | 'RECOVERING'
  | 'COMPLETED'
  | 'FAILED'
  | 'OUTCOME_UNKNOWN'
  | 'UNAVAILABLE';

export type RevalidationDimension =
  | 'NOT_REQUIRED'
  | 'REQUIRED'
  | 'NOT_STARTED'
  | 'RUNNING'
  | 'PASSED'
  | 'FAILED'
  | 'WITHHELD'
  | 'INTERRUPTED'
  | 'UNAVAILABLE';

export type RepairViewStatus =
  | 'READY'
  | 'UNAVAILABLE'
  | 'NO_REMEDIATION_REQUIRED'
  | 'AUDIT_ONLY'
  | 'LOADING'
  | 'ERROR';

export type RepairOperationFamily =
  | 'UPDATE_DIFFERING_ATTRIBUTES'
  | 'INSERT_MISSING_TARGET'
  | 'DELETE_EXTRA_TARGET'
  | 'STRUCTURAL_UNSUPPORTED'
  | 'NO_SAFE_AUTOMATIC_PROPOSAL'
  | 'MANUAL_REMEDIATION';

export type RepairRiskLevel =
  | 'LOW'
  | 'MEDIUM'
  | 'HIGH'
  | 'CONSEQUENTIAL_DESTRUCTIVE';

export type AttributeValueKind =
  | 'SCALAR'
  | 'NULL'
  | 'EMPTY_STRING'
  | 'WHITESPACE'
  | 'PROTECTED'
  | 'LOB_TRUNCATED'
  | 'ABSENT';

export interface ProposedAttributeChange {
  attributeName: string;
  sourceValue: any;
  sourceValueKind: AttributeValueKind;
  sourceType?: string;
  currentTargetValue: any;
  currentTargetValueKind: AttributeValueKind;
  currentTargetType?: string;
  proposedTargetValue: any;
  proposedTargetValueKind: AttributeValueKind;
  proposedTargetType?: string;
  isKey?: boolean;
  isSensitive?: boolean;
  transformationNote?: string;
  lobMetadata?: {
    byteLength: number;
    mimeType: string;
    digest?: string;
  };
}

export interface RepairProposalModel {
  proposalId: string;
  proposalVersion: string;
  proposalFingerprint: string;
  operationFamily: RepairOperationFamily;
  targetObject: string;
  recordKey: string;
  summaryNote: string;
  detailedRationale: string;
  proposedChanges: ProposedAttributeChange[];
  canonicalDmlPreview?: string;
  createdAt: string;
}

export interface RepairImpactPreviewModel {
  affectedObjectsCount: number;
  affectedRecordsCount: number;
  affectedAttributesCount: number;
  targetSystem: string;
  targetEndpointLabel: string;
  targetLocation: string;
  estimatedWriteScope: string;
  protectedDataInvolved: boolean;
  revalidationObligation: string;
  riskLevel: RepairRiskLevel;
  riskExplanation: string;
}

export interface GovernanceApprover {
  role: string;
  userName?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  timestamp?: string;
  signatureDigest?: string;
}

export interface RepairGovernanceModel {
  state: GovernanceDimension;
  policyId: string;
  policyName: string;
  policySummary: string;
  approvalRequired: boolean;
  quorumRequired: number;
  quorumSatisfied: number;
  makerCheckerSatisfied: boolean;
  approvers: GovernanceApprover[];
  conditions: string[];
  boundPlanFingerprint: string;
  expiresAt?: string;
  rejectionReason?: string;
  isAuthorized: boolean;
  authorizationNote?: string;
}

export interface P7bExecutionContext {
  site: string;
  placement: string;
  locality: string;
  residency: string;
  ownershipFencing: string;
  recoveryStatus: string;
  leaseExpiresAt?: string;
}

export interface RepairExecutionModel {
  state: ExecutionDimension;
  executionId?: string;
  scheduledAt?: string;
  startedAt?: string;
  completedAt?: string;
  progressPercent: number;
  totalOperations: number;
  appliedCount: number;
  unresolvedCount: number;
  unknownOutcomeCount: number;
  errorMessage?: string;
  unknownOutcomeWarning?: string;
  providerCommitState: 'CONFIRMED' | 'UNCONFIRMED' | 'UNKNOWN';
  p7bContext?: P7bExecutionContext;
}

export interface RevalidationProofTierItem {
  tier: string;
  name: string;
  status: 'PASSED' | 'FAILED' | 'WITHHELD' | 'RUNNING' | 'PENDING';
  detail: string;
  differencesFound: number;
}

export interface RepairRevalidationModel {
  state: RevalidationDimension;
  revalidationId?: string;
  engine: string;
  startedAt?: string;
  completedAt?: string;
  proofTiers: RevalidationProofTierItem[];
  remainingDiscrepanciesCount: number;
  verdictSummary: string;
  findingsNote?: string;
  withheldReason?: string;
}

export interface SelectedFindingsScopeModel {
  selectionSetId: string;
  totalSelectedFindings: number;
  selectedObjects: string[];
  affectedRecordKeys: string[];
  findingCategories: string[];
  originatingWorkspace: 'DISCREPANCIES' | 'MANUAL' | 'DIRECT';
  selectionTimestamp: string;
  isBulkAggregate: boolean;
}

export interface RemediationSummaryModel {
  overallState: string;
  conciseExplanation: string;
  eligibility: RepairEligibilityDimension;
  proposalState: RepairProposalDimension;
  governanceState: GovernanceDimension;
  executionState: ExecutionDimension;
  revalidationState: RevalidationDimension;
  isExecutorAvailable: boolean;
  isReadonlyMission: boolean;
}

export interface RepairTechnicalDetailsModel {
  proposalId?: string;
  proposalVersion?: string;
  proposalFingerprint?: string;
  executionId?: string;
  providerOperationId?: string;
  checkpointSequence?: string;
  p7bPlacementDigest?: string;
  recoveryJournalRef?: string;
  evidenceRef?: string;
  revalidationMissionId?: string;
  canonicalDmlStatement?: string;
}

export interface RepairWorkspaceState {
  viewStatus: RepairViewStatus;
  summary: RemediationSummaryModel;
  selectedScope: SelectedFindingsScopeModel;
  proposal: RepairProposalModel | null;
  impact: RepairImpactPreviewModel | null;
  governance: RepairGovernanceModel | null;
  execution: RepairExecutionModel | null;
  revalidation: RepairRevalidationModel | null;
  technicalDetails: RepairTechnicalDetailsModel | null;
  errorMessage?: string;
  isConfirmModalOpen: boolean;
  isTechnicalDrawerOpen: boolean;
  activeScenarioId?: string;
}
