import { Injectable, inject, signal, computed } from '@angular/core';
import { MigrationUiService } from './migration-ui.service';
import { Step7PlanStoreService } from './step7-plan-store.service';
import { IpcService } from './ipc.service';
import { Step8GovernanceAdapterService } from './step8-governance-adapter.service';
import {
  OverallReadinessPresentation,
  GovernanceGatePresentation,
  GateApprovalStatus,
  ReadinessCategoryGroup,
  ReadinessCheckPresentation,
  ReadinessCheckCategory,
  RequiredActionPresentation,
  PolicyAcknowledgementPresentation,
  GovernedPlanSnapshot,
  GovernanceActivityEvent
} from '../../modules/migration/create/steps/step8-governance.models';

@Injectable({
  providedIn: 'root'
})
export class Step8GovernanceStoreService {
  public ms: MigrationUiService;
  public step7Store: Step7PlanStoreService;
  public ipc: IpcService;
  public adapter: Step8GovernanceAdapterService;

  constructor(
    ms?: MigrationUiService,
    step7Store?: Step7PlanStoreService,
    ipc?: IpcService,
    adapter?: Step8GovernanceAdapterService
  ) {
    try { this.ms = ms || inject(MigrationUiService); } catch { this.ms = ms || new MigrationUiService(); }
    try { this.step7Store = step7Store || inject(Step7PlanStoreService); } catch { this.step7Store = step7Store || new Step7PlanStoreService(); }
    try { this.ipc = ipc || inject(IpcService); } catch { this.ipc = ipc || new IpcService(); }
    try { this.adapter = adapter || inject(Step8GovernanceAdapterService); } catch { this.adapter = adapter || new Step8GovernanceAdapterService(); }
  }

  // --------------------------------------------------------------------------
  // REACTIVE STATE SIGNALS
  // --------------------------------------------------------------------------
  public gateDecisions = signal<Map<string, { status: GateApprovalStatus; comment?: string; actor?: string; role?: string; decidedAt?: string }>>(new Map());
  public recordedAcks = signal<Map<string, { isAcknowledged: boolean; by?: string; at?: string; rationale?: string }>>(new Map());
  public retriedCheckIds = signal<Set<string>>(new Set());
  public expandedCategoryIds = signal<Set<ReadinessCheckCategory>>(new Set());

  // Drawer and Modal Visibility Signals
  public selectedApprovalGate = signal<GovernanceGatePresentation | null>(null);
  public selectedReadinessCheck = signal<ReadinessCheckPresentation | null>(null);
  public isTechnicalModalOpen = signal<boolean>(false);
  public isActivityDrawerOpen = signal<boolean>(false);
  public isRetryingCheck = signal<boolean>(false);

  // --------------------------------------------------------------------------
  // REACTIVE COMPUTED PROJECTIONS
  // --------------------------------------------------------------------------
  public governanceGates = computed<GovernanceGatePresentation[]>(() => {
    const plan = this.step7Store.activePlan();
    const decisions = this.gateDecisions();
    return this.adapter.adaptGovernanceGates(plan, decisions);
  });

  public readinessCategories = computed<ReadinessCategoryGroup[]>(() => {
    const draft = this.ms.wizardDraft();
    const plan = this.step7Store.activePlan();
    const retried = this.retriedCheckIds();
    const expanded = this.expandedCategoryIds();
    return this.adapter.adaptReadinessCategories(draft, plan, retried, expanded);
  });

  public policyAcknowledgements = computed<PolicyAcknowledgementPresentation[]>(() => {
    const draft = this.ms.wizardDraft();
    const acks = this.recordedAcks();
    return this.adapter.adaptPolicyAcknowledgements(draft, acks);
  });

  public requiredActions = computed<RequiredActionPresentation[]>(() => {
    const gates = this.governanceGates();
    const categories = this.readinessCategories();
    const acks = this.policyAcknowledgements();
    return this.adapter.adaptRequiredActions(gates, categories, acks);
  });

  public overallReadiness = computed<OverallReadinessPresentation>(() => {
    const gates = this.governanceGates();
    const categories = this.readinessCategories();
    const acks = this.policyAcknowledgements();
    const actions = this.requiredActions();
    return this.adapter.adaptOverallReadiness(gates, categories, acks, actions);
  });

  public governedPlanSnapshot = computed<GovernedPlanSnapshot>(() => {
    const draft = this.ms.wizardDraft();
    const plan = this.step7Store.activePlan();
    const overall = this.overallReadiness();
    return this.adapter.adaptGovernedPlanSnapshot(draft, plan, overall.status);
  });

  public activityEvents = computed<GovernanceActivityEvent[]>(() => {
    const draft = this.ms.wizardDraft();
    const decisions = this.gateDecisions();
    return this.adapter.adaptActivityEvents(draft, decisions);
  });

  // --------------------------------------------------------------------------
  // CANONICAL STEP 8 -> STEP 9 ELIGIBILITY (CAN CONTINUE TO REVIEW)
  // --------------------------------------------------------------------------
  public canContinueToReview = computed<boolean>(() => {
    const overall = this.overallReadiness();
    // Cannot proceed if there are hard blockers or rejected gates
    if (overall.readinessSummary.blockedCount > 0) return false;
    if (this.governanceGates().some(g => g.status === 'REJECTED')) return false;

    // All required gates must be approved or satisfied (or zero gates exist)
    const gates = this.governanceGates();
    const allGatesApproved = gates.length === 0 || gates.every(g => g.status === 'APPROVED' || g.status === 'SATISFIED');

    // All policy acknowledgements must be recorded
    const acks = this.policyAcknowledgements();
    const allAcksRecorded = acks.every(a => a.isAcknowledged);

    return allGatesApproved && allAcksRecorded;
  });

  // Step 8 Validation Guard used by Wizard Shell
  public isStep8Valid = computed<boolean>(() => {
    return this.canContinueToReview();
  });

  // --------------------------------------------------------------------------
  // STORE ACTIONS & IPC ORCHESTRATION
  // --------------------------------------------------------------------------

  public openApprovalDrawer(gate: GovernanceGatePresentation): void {
    this.selectedApprovalGate.set(gate);
    this.selectedReadinessCheck.set(null);
  }

  public closeApprovalDrawer(): void {
    this.selectedApprovalGate.set(null);
  }

  public async approveGate(gateId: string, comment: string): Promise<void> {
    const gate = this.governanceGates().find(g => g.id === gateId);
    if (!gate) return;

    // Invoke real IPC governance operation
    await this.ipc.invoke('engine/governance', 'approve_gate', {
      planId: this.step7Store.activePlan().technicalDetails?.planId || 'PLAN-MIG-2026-0905-A8',
      gateId,
      comment,
      actorRole: gate.actorContext.currentActorRole,
      actorName: gate.actorContext.currentActorName
    });

    // Update reactive state from result
    this.gateDecisions.update(map => {
      const next = new Map(map);
      next.set(gateId, {
        status: 'APPROVED',
        comment,
        actor: gate.actorContext.currentActorName,
        role: gate.actorContext.currentActorRole,
        decidedAt: new Date().toISOString()
      });
      return next;
    });

    this.closeApprovalDrawer();
  }

  public async rejectGate(gateId: string, reason: string): Promise<void> {
    const gate = this.governanceGates().find(g => g.id === gateId);
    if (!gate) return;

    // Invoke real IPC governance operation
    await this.ipc.invoke('engine/governance', 'reject_gate', {
      planId: this.step7Store.activePlan().technicalDetails?.planId || 'PLAN-MIG-2026-0905-A8',
      gateId,
      reason,
      actorRole: gate.actorContext.currentActorRole,
      actorName: gate.actorContext.currentActorName
    });

    // Update reactive state from result
    this.gateDecisions.update(map => {
      const next = new Map(map);
      next.set(gateId, {
        status: 'REJECTED',
        comment: reason,
        actor: gate.actorContext.currentActorName,
        role: gate.actorContext.currentActorRole,
        decidedAt: new Date().toISOString()
      });
      return next;
    });

    this.closeApprovalDrawer();
  }

  public openReadinessDrawer(check: ReadinessCheckPresentation): void {
    this.selectedReadinessCheck.set(check);
    this.selectedApprovalGate.set(null);
  }

  public closeReadinessDrawer(): void {
    this.selectedReadinessCheck.set(null);
  }

  public async retryCheck(checkId: string): Promise<void> {
    this.isRetryingCheck.set(true);

    try {
      // Invoke real IPC readiness evaluation operation
      await this.ipc.invoke('engine/readiness', 'evaluate_check', {
        checkId,
        mode: this.ms.wizardDraft().mode
      });

      this.retriedCheckIds.update(set => {
        const next = new Set(set);
        next.add(checkId);
        return next;
      });
    } finally {
      this.isRetryingCheck.set(false);
    }
  }

  public async recordAcknowledgement(ackId: string, rationale: string): Promise<void> {
    // Invoke real IPC governance acknowledgement operation
    await this.ipc.invoke('engine/governance', 'record_acknowledgement', {
      ackId,
      rationale,
      actorRole: 'Lead DBA'
    });

    this.recordedAcks.update(map => {
      const next = new Map(map);
      next.set(ackId, {
        isAcknowledged: true,
        by: 'db_admin_prod (Lead DBA)',
        at: new Date().toISOString(),
        rationale
      });
      return next;
    });
  }

  public toggleCategoryExpansion(categoryId: ReadinessCheckCategory): void {
    this.expandedCategoryIds.update(set => {
      const next = new Set(set);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  }

  public openTechnicalModal(): void {
    this.isTechnicalModalOpen.set(true);
  }

  public closeTechnicalModal(): void {
    this.isTechnicalModalOpen.set(false);
  }

  public openActivityDrawer(): void {
    this.isActivityDrawerOpen.set(true);
  }

  public closeActivityDrawer(): void {
    this.isActivityDrawerOpen.set(false);
  }

  public routeToUpstreamStep(stepIndex?: number): void {
    if (stepIndex && stepIndex >= 1 && stepIndex <= 7) {
      this.ms.updateDraft({ currentStep: stepIndex });
    }
  }
}
