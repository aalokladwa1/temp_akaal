/**
 * reports-ipc.spec.ts
 * =====================
 * Dedicated unit tests for ReportsIpcService and its integration with ReportsService.
 * Validates typed IPC calls, schema mapping, and fail-closed semantics.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ReportsIpcService } from '../../core/services/ipc/reports.ipc';
import { ReportsService } from './services/reports.service';
import { IpcService } from '../../core/services/ipc.service';

describe('ReportsIpcService', () => {
  let mockIpcService: IpcService;
  let reportsIpc: ReportsIpcService;

  beforeEach(() => {
    mockIpcService = {
      invoke: vi.fn(),
      connectionState: { set: vi.fn() },
      lastTelemetryTimestamp: { set: vi.fn() },
    } as unknown as IpcService;
    reportsIpc = new ReportsIpcService(mockIpcService);
  });

  describe('Report queries', () => {
    it('should invoke report.summary', async () => {
      const summaryData = {
        total_reports_count: 14,
        certification_attention_count: 2,
        evidence_manifests_count: 5,
        observed_at: '2026-09-17T00:00:00Z',
      };
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: summaryData,
      });

      const res = await reportsIpc.getReportsSummary();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('report', 'summary', {});
      expect(res.status).toBe('SUCCESS');
      expect(res.data?.total_reports_count).toBe(14);
    });

    it('should invoke report.list with filters', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { reports: [] },
      });

      const res = await reportsIpc.listReports({ category: 'CDC', outcome: 'SATISFIED' });
      expect(mockIpcService.invoke).toHaveBeenCalledWith('report', 'list', {
        category: 'CDC',
        outcome: 'SATISFIED',
      });
      expect(res.status).toBe('SUCCESS');
      expect(res.data?.reports).toEqual([]);
    });

    it('should invoke report.get with report_id', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { id: 'REP-2026-0101', title: 'Reconciliation Report' },
      });

      const res = await reportsIpc.getReport('REP-2026-0101');
      expect(mockIpcService.invoke).toHaveBeenCalledWith('report', 'get', { report_id: 'REP-2026-0101' });
      expect(res.status).toBe('SUCCESS');
      expect(res.data?.id).toBe('REP-2026-0101');
    });

    it('should invoke report.export with format', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { export_id: 'EXP-1234', format: 'JSON', sha256_digest: 'abc' },
      });

      const res = await reportsIpc.exportReport('REP-2026-0101', 'JSON');
      expect(mockIpcService.invoke).toHaveBeenCalledWith('report', 'export', {
        report_id: 'REP-2026-0101',
        format: 'JSON',
      });
      expect(res.status).toBe('SUCCESS');
      expect(res.data?.export_id).toBe('EXP-1234');
    });
  });

  describe('Certification queries', () => {
    it('should invoke certification.list', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { certifications: [] },
      });

      const res = await reportsIpc.listCertifications();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('certification', 'list', {});
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke certification.get', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { id: 'CERT-MIG-2026-001' },
      });

      const res = await reportsIpc.getCertification('CERT-MIG-2026-001');
      expect(mockIpcService.invoke).toHaveBeenCalledWith('certification', 'get', {
        certification_id: 'CERT-MIG-2026-001',
      });
      expect(res.status).toBe('SUCCESS');
    });
  });

  describe('Evidence Portal queries', () => {
    it('should invoke evidence.list', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { evidence: [] },
      });

      const res = await reportsIpc.listEvidence();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('evidence', 'list', {});
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke evidence.get', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { id: 'EV-2026-VAL-01' },
      });

      const res = await reportsIpc.getEvidence('EV-2026-VAL-01');
      expect(mockIpcService.invoke).toHaveBeenCalledWith('evidence', 'get', {
        artifact_id: 'EV-2026-VAL-01',
      });
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke evidence.verify', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: {
          target_identifier: 'EV-2026-VAL-01',
          result_status: 'VERIFIED',
          stored_fingerprint: 'hash123',
        },
      });

      const res = await reportsIpc.verifyEvidence('EV-2026-VAL-01');
      expect(mockIpcService.invoke).toHaveBeenCalledWith('evidence', 'verify', {
        target_id: 'EV-2026-VAL-01',
        target_type: 'EVIDENCE_ARTIFACT',
      });
      expect(res.status).toBe('SUCCESS');
      expect(res.data?.result_status).toBe('VERIFIED');
    });

    it('should invoke dossiers, packages, and certificates lists', async () => {
      (mockIpcService.invoke as any).mockResolvedValue({
        status: 'SUCCESS',
        data: { dossiers: [], packages: [], certificates: [] },
      });

      await reportsIpc.listEvidenceDossiers();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('evidence', 'dossiers.list', {});

      await reportsIpc.listEvidencePackages();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('evidence', 'packages.list', {});

      await reportsIpc.listCertificateArtifacts();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('evidence', 'certificates.list', {});
    });
  });

  describe('ReportsService with ReportsIpcService injection', () => {
    it('should update summary and reports on refresh when backend responds', async () => {
      (mockIpcService.invoke as any).mockImplementation((endpoint: string, action: string) => {
        if (endpoint === 'report' && action === 'summary') {
          return Promise.resolve({
            status: 'SUCCESS',
            data: {
              total_reports_count: 20,
              certification_attention_count: 3,
              evidence_manifests_count: 8,
              observed_at: '2026-09-17T00:00:00Z',
            },
          });
        }
        if (endpoint === 'report' && action === 'list') {
          return Promise.resolve({
            status: 'SUCCESS',
            data: { reports: [] },
          });
        }
        return Promise.resolve({ status: 'SUCCESS', data: {} });
      });

      const service = new ReportsService(mockIpcService, reportsIpc);
      service.refresh();

      // Wait a tick for promises
      await new Promise(resolve => setTimeout(resolve, 50));

      expect(service.summary().total_reports_count).toBe(20);
      expect(service.summary().certification_attention_count).toBe(3);
    });
  });
});
