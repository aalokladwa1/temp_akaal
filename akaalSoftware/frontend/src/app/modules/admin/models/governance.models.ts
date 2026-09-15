/**
 * AKAAL Administration — 5.3 Governance Centre Domain Models
 */

export interface GovernancePolicy {
  id: string;
  name: string;
  code: string;
  description: string;
  category: 'DATA_CLASSIFICATION' | 'OPERATIONAL_ISOLATION' | 'ENCRYPTION_KEY' | 'SCHEMA_FREEZE';
  enforcementLevel: 'MANDATORY_BLOCKING' | 'AUDIT_WARNING' | 'DISABLED';
  targetScope: 'GLOBAL' | 'ORGANIZATION' | 'WORKSPACE';
  boundResourcesCount: number;
  updatedAt: string;
  updatedBy: string;
}

export interface PolicySimulationResult {
  policyCode: string;
  targetResource: string;
  action: string;
  evaluationDecision: 'PERMITTED' | 'DENIED' | 'REQUIRES_FOUR_EYES_APPROVAL';
  reasons: string[];
  evaluatedAt: string;
}

export interface ApprovalChain {
  id: string;
  name: string;
  code: string;
  description: string;
  targetOperation: string;
  stagesCount: number;
  quorumApproversRequired: number;
  timeoutHours: number;
  status: 'ACTIVE' | 'DRAFT' | 'DISABLED';
  createdAt: string;
}

export interface ApproverGroup {
  id: string;
  name: string;
  code: string;
  description: string;
  eligibleApprovers: { name: string; email: string; title: string }[];
  quorumThreshold: number;
  status: 'ACTIVE' | 'SUSPENDED';
  createdAt: string;
}

export interface MakerCheckerPolicy {
  id: string;
  entityType: 'MIGRATION_EXECUTION' | 'SCHEMA_ALTERATION' | 'SECRET_ROTATION' | 'POLICY_MUTATION';
  dualControlEnforced: boolean;
  selfApprovalProhibited: boolean;
  quorumRequirement: number;
  auditAttestationRequired: boolean;
  updatedAt: string;
  updatedBy: string;
}

export interface SodRule {
  id: string;
  code: string;
  name: string;
  description: string;
  incompatibleRoleA: string;
  incompatibleRoleB: string;
  enforcementMode: 'PREVENTATIVE_BLOCKING' | 'DETECTIVE_AUDIT';
  activeViolationsCount: number;
  createdAt: string;
}

export interface PrivilegedOperationConfig {
  id: string;
  operationCode: string;
  operationName: string;
  riskTier: 'CRITICAL_HSM' | 'HIGH_TRANSACTIONAL' | 'ELEVATED_SCHEMA';
  approvalChainName: string;
  fourEyesRequired: boolean;
  breakGlassEligible: boolean;
  status: 'PROTECTED' | 'RESTRICTED';
}

export interface GovernanceWaiver {
  id: string;
  waiverCode: string;
  justification: string;
  targetPolicy: string;
  targetResource: string;
  beneficiaryPrincipal: string;
  approvedBy: string;
  validFrom: string;
  validUntil: string;
  status: 'ACTIVE' | 'EXPIRED' | 'REVOKED';
}

export interface BreakGlassConfig {
  id: string;
  status: 'ESCROW_ARMED' | 'ACTIVATED_ELEVATED' | 'STANDBY_LOCKED';
  emergencyEscrowKeyId: string;
  primaryIncidentCommander: string;
  secondaryIncidentCommander: string;
  autoRevokeHours: number;
  lastDrillDate: string;
  totalHistoricalActivations: number;
}

export interface GovernanceAuditRecord {
  id: string;
  eventType: string;
  principalName: string;
  principalEmail: string;
  targetResource: string;
  decision: 'APPROVED' | 'REJECTED' | 'ENFORCED' | 'WAIVED' | 'ELEVATED';
  timestamp: string;
  details: string;
}
