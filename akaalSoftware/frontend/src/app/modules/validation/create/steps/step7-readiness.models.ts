/**
 * Step 7 — Governance & Readiness Models
 *
 * Defines presentation models, scalable readiness domains, and presentation states.
 * NOTE: Angular renders these states; it does NOT author canonical backend readiness truth.
 */

export type ValidationReadinessStatus =
  | 'NOT_EVALUATED'
  | 'EVALUATING'
  | 'READY'
  | 'READY_WITH_ATTENTION'
  | 'AWAITING_GOVERNANCE'
  | 'BLOCKED'
  | 'STALE'
  | 'EVALUATION_UNAVAILABLE';

export type ValidationReadinessDomain =
  | 'CONNECTIVITY_ACCESS'
  | 'SCOPE_CORRESPONDENCE'
  | 'BASELINE_LEGITIMACY'
  | 'ASSURANCE_COMPATIBILITY'
  | 'GOVERNANCE_OPERATIONAL';

export type CheckEvaluationStatus = 'READY' | 'WARNING' | 'BLOCKER' | 'NOT_EVALUATED';

export interface ReadinessCheckItem {
  id: string;
  domain: ValidationReadinessDomain;
  name: string;
  status: CheckEvaluationStatus;
  observation: string;
  affectedResources: string[];
  technicalDetail?: string;
  remediationGuidance?: string;
}

export interface DomainCategoryGroup {
  id: ValidationReadinessDomain;
  title: string;
  description: string;
  checks: ReadinessCheckItem[];
  passedCount: number;
  totalCount: number;
  hasBlockers: boolean;
  hasWarnings: boolean;
  isExpanded: boolean;
}

export interface RequiredActionItem {
  id: string;
  severity: 'BLOCKER' | 'ACKNOWLEDGEMENT_REQUIRED' | 'WARNING';
  title: string;
  description: string;
  actionLabel: string;
  upstreamStep?: number;
  ackId?: string;
}

export interface OperationalAcknowledgement {
  id: string;
  title: string;
  summary: string;
  isAcknowledged: boolean;
  acknowledgedAt?: string;
  acknowledgedBy?: string;
}

export interface OverallValidationReadiness {
  status: ValidationReadinessStatus;
  statusLabel: string;
  summaryText: string;
  domainsCount: number;
  passedChecksCount: number;
  totalChecksCount: number;
  requiredActionCount: number;
  isEvaluationConnected: boolean;
}

export interface Step7VisualFixture {
  status: ValidationReadinessStatus;
  statusLabel: string;
  summaryText: string;
  isEvaluationConnected: boolean;
  domains: DomainCategoryGroup[];
  actions: RequiredActionItem[];
  acknowledgements: OperationalAcknowledgement[];
}
