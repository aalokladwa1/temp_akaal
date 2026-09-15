/**
 * AKAAL Reports — Part 1: Reports Domain Models
 * Clean domain types for Reports Home, Recent Reports, Certification Attention,
 * Evidence Activity, and the 14-Category Frozen Report Taxonomy.
 */

export type SectionLoadingState = 
  | 'LOADING' 
  | 'AVAILABLE_WITH_DATA' 
  | 'AVAILABLE_EMPTY' 
  | 'PARTIAL' 
  | 'UNAVAILABLE' 
  | 'UNAUTHORIZED' 
  | 'ERROR';

/**
 * 14 Canonical Frozen Report Categories (Preserved for Report Library)
 */
export type ReportCategoryKey = 
  | 'MIGRATION'
  | 'SCHEMA_COMPATIBILITY'
  | 'VALIDATION_RECONCILIATION'
  | 'DATA_QUALITY'
  | 'PERFORMANCE'
  | 'CDC'
  | 'CUTOVER_FAILBACK'
  | 'RECOVERY_RELIABILITY'
  | 'SECURITY'
  | 'COMPLIANCE'
  | 'GOVERNANCE_APPROVAL'
  | 'AUDIT'
  | 'INFRASTRUCTURE_FLEET'
  | 'EXECUTIVE';

export interface ReportCategoryDefinition {
  key: ReportCategoryKey;
  label: string;
  description: string;
  icon: string;
  technicalScope: string;
}

export const REPORT_CATEGORIES: ReportCategoryDefinition[] = [
  {
    key: 'MIGRATION',
    label: 'Migration',
    description: 'Execution outcomes, transferred data volume, stage progression, retries, and savepoints.',
    icon: 'layers',
    technicalScope: 'Engine execution & pipeline completion'
  },
  {
    key: 'SCHEMA_COMPATIBILITY',
    label: 'Schema & Compatibility',
    description: 'Object conversion findings, datatype mappings, unsupported features, and structural drift.',
    icon: 'file-code',
    technicalScope: 'Structural & relational parity'
  },
  {
    key: 'VALIDATION_RECONCILIATION',
    label: 'Validation & Reconciliation',
    description: 'Count reconciliations, checksum results, discrepancy summaries, and repair verification.',
    icon: 'check-circle-2',
    technicalScope: 'Dual-engine verification'
  },
  {
    key: 'DATA_QUALITY',
    label: 'Data Quality',
    description: 'Constraint rule evaluations, cleansing transformations, referential drift, and quarantine records.',
    icon: 'shield-check',
    technicalScope: 'Value & semantic validation'
  },
  {
    key: 'PERFORMANCE',
    label: 'Performance',
    description: 'Execution duration, effective throughput, partition latency, and durable stage performance.',
    icon: 'zap',
    technicalScope: 'Throughput & stage latency'
  },
  {
    key: 'CDC',
    label: 'CDC',
    description: 'Continuous capture and apply rates, provider-specific boundary positions, and conflict handling.',
    icon: 'activity',
    technicalScope: 'Replication state & boundaries'
  },
  {
    key: 'CUTOVER_FAILBACK',
    label: 'Cutover & Failback',
    description: 'Switchover readiness evidence, dual-control approval gates, transition milestones, and rollback safety.',
    icon: 'refresh-ccw',
    technicalScope: 'Cutover decision governance'
  },
  {
    key: 'RECOVERY_RELIABILITY',
    label: 'Recovery & Reliability',
    description: 'Failure events, restart reconstructions, checkpoint histories, and worker lease fencing evidence.',
    icon: 'database',
    technicalScope: 'Fault tolerance & checkpoint integrity'
  },
  {
    key: 'SECURITY',
    label: 'Security',
    description: 'Authorization activity, denied operations, identity session findings, and transport security evidence.',
    icon: 'lock',
    technicalScope: 'Access control & transport security'
  },
  {
    key: 'COMPLIANCE',
    label: 'Compliance',
    description: 'Technical control evaluations, separation of duties records, data protection evidence, and exceptions.',
    icon: 'clipboard-check',
    technicalScope: 'Technical controls & policy enforcement'
  },
  {
    key: 'GOVERNANCE_APPROVAL',
    label: 'Governance & Approval',
    description: 'Approval barrier ledgers, required quorum requirements, approver decision records, and conditions.',
    icon: 'users',
    technicalScope: 'Approval barriers & quorum records'
  },
  {
    key: 'AUDIT',
    label: 'Audit',
    description: 'Append-only actor action journals, privileged operations, failed access attempts, and target context.',
    icon: 'history',
    technicalScope: 'Chronological provenance journal'
  },
  {
    key: 'INFRASTRUCTURE_FLEET',
    label: 'Infrastructure & Fleet',
    description: 'Worker node inventory, capacity utilization, workload placements, and historical cluster logs.',
    icon: 'server',
    technicalScope: 'Cluster & worker inventory'
  },
  {
    key: 'EXECUTIVE',
    label: 'Executive',
    description: 'Program milestones, technical domain rollups, exception summaries, and technical drill-downs.',
    icon: 'layout-dashboard',
    technicalScope: 'High-level programmatic rollup'
  }
];

export type ReportOutcome = 
  | 'SATISFIED'
  | 'DEFECTS_FOUND'
  | 'CONVERGED'
  | 'IN_PROGRESS'
  | 'RECONCILED'
  | 'BLOCKED'
  | 'NOT_APPLICABLE'
  | 'UNKNOWN';

export type CertificationStatus = 
  | 'CERTIFIED'
  | 'NOT_CERTIFIED'
  | 'PENDING_EVALUATION'
  | 'REVOKED'
  | 'NOT_ESTABLISHED'
  | 'UNDER_REVIEW'
  | 'UNKNOWN';

export type EvidenceAvailabilityState = 
  | 'AVAILABLE'
  | 'PARTIAL'
  | 'PENDING'
  | 'UNAVAILABLE'
  | 'VERIFIED'
  | 'INTEGRITY_CHECK_FAILED';

export interface ReportItemDTO {
  id: string;
  title: string;
  category: ReportCategoryKey;
  category_label: string;
  subject_id: string;
  subject_name: string;
  subject_type: 'MIGRATION' | 'VALIDATION' | 'PROJECT' | 'PLATFORM' | 'AUDIT';
  generated_at: string;
  outcome?: ReportOutcome;
  summary: string;
  certification_status?: CertificationStatus;
  evidence_state: EvidenceAvailabilityState;
  evidence_manifest_ref?: string;
  download_formats: ('PDF' | 'JSON' | 'ZIP' | 'CSV')[];
  deep_link_route: string;
}

export interface RelatedEvidenceArtifactDTO {
  id: string;
  title: string;
  artifact_type: string;
  subject_name: string;
  sha256_digest: string;
  integrity_state: 'VERIFIED' | 'PENDING' | 'UNVERIFIED' | 'UNAVAILABLE';
  created_at: string;
  byte_size?: number;
  deep_link_route: string;
}

import { ReportPayloadUnion } from './report-payloads.models';

export interface ReportScopeAndInputsDTO {
  tenant?: string;
  workspace?: string;
  project_name?: string;
  migration_name?: string;
  validation_name?: string;
  run_id?: string;
  plan_version?: string;
  execution_mode?: string;
  source_instance?: string;
  target_instance?: string;
  included_objects_count?: number;
  excluded_objects_count?: number;
  time_window_start?: string;
  time_window_end?: string;
  parameters?: Record<string, string | number | boolean>;
}

export interface ReportTrustAndProvenanceDTO {
  report_id: string;
  generated_at: string;
  producer_engine: string;
  producer_version: string;
  run_or_plan_binding: string;
  artifact_sha256_fingerprint: string;
  integrity_state: 'VERIFIED' | 'PENDING' | 'UNVERIFIED';
  completeness: 'COMPLETE' | 'PARTIAL' | 'SECTION_UNAVAILABLE';
  evidence_references: string[];
}

export interface ReportDetailEnvelopeDTO {
  id: string;
  title: string;
  category: ReportCategoryKey;
  category_label: string;
  subject_id: string;
  subject_name: string;
  subject_type: string;
  generated_at: string;
  outcome?: ReportOutcome;
  summary: string;
  available_export_formats: ('PDF' | 'JSON' | 'CSV' | 'ZIP')[];
  scope_and_inputs: ReportScopeAndInputsDTO;
  trust_and_provenance: ReportTrustAndProvenanceDTO;
  related_evidence: RelatedEvidenceArtifactDTO[];
  payload: ReportPayloadUnion;
}

export type ExportFormat = 'PDF' | 'JSON' | 'CSV' | 'ZIP';

export interface ExportRequestDTO {
  report_id: string;
  format: ExportFormat;
  include_evidence_bundle?: boolean;
}

export interface ExportResponseDTO {
  export_id: string;
  report_id: string;
  format: ExportFormat;
  status: 'READY' | 'GENERATING' | 'FAILED';
  download_url?: string;
  file_name?: string;
  byte_size?: number;
  generated_at: string;
}

export interface CertificationAttentionItemDTO {
  id: string;
  subject_name: string;
  subject_type: string;
  condition_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  headline: string;
  detail: string;
  related_report_id?: string;
  related_report_title?: string;
  detected_at: string;
  deep_link: string;
}

export interface EvidenceActivityItemDTO {
  id: string;
  activity_type: string;
  subject_name: string;
  occurred_at: string;
  artifact_type: string;
  verification_status: 'VERIFIED' | 'PENDING' | 'UNVERIFIED' | 'UNAVAILABLE';
  summary: string;
  deep_link: string;
}

export interface ReportsSummaryMetricsDTO {
  total_reports_count: number;
  certification_attention_count: number;
  evidence_manifests_count: number;
  observed_at: string;
}

export interface ReportsHomeDataDTO {
  summary: ReportsSummaryMetricsDTO;
  recent_reports: ReportItemDTO[];
  certification_attention: CertificationAttentionItemDTO[];
  evidence_activity: EvidenceActivityItemDTO[];
}

export interface LibraryFilterOptions {
  search_query: string;
  category: string;
  subject: string;
  outcome: string;
  sort_field: 'generated_at' | 'title' | 'category';
  sort_direction: 'asc' | 'desc';
  page_index: number;
  page_size: number;
}

export function formatReportText(value: string | null | undefined): string {
  if (!value) return '';
  return value
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase())
    .replace(/\bCdc\b/gi, 'CDC')
    .replace(/\bDdl\b/gi, 'DDL')
    .replace(/\bWal\b/gi, 'WAL')
    .replace(/\bIpc\b/gi, 'IPC')
    .replace(/\bTls\b/gi, 'TLS')
    .replace(/\bSql\b/gi, 'SQL')
    .replace(/\bRca\b/gi, 'RCA')
    .replace(/\bSoc2\b/gi, 'SOC2')
    .replace(/\bHipaa\b/gi, 'HIPAA')
    .replace(/\bGdpr\b/gi, 'GDPR');
}

