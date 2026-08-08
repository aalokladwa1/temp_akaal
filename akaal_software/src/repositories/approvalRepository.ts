import type { GovernanceApproval, GateId, TeamRole } from '../types/migration';
import { ipcService } from '../services/ipcService';

type ApprovalChangeListener = (approvals: GovernanceApproval[]) => void;

class ApprovalRepository {
  private approvals: GovernanceApproval[] = [];
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

    // Forward approval decision to Engine Gateway over IPC capability
    ipcService.invokeEngineCapability('submit_approval_decision', JSON.stringify({
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

  public async syncFromEngine(): Promise<GovernanceApproval[]> {
    try {
      const rawRes = await ipcService.invokeEngineCapability('get_approval_queue', '{}');
      const res = JSON.parse(rawRes);
      if (res && Array.isArray(res.approvals) && res.approvals.length > 0) {
        const mapped: GovernanceApproval[] = res.approvals.map((pkt: any) => ({
          id: pkt.id || pkt.approval_reference_id || `appr-${Date.now()}`,
          gate: pkt.gate || 'GATE_1',
          gateTitle: pkt.gateTitle || 'Pre-Execution Safety Review',
          migrationId: pkt.migration_id || pkt.migrationId || 'mig-active',
          migrationName: pkt.migration_name || pkt.migrationName || 'Database Migration',
          projectName: pkt.project_name || pkt.projectName || 'Enterprise Workspace',
          requestedBy: pkt.requested_by || pkt.requestedBy || 'Aalok',
          requestedAt: pkt.requested_at || pkt.requestedAt || new Date().toISOString(),
          expiresAt: pkt.expires_at || pkt.expiresAt || new Date(Date.now() + 86400000).toISOString(),
          status: (pkt.status || 'pending').toLowerCase() as any,
          requiredRoles: pkt.required_roles || ['Lead DBA'],
          fourEyesConfirmed: pkt.status === 'approved',
          riskScore: pkt.risk_score || 0.1,
          summary: pkt.summary || 'Authoritative backend approval packet',
          decisionReason: pkt.decisionReason,
          approver: pkt.approver,
          comments: pkt.comments || []
        }));
        this.setApprovalsFromIPC(mapped);
        return mapped;
      }
    } catch {
      // Return local memory repository
    }
    return this.getApprovals();
  }
}

export const approvalRepository = new ApprovalRepository();
