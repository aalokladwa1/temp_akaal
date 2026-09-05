import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';
import { PlanDagNode, PlanDagEdge, ApprovalBarrierConfig } from './step7-plan.models';

@Component({
  selector: 'app-step7-plan-flow',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-3 font-sans select-none">
      
      <!-- FLOW STAGES CONTAINER -->
      <div class="flex flex-col gap-0 relative">
        @for (node of store.nodes(); track node.id; let idx = $index; let isLast = $last) {
          
          <!-- STAGE / BARRIER ROW -->
          <div class="flex flex-col items-center w-full">
            
            <!-- 1. EXECUTION STAGE CARD -->
            @if (node.nodeType === 'EXECUTION_STAGE') {
              <div
                (click)="store.openStageDrawer(node)"
                class="w-full bg-white border rounded-xl p-4 cursor-pointer transition-colors text-left"
                [class.border-blue-600]="store.selectedStage()?.id === node.id"
                [class.bg-blue-50]="store.selectedStage()?.id === node.id"
                [class.border-slate-200]="store.selectedStage()?.id !== node.id"
                [class.hover:border-slate-400]="store.selectedStage()?.id !== node.id">
                
                <div class="flex items-start justify-between gap-4">
                  
                  <!-- Left: Icon, Number, Title, Purpose -->
                  <div class="flex items-start gap-3.5 min-w-0">
                    <div
                      class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border"
                      [class.bg-blue-50]="node.category === 'INGESTION'"
                      [class.text-blue-700]="node.category === 'INGESTION'"
                      [class.border-blue-200]="node.category === 'INGESTION'"
                      [class.bg-indigo-50]="node.category === 'TRANSFORMATION'"
                      [class.text-indigo-700]="node.category === 'TRANSFORMATION'"
                      [class.border-indigo-200]="node.category === 'TRANSFORMATION'"
                      [class.bg-emerald-50]="node.category === 'VALIDATION'"
                      [class.text-emerald-700]="node.category === 'VALIDATION'"
                      [class.border-emerald-200]="node.category === 'VALIDATION'"
                      [class.bg-amber-50]="node.category === 'GOVERNANCE'"
                      [class.text-amber-700]="node.category === 'GOVERNANCE'"
                      [class.border-amber-200]="node.category === 'GOVERNANCE'"
                      [class.bg-slate-100]="node.category === 'SYSTEM'"
                      [class.text-slate-700]="node.category === 'SYSTEM'"
                      [class.border-slate-200]="node.category === 'SYSTEM'">
                      <app-lucide-icon [name]="getStageIcon(node.stageType)" [size]="18"></app-lucide-icon>
                    </div>

                    <div class="flex flex-col gap-1 min-w-0">
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-xs font-mono font-bold text-slate-500">STAGE {{ node.order }}</span>
                        <h4 class="text-sm font-bold text-slate-900 m-0 tracking-tight">{{ node.label }}</h4>
                        
                        <!-- Category Badge -->
                        <span
                          class="px-2 py-0.5 rounded text-[10.5px] font-bold uppercase tracking-wider border"
                          [class.bg-blue-50]="node.category === 'INGESTION'"
                          [class.text-blue-700]="node.category === 'INGESTION'"
                          [class.border-blue-200]="node.category === 'INGESTION'"
                          [class.bg-indigo-50]="node.category === 'TRANSFORMATION'"
                          [class.text-indigo-700]="node.category === 'TRANSFORMATION'"
                          [class.border-indigo-200]="node.category === 'TRANSFORMATION'"
                          [class.bg-emerald-50]="node.category === 'VALIDATION'"
                          [class.text-emerald-700]="node.category === 'VALIDATION'"
                          [class.border-emerald-200]="node.category === 'VALIDATION'"
                          [class.bg-amber-50]="node.category === 'GOVERNANCE'"
                          [class.text-amber-700]="node.category === 'GOVERNANCE'"
                          [class.border-amber-200]="node.category === 'GOVERNANCE'"
                          [class.bg-slate-100]="node.category === 'SYSTEM'"
                          [class.text-slate-700]="node.category === 'SYSTEM'"
                          [class.border-slate-200]="node.category === 'SYSTEM'">
                          {{ node.category }}
                        </span>

                        @if (node.isContinuous) {
                          <span class="px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 text-[10.5px] font-bold flex items-center gap-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-purple-600"></span>
                            {{ node.continuousLabel || 'Continuous' }}
                          </span>
                        }

                        @if (node.hasIssues) {
                          <span class="px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 text-[10.5px] font-bold flex items-center gap-1">
                            <app-lucide-icon name="alert-triangle" [size]="11"></app-lucide-icon>
                            <span>{{ node.issueIds?.length || 1 }} advisory</span>
                          </span>
                        }
                      </div>

                      <p class="text-xs text-slate-600 m-0 line-clamp-1">{{ node.purpose }}</p>
                    </div>
                  </div>

                  <!-- Right: Stage Execution Metrics & Action -->
                  <div class="flex items-center gap-3 shrink-0">
                    <div class="flex items-center gap-2">
                      @if (node.workerAllocation) {
                        <div class="px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 flex items-center gap-1.5 text-slate-700" title="Worker Allocation">
                          <app-lucide-icon name="cpu" [size]="13" class="text-slate-500"></app-lucide-icon>
                          <span class="font-bold text-slate-900 text-xs">{{ node.workerAllocation }}</span>
                          <span class="text-slate-500 text-[11px]">workers</span>
                        </div>
                      }

                      @if (node.batchSizeMb) {
                        <div class="px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 flex items-center gap-1.5 text-slate-700" title="Batch Size">
                          <app-lucide-icon name="layers" [size]="13" class="text-slate-500"></app-lucide-icon>
                          <span class="font-bold text-slate-900 text-xs">{{ node.batchSizeMb }}</span>
                          <span class="text-slate-500 text-[11px]">MB batch</span>
                        </div>
                      }

                      <div class="px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 flex items-center gap-1.5 text-slate-700" title="Estimated Duration">
                        <app-lucide-icon name="clock" [size]="13" class="text-slate-500"></app-lucide-icon>
                        <span class="font-bold text-slate-900 text-xs">{{ node.estimatedDuration }}</span>
                      </div>
                    </div>

                    <div class="flex items-center text-slate-400 hover:text-blue-600 pl-1">
                      <app-lucide-icon name="chevron-right" [size]="18"></app-lucide-icon>
                    </div>
                  </div>

                </div>
              </div>
            }

            <!-- 2. APPROVAL BARRIER CARD -->
            @if (node.nodeType === 'APPROVAL_BARRIER' && node.barrierConfig) {
              <div
                (click)="store.openGateDrawer(node.barrierConfig)"
                class="w-full bg-amber-50 border border-amber-300 rounded-xl p-3.5 cursor-pointer transition-colors text-left"
                [class.ring-2]="store.selectedGate()?.id === node.barrierConfig.id"
                [class.ring-amber-500]="store.selectedGate()?.id === node.barrierConfig.id"
                [class.hover:border-amber-400]="store.selectedGate()?.id !== node.barrierConfig.id">
                
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-start gap-3 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-amber-100 border border-amber-300 text-amber-900 flex items-center justify-center shrink-0">
                      <app-lucide-icon name="shield-check" [size]="16"></app-lucide-icon>
                    </div>

                    <div class="flex flex-col gap-0.5 min-w-0">
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="px-2 py-0.5 rounded bg-amber-200 text-amber-950 font-bold text-[10px] uppercase tracking-wider">
                          {{ node.barrierConfig.isMandatory ? 'Mandatory Policy Barrier' : 'Planned Governance Gate' }}
                        </span>
                        <h4 class="text-xs font-bold text-amber-950 m-0">{{ node.barrierConfig.gateName }}</h4>
                        <span class="text-xs font-semibold text-amber-800">
                          ({{ formatSignerPolicy(node.barrierConfig.signerPolicy) }} &middot; {{ node.barrierConfig.requiredSignatures }} {{ node.barrierConfig.requiredSignatures === 1 ? 'Signature' : 'Signatures' }})
                        </span>
                      </div>
                      <p class="text-[11.5px] text-amber-900 m-0 line-clamp-1">
                        {{ node.barrierConfig.description }}
                      </p>
                    </div>
                  </div>

                  <!-- Right: Invariants & Preconditions chips -->
                  <div class="flex items-center gap-2 shrink-0">
                    @if (node.barrierConfig.separationOfDuties) {
                      <span class="px-2 py-0.5 rounded bg-white border border-amber-300 text-amber-900 text-[10px] font-bold">
                        SoD Enforced
                      </span>
                    }

                    @if (node.barrierConfig.requireDlqEmpty) {
                      <span class="px-2 py-0.5 rounded bg-white border border-amber-300 text-amber-900 text-[10px] font-medium">
                        DLQ Clean
                      </span>
                    }

                    @if (node.barrierConfig.cdcMaxLagMs) {
                      <span class="px-2 py-0.5 rounded bg-white border border-amber-300 text-amber-900 text-[10px] font-medium">
                        Lag &le; {{ node.barrierConfig.cdcMaxLagMs }}ms
                      </span>
                    }

                    <div class="flex items-center text-amber-700 pl-1">
                      <app-lucide-icon name="chevron-right" [size]="16"></app-lucide-icon>
                    </div>
                  </div>
                </div>

              </div>
            }

            <!-- 3. CONNECTOR STEM & ADD GATE AFFORDANCE -->
            @if (!isLast) {
              <div class="h-6 w-full flex items-center justify-center relative my-0.5 group">
                <!-- Vertical Line -->
                <div class="w-[2px] h-full bg-slate-200"></div>

                <!-- Add Gate Button on Hover / Click -->
                @if (isEdgeEligible(node.id)) {
                  <button
                    type="button"
                    (click)="openAddGateForNode(node.id)"
                    class="absolute px-2.5 py-0.5 rounded-full bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 text-slate-600 hover:text-blue-700 text-[10.5px] font-semibold flex items-center gap-1 shadow-none transition-colors cursor-pointer z-10"
                    title="Insert Approval Gate at this boundary">
                    <app-lucide-icon name="plus" [size]="11"></app-lucide-icon>
                    <span>Add Gate</span>
                  </button>
                }
              </div>
            }

          </div>
        }
      </div>

    </div>
  `
})
export class Step7PlanFlowComponent {
  public store = inject(Step7PlanStoreService);

  public getStageIcon(stageType: string): string {
    switch (stageType) {
      case 'PRE_FLIGHT': return 'check-circle-2';
      case 'SCHEMA_DDL': return 'code-2';
      case 'DATA_PREPARATION': return 'wrench';
      case 'BULK_EXTRACT': return 'database';
      case 'BULK_LOAD': return 'upload';
      case 'CDC_CAPTURE': return 'radio';
      case 'CDC_APPLY': return 'zap';
      case 'STATE_COMPARE': return 'git-compare';
      case 'INDEX_REBUILD': return 'file-code-2';
      case 'POST_VALIDATION': return 'shield-check';
      case 'CUTOVER': return 'flag';
      case 'ROLLBACK_GUARD': return 'rotate-ccw';
      default: return 'workflow';
    }
  }

  public formatSignerPolicy(policy: string): string {
    switch (policy) {
      case 'FOUR_EYES': return 'Four-Eyes Principle';
      case 'SOLE_OWNER': return 'Sole Owner';
      case 'CAB_COMMITTEE': return 'CAB Committee';
      case 'DUAL_DBA_SEC': return 'Dual DBA & Security';
      default: return policy;
    }
  }

  public isEdgeEligible(nodeId: string): boolean {
    const eligible = this.store.eligibleEdges();
    return eligible.some(e => e.source === nodeId);
  }

  public openAddGateForNode(nodeId: string): void {
    const edge = this.store.eligibleEdges().find(e => e.source === nodeId);
    if (edge) {
      this.store.openAddGateModal(edge.id);
    }
  }
}
