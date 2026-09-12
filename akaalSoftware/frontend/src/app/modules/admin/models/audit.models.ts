/**
 * AKAAL Administration — 5.9 Audit Models
 * Models for Audit Policies, Administrative Audit Trail, Audit Destinations / SIEM,
 * Evidence Retention, Legal Hold, Audit Integrity Verification, and Audit Export.
 */

export type AuditPolicyCategory =
  | 'ADMIN_ACTIONS'
  | 'DATA_ACCESS'
  | 'SECURITY_OPERATIONS'
  | 'PIPELINE_EXECUTION';

export type AuditSeverityFilter = 'ALL' | 'WARNING_AND_ABOVE' | 'ERROR_ONLY';

export interface AuditPolicy {
  id: string;
  name: string;
  category: AuditPolicyCategory;
  severityFilter: AuditSeverityFilter;
  retentionDays: number;
  destinations: string[];
  description: string;
  status: 'ACTIVE' | 'SUSPENDED';
  updatedAt: string;
}

export interface AdministrativeAuditEvent {
  id: string;
  timestamp: string;
  actor: string;
  actorRole: string;
  action: string;
  resourceType: string;
  resourceId: string;
  outcome: 'SUCCESS' | 'FAILURE' | 'DENIED';
  ipAddress: string;
  correlationId: string;
  details: string;
}

export interface AuditDestination {
  id: string;
  name: string;
  destinationType: 'SYSLOG' | 'HTTP_WEBHOOK' | 'SIEM_COLLECTOR';
  endpointUrl: string;
  format: 'CEF' | 'LEEF' | 'JSON_STRUCTURED';
  credentialRef?: string;
  tlsEnforced: boolean;
  status: 'CONFIGURED' | 'DISABLED';
  createdAt: string;
}

export interface EvidenceRetentionPolicy {
  id: string;
  name: string;
  evidenceClass: string;
  retentionYears: number;
  dispositionAction: 'ARCHIVE_COLD' | 'PURGE_CONFIRMED';
  legalHoldExempt: boolean;
  status: 'ENFORCED' | 'AUDIT_ONLY';
}

export interface LegalHold {
  id: string;
  caseId: string;
  matterName: string;
  custodian: string;
  scopeDescription: string;
  holdCreatedDate: string;
  heldItemsCount: number;
  status: 'ACTIVE' | 'RELEASED';
  releasedDate?: string;
  releaseReason?: string;
}

export interface AuditIntegrityVerification {
  id: string;
  verificationTimestamp: string;
  targetPeriod: string;
  totalEntriesEvaluated: number;
  sha256MerkleRootDigest: string;
  verificationResult: 'DIGEST_VERIFIED' | 'DIGEST_MISMATCH';
  auditedBy: string;
  signatureAlgorithm: string;
}

export interface AuditExportRequest {
  id: string;
  requestedAt: string;
  requestedBy: string;
  format: 'JSON' | 'CSV' | 'ZIP';
  dateRange: string;
  status: 'COMPLETED' | 'IN_PROGRESS';
  downloadSize: string;
  recordCount: number;
}
