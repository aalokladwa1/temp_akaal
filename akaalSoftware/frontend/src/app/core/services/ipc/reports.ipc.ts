import { Injectable, inject } from '@angular/core';
import { IpcService } from '../ipc.service';
import type { IPCResponse } from '../../models/ipc.models';
import type {
  ReportsSummaryMetricsDTO,
  ReportItemDTO,
  ReportDetailEnvelopeDTO,
  ExportResponseDTO,
  ExportFormat,
} from '../../../modules/reports/models/reports.models';
import type {
  CertificationSummaryDTO,
  CertificationDetailEnvelopeDTO,
  VerificationResultDTO,
} from '../../../modules/reports/models/certification.models';
import type {
  EvidenceItemDTO,
  EvidenceDetailEnvelopeDTO,
  DossierDTO,
  EvidencePackageDTO,
  CertificateArtifactDTO,
} from '../../../modules/reports/models/evidence.models';

@Injectable({ providedIn: 'root' })
export class ReportsIpc {
  private ipc: IpcService;

  constructor(ipcService?: IpcService) {
    if (ipcService) {
      this.ipc = ipcService;
    } else {
      try {
        this.ipc = inject(IpcService, { optional: true }) || new IpcService();
      } catch {
        this.ipc = new IpcService();
      }
    }
  }

  // -- Reports ---------------------------------------------------------------

  public async getReportsSummary(): Promise<IPCResponse<ReportsSummaryMetricsDTO>> {
    return this.ipc.invoke<ReportsSummaryMetricsDTO>('report', 'summary', {});
  }

  public async listReports(params: { category?: string; outcome?: string; search?: string } = {}): Promise<
    IPCResponse<{ reports: ReportItemDTO[] }>
  > {
    return this.ipc.invoke<{ reports: ReportItemDTO[] }>('report', 'list', { ...params });
  }

  public async getReport(reportId: string): Promise<IPCResponse<ReportDetailEnvelopeDTO>> {
    return this.ipc.invoke<ReportDetailEnvelopeDTO>('report', 'get', { report_id: reportId });
  }

  public async exportReport(reportId: string, format: ExportFormat | string = 'JSON'): Promise<
    IPCResponse<ExportResponseDTO>
  > {
    return this.ipc.invoke<ExportResponseDTO>('report', 'export', { report_id: reportId, format });
  }

  // -- Trust & Certification -------------------------------------------------

  public async listCertifications(params: Record<string, unknown> = {}): Promise<
    IPCResponse<{ certifications: CertificationSummaryDTO[] }>
  > {
    return this.ipc.invoke<{ certifications: CertificationSummaryDTO[] }>('certification', 'list', { ...params });
  }

  public async getCertification(certificationId: string): Promise<IPCResponse<CertificationDetailEnvelopeDTO>> {
    return this.ipc.invoke<CertificationDetailEnvelopeDTO>('certification', 'get', {
      certification_id: certificationId,
    });
  }

  // -- Evidence Portal -------------------------------------------------------

  public async listEvidence(params: Record<string, unknown> = {}): Promise<
    IPCResponse<{ evidence: EvidenceItemDTO[] }>
  > {
    return this.ipc.invoke<{ evidence: EvidenceItemDTO[] }>('evidence', 'list', { ...params });
  }

  public async getEvidence(artifactId: string): Promise<IPCResponse<EvidenceDetailEnvelopeDTO>> {
    return this.ipc.invoke<EvidenceDetailEnvelopeDTO>('evidence', 'get', { artifact_id: artifactId });
  }

  public async verifyEvidence(targetId: string, targetType: string = 'EVIDENCE_ARTIFACT'): Promise<
    IPCResponse<VerificationResultDTO>
  > {
    return this.ipc.invoke<VerificationResultDTO>('evidence', 'verify', {
      target_id: targetId,
      target_type: targetType,
    });
  }

  public async listEvidenceDossiers(): Promise<IPCResponse<{ dossiers: DossierDTO[] }>> {
    return this.ipc.invoke<{ dossiers: DossierDTO[] }>('evidence', 'dossiers.list', {});
  }

  public async listEvidencePackages(): Promise<IPCResponse<{ packages: EvidencePackageDTO[] }>> {
    return this.ipc.invoke<{ packages: EvidencePackageDTO[] }>('evidence', 'packages.list', {});
  }

  public async listCertificateArtifacts(): Promise<IPCResponse<{ certificates: CertificateArtifactDTO[] }>> {
    return this.ipc.invoke<{ certificates: CertificateArtifactDTO[] }>('evidence', 'certificates.list', {});
  }
}

// Backward compatibility alias for ReportsIpcService
export type ReportsIpcService = ReportsIpc;
export const ReportsIpcService = ReportsIpc;
