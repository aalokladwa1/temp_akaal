/**
 * AKAAL Reports — Part 4: Evidence Portal Domain Models
 * Strict semantic separation:
 *   REPORT ≠ CERTIFICATION ≠ EVIDENCE ≠ DOSSIER ≠ CERTIFICATE ≠ EVIDENCE PACKAGE.
 *   Digest ≠ Digital Signature | Approver Record ≠ Cryptographic Signature.
 *   Certificate Artifact ≠ X.509/PKI | Package ≠ Generic ZIP Format.
 * Zero-fake production law: Truthful models representing canonical backend semantics.
 */

export type EvidenceArtifactType = 
  | 'MANIFEST_SNAPSHOT'
  | 'MERKLE_TREE_DIGEST'
  | 'GOVERNANCE_LEDGER'
  | 'SCHEMA_DIFF'
  | 'WATERMARK_LOG'
  | 'INTEGRITY_SCAN'
  | 'AUDIT_JOURNAL'
  | 'RECOVERY_CHECKPOINT'
  | string;

export type EvidenceLifecycleState = 
  | 'ACTIVE'
  | 'SUPERSEDED'
  | 'ARCHIVED'
  | string;

export type EvidenceIntegrityResultStatus = 
  | 'VERIFIED'
  | 'MISMATCH'
  | 'UNAVAILABLE'
  | 'NOT_EVALUATED'
  | 'ERROR';

export interface EvidenceScopeDTO {
  tenant?: string;
  workspace?: string;
  project_name?: string;
  migration_name?: string;
  validation_name?: string;
  run_id?: string;
  plan_version?: string;
  time_window_start?: string;
  time_window_end?: string;
  target_object_scope?: string;
  custom_context?: Record<string, string | number | boolean>;
}

export interface EvidenceProvenanceDTO {
  producer_authority: string;
  created_at: string;
  subject_context: string;
  run_or_plan_binding?: string;
  canonical_reference?: string;
  notes?: string;
}

export interface EvidenceTrustIntegrityDTO {
  fingerprint?: string;
  fingerprint_algorithm?: string;
  verification_status?: EvidenceIntegrityResultStatus;
  verification_method?: string;
  verified_at?: string;
  merkle_root?: string;
  stored_fingerprint?: string;
  computed_fingerprint?: string;
  detail_notes?: string;
}

export interface EvidenceItemDTO {
  id: string;
  title: string;
  artifact_type: EvidenceArtifactType;
  subject_name: string;
  subject_id: string;
  created_at: string;
  producer_authority: string;
  fingerprint?: string;
  byte_size?: number;
  lifecycle?: EvidenceLifecycleState;
  integrity_status?: EvidenceIntegrityResultStatus;
  dossier_id?: string;
  certificate_id?: string;
  report_id?: string;
  deep_link_route: string;
}

export interface EvidenceDetailEnvelopeDTO {
  id: string;
  title: string;
  artifact_type: EvidenceArtifactType;
  subject_name: string;
  subject_id: string;
  created_at: string;
  producer_authority: string;
  summary: string;
  scope?: EvidenceScopeDTO;
  provenance?: EvidenceProvenanceDTO;
  integrity?: EvidenceTrustIntegrityDTO;
  raw_content_preview?: string;
  related_dossier_ids?: string[];
  related_certificate_ids?: string[];
  related_report_ids?: string[];
  download_supported?: boolean;
  download_file_name?: string;
}

export interface DossierDTO {
  id: string;
  title: string;
  subject_name: string;
  subject_id: string;
  domain: string;
  description: string;
  created_at: string;
  evidence_count: number;
  lifecycle?: EvidenceLifecycleState;
  evidence_items: EvidenceItemDTO[];
}

export interface CertificateArtifactDTO {
  id: string;
  title: string;
  subject_name: string;
  subject_id: string;
  domain: 'MIGRATION' | 'VALIDATION' | string;
  issued_at: string;
  producer_authority: string;
  certification_id?: string;
  decision: string;
  fingerprint?: string;
  evidence_refs: string[];
  download_supported?: boolean;
}

export interface PackageManifestItemDTO {
  id: string;
  file_name: string;
  artifact_type: EvidenceArtifactType;
  byte_size?: number;
  fingerprint?: string;
  integrity_status?: EvidenceIntegrityResultStatus;
}

export interface EvidencePackageDTO {
  id: string;
  title: string;
  subject_name: string;
  subject_id: string;
  status: 'READY' | 'UNAVAILABLE' | string;
  generated_at: string;
  fingerprint?: string;
  byte_size?: number;
  manifest_items: PackageManifestItemDTO[];
  download_supported?: boolean;
}

export interface EvidencePaginationQuery {
  search_query: string;
  artifact_type: string;
  lifecycle: string;
  sort_field: 'created_at' | 'title';
  sort_direction: 'asc' | 'desc';
  page_index: number;
  page_size: number;
}

export interface PaginatedResult<T> {
  items: T[];
  total_count: number;
  page_index: number;
  page_size: number;
  total_pages: number;
}

export function formatEvidenceType(type: string | null | undefined): string {
  if (!type) return '';
  return type
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase())
    .replace(/\bCdc\b/gi, 'CDC')
    .replace(/\bAst\b/gi, 'AST')
    .replace(/\bWal\b/gi, 'WAL');
}
