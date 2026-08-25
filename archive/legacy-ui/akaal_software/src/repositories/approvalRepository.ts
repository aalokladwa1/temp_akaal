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

  public async processDecision(
    id: string,
    decision: 'approved' | 'rejected' | 'changes_requested',
    approver: string,
    reason: string
  ): Promise<GovernanceApproval | null> {
    const index = this.approvals.findIndex((a) => a.id === id);
    const item = index !== -1 ? this.approvals[index] : null;

    try {
      // Forward approval decision to Engine Gateway over IPC capability
      await ipcService.invokeEngineCapability('submit_approval_decision', JSON.stringify({
        approval_id: id,
        approval_reference_id: id,
        decision,
        approver,
        reason,
        gate: item?.gate,
        migration_id: item?.migrationId,
      }));

      // Reconcile authoritatively from Engine Gateway CentralStateStore
      await this.syncFromEngine();
    } catch (err) {
      console.warn('submit_approval_decision IPC sync note:', err);
    }

    const updated = this.approvals.find((a) => a.id === id || (item && a.migrationId === item.migrationId));
    return updated || item;
  }

  public setApprovalsFromIPC(incoming: GovernanceApproval[]): void {
    this.approvals = incoming;
    this.notify();
  }

  public async syncFromEngine(): Promise<GovernanceApproval[]> {
    try {
      const rawRes = await ipcService.invokeEngineCapability('get_approval_queue', '{}');
      const parsed = typeof rawRes === 'string' ? JSON.parse(rawRes) : rawRes;
      const res = parsed?.result ? (typeof parsed.result === 'string' ? JSON.parse(parsed.result) : parsed.result) : parsed;

      if (res && Array.isArray(res.approvals)) {
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
          requiredRoles: pkt.required_roles || pkt.requiredRoles || ['Lead DBA'],
          fourEyesConfirmed: pkt.status === 'approved',
          riskScore: typeof pkt.riskScore === 'number' ? pkt.riskScore : (pkt.risk_score || 0.1),
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
    return this.approvals;
  }
}

export const approvalRepository = new ApprovalRepository();
