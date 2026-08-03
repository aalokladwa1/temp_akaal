import type { GovernanceApproval, GateId, TeamRole } from '../types/migration';

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
