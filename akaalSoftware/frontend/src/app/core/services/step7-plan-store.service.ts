import { Injectable, inject, signal, computed } from '@angular/core';
import { MigrationUiService } from './migration-ui.service';
import { Step7PlanAdapterService } from './step7-plan-adapter.service';
import {
  PlanDagNode,
  PlanDagEdge,
  PlanReviewIssue,
  PlanSummaryData,
  TechnicalPlanDetails,
  Step7PlanDescriptor,
  ApprovalBarrierConfig,
  NewGateDraft
} from '../../modules/migration/create/steps/step7-plan.models';

@Injectable({
  providedIn: 'root'
})
export class Step7PlanStoreService {
  public ms: MigrationUiService;
  public adapter: Step7PlanAdapterService;

  constructor(ms?: MigrationUiService, adapter?: Step7PlanAdapterService) {
    try {
      this.ms = ms || inject(MigrationUiService);
    } catch {
      this.ms = ms || new MigrationUiService();
    }
    try {
      this.adapter = adapter || inject(Step7PlanAdapterService);
    } catch {
      this.adapter = adapter || new Step7PlanAdapterService();
    }
  }

  // Reactive State Signals
  public customBarriers = signal<ApprovalBarrierConfig[]>([]);
  public acknowledgedIssueIds = signal<Set<string>>(new Set());

  // Drawer and Modal Visibility Signals
  public selectedStage = signal<PlanDagNode | null>(null);
  public selectedGate = signal<ApprovalBarrierConfig | null>(null);
  public isAddGateModalOpen = signal<boolean>(false);
  public selectedPlacementEdgeId = signal<string>('');
  public isTechnicalModalOpen = signal<boolean>(false);
  public highlightedGateId = signal<string | null>(null);
  public showAllAdvisories = signal<boolean>(false);
  public stageDrawerSearch = signal<string>('');

  // Active Plan Descriptor computed from Wizard State + Custom Barriers + Acknowledgements
  public activePlan = computed<Step7PlanDescriptor>(() => {
    const draft = this.ms.wizardDraft();
    const custom = this.customBarriers();
    const acked = this.acknowledgedIssueIds();
    return this.adapter.buildPlanDescriptor(draft, custom, acked);
  });

  // Direct Computed Projections
  public nodes = computed<PlanDagNode[]>(() => this.activePlan().nodes);
  public edges = computed<PlanDagEdge[]>(() => this.activePlan().edges);
  public summary = computed<PlanSummaryData>(() => this.activePlan().summary);
  public issues = computed<PlanReviewIssue[]>(() => this.activePlan().issues);
  public technicalDetails = computed<TechnicalPlanDetails>(() => this.activePlan().technicalDetails);

  // Filtered Stages (excluding barrier nodes for stage specific lists)
  public executionStages = computed<PlanDagNode[]>(() => {
    return this.nodes().filter(n => n.nodeType === 'EXECUTION_STAGE');
  });

  // Governance Approval Gates in Current Plan
  public approvalGates = computed<ApprovalBarrierConfig[]>(() => {
    const list: ApprovalBarrierConfig[] = [];
    for (const node of this.nodes()) {
      if (node.nodeType === 'APPROVAL_BARRIER' && node.barrierConfig) {
        list.push(node.barrierConfig);
      }
    }
    return list;
  });

  // Eligible Edges for adding approval barriers
  public eligibleEdges = computed<PlanDagEdge[]>(() => {
    return this.edges().filter(e => e.isApprovalBarrierEligible && !e.hasApprovalBarrier);
  });

  // Issue Counts by Category
  public blockerIssues = computed<PlanReviewIssue[]>(() => {
    return this.issues().filter(i => i.category === 'MUST_RESOLVE');
  });

  public reviewRequiredIssues = computed<PlanReviewIssue[]>(() => {
    return this.issues().filter(i => i.category === 'REVIEW_REQUIRED');
  });

  public advisoryIssues = computed<PlanReviewIssue[]>(() => {
    return this.issues().filter(i => i.category === 'ADVISORY');
  });

  public visibleAdvisoryIssues = computed<PlanReviewIssue[]>(() => {
    const all = this.advisoryIssues();
    if (this.showAllAdvisories()) {
      return all;
    }
    return all.slice(0, 2);
  });

  public blockerCount = computed<number>(() => this.blockerIssues().length);
  public reviewCount = computed<number>(() => this.reviewRequiredIssues().length);
  public advisoryCount = computed<number>(() => this.advisoryIssues().length);

  // Step 7 Validation Guard: Proceed only if zero unresolved Must-Resolve blockers
  public isStep7Valid = computed<boolean>(() => {
    return this.blockerCount() === 0 && this.nodes().length > 0;
  });

  // Actions
  public openStageDrawer(stage: PlanDagNode): void {
    this.selectedStage.set(stage);
    this.selectedGate.set(null);
    this.stageDrawerSearch.set('');
  }

  public closeStageDrawer(): void {
    this.selectedStage.set(null);
    this.stageDrawerSearch.set('');
  }

  public openGateDrawer(gate: ApprovalBarrierConfig): void {
    this.selectedGate.set(gate);
    this.selectedStage.set(null);
  }

  public closeGateDrawer(): void {
    this.selectedGate.set(null);
  }

  public openAddGateModal(placementEdgeId?: string): void {
    if (placementEdgeId) {
      this.selectedPlacementEdgeId.set(placementEdgeId);
    } else {
      const firstEligible = this.eligibleEdges()[0];
      this.selectedPlacementEdgeId.set(firstEligible ? firstEligible.id : '');
    }
    this.isAddGateModalOpen.set(true);
  }

  public closeAddGateModal(): void {
    this.isAddGateModalOpen.set(false);
    this.selectedPlacementEdgeId.set('');
  }

  public openTechnicalModal(): void {
    this.isTechnicalModalOpen.set(true);
  }

  public closeTechnicalModal(): void {
    this.isTechnicalModalOpen.set(false);
  }

  public setHighlightedGate(gateId: string | null): void {
    this.highlightedGateId.set(gateId);
  }

  public toggleShowAllAdvisories(): void {
    this.showAllAdvisories.update(v => !v);
  }

  public setStageDrawerSearch(query: string): void {
    this.stageDrawerSearch.set(query);
  }

  public toggleAcknowledgeIssue(issueId: string): void {
    this.acknowledgedIssueIds.update(set => {
      const next = new Set(set);
      if (next.has(issueId)) {
        next.delete(issueId);
      } else {
        next.add(issueId);
      }
      return next;
    });
  }

  public addApprovalGate(draft: NewGateDraft): void {
    const targetEdge = this.edges().find(e => e.id === draft.placementEdgeId);
    if (!targetEdge) return;

    const gateId = `barrier-custom-${Date.now()}`;
    const newBarrier: ApprovalBarrierConfig = {
      id: gateId,
      gateName: draft.gateName.trim() || 'Custom Approval Gate',
      description: draft.description.trim() || 'Operator-configured approval checkpoint.',
      protectedOperation: draft.protectedOperation.trim() || 'Downstream Stage Execution',
      signerPolicy: draft.signerPolicy,
      requiredSignatures: draft.requiredSignatures,
      approverRoles: ['DBA_ADMIN', 'MIGRATION_OWNER'],
      separationOfDuties: true,
      cdcMaxLagMs: draft.cdcMaxLagMs,
      requireDlqEmpty: draft.requireDlqEmpty,
      requireCheckpointClean: draft.requireCheckpointClean,
      requireValidationPass: draft.requireValidationPass,
      requireTargetTablesEmpty: draft.requireTargetTablesEmpty,
      rejectionAction: draft.rejectionAction,
      timeoutMinutes: draft.timeoutMinutes,
      timeoutAction: draft.timeoutAction,
      planBindingHash: this.adapter['calculateHash'](`${gateId}-${draft.signerPolicy}`),
      isMandatory: false,
      policyLocked: false,
      afterStageId: targetEdge.source,
      beforeStageId: targetEdge.target
    };

    this.customBarriers.update(list => [...list, newBarrier]);
    this.closeAddGateModal();
  }

  public updateApprovalGate(updated: ApprovalBarrierConfig): void {
    this.customBarriers.update(list => {
      return list.map(b => b.id === updated.id ? updated : b);
    });
    this.closeGateDrawer();
  }

  public removeApprovalGate(gateId: string): void {
    this.customBarriers.update(list => list.filter(b => b.id !== gateId));
    if (this.selectedGate()?.id === gateId) {
      this.closeGateDrawer();
    }
  }

  public routeToUpstreamStep(stepIndex: number): void {
    this.ms.updateDraft({ currentStep: stepIndex });
  }
}

