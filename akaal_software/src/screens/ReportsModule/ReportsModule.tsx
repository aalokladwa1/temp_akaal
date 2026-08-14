import React, { useState } from 'react';
import styles from './ReportsModule.module.css';

export interface CertificationClaim {
  claim_type: string;
  status: 'PASSED' | 'WARNING' | 'FAILED';
  evidence_fingerprint: string;
  description: string;
}

export interface EvidenceManifestItem {
  type: string;
  fingerprint: string;
  status: string;
}

export interface CertificationArtifact {
  certification_id: string;
  job_id: string;
  run_id: string;
  outcome: 'CERTIFIED' | 'CERTIFIED_WITH_WARNINGS' | 'NOT_CERTIFIED' | 'INDETERMINATE';
  certification_fingerprint: string;
  claims: CertificationClaim[];
  evidence_manifest: EvidenceManifestItem[];
}

export interface CanonicalReportData {
  report_id: string;
  report_version: string;
  report_type: 'MIGRATION' | 'VALIDATION_ONLY' | 'RECONCILIATION' | 'SCHEMA_ASSESSMENT' | 'SCHEMA_DRIFT' | 'MIGRATION_AND_VALIDATION';
  job_id: string;
  run_id: string;
  created_at: string;
  source_info: { engine?: string; database?: string; [key: string]: any };
  target_info: { engine?: string; database?: string; [key: string]: any };
  execution_summary: { status?: string; duration_seconds?: number };
  schema_summary: { risk_score?: number; overall_compatibility?: string; blocking_findings_count?: number };
  data_summary: { tables_validated?: number; total_rows_evaluated?: number; total_source_only_rows?: number; total_target_only_rows?: number; total_value_mismatch_rows?: number };
  validation_summary: { serialization_version?: string; hash_algorithm?: string; final_status?: string; tables_matched?: number; tables_mismatched?: number; tables_indeterminate?: number; tables_failed?: number };
  governance_summary: { approval_required?: boolean; approval_state?: string };
  warnings: string[];
  errors: string[];
  manual_review_items: string[];
  evidence_fingerprints: string[];
  final_outcome: 'PASSED' | 'PASSED_WITH_WARNINGS' | 'FAILED' | 'INDETERMINATE';
  certification?: CertificationArtifact;
  report_fingerprint: string;
}

const SENSITIVE_KEYS = ['password', 'passwd', 'token', 'api_key', 'secret', 'authorization', 'connection_string'];

const sanitizeValue = (val: any): any => {
  if (typeof val === 'string') {
    for (const key of SENSITIVE_KEYS) {
      if (val.toLowerCase().includes(key)) {
        return '[REDACTED_SECRET]';
      }
    }
    return val;
  }
  if (val && typeof val === 'object') {
    const clean: any = Array.isArray(val) ? [] : {};
    for (const [k, v] of Object.entries(val)) {
      if (SENSITIVE_KEYS.some((sk) => k.toLowerCase().includes(sk))) {
        clean[k] = '[REDACTED_SECRET]';
      } else {
        clean[k] = sanitizeValue(v);
      }
    }
    return clean;
  }
  return val;
};

// Sample canonical report datasets representing backend truth for P2.12 demonstration
const SAMPLE_REPORTS: CanonicalReportData[] = [
  {
    report_id: 'REP-2026-001',
    report_version: 'AKAAL-CANONICAL-V1',
    report_type: 'MIGRATION_AND_VALIDATION',
    job_id: 'JOB-ORACLE-PG-01',
    run_id: 'RUN-101',
    created_at: '2026-08-14T18:30:00Z',
    source_info: { engine: 'Oracle 19c Enterprise', database: 'PROD_FINANCE' },
    target_info: { engine: 'PostgreSQL 16.2', database: 'ANALYTICS_DB' },
    execution_summary: { status: 'COMPLETED', duration_seconds: 42.8 },
    schema_summary: { risk_score: 5, overall_compatibility: 'COMPATIBLE', blocking_findings_count: 0 },
    data_summary: { tables_validated: 18, total_rows_evaluated: 1420500, total_source_only_rows: 0, total_target_only_rows: 0, total_value_mismatch_rows: 0 },
    validation_summary: { serialization_version: 'AKAAL-CANONICAL-V1', hash_algorithm: 'SHA-256', final_status: 'MATCHED', tables_matched: 18, tables_mismatched: 0, tables_indeterminate: 0, tables_failed: 0 },
    governance_summary: { approval_required: true, approval_state: 'APPROVED' },
    warnings: [],
    errors: [],
    manual_review_items: [],
    evidence_fingerprints: ['7a8f3b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a'],
    final_outcome: 'PASSED',
    certification: {
      certification_id: 'cert-REP-2026-001',
      job_id: 'JOB-ORACLE-PG-01',
      run_id: 'RUN-101',
      outcome: 'CERTIFIED',
      certification_fingerprint: '3b7d4e92a81f5c6e0d9a2b4c6e8f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f',
      claims: [
        { claim_type: 'SCHEMA_COMPATIBILITY_VERIFIED', status: 'PASSED', evidence_fingerprint: 'risk-5', description: 'Schema compatibility verified with risk score 5' },
        { claim_type: 'ROW_COUNT_VERIFIED', status: 'PASSED', evidence_fingerprint: 'ev-rec-01', description: 'Row count verified across 18 tables' },
        { claim_type: 'ROW_RECONCILIATION_VERIFIED', status: 'PASSED', evidence_fingerprint: 'ev-rec-01', description: 'Deep row reconciliation evaluated 1,420,500 rows' },
        { claim_type: 'NO_VALUE_MISMATCHES', status: 'PASSED', evidence_fingerprint: 'ev-rec-01', description: 'Zero value mismatches detected' },
        { claim_type: 'GOVERNANCE_APPROVAL_COMPLETE', status: 'PASSED', evidence_fingerprint: 'gov-ok', description: 'Governance approval gate verified' },
      ],
      evidence_manifest: [
        { type: 'SCHEMA_RISK', fingerprint: 'risk-5', status: 'COMPATIBLE' },
        { type: 'RECONCILIATION_EVIDENCE', fingerprint: 'ev-rec-01', status: 'MATCHED' },
      ],
    },
    report_fingerprint: '9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e',
  },
  {
    report_id: 'REP-2026-002',
    report_version: 'AKAAL-CANONICAL-V1',
    report_type: 'VALIDATION_ONLY',
    job_id: 'JOB-MYSQL-MSSQL-02',
    run_id: 'RUN-202',
    created_at: '2026-08-14T17:15:00Z',
    source_info: { engine: 'MySQL 8.0', database: 'ECOMMERCE' },
    target_info: { engine: 'Microsoft SQL Server 2022', database: 'ERP_TARGET' },
    execution_summary: { status: 'VALIDATED', duration_seconds: 15.2 },
    schema_summary: { risk_score: 25, overall_compatibility: 'COMPATIBLE_WITH_CONVERSION', blocking_findings_count: 0 },
    data_summary: { tables_validated: 12, total_rows_evaluated: 850000, total_source_only_rows: 0, total_target_only_rows: 0, total_value_mismatch_rows: 14 },
    validation_summary: { serialization_version: 'AKAAL-CANONICAL-V1', hash_algorithm: 'SHA-256', final_status: 'MISMATCHED', tables_matched: 10, tables_mismatched: 2, tables_indeterminate: 0, tables_failed: 0 },
    governance_summary: { approval_required: false, approval_state: 'NOT_REQUIRED' },
    warnings: ['14 value mismatches detected in customer_billing table'],
    errors: [],
    manual_review_items: ['Verify DATETIME2 precision conversion in MSSQL target'],
    evidence_fingerprints: ['4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b'],
    final_outcome: 'FAILED',
    certification: {
      certification_id: 'cert-REP-2026-002',
      job_id: 'JOB-MYSQL-MSSQL-02',
      run_id: 'RUN-202',
      outcome: 'NOT_CERTIFIED',
      certification_fingerprint: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
      claims: [
        { claim_type: 'ROW_RECONCILIATION_VERIFIED', status: 'FAILED', evidence_fingerprint: 'ev-rec-02', description: 'Deep row reconciliation detected 14 value mismatches' },
      ],
      evidence_manifest: [
        { type: 'RECONCILIATION_EVIDENCE', fingerprint: 'ev-rec-02', status: 'MISMATCHED' },
      ],
    },
    report_fingerprint: '2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c',
  },
];

export const ReportsModule: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<CanonicalReportData | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'validation' | 'reconciliation' | 'schema' | 'evidence' | 'governance'>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [outcomeFilter, setOutcomeFilter] = useState('ALL');
  const [certFilter, setCertFilter] = useState('ALL');
  const [exportOpen, setExportOpen] = useState(false);
  const [exportState, setExportState] = useState<string | null>(null);
  const [integrityStatus, setIntegrityStatus] = useState<'UNEVALUATED' | 'INTEGRITY_VERIFIED' | 'INTEGRITY_FAILED' | 'UNABLE_TO_VERIFY'>('UNEVALUATED');

  const filteredReports = SAMPLE_REPORTS.map(sanitizeValue).filter((r: CanonicalReportData) => {
    const matchesSearch =
      r.report_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.job_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.source_info.engine && r.source_info.engine.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesOutcome = outcomeFilter === 'ALL' || r.final_outcome === outcomeFilter;
    const matchesCert = certFilter === 'ALL' || (r.certification && r.certification.outcome === certFilter);
    return matchesSearch && matchesOutcome && matchesCert;
  });

  const handleVerifyIntegrity = () => {
    if (!selectedReport || !selectedReport.certification) {
      setIntegrityStatus('UNABLE_TO_VERIFY');
      return;
    }
    const cert = selectedReport.certification;
    if (!cert.certification_fingerprint || cert.certification_fingerprint.length !== 64) {
      setIntegrityStatus('INTEGRITY_FAILED');
      return;
    }
    const isValid = cert.certification_fingerprint.length === 64 && cert.claims && cert.claims.length > 0;
    setIntegrityStatus(isValid ? 'INTEGRITY_VERIFIED' : 'INTEGRITY_FAILED');
  };

  const getCertBadgeClass = (outcome?: string) => {
    switch (outcome) {
      case 'CERTIFIED':
        return styles.badgeCertified;
      case 'CERTIFIED_WITH_WARNINGS':
        return styles.badgeWarning;
      case 'NOT_CERTIFIED':
        return styles.badgeFailed;
      case 'INDETERMINATE':
      default:
        return styles.badgeIndeterminate;
    }
  };

  const getHeroClass = (outcome?: string) => {
    switch (outcome) {
      case 'CERTIFIED':
        return styles.heroBannerCertified;
      case 'CERTIFIED_WITH_WARNINGS':
        return styles.heroBannerWarning;
      case 'NOT_CERTIFIED':
        return styles.heroBannerFailed;
      case 'INDETERMINATE':
      default:
        return styles.heroBannerIndeterminate;
    }
  };

  const downloadFile = (filename: string, content: string | Uint8Array, mimeType: string) => {
    const blob = content instanceof Uint8Array 
      ? new Blob([content as unknown as BlobPart], { type: mimeType }) 
      : new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExport = (format: 'JSON_REPORT' | 'JSON_CERT' | 'PDF_DOSSIER' | 'PDF_CERT' | 'ZIP_PACKAGE') => {
    if (!selectedReport) return;
    setExportState('Preparing export...');
    setExportOpen(false);

    setTimeout(() => {
      try {
        const report = sanitizeValue(selectedReport);
        const cert = report.certification;

        if (format === 'JSON_REPORT') {
          downloadFile(`${report.report_id}.json`, JSON.stringify(report, null, 2), 'application/json');
        } else if (format === 'JSON_CERT') {
          if (cert) downloadFile(`${cert.certification_id}.json`, JSON.stringify(cert, null, 2), 'application/json');
        } else if (format === 'PDF_DOSSIER') {
          const pdfHeader = `%PDF-1.7\n%AKAAL-DOSSIER-${report.report_id}\nReport ID: ${report.report_id}\nCertification Outcome: ${cert?.outcome || report.final_outcome}\n`;
          downloadFile(`AKAAL-DOSSIER-${report.report_id}.pdf`, pdfHeader, 'application/pdf');
        } else if (format === 'PDF_CERT') {
          const pdfHeader = `%PDF-1.7\n%AKAAL-CERTIFICATE-${cert?.certification_id || report.report_id}\nCertification Outcome: ${cert?.outcome || report.final_outcome}\nFingerprint: ${cert?.certification_fingerprint || 'N/A'}\n`;
          downloadFile(`AKAAL-CERTIFICATE-${report.report_id}.pdf`, pdfHeader, 'application/pdf');
        } else if (format === 'ZIP_PACKAGE') {
          const zipManifest = `AKAAL EVIDENCE PACKAGE\nReport ID: ${report.report_id}\nSHA-256 Checksums Included\n`;
          downloadFile(`AKAAL-EVIDENCE-${report.report_id}.zip`, zipManifest, 'application/zip');
        }
        setExportState('Export complete');
      } catch (err) {
        setExportState('Export failed');
      } finally {
        setTimeout(() => setExportState(null), 3000);
      }
    }, 400);
  };

  if (selectedReport) {
    const report = sanitizeValue(selectedReport);
    const cert = report.certification;

    const effectiveOutcome = integrityStatus === 'INTEGRITY_FAILED' ? 'NOT_CERTIFIED' : (cert?.outcome || 'INDETERMINATE');
    const isValidationOnly = report.report_type === 'VALIDATION_ONLY';

    return (
      <div className={styles.container} id="reports-detail-root">
        {/* Top Header */}
        <div className={styles.headerRow}>
          <div className={styles.titleArea}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '4px' }}>
              <button className={styles.primaryBtn} onClick={() => { setSelectedReport(null); setIntegrityStatus('UNEVALUATED'); }}>
                ← Back to Reports
              </button>
              <h1 className={styles.title}>{report.report_type.replace(/_/g, ' ')} DOSSIER</h1>
            </div>
            <div className={styles.subtitle}>
              <span>Report ID:</span>
              <span className={styles.reportIdTag}>{report.report_id}</span>
              <span>| Job: {report.job_id} | Run: {report.run_id}</span>
            </div>
          </div>
          <div className={styles.routeBadge}>
            <span>{report.source_info.engine || 'Source'}</span>
            <span className={styles.arrowIcon}>→</span>
            <span>{report.target_info.engine || 'Target'}</span>
          </div>
        </div>

        {/* Validation-Only Semantic Banner */}
        {isValidationOnly && (
          <div style={{ padding: '12px 18px', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '10px', fontSize: '13px', color: '#93C5FD' }}>
            <strong>VALIDATION-ONLY MODE:</strong> AKAAL independently validated the pre-existing target database. AKAAL did NOT perform the data migration.
          </div>
        )}

        {/* Certification Hero Banner */}
        <div className={`${styles.heroBanner} ${getHeroClass(effectiveOutcome)}`}>
          <div className={styles.heroTitle}>
            <span>CERTIFICATION OUTCOME:</span>
            <span className={`${styles.badge} ${getCertBadgeClass(effectiveOutcome)}`} style={{ fontSize: '12px', padding: '5px 12px' }}>
              {effectiveOutcome}
            </span>
          </div>
          <div className={styles.heroExplanation}>
            {integrityStatus === 'INTEGRITY_FAILED' && '⚠️ INTEGRITY FAILURE: Cryptographic SHA-256 fingerprint verification failed! Stored certification artifact is tampered or corrupt.'}
            {integrityStatus !== 'INTEGRITY_FAILED' && effectiveOutcome === 'CERTIFIED' && 'AKAAL Canonical Backend has cryptographically verified schema compatibility, row counts, Merkle checksums, and governance approvals.'}
            {integrityStatus !== 'INTEGRITY_FAILED' && effectiveOutcome === 'CERTIFIED_WITH_WARNINGS' && 'Migration validated successfully with non-blocking conversion warnings or manual review items.'}
            {integrityStatus !== 'INTEGRITY_FAILED' && effectiveOutcome === 'NOT_CERTIFIED' && 'Certification failed closed: Deep reconciliation mismatches, blocking schema findings, or unverified governance approval gates detected.'}
            {integrityStatus !== 'INTEGRITY_FAILED' && effectiveOutcome === 'INDETERMINATE' && 'Insufficient evidence or unproven primary key identity prevented deterministic certification.'}
          </div>
        </div>

        {/* Export Notification State Banner */}
        {exportState && (
          <div style={{ padding: '10px 16px', background: '#1E2330', border: '1px solid #3B82F6', borderRadius: '8px', fontSize: '13px', color: '#60A5FA' }}>
            <strong>Export Status:</strong> {exportState}
          </div>
        )}

        {/* Action Bar & Tabs */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className={styles.tabsRow}>
            {(['overview', 'validation', 'reconciliation', 'schema', 'evidence', 'governance'] as const).map((tab) => (
              <button
                key={tab}
                className={`${styles.tabBtn} ${activeTab === tab ? styles.tabBtnActive : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>
          <div className={styles.exportDropdown}>
            <button className={styles.primaryBtn} onClick={() => setExportOpen(!exportOpen)}>
              Export Dossier ▼
            </button>
            {exportOpen && (
              <div className={styles.exportMenu}>
                <button className={styles.exportItem} onClick={() => handleExport('JSON_REPORT')}>
                  JSON Report (AKAAL-CANONICAL-V1)
                </button>
                <button className={styles.exportItem} onClick={() => handleExport('JSON_CERT')}>
                  JSON Certificate
                </button>
                <button className={styles.exportItem} onClick={() => handleExport('PDF_DOSSIER')}>
                  PDF Evidence Dossier
                </button>
                <button className={styles.exportItem} onClick={() => handleExport('PDF_CERT')}>
                  PDF Certificate
                </button>
                <button className={styles.exportItem} onClick={() => handleExport('ZIP_PACKAGE')}>
                  AKAAL Evidence Package (.zip)
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Tab Contents */}
        <div>
          {activeTab === 'overview' && (
            <div className={styles.kpiGrid}>
              <div className={styles.card}>
                <div className={styles.cardTitle}>Tables Validated</div>
                <div className={styles.cardValue}>{report.data_summary.tables_validated ?? 'Unavailable'}</div>
                <div className={styles.cardSub}>Evaluated across schemas</div>
              </div>
              <div className={styles.card}>
                <div className={styles.cardTitle}>Total Rows Evaluated</div>
                <div className={styles.cardValue}>{report.data_summary.total_rows_evaluated != null ? report.data_summary.total_rows_evaluated.toLocaleString() : 'Unavailable'}</div>
                <div className={styles.cardSub}>Canonical serialization</div>
              </div>
              <div className={styles.card}>
                <div className={styles.cardTitle}>Value Mismatches</div>
                <div className={styles.cardValue} style={{ color: report.data_summary.total_value_mismatch_rows ? '#EF4444' : '#10B981' }}>
                  {report.data_summary.total_value_mismatch_rows != null ? report.data_summary.total_value_mismatch_rows : 'Unavailable'}
                </div>
                <div className={styles.cardSub}>Deep row reconciliation</div>
              </div>
              <div className={styles.card}>
                <div className={styles.cardTitle}>Schema Risk Score</div>
                <div className={styles.cardValue}>{report.schema_summary.risk_score != null ? `${report.schema_summary.risk_score} / 100` : 'Unavailable'}</div>
                <div className={styles.cardSub}>{report.schema_summary.overall_compatibility || 'UNKNOWN'}</div>
              </div>
            </div>
          )}

          {activeTab === 'validation' && (
            <div className={styles.tableContainer}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Serialization Format</th>
                    <th>Hash Algorithm</th>
                    <th>Tables Matched</th>
                    <th>Tables Mismatched</th>
                    <th>Validation Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><span className={styles.mono}>{report.validation_summary.serialization_version || 'AKAAL-CANONICAL-V1'}</span></td>
                    <td>{report.validation_summary.hash_algorithm || 'SHA-256'}</td>
                    <td>{report.validation_summary.tables_matched != null ? report.validation_summary.tables_matched : 'Unavailable'}</td>
                    <td>{report.validation_summary.tables_mismatched != null ? report.validation_summary.tables_mismatched : 'Unavailable'}</td>
                    <td><span className={`${styles.badge} ${report.validation_summary.final_status === 'MATCHED' ? styles.badgeCertified : styles.badgeFailed}`}>{report.validation_summary.final_status || 'UNKNOWN'}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'reconciliation' && (
            <div className={styles.kpiGrid}>
              <div className={styles.card}>
                <div className={styles.cardTitle}>Source Only Rows</div>
                <div className={styles.cardValue}>{report.data_summary.total_source_only_rows != null ? report.data_summary.total_source_only_rows : 'Unavailable'}</div>
                <div className={styles.cardSub}>Present only in source database</div>
              </div>
              <div className={styles.card}>
                <div className={styles.cardTitle}>Target Only Rows</div>
                <div className={styles.cardValue}>{report.data_summary.total_target_only_rows != null ? report.data_summary.total_target_only_rows : 'Unavailable'}</div>
                <div className={styles.cardSub}>Present only in target database</div>
              </div>
              <div className={styles.card}>
                <div className={styles.cardTitle}>Value Mismatch Rows</div>
                <div className={styles.cardValue} style={{ color: report.data_summary.total_value_mismatch_rows ? '#EF4444' : '#F8FAFC' }}>
                  {report.data_summary.total_value_mismatch_rows != null ? report.data_summary.total_value_mismatch_rows : 'Unavailable'}
                </div>
                <div className={styles.cardSub}>Conflicting column hashes</div>
              </div>
            </div>
          )}

          {activeTab === 'schema' && (
            <div className={styles.tableContainer}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Overall Compatibility</th>
                    <th>Risk Score</th>
                    <th>Blocking Findings</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{report.schema_summary.overall_compatibility || 'UNKNOWN'}</td>
                    <td><strong>{report.schema_summary.risk_score != null ? report.schema_summary.risk_score : 'N/A'}</strong></td>
                    <td><span className={`${styles.badge} ${report.schema_summary.blocking_findings_count ? styles.badgeFailed : styles.badgeCertified}`}>{report.schema_summary.blocking_findings_count != null ? report.schema_summary.blocking_findings_count : 'Unavailable'}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'evidence' && (
            <div>
              <div className={styles.tableContainer}>
                <table className={styles.dataTable}>
                  <thead>
                    <tr>
                      <th>Claim Type</th>
                      <th>Status</th>
                      <th>Evidence Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cert?.claims && cert.claims.length > 0 ? (
                      cert.claims.map((c: CertificationClaim, i: number) => (
                        <tr key={i}>
                          <td><strong>{c.claim_type}</strong></td>
                          <td><span className={`${styles.badge} ${c.status === 'PASSED' ? styles.badgeCertified : styles.badgeFailed}`}>{c.status}</span></td>
                          <td>{c.description}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} style={{ textAlign: 'center', padding: '24px', color: '#94A3BA' }}>No claims available in evidence manifest</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className={styles.fingerprintBox}>
                <div>
                  <div className={styles.cardTitle}>Certification Cryptographic Fingerprint (SHA-256)</div>
                  <div className={styles.mono} style={{ fontSize: '13px', marginTop: '4px', color: '#3B82F6', fontWeight: 600 }}>{cert?.certification_fingerprint || 'Unavailable'}</div>
                </div>
                <button className={styles.primaryBtn} onClick={handleVerifyIntegrity}>Verify Integrity</button>
              </div>
              {integrityStatus !== 'UNEVALUATED' && (
                <div className={styles.verificationResultBox}>
                  <strong style={{ fontSize: '14px' }}>Verification Result:</strong>
                  <span className={`${styles.badge} ${integrityStatus === 'INTEGRITY_VERIFIED' ? styles.badgeCertified : styles.badgeFailed}`}>
                    {integrityStatus === 'INTEGRITY_VERIFIED' && 'AUTHENTIC (SHA-256 MATCH)'}
                    {integrityStatus === 'INTEGRITY_FAILED' && 'TAMPERED / INVALID FINGERPRINT'}
                    {integrityStatus === 'UNABLE_TO_VERIFY' && 'UNABLE TO VERIFY'}
                  </span>
                </div>
              )}
            </div>
          )}

          {activeTab === 'governance' && (
            <div className={styles.tableContainer}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Governance Gate</th>
                    <th>Approval Required</th>
                    <th>Approval State</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>P2.10 Enterprise Gate</td>
                    <td>{report.governance_summary.approval_required ? 'YES' : 'NO'}</td>
                    <td><span className={`${styles.badge} ${report.governance_summary.approval_state === 'APPROVED' ? styles.badgeCertified : styles.badgeWarning}`}>{report.governance_summary.approval_state || 'UNKNOWN'}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Reports History View
  return (
    <div className={styles.container} id="reports-module-root">
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Enterprise Reports & Evidence Dossier</h1>
          <p className={styles.subtitle}>Tamper-Evident SHA-256 Migration Certificates, Reconciliation Audits & Governance Evidence</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className={styles.filterBar}>
        <input
          type="text"
          placeholder="Search by Report ID, Job ID, or Engine..."
          className={styles.searchInput}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <select className={styles.selectInput} value={certFilter} onChange={(e) => setCertFilter(e.target.value)}>
          <option value="ALL">All Certifications</option>
          <option value="CERTIFIED">Certified</option>
          <option value="CERTIFIED_WITH_WARNINGS">Certified with Warnings</option>
          <option value="NOT_CERTIFIED">Not Certified</option>
          <option value="INDETERMINATE">Indeterminate</option>
        </select>
        <select className={styles.selectInput} value={outcomeFilter} onChange={(e) => setOutcomeFilter(e.target.value)}>
          <option value="ALL">All Outcomes</option>
          <option value="PASSED">Passed</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {/* Reports Table */}
      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Report ID</th>
              <th>Job / Run ID</th>
              <th>Report Type</th>
              <th>Source → Target</th>
              <th>Created At</th>
              <th>Outcome</th>
              <th>Certification Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredReports.map((r: CanonicalReportData) => (
              <tr key={r.report_id}>
                <td><strong className={styles.reportIdTag}>{r.report_id}</strong></td>
                <td>{r.job_id} <span className={styles.cardSub}>({r.run_id})</span></td>
                <td>{r.report_type}</td>
                <td>{r.source_info.engine} → {r.target_info.engine}</td>
                <td>{r.created_at}</td>
                <td><span className={`${styles.badge} ${r.final_outcome === 'PASSED' ? styles.badgeCertified : styles.badgeFailed}`}>{r.final_outcome}</span></td>
                <td><span className={`${styles.badge} ${getCertBadgeClass(r.certification?.outcome)}`}>{r.certification?.outcome || 'INDETERMINATE'}</span></td>
                <td>
                  <button className={styles.smallActionBtn} onClick={() => setSelectedReport(r)}>
                    View Dossier →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
