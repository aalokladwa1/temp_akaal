/**
 * AKAAL Reports — Part 3: Trust & Certification Domain Models
 * Strict semantic separation: Certification Decision ≠ Validation Finding ≠ Workflow State ≠ UI Data Availability ≠ Verification Result.
 * Zero-fake production law: Truthful types reflecting canonical backend semantics.
 */

export type CertificationDomain = 'MIGRATION' | 'VALIDATION';

/**
 * Formal certification decision state.
 * Distinct from validation findings (e.g. DEFECTS_FOUND) and UI availability (e.g. UNAVAILABLE).
 */
export type CertificationDecisionState = 
  | 'CERTIFIED'
  | 'NOT_CERTIFIED'
  | 'CERTIFICATION_NOT_ISSUED'
  | 'REVOKED'
  | 'EXPIRED'
  | 'PENDING_EVALUATION'
  | 'UNKNOWN';

export type CertificationLifecycleState = 
  | 'ACTIVE'
  | 'SUPERSEDED'
  | 'ARCHIVED'
  | 'DRAFT'
  | 'RETIRED';

/**
 * Evaluation outcome for an individual assertion / criterion.
 */
export type CriterionEvaluationOutcome = 
  | 'SATISFIED'
  | 'NOT_SATISFIED'
  | 'NOT_EVALUATED'
  | 'NOT_APPLICABLE'
  | 'EXCEPTION'
  | 'UNKNOWN';

export type VerificationResultStatus = 
  | 'VERIFIED'
  | 'MISMATCH'
  | 'UNAVAILABLE'
  | 'ERROR';

export type GovernanceDecisionStatus = 
  | 'APPROVED'
  | 'REJECTED'
  | 'PENDING'
  | 'OVERRIDDEN'
  | 'NOT_APPLICABLE';

export type ExceptionStatus = 
  | 'UNRESOLVED'
  | 'WAIVED'
  | 'EXPIRED'
  | 'REQUIRES_MANUAL_REVIEW';

export interface CertificationCriterionDTO {
  id: string;
  name: string;
  required_condition: string;
  observed_result: string;
  outcome: CriterionEvaluationOutcome;
  evidence_ref?: string;
  evidence_title?: string;
}

export interface CertificationEvidenceItemDTO {
  id: string;
  title: string;
  artifact_type: string;
  subject_name: string;
  sha256_digest: string;
  integrity_state: 'VERIFIED' | 'PENDING' | 'UNVERIFIED' | 'UNAVAILABLE';
  created_at: string;
  deep_link_route: string;
}

export interface ApproverRecordDTO {
  role: string;
  actor_name: string;
  timestamp: string;
  decision: string;
}

export interface CertificationGovernanceRecordDTO {
  barrier_name: string;
  decision_status: GovernanceDecisionStatus;
  required_quorum?: number;
  approvals_received?: number;
  required_roles?: string[];
  approvers?: ApproverRecordDTO[];
  conditions?: string[];
}

export interface CertificationExceptionDTO {
  id: string;
  condition: string;
  detail: string;
  status: ExceptionStatus;
  updated_at: string;
}

export interface CertificationIntegrityDTO {
  sha256_fingerprint: string;
  producer_authority: string;
  verification_status: 'VERIFIED' | 'UNVERIFIED' | 'MISMATCH' | 'UNAVAILABLE';
  verification_method: string;
  verified_at?: string;
}

export interface CertificationSummaryDTO {
  id: string;
  domain: CertificationDomain;
  title: string;
  subject_name: string;
  subject_id: string;
  issued_at: string;
  decision: CertificationDecisionState;
  lifecycle: CertificationLifecycleState;
  summary: string;
}

export interface MigrationCertificationPayloadDTO {
  execution_mode: string;
  execution_outcome: string;
  transferred_scope_summary: string;
  checkpoint_recovery_evidence_summary: string;
  cutover_evidence_summary?: string;
  validation_link_summary?: string;
}

export interface ValidationCertificationPayloadDTO {
  validation_scope_summary: string;
  source_target_comparison_summary: string;
  count_reconciliation_summary: string;
  checksum_merkle_summary: string;
  discrepancies_summary: string;
  repair_revalidation_summary?: string;
}

export interface CertificationDetailEnvelopeDTO {
  id: string;
  domain: CertificationDomain;
  title: string;
  subject_name: string;
  subject_id: string;
  issued_at: string;
  producer_authority: string;
  decision: CertificationDecisionState;
  lifecycle: CertificationLifecycleState;
  summary: string;
  scope_summary: string;
  criteria: CertificationCriterionDTO[];
  evidence: CertificationEvidenceItemDTO[];
  governance?: CertificationGovernanceRecordDTO;
  exceptions: CertificationExceptionDTO[];
  integrity: CertificationIntegrityDTO;
  related_report_ids: string[];
  migration_payload?: MigrationCertificationPayloadDTO;
  validation_payload?: ValidationCertificationPayloadDTO;
}

export interface VerificationResultDTO {
  target_identifier: string;
  target_type: 'CERTIFICATION' | 'EVIDENCE_ARTIFACT' | 'REPORT_MANIFEST';
  method: string;
  result_status: VerificationResultStatus;
  verified_at: string;
  stored_fingerprint?: string;
  computed_fingerprint?: string;
  detail_notes: string;
}

export function formatCertificationDecision(decision: CertificationDecisionState): string {
  switch (decision) {
    case 'CERTIFIED': return 'Certified';
    case 'NOT_CERTIFIED': return 'Not Certified';
    case 'CERTIFICATION_NOT_ISSUED': return 'No Certification Issued';
    case 'REVOKED': return 'Revoked';
    case 'EXPIRED': return 'Expired';
    case 'PENDING_EVALUATION': return 'Pending Evaluation';
    case 'UNKNOWN':
    default:
      return 'Unknown';
  }
}

export function formatCriterionOutcome(outcome: CriterionEvaluationOutcome): string {
  switch (outcome) {
    case 'SATISFIED': return 'Satisfied';
    case 'NOT_SATISFIED': return 'Not Satisfied';
    case 'NOT_EVALUATED': return 'Not Evaluated';
    case 'NOT_APPLICABLE': return 'Not Applicable';
    case 'EXCEPTION': return 'Exception';
    case 'UNKNOWN':
    default:
      return 'Unknown';
  }
}
