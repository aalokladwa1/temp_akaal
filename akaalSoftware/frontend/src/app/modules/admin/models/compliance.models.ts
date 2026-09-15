/**
 * AKAAL Administration — 5.8 Compliance Models
 * Canonical models for Control Frameworks, Framework Views, Custom Frameworks,
 * Technical Control Mapping, Compliance Exceptions, and Evidence.
 */

export type RegulatoryDomain = 'GDPR' | 'PCI_DSS' | 'HIPAA' | 'SOC_2' | 'ISO_27001';

export type MappingState = 'FULLY_MAPPED' | 'PARTIALLY_MAPPED' | 'UNMAPPED' | 'EXCEPTION_RECORDED';

export type ComplianceEvidenceType =
  | 'HASH_ATTESTATION'
  | 'ENCRYPTION_PROOF'
  | 'IMMUTABLE_LOG_DIGEST'
  | 'ACCESS_AUDIT_SAMPLE';

export interface ControlFramework {
  id: string;
  name: string;
  code: string;
  version: string;
  regulatoryDomain: RegulatoryDomain;
  authorityBody: string;
  totalControls: number;
  mappedControlsCount: number;
  status: 'ACTIVE' | 'ARCHIVED';
  isBuiltIn: boolean;
  description: string;
}

export interface FrameworkControl {
  id: string;
  frameworkId: string;
  controlCode: string;
  title: string;
  domain: string;
  description: string;
  mappedTechnicalControls: string[];
  mappingState: MappingState;
  evidenceCount: number;
  exceptionId?: string;
}

export interface CustomFramework {
  id: string;
  name: string;
  code: string;
  version: string;
  authorityOwner: string;
  description: string;
  controlsCount: number;
  createdAt: string;
  status: 'ACTIVE' | 'DRAFT';
}

export interface ControlMapping {
  id: string;
  frameworkControlId: string;
  frameworkName: string;
  controlCode: string;
  akaalTechnicalControlId: string;
  technicalControlName: string;
  rationale: string;
  verifiedAt: string;
  status: 'ACTIVE' | 'PENDING_REVIEW';
}

export interface ComplianceException {
  id: string;
  code: string;
  title: string;
  frameworkId: string;
  controlCode: string;
  reason: string;
  scope: string;
  justification: string;
  approvedBy: string;
  validUntil: string;
  status: 'APPROVED' | 'PENDING' | 'EXPIRED';
}

export interface ComplianceEvidence {
  id: string;
  evidenceType: ComplianceEvidenceType;
  title: string;
  relatedControlCode: string;
  originSystem: string;
  sha256Digest: string;
  verificationStatus: 'DIGEST_VERIFIED' | 'UNVERIFIED';
  collectedAt: string;
  sizeBytes: number;
}
