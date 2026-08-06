import type { GovernanceApproval, GateId, TeamRole } from '../types/migration';
import { ipcService } from '../services/ipcService';

type ApprovalChangeListener = (approvals: GovernanceApproval[]) => void;

class ApprovalRepository {
  private approvals: GovernanceApproval[] = [
    {
      id: 'appr-001',
      gate: 'GATE_1',
      gateTitle: 'Gate 1: Discovery & Scope Assessment',
      migrationId: 'MIG-2026-0806-001',
      migrationName: 'Oracle ERP Core Migration',
      projectName: 'Oracle to Postgres Infrastructure Cutover',
      requestedBy: 'Aalok (Lead DBA)',
      requestedAt: '2026-08-06T14:15:00Z',
      expiresAt: '2026-08-07T14:15:00Z',
      status: 'pending',
      requiredRoles: ['Lead DBA', 'Enterprise Architect'],
      fourEyesConfirmed: false,
      riskScore: 0.12,
      summary: 'Catalog fencing passed (100%). 3 DBs, 4 Schemas, 124 Objects cataloged. Readiness 99.4%.',
      evidenceSummary: 'Catalog discovery probe SHA-256 digest verified. Zero fatal DDL conversion blockers.',
      comments: [
        { author: 'Aalok', timestamp: '2026-08-06T14:16:00Z', text: 'All catalog probes completed cleanly. Ready for Gate 1 sign-off.' },
      ],
    },
    {
      id: 'appr-002',
      gate: 'GATE_2',
      gateTitle: 'Gate 2: Migration Plan & Execution Approval',
      migrationId: 'MIG-2026-0806-002',
      migrationName: 'Financial Audit Ledger Migration',
      projectName: 'Finance Core Cloud Modernization',
      requestedBy: 'Elena (SecOps Lead)',
      requestedAt: '2026-08-06T12:00:00Z',
      expiresAt: '2026-08-07T12:00:00Z',
      status: 'pending',
      requiredRoles: ['Lead DBA', 'Security Lead', 'Compliance Officer'],
      fourEyesConfirmed: true,
      riskScore: 0.78,
      summary: '11 Tier Topological DAG Plan generated. 8 Workers, Batch Size 10k, SHA-256 Masking rules active.',
      evidenceSummary: 'Target DDL checksum verified. PK surrogate policies confirmed compliant.',
      comments: [
        { author: 'Elena', timestamp: '2026-08-06T12:05:00Z', text: 'Security scan passed. Mandatory TLS 1.3 encryption enforced.' },
        { author: 'Marcus', timestamp: '2026-08-06T13:10:00Z', text: 'Compliance review completed. PCI-DSS columns redacted.' },
      ],
    },
    {
      id: 'appr-003',
      gate: 'GATE_3',
      gateTitle: 'Gate 3: Production Cutover Authorization',
      migrationId: 'MIG-2026-0806-003',
      migrationName: 'Customer Master CDC Synchronization',
      projectName: 'CRM Core Database Sync',
      requestedBy: 'Sarah (Migration Commander)',
      requestedAt: '2026-08-06T15:00:00Z',
      expiresAt: '2026-08-06T18:00:00Z',
      status: 'pending',
      requiredRoles: ['Migration Director', 'Operations Lead'],
      fourEyesConfirmed: true,
      riskScore: 0.25,
      summary: 'CDC Synchronization Lag = 0.000s. Validation score 100% (CRC32 Checksum). 1.24B rows loaded.',
      evidenceSummary: 'LSN Checkpoint chkpt-04a8f910-lsn sealed. Target DB readiness probes green.',
      comments: [
        { author: 'Sarah', timestamp: '2026-08-06T15:02:00Z', text: 'Replication lag at zero. Ready for GO / NO-GO cutover sign-off.' },
      ],
    },
    {
      id: 'appr-004',
      gate: 'GATE_2',
      gateTitle: 'Gate 2: Migration Plan & Execution Approval',
      migrationId: 'MIG-2026-0806-004',
      migrationName: 'Supply Chain Inventory Database',
      projectName: 'Logistics Infrastructure Upgrade',
      requestedBy: 'David (Systems Architect)',
      requestedAt: '2026-08-05T09:30:00Z',
      expiresAt: '2026-08-06T09:30:00Z',
      status: 'approved',
      requiredRoles: ['Lead DBA', 'Security Lead'],
      fourEyesConfirmed: true,
      riskScore: 0.15,
      summary: 'Execution DAG plan approved. 4 Workers allocated. Pre-flight simulation passed.',
      evidenceSummary: 'CAB Ticket CAB-8894-SIGNED confirmed.',
      approver: 'Aalok',
      approvedAt: '2026-08-05T10:15:00Z',
      decisionReason: 'Plan validated and CAB change ticket verified.',
      comments: [
        { author: 'Aalok', timestamp: '2026-08-05T10:15:00Z', text: 'Decision: APPROVED — Plan validated and CAB change ticket verified.' },
      ],
    },
    {
      id: 'appr-005',
      gate: 'GATE_1',
      gateTitle: 'Gate 1: Discovery & Scope Assessment',
      migrationId: 'MIG-2026-0806-005',
      migrationName: 'HR Legacy Payroll Migration',
      projectName: 'Human Resources Platform Upgrade',
      requestedBy: 'Robert (DBA)',
      requestedAt: '2026-08-04T11:00:00Z',
      expiresAt: '2026-08-05T11:00:00Z',
      status: 'rejected',
      requiredRoles: ['Enterprise Architect', 'Lead DBA'],
      fourEyesConfirmed: false,
      riskScore: 0.85,
      summary: 'High risk scoring due to 14 unindexed primary-keyless tables in legacy schema.',
      evidenceSummary: 'Discovery probe flagged 14 tables requiring surrogate key definition.',
      approver: 'Aalok',
      approvedAt: '2026-08-04T11:45:00Z',
      decisionReason: 'Changes required: Primary keyless tables must be resolved before proceeding.',
      comments: [
        { author: 'Aalok', timestamp: '2026-08-04T11:45:00Z', text: 'Decision: REJECTED — Changes required: Primary keyless tables must be resolved before proceeding.' },
      ],
    },
    {
      id: 'appr-006',
      gate: 'GATE_3',
      gateTitle: 'Gate 3: Production Cutover Authorization',
      migrationId: 'MIG-2026-0806-006',
      migrationName: 'Global Analytics Data Warehouse',
      projectName: 'Enterprise DW Cloud Transition',
      requestedBy: 'Chen (Analytics Lead)',
      requestedAt: '2026-08-05T08:00:00Z',
      expiresAt: '2026-08-05T12:00:00Z',
      status: 'pending',
      requiredRoles: ['Migration Director', 'Operations Lead'],
      fourEyesConfirmed: false,
      riskScore: 0.92,
      summary: 'SLA BREACHED: Cutover authorization pending past 4-hour window SLA. CDC Lag 0.004s.',
      evidenceSummary: 'SLA breach alert dispatched to Migration Commander.',
      comments: [
        { author: 'Chen', timestamp: '2026-08-05T08:05:00Z', text: 'Awaiting cutover window authorization signal.' },
      ],
    },
  ];
  private listeners: Set<ApprovalChangeListener> = new Set();

  public getApprovals(): GovernanceApproval[] {
    return [...this.approvals];
  }

  public getPendingApprovals(): GovernanceApproval[] {
    return this.approvals.filter((a) => a.status === 'pending');
  }

  public getApprovalHistory(): GovernanceApproval[] {
    return this.approvals.filter((a) => a.status !== 'pending');
  }

  public subscribe(listener: ApprovalChangeListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    const copy = [...this.approvals];
    this.listeners.forEach((fn) => fn(copy));
  }

  public createApprovalRequest(
    gate: GateId,
    gateTitle: string,
    migrationId: string,
    migrationName: string,
    projectName: string,
    requestedBy: string,
    requiredRoles: TeamRole[],
    summary: string,
    evidenceSummary?: string,
    riskScore?: number
  ): GovernanceApproval {
    const req: GovernanceApproval = {
      id: `appr-${Date.now()}`,
      gate,
      gateTitle,
      migrationId,
      migrationName,
      projectName,
      requestedBy,
      requestedAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      status: 'pending',
      requiredRoles,
      fourEyesConfirmed: false,
      riskScore,
      summary,
      evidenceSummary,
      comments: [],
    };

    this.approvals = [req, ...this.approvals];
    this.notify();
    return req;
  }

  public processDecision(
    id: string,
    decision: 'approved' | 'rejected' | 'changes_requested',
    approver: string,
    reason: string
  ): GovernanceApproval | null {
    const index = this.approvals.findIndex((a) => a.id === id);
    if (index === -1) return null;

    const item = this.approvals[index];
    const updated: GovernanceApproval = {
      ...item,
      status: decision,
      approver,
      approvedAt: new Date().toISOString(),
      decisionReason: reason,
      fourEyesConfirmed: decision === 'approved',
      comments: [
        ...(item.comments || []),
        { author: approver, timestamp: new Date().toISOString(), text: `Decision: ${decision.toUpperCase()} — ${reason}` },
      ],
    };

    // Forward approval decision to Engine Gateway over IPC
    ipcService.invokeEngineCapability('request_approval', JSON.stringify({
      approval_id: id,
      decision,
      approver,
      reason,
      gate: item.gate,
    })).catch(() => {});

    this.approvals[index] = updated;
    this.notify();
    return updated;
  }

  public setApprovalsFromIPC(incoming: GovernanceApproval[]): void {
    this.approvals = incoming;
    this.notify();
  }
}

export const approvalRepository = new ApprovalRepository();
