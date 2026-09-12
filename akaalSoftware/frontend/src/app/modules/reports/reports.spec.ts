/**
 * AKAAL Reports — Part 2: Reports Unit Test Suite
 * Tests for ReportsService, 14-Category Frozen Taxonomy, Filters, Projections, Text Sanitizers,
 * Library View Modes, Inventory Filtering/Sorting/Pagination, and All 14 Type-Specific Envelopes.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { ReportsService } from './services/reports.service';
import { 
  REPORT_CATEGORIES, 
  formatReportText, 
  ReportCategoryKey,
  ReportsHomeDataDTO 
} from './models/reports.models';

describe('Reports Module & ReportsService', () => {
  let service: ReportsService;

  beforeEach(() => {
    service = new ReportsService();
  });

  describe('14-Category Frozen Taxonomy (Preserved for Report Library)', () => {
    it('should declare all 14 canonical report categories', () => {
      expect(REPORT_CATEGORIES.length).toBe(14);
      const keys = REPORT_CATEGORIES.map(c => c.key);
      const expectedKeys: ReportCategoryKey[] = [
        'MIGRATION',
        'SCHEMA_COMPATIBILITY',
        'VALIDATION_RECONCILIATION',
        'DATA_QUALITY',
        'PERFORMANCE',
        'CDC',
        'CUTOVER_FAILBACK',
        'RECOVERY_RELIABILITY',
        'SECURITY',
        'COMPLIANCE',
        'GOVERNANCE_APPROVAL',
        'AUDIT',
        'INFRASTRUCTURE_FLEET',
        'EXECUTIVE'
      ];
      expectedKeys.forEach(k => {
        expect(keys).toContain(k);
      });
    });

    it('should have descriptive labels, icons, and technical scopes for every category', () => {
      REPORT_CATEGORIES.forEach(category => {
        expect(category.label).toBeTruthy();
        expect(category.icon).toBeTruthy();
        expect(category.description).toBeTruthy();
        expect(category.technicalScope).toBeTruthy();
      });
    });
  });

  describe('formatReportText sanitizer helper', () => {
    it('should format snake_case to Title Case and capitalize enterprise acronyms', () => {
      expect(formatReportText('SCHEMA_COMPATIBILITY')).toBe('Schema Compatibility');
      expect(formatReportText('VALIDATION_RECONCILIATION')).toBe('Validation Reconciliation');
      expect(formatReportText('DATA_QUALITY')).toBe('Data Quality');
      expect(formatReportText('M2_BULK_CDC')).toBe('M2 Bulk CDC');
      expect(formatReportText('SOC2_HIPAA_COMPLIANCE')).toBe('SOC2 HIPAA Compliance');
      expect(formatReportText('GDPR_AUDIT')).toBe('GDPR Audit');
      expect(formatReportText('DDL_TRANSLATION')).toBe('DDL Translation');
      expect(formatReportText('WAL_RECORD_REPLAY')).toBe('WAL Record Replay');
      expect(formatReportText('TLS_HANDSHAKE')).toBe('TLS Handshake');
      expect(formatReportText('SQL_SYNTAX')).toBe('SQL Syntax');
      expect(formatReportText('RCA_ANALYSIS')).toBe('RCA Analysis');
    });

    it('should handle null, undefined, or empty values safely', () => {
      expect(formatReportText(null)).toBe('');
      expect(formatReportText(undefined)).toBe('');
      expect(formatReportText('')).toBe('');
    });
  });

  describe('ReportsService State & Projections (Home Bounded Preview Law)', () => {
    it('should initialize with default summary metrics', () => {
      const summary = service.summary();
      expect(summary).toBeDefined();
      expect(summary.total_reports_count).toBeGreaterThan(0);
      expect(summary.evidence_manifests_count).toBeGreaterThan(0);
    });

    it('should bound recent reports to maximum 8 items on Home', () => {
      expect(service.recentReports().length).toBeLessThanOrEqual(8);
      expect(service.recentReports().length).toBeGreaterThan(0);
    });

    it('should bound certification attention to maximum 6 items on Home', () => {
      expect(service.certificationAttention().length).toBeLessThanOrEqual(6);
      expect(service.hasCertificationAttention()).toBe(true);
    });

    it('should bound evidence activity to maximum 6 items on Home', () => {
      expect(service.evidenceActivity().length).toBeLessThanOrEqual(6);
      expect(service.hasEvidenceActivity()).toBe(true);
    });

    it('should update section states truthfully', () => {
      service.setSectionState('summary', 'LOADING');
      expect(service.summaryState()).toBe('LOADING');

      service.setSectionState('reports', 'UNAVAILABLE');
      expect(service.reportsState()).toBe('UNAVAILABLE');

      service.setSectionState('certification', 'AVAILABLE_EMPTY');
      expect(service.certificationState()).toBe('AVAILABLE_EMPTY');

      service.setSectionState('evidence', 'ERROR');
      expect(service.evidenceState()).toBe('ERROR');

      service.setSectionState('library', 'PARTIAL');
      expect(service.libraryState()).toBe('PARTIAL');
    });

    it('should filter reports by search query', () => {
      service.reportSearchQuery.set('Core Banking');
      const filtered = service.filteredReports();
      expect(filtered.length).toBeGreaterThan(0);
      filtered.forEach(r => {
        const text = (r.title + ' ' + r.subject_name + ' ' + r.id + ' ' + r.category_label).toLowerCase();
        expect(text).toContain('core banking');
      });
    });

    it('should handle custom initialization data correctly', () => {
      const customData: Partial<ReportsHomeDataDTO> = {
        summary: {
          total_reports_count: 42,
          certification_attention_count: 0,
          evidence_manifests_count: 15,
          observed_at: new Date().toISOString()
        },
        certification_attention: []
      };

      service.initializeState(customData);
      expect(service.summary().total_reports_count).toBe(42);
      expect(service.hasCertificationAttention()).toBe(false);
    });

    it('should trigger refresh state', () => {
      service.refresh();
      expect(service.isRefreshing()).toBe(true);
    });
  });

  describe('Part 2: Report Library Navigation & Views', () => {
    it('should start in CATALOG view mode with no selected report', () => {
      expect(service.activeLibraryView()).toBe('CATALOG');
      expect(service.selectedReport()).toBeNull();
      expect(service.selectedCategory()).toBeNull();
    });

    it('should switch between CATALOG, INVENTORY, and CATEGORY_VIEW modes', () => {
      service.selectLibraryView('INVENTORY');
      expect(service.activeLibraryView()).toBe('INVENTORY');

      service.selectCategory('MIGRATION');
      expect(service.activeLibraryView()).toBe('CATEGORY_VIEW');
      expect(service.selectedCategory()).toBe('MIGRATION');
      expect(service.categoryScopedReports().length).toBeGreaterThan(0);

      service.selectLibraryView('CATALOG');
      expect(service.activeLibraryView()).toBe('CATALOG');
    });

    it('should open and close reports with full envelopes', () => {
      service.openReportById('REP-2026-0101');
      expect(service.activeLibraryView()).toBe('REPORT_DETAIL');
      expect(service.selectedReport()).toBeDefined();
      expect(service.selectedReport()?.id).toBe('REP-2026-0101');
      expect(service.selectedReport()?.category).toBe('VALIDATION_RECONCILIATION');
      expect(service.selectedReport()?.payload.kind).toBe('VALIDATION_RECONCILIATION');

      service.closeReport();
      expect(service.selectedReport()).toBeNull();
      expect(service.activeLibraryView()).toBe('CATALOG');
    });
  });

  describe('Part 2: Inventory Filtering, Sorting & Pagination', () => {
    it('should filter inventory by category', () => {
      service.inventoryCategoryFilter.set('MIGRATION');
      const filtered = service.filteredInventoryReports();
      expect(filtered.length).toBeGreaterThan(0);
      filtered.forEach(r => {
        expect(r.category).toBe('MIGRATION');
      });
    });

    it('should filter inventory by outcome', () => {
      service.inventoryOutcomeFilter.set('SATISFIED');
      const filtered = service.filteredInventoryReports();
      expect(filtered.length).toBeGreaterThan(0);
      filtered.forEach(r => {
        expect(r.outcome).toBe('SATISFIED');
      });
    });

    it('should filter inventory by search query', () => {
      service.inventorySearchQuery.set('Snowflake');
      const filtered = service.filteredInventoryReports();
      expect(filtered.length).toBe(1);
      expect(filtered[0].title).toContain('Snowflake');
    });

    it('should paginate inventory correctly', () => {
      service.inventoryPageSize.set(4);
      service.inventoryPageIndex.set(1);
      const page1 = service.paginatedInventoryReports();
      expect(page1.length).toBeLessThanOrEqual(4);

      const totalPages = service.totalInventoryPages();
      expect(totalPages).toBeGreaterThan(1);
    });
  });

  describe('Part 2: All 14 Type-Specific Report Envelopes', () => {
    const allReportIds = [
      { id: 'REP-2026-0101', expectedKind: 'VALIDATION_RECONCILIATION' },
      { id: 'REP-2026-0102', expectedKind: 'SCHEMA_COMPATIBILITY' },
      { id: 'REP-2026-0103', expectedKind: 'CDC' },
      { id: 'REP-2026-0104', expectedKind: 'MIGRATION' },
      { id: 'REP-2026-0105', expectedKind: 'PERFORMANCE' },
      { id: 'REP-2026-0106', expectedKind: 'DATA_QUALITY' },
      { id: 'REP-2026-0107', expectedKind: 'CUTOVER_FAILBACK' },
      { id: 'REP-2026-0108', expectedKind: 'RECOVERY_RELIABILITY' },
      { id: 'REP-2026-0109', expectedKind: 'SECURITY' },
      { id: 'REP-2026-0110', expectedKind: 'COMPLIANCE' },
      { id: 'REP-2026-0111', expectedKind: 'GOVERNANCE_APPROVAL' },
      { id: 'REP-2026-0112', expectedKind: 'AUDIT' },
      { id: 'REP-2026-0113', expectedKind: 'INFRASTRUCTURE_FLEET' },
      { id: 'REP-2026-0114', expectedKind: 'EXECUTIVE' }
    ];

    allReportIds.forEach(({ id, expectedKind }) => {
      it(`should generate full envelope with valid payload for ${expectedKind} (${id})`, () => {
        service.openReportById(id);
        const report = service.selectedReport();
        expect(report).toBeDefined();
        expect(report?.id).toBe(id);
        expect(report?.payload.kind).toBe(expectedKind);
        expect(report?.scope_and_inputs).toBeDefined();
        expect(report?.trust_and_provenance).toBeDefined();
        expect(report?.trust_and_provenance.artifact_sha256_fingerprint).toBeTruthy();
        expect(report?.related_evidence.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Part 2: Export Flow & Dispatching', () => {
    it('should open and close export modal', () => {
      const report = service.paginatedInventoryReports()[0];
      service.openExportModal(report);
      expect(service.isExportModalOpen()).toBe(true);
      expect(service.exportTargetReport()?.id).toBe(report.id);

      service.closeExportModal();
      expect(service.isExportModalOpen()).toBe(false);
      expect(service.exportTargetReport()).toBeNull();
    });
  });

  describe('Part 3: Trust & Certification State & Navigation', () => {
    it('should initialize with default certification tab set to OVERVIEW', () => {
      expect(service.activeCertTab()).toBe('OVERVIEW');
      expect(service.selectedCertId()).toBeNull();
    });

    it('should switch tabs between OVERVIEW, MIGRATION, VALIDATION, and VERIFICATION', () => {
      service.selectCertificationTab('MIGRATION');
      expect(service.activeCertTab()).toBe('MIGRATION');

      service.selectCertificationTab('VALIDATION');
      expect(service.activeCertTab()).toBe('VALIDATION');

      service.selectCertificationTab('VERIFICATION');
      expect(service.activeCertTab()).toBe('VERIFICATION');

      service.selectCertificationTab('OVERVIEW');
      expect(service.activeCertTab()).toBe('OVERVIEW');
    });

    it('should retrieve all certifications across migration and validation domains', () => {
      const all = service.allCertifications();
      expect(all.length).toBeGreaterThan(0);
      const domains = all.map(c => c.domain);
      expect(domains).toContain('MIGRATION');
      expect(domains).toContain('VALIDATION');
    });

    it('should open and resolve a Migration Certification detail envelope with distinct domain payload', () => {
      service.openCertificationById('CERT-MIG-2026-001');
      const cert = service.selectedCertification();
      expect(cert).toBeDefined();
      expect(cert?.id).toBe('CERT-MIG-2026-001');
      expect(cert?.domain).toBe('MIGRATION');
      expect(cert?.decision).toBe('CERTIFIED');
      expect(cert?.criteria.length).toBeGreaterThan(0);
      expect(cert?.evidence.length).toBeGreaterThan(0);
      expect(cert?.governance?.decision_status).toBe('APPROVED');
      expect(cert?.migration_payload).toBeDefined();
      expect(cert?.migration_payload?.execution_mode).toBeTruthy();
    });

    it('should open and resolve a Validation Certification detail envelope with distinct domain payload', () => {
      service.openCertificationById('CERT-VAL-2026-002');
      const cert = service.selectedCertification();
      expect(cert).toBeDefined();
      expect(cert?.id).toBe('CERT-VAL-2026-002');
      expect(cert?.domain).toBe('VALIDATION');
      expect(cert?.decision).toBe('CERTIFIED');
      expect(cert?.criteria.length).toBeGreaterThan(0);
      expect(cert?.validation_payload).toBeDefined();
      expect(cert?.validation_payload?.count_reconciliation_summary).toBeTruthy();
    });

    it('should execute verification and return exact status and fingerprints for a valid certification', () => {
      service.verifyArtifactTarget('CERT-MIG-2026-001');
      expect(service.activeCertTab()).toBe('VERIFICATION');
      const res = service.activeVerificationResult();
      expect(res).toBeDefined();
      expect(res?.target_identifier).toBe('CERT-MIG-2026-001');
      expect(res?.result_status).toBe('VERIFIED');
      expect(res?.stored_fingerprint).toBeTruthy();
      expect(res?.computed_fingerprint).toBe(res?.stored_fingerprint);
    });

    it('should execute verification and return exact status for an evidence artifact', () => {
      service.verifyArtifactTarget('EV-2026-VAL-01');
      expect(service.activeCertTab()).toBe('VERIFICATION');
      const res = service.activeVerificationResult();
      expect(res).toBeDefined();
      expect(res?.target_identifier).toBe('EV-2026-VAL-01');
      expect(res?.result_status).toBe('VERIFIED');
    });

    it('should return UNAVAILABLE for an unresolved target identifier', () => {
      service.verifyArtifactTarget('UNKNOWN-TARGET-999');
      expect(service.activeCertTab()).toBe('VERIFICATION');
      const res = service.activeVerificationResult();
      expect(res).toBeDefined();
      expect(res?.result_status).toBe('UNAVAILABLE');
    });

    it('should clear selected certification cleanly', () => {
      service.openCertificationById('CERT-MIG-2026-001');
      expect(service.selectedCertId()).toBe('CERT-MIG-2026-001');
      service.clearSelectedCertification();
      expect(service.selectedCertId()).toBeNull();
      expect(service.selectedCertification()).toBeNull();
    });
  });

  describe('Part 4: Evidence Portal Reactive Store & State Machine', () => {
    it('should initialize with canonical evidence items, dossiers, certificates, and packages', () => {
      expect(service.evidenceItems().length).toBeGreaterThanOrEqual(8);
      expect(service.dossiers().length).toBeGreaterThanOrEqual(2);
      expect(service.certificateArtifacts().length).toBeGreaterThanOrEqual(3);
      expect(service.evidencePackages().length).toBeGreaterThanOrEqual(2);
      expect(service.activeEvidenceTab()).toBe('EXPLORER');
    });

    it('should filter evidence by search query across title, subject, and identifier', () => {
      service.updateEvidenceFilter({ search_query: 'Merkle' });
      const res = service.paginatedEvidence();
      expect(res.items.length).toBeGreaterThan(0);
      res.items.forEach(item => {
        expect(item.title.toLowerCase() + item.subject_name.toLowerCase() + item.id.toLowerCase()).toContain('merkle');
      });
      service.updateEvidenceFilter({ search_query: '' });
    });

    it('should filter evidence by canonical artifact type', () => {
      service.updateEvidenceFilter({ artifact_type: 'MANIFEST_SNAPSHOT' });
      const res = service.paginatedEvidence();
      expect(res.items.length).toBeGreaterThan(0);
      res.items.forEach(item => {
        expect(item.artifact_type).toBe('MANIFEST_SNAPSHOT');
      });
      service.updateEvidenceFilter({ artifact_type: 'ALL' });
    });

    it('should paginate evidence using server/read-model pagination contract', () => {
      service.updateEvidenceFilter({ page_size: 3, page_index: 0 });
      const page1 = service.paginatedEvidence();
      expect(page1.items.length).toBe(3);
      expect(page1.page_index).toBe(0);
      expect(page1.total_pages).toBe(Math.ceil(page1.total_count / 3));

      service.updateEvidenceFilter({ page_index: 1 });
      const page2 = service.paginatedEvidence();
      expect(page2.items.length).toBe(3);
      expect(page2.page_index).toBe(1);
      expect(page2.items[0].id).not.toBe(page1.items[0].id);

      // Reset
      service.updateEvidenceFilter({ page_size: 10, page_index: 0 });
    });

    it('should open and resolve an Evidence Detail envelope with all 5 inspection tabs', () => {
      service.openEvidenceDetail('EV-2026-MIG-01');
      const env = service.selectedEvidenceEnvelope();
      expect(env).toBeDefined();
      expect(env?.id).toBe('EV-2026-MIG-01');
      expect(env?.title).toBe('Partition Bulk Transfer Manifest');
      expect(env?.producer_authority).toBeTruthy();
      expect(env?.summary).toBeTruthy();
      expect(env?.scope).toBeDefined();
      expect(env?.scope?.migration_name).toBeTruthy();
      expect(env?.provenance).toBeDefined();
      expect(env?.provenance?.producer_authority).toBeTruthy();
      expect(env?.integrity).toBeDefined();
      expect(env?.integrity?.verification_status).toBe('VERIFIED');
      expect(env?.integrity?.fingerprint).toBeTruthy();
      expect(env?.related_dossier_ids?.length).toBeGreaterThan(0);
      expect(env?.related_certificate_ids?.length).toBeGreaterThan(0);
      expect(env?.related_report_ids?.length).toBeGreaterThan(0);

      service.clearSelectedEvidence();
      expect(service.selectedEvidenceEnvelope()).toBeNull();
    });

    it('should open and resolve a Dossier with attached included evidence items', () => {
      service.selectDossier('DOS-2026-001');
      expect(service.activeEvidenceTab()).toBe('DOSSIERS');
      const dossier = service.selectedDossier();
      expect(dossier).toBeDefined();
      expect(dossier?.id).toBe('DOS-2026-001');
      expect(dossier?.domain).toBeTruthy();
      expect(dossier?.evidence_items.length).toBeGreaterThan(0);

      service.clearSelectedDossier();
      expect(service.selectedDossier()).toBeNull();
    });

    it('should open and resolve a Certificate Artifact with canonical certification reference', () => {
      service.selectCertificateArtifact('CERT-MIG-2026-001');
      expect(service.activeEvidenceTab()).toBe('CERTIFICATES');
      const cert = service.selectedCertificateArtifact();
      expect(cert).toBeDefined();
      expect(cert?.id).toBe('CERT-MIG-2026-001');
      expect(cert?.producer_authority).toBeTruthy();
      expect(cert?.decision).toBe('CERTIFIED');
      expect(cert?.evidence_refs.length).toBeGreaterThan(0);

      service.clearSelectedCertificateArtifact();
      expect(service.selectedCertificateArtifact()).toBeNull();
    });

    it('should open and resolve an Evidence Package with bounded manifest items', () => {
      service.selectEvidencePackage('PKG-2026-001');
      expect(service.activeEvidenceTab()).toBe('PACKAGES');
      const pkg = service.selectedEvidencePackage();
      expect(pkg).toBeDefined();
      expect(pkg?.id).toBe('PKG-2026-001');
      expect(pkg?.status).toBe('READY');
      expect(pkg?.manifest_items.length).toBeGreaterThan(0);
      expect(pkg?.download_supported).toBe(true);

      service.clearSelectedEvidencePackage();
      expect(service.selectedEvidencePackage()).toBeNull();
    });

    it('should verify an Evidence Package and record in verification history', () => {
      service.verifyArtifactTarget('PKG-2026-001');
      expect(service.activeEvidenceTab()).toBe('VERIFICATION');
      const res = service.activeVerificationResult();
      expect(res).toBeDefined();
      expect(res?.target_identifier).toBe('PKG-2026-001');
      expect(res?.result_status).toBe('VERIFIED');
      expect(res?.stored_fingerprint).toBeTruthy();
      expect(service.verificationHistory()[0].target_identifier).toBe('PKG-2026-001');
    });

    it('should verify a Certificate Artifact and record in verification history', () => {
      service.verifyArtifactTarget('CERT-VAL-2026-002');
      expect(service.activeEvidenceTab()).toBe('VERIFICATION');
      const res = service.activeVerificationResult();
      expect(res).toBeDefined();
      expect(res?.target_identifier).toBe('CERT-VAL-2026-002');
      expect(res?.result_status).toBe('VERIFIED');
      expect(service.verificationHistory()[0].target_identifier).toBe('CERT-VAL-2026-002');
    });

    it('should return UNAVAILABLE for unknown verification targets and record in history', () => {
      service.verifyArtifactTarget('CORRUPTED-TARGET-999');
      expect(service.activeEvidenceTab()).toBe('VERIFICATION');
      const res = service.activeVerificationResult();
      expect(res).toBeDefined();
      expect(res?.result_status).toBe('UNAVAILABLE');
      expect(service.verificationHistory()[0].target_identifier).toBe('CORRUPTED-TARGET-999');
    });
  });
});

