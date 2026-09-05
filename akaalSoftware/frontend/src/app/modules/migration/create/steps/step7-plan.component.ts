import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';
import { Step7PlanFlowComponent } from './step7-plan-flow.component';
import { Step7StageDrawerComponent } from './step7-stage-drawer.component';
import { Step7ApprovalDrawerComponent } from './step7-approval-drawer.component';
import { Step7AddGateModalComponent } from './step7-add-gate-modal.component';
import { Step7TechnicalModalComponent } from './step7-technical-modal.component';

@Component({
  selector: 'app-step7-plan',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    Step7PlanFlowComponent,
    Step7StageDrawerComponent,
    Step7ApprovalDrawerComponent,
    Step7AddGateModalComponent,
    Step7TechnicalModalComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full font-sans select-none text-xs pb-12">
      
      <!-- ========================================================================= -->
      <!-- CLEAN PAGE HEADING (NO BADGES, NO EXTRA PILLS)                           -->
      <!-- ========================================================================= -->
      <h1 class="text-xl font-bold text-slate-900 m-0 tracking-tight">Dynamic Migration Plan</h1>

      <!-- ========================================================================= -->
      <!-- SECTION 1: MIGRATION PLAN (TOPOLOGY & FLOW)                              -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex flex-col gap-0.5">
          <h2 class="text-sm font-bold text-slate-900 m-0">1. Migration Plan</h2>
          <p class="text-xs text-slate-500 m-0">
            Logical execution topology derived from Steps 1–6. Inspect stages, work allocations, and approval barriers.
          </p>
        </div>

        <!-- FLOW RENDERER COMPONENT -->
        <app-step7-plan-flow />
      </section>

      <!-- ========================================================================= -->
      <!-- SECTION 2: PLAN REVIEW (MUST RESOLVE / REVIEW REQUIRED / ADVISORIES)     -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex flex-col gap-0.5">
          <h2 class="text-sm font-bold text-slate-900 m-0">2. Plan Review</h2>
          <p class="text-xs text-slate-500 m-0">
            Pre-execution static analysis and policy validation. Resolve blockers before continuing to Step 8.
          </p>
        </div>

        <div class="flex flex-col gap-3.5">
          
          <!-- 2.1 MUST RESOLVE (BLOCKERS) -->
          <div class="bg-white border rounded-xl overflow-hidden"
            [class.border-rose-300]="store.blockerCount() !== 0"
            [class.border-slate-200]="store.blockerCount() === 0">
            
            <div class="p-3.5 flex items-center justify-between border-b"
              [class.bg-rose-50]="store.blockerCount() !== 0"
              [class.border-rose-200]="store.blockerCount() !== 0"
              [class.bg-slate-50]="store.blockerCount() === 0"
              [class.border-slate-200]="store.blockerCount() === 0">
              
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900 text-xs">Must Resolve</span>
                <span
                  class="px-2 py-0.5 rounded text-[10.5px] font-bold border"
                  [class.bg-rose-100]="store.blockerCount() !== 0"
                  [class.text-rose-900]="store.blockerCount() !== 0"
                  [class.border-rose-300]="store.blockerCount() !== 0"
                  [class.bg-slate-100]="store.blockerCount() === 0"
                  [class.text-slate-700]="store.blockerCount() === 0"
                  [class.border-slate-200]="store.blockerCount() === 0">
                  {{ store.blockerCount() }}
                </span>
              </div>

              @if (store.blockerCount() === 0) {
                <span class="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                  <app-lucide-icon name="check-circle-2" [size]="13"></app-lucide-icon>
                  <span>Zero Blockers — Plan is valid for execution</span>
                </span>
              }
            </div>

            @if (store.blockerCount() !== 0) {
              <div class="p-3.5 flex flex-col gap-3 divide-y divide-slate-100">
                @for (issue of store.blockerIssues(); track issue.id) {
                  <div class="flex items-start justify-between gap-3 pt-2 first:pt-0">
                    <div class="flex items-start gap-2.5 min-w-0">
                      <app-lucide-icon name="alert-octagon" [size]="15" class="text-rose-600 shrink-0 mt-0.5"></app-lucide-icon>
                      <div class="flex flex-col gap-0.5">
                        <span class="font-bold text-slate-900 text-xs">{{ issue.title }}</span>
                        <p class="text-[11.5px] text-slate-600 m-0">{{ issue.impact }}</p>
                        <span class="text-[11px] text-slate-500 font-mono">Affected Scope: {{ issue.affectedScope }}</span>
                      </div>
                    </div>

                    @if (issue.upstreamStep) {
                      <button
                        type="button"
                        (click)="store.routeToUpstreamStep(issue.upstreamStep)"
                        class="h-7 px-2.5 rounded bg-rose-50 border border-rose-200 hover:bg-rose-100 text-rose-800 text-[11px] font-semibold flex items-center gap-1 shrink-0 cursor-pointer transition-colors">
                        <span>{{ issue.upstreamStepLabel || 'Fix in Step ' + issue.upstreamStep }}</span>
                        <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                      </button>
                    }
                  </div>
                }
              </div>
            }
          </div>

          <!-- 2.2 REVIEW REQUIRED (WARNINGS WITH UPSTREAM NAVIGATION & PER-ISSUE ACK) -->
          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div class="p-3.5 bg-amber-50 border-b border-amber-200 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900 text-xs">Review Required</span>
                <span class="px-2 py-0.5 rounded text-[10.5px] font-bold bg-amber-100 text-amber-900 border border-amber-200">
                  {{ store.reviewCount() }}
                </span>
              </div>
              <span class="text-[11px] text-slate-500 font-medium">Operational recommendations requiring review or acknowledgement</span>
            </div>

            <div class="p-3.5 flex flex-col gap-3 divide-y divide-slate-100">
              @for (issue of store.reviewRequiredIssues(); track issue.id) {
                <div class="flex items-start justify-between gap-4 pt-3 first:pt-0">
                  <div class="flex items-start gap-2.5 min-w-0">
                    <app-lucide-icon name="alert-triangle" [size]="15" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
                    <div class="flex flex-col gap-1 min-w-0">
                      <span class="font-bold text-slate-900 text-xs">{{ issue.title }}</span>
                      <p class="text-[11.5px] text-slate-600 m-0">{{ issue.impact }}</p>
                      
                      <!-- Per-issue risk acknowledgement -->
                      <label class="flex items-center gap-2 pt-1 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          [checked]="issue.isAcknowledged"
                          (change)="store.toggleAcknowledgeIssue(issue.id)"
                          class="rounded border-slate-300 text-blue-600 focus:ring-0" />
                        <span class="text-[11px] text-slate-600">Acknowledge operational consideration for this migration</span>
                      </label>
                    </div>
                  </div>

                  @if (issue.upstreamStep) {
                    <button
                      type="button"
                      (click)="store.routeToUpstreamStep(issue.upstreamStep)"
                      class="h-7 px-2.5 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 text-[11px] font-semibold flex items-center gap-1 shrink-0 cursor-pointer transition-colors">
                      <span>{{ issue.upstreamStepLabel || 'Review in Step ' + issue.upstreamStep }}</span>
                      <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                    </button>
                  }
                </div>
              }
            </div>
          </div>

          <!-- 2.3 ADVISORIES (INFORMATIONAL) -->
          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div class="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900 text-xs">Advisories</span>
                <span class="px-2 py-0.5 rounded text-[10.5px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ store.advisoryCount() }}
                </span>
              </div>

              @if (store.advisoryCount() > 2) {
                <button
                  type="button"
                  (click)="store.toggleShowAllAdvisories()"
                  class="text-[11px] font-semibold text-blue-600 hover:text-blue-800 cursor-pointer transition-colors">
                  {{ store.showAllAdvisories() ? 'Show Fewer' : 'Show All ' + store.advisoryCount() + ' Advisories' }}
                </button>
              }
            </div>

            <div class="p-3.5 flex flex-col gap-2.5 divide-y divide-slate-100">
              @for (issue of store.visibleAdvisoryIssues(); track issue.id) {
                <div class="flex items-start gap-2.5 pt-2 first:pt-0">
                  <app-lucide-icon name="info" [size]="14" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
                  <div class="flex flex-col gap-0.5">
                    <span class="font-bold text-slate-800 text-xs">{{ issue.title }}</span>
                    <p class="text-[11.5px] text-slate-600 m-0">{{ issue.impact }}</p>
                  </div>
                </div>
              }
            </div>
          </div>

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- SECTION 3: GOVERNANCE BOUNDARIES (APPROVAL GATES & POLICIES)              -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-4">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 m-0">3. Governance Boundaries</h2>
            <p class="text-xs text-slate-500 m-0">
              Configured approval gates and execution hold points. Approvals are formally submitted in Step 8: Governance & Execution.
            </p>
          </div>

          <button
            type="button"
            (click)="store.openAddGateModal()"
            class="h-8 px-3.5 rounded-lg bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors shrink-0">
            <app-lucide-icon name="plus" [size]="13"></app-lucide-icon>
            <span>Add Approval Gate</span>
          </button>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold text-slate-600">
                <th class="py-2.5 px-3.5">Gate Name</th>
                <th class="py-2.5 px-3">Topology Placement</th>
                <th class="py-2.5 px-3">Signer Policy</th>
                <th class="py-2.5 px-3">Preconditions</th>
                <th class="py-2.5 px-3">Reject Action</th>
                <th class="py-2.5 px-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-[11.5px]">
              @for (gate of store.approvalGates(); track gate.id) {
                <tr class="hover:bg-slate-50">
                  <td class="py-3 px-3.5 font-bold text-slate-900">
                    <div class="flex items-center gap-2">
                      <span>{{ gate.gateName }}</span>
                      @if (gate.isMandatory) {
                        <span class="px-1.5 py-0.2 rounded bg-amber-100 text-amber-900 text-[9.5px] font-bold border border-amber-200">
                          Mandatory
                        </span>
                      }
                    </div>
                  </td>
                  <td class="py-3 px-3 text-slate-600 font-mono text-[11px]">
                    Between Stage {{ getStageOrder(gate.afterStageId) }} &rarr; Stage {{ getStageOrder(gate.beforeStageId) }}
                  </td>
                  <td class="py-3 px-3 text-slate-700 font-medium">
                    {{ formatSignerPolicy(gate.signerPolicy) }} ({{ gate.requiredSignatures }} signers)
                  </td>
                  <td class="py-3 px-3 text-slate-600 text-[11px]">
                    {{ gate.requireDlqEmpty ? 'DLQ Clean' : '' }}{{ gate.cdcMaxLagMs ? ', Lag \u2264 ' + gate.cdcMaxLagMs + 'ms' : '' }}
                  </td>
                  <td class="py-3 px-3 text-slate-700 font-mono text-[10.5px]">
                    {{ gate.rejectionAction }}
                  </td>
                  <td class="py-3 px-3.5 text-right">
                    <div class="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        (click)="store.openGateDrawer(gate)"
                        class="h-6 px-2 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 text-[10.5px] font-semibold cursor-pointer transition-colors">
                        Configure
                      </button>
                      @if (!gate.isMandatory) {
                        <button
                          type="button"
                          (click)="store.removeApprovalGate(gate.id)"
                          class="h-6 px-2 rounded bg-red-50 border border-red-200 hover:bg-red-100 text-red-700 text-[10.5px] font-semibold cursor-pointer transition-colors">
                          Remove
                        </button>
                      }
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- SECTION 4: PLAN SUMMARY (4-COLUMN FACTUAL GRID)                          -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-4">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 m-0">4. Plan Summary</h2>
            <p class="text-xs text-slate-500 m-0">
              Authoritative snapshot of migration scope, runtime profile, and assurance controls.
            </p>
          </div>

          <button
            type="button"
            (click)="store.openTechnicalModal()"
            class="h-8 px-3.5 rounded-lg bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors shrink-0">
            <app-lucide-icon name="file-code-2" [size]="13"></app-lucide-icon>
            <span>View Technical Details (JSON & SHA-256)</span>
          </button>
        </div>

        <div class="grid grid-cols-4 gap-3.5">
          
          <!-- Column 1: Migration & Topology -->
          <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-3">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
              <app-lucide-icon name="git-compare" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Migration</span>
            </h3>

            <div class="flex flex-col gap-2 text-xs">
              <div>
                <span class="text-[11px] text-slate-500">Source Endpoint:</span>
                <p class="font-mono font-semibold text-slate-900 m-0 truncate">{{ store.summary().migration.sourceEngine }} ({{ store.summary().migration.sourceEndpoint }})</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Target Endpoint:</span>
                <p class="font-mono font-semibold text-slate-900 m-0 truncate">{{ store.summary().migration.targetEngine }} ({{ store.summary().migration.targetEndpoint }})</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Execution Mode:</span>
                <p class="font-semibold text-blue-700 m-0">{{ store.summary().migration.modeLabel }}</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Target Environment:</span>
                <p class="font-semibold text-slate-900 m-0">{{ store.summary().migration.environment }}</p>
              </div>
            </div>
          </div>

          <!-- Column 2: Scope & Controls -->
          <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-3">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
              <app-lucide-icon name="database" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Scope & Controls</span>
            </h3>

            <div class="flex flex-col gap-2 text-xs">
              <div>
                <span class="text-[11px] text-slate-500">Assigned Scope:</span>
                <p class="font-semibold text-slate-900 m-0">{{ store.summary().scope.totalObjects }} Objects ({{ store.summary().scope.totalPartitions }} Partitions)</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Total Volume:</span>
                <p class="font-semibold text-slate-900 m-0">{{ (store.summary().scope.totalEstimatedBytes / (1024*1024*1024)).toFixed(1) }} GB</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Estimated Rows:</span>
                <p class="font-mono font-semibold text-slate-900 m-0">{{ store.summary().scope.totalEstimatedRows.toLocaleString() }}</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Active Transformation Rules:</span>
                <p class="font-semibold text-slate-900 m-0">{{ store.summary().scope.mappingRuleCount }} Mappings &middot; {{ store.summary().scope.filterRuleCount }} Filters</p>
              </div>
            </div>
          </div>

          <!-- Column 3: Execution Profile -->
          <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-3">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
              <app-lucide-icon name="cpu" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Execution Profile</span>
            </h3>

            <div class="flex flex-col gap-2 text-xs">
              <div>
                <span class="text-[11px] text-slate-500">Worker Concurrency:</span>
                <p class="font-semibold text-slate-900 m-0">{{ store.summary().execution.workerConcurrency }} Concurrent Workers</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Chunk Buffer:</span>
                <p class="font-semibold text-slate-900 m-0">{{ store.summary().execution.chunkBufferMb }} MB Chunk Buffer</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Recovery Strategy:</span>
                <p class="font-semibold text-slate-900 m-0 truncate">{{ store.summary().execution.recoveryStrategy }}</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">CDC Streaming:</span>
                <p class="font-semibold text-slate-900 m-0">{{ store.summary().execution.cdcStreaming }}</p>
              </div>
            </div>
          </div>

          <!-- Column 4: Assurance & Governance -->
          <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-3">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
              <app-lucide-icon name="shield-check" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Assurance</span>
            </h3>

            <div class="flex flex-col gap-2 text-xs">
              <div>
                <span class="text-[11px] text-slate-500">Validation Mode:</span>
                <p class="font-semibold text-slate-900 m-0">{{ store.summary().assurance.validationMode }}</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Sampling Rate:</span>
                <p class="font-semibold text-slate-900 m-0">{{ store.summary().assurance.samplingRate }}</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Approval Gates:</span>
                <p class="font-semibold text-amber-900 m-0">{{ store.summary().assurance.approvalGateCount }} Gates Configured</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Fingerprint Binding:</span>
                <p class="font-mono text-slate-600 text-[10.5px] truncate" title="{{ store.technicalDetails().canonicalFingerprint }}">
                  {{ store.technicalDetails().canonicalFingerprint.substring(0, 16) }}...
                </p>
              </div>
            </div>
          </div>

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- SLIDE-OVER DRAWERS & MODALS                                               -->
      <!-- ========================================================================= -->
      @if (store.selectedStage()) {
        <app-step7-stage-drawer />
      }

      @if (store.selectedGate()) {
        <app-step7-approval-drawer />
      }

      @if (store.isAddGateModalOpen()) {
        <app-step7-add-gate-modal />
      }

      @if (store.isTechnicalModalOpen()) {
        <app-step7-technical-modal />
      }

    </div>
  `
})
export class Step7PlanComponent {
  public store = inject(Step7PlanStoreService);
  public ms = inject(MigrationUiService);

  public formatSignerPolicy(policy: string): string {
    switch (policy) {
      case 'FOUR_EYES': return 'Four-Eyes Principle';
      case 'SOLE_OWNER': return 'Sole Owner';
      case 'CAB_COMMITTEE': return 'CAB Committee';
      case 'DUAL_DBA_SEC': return 'Dual DBA & Security';
      default: return policy;
    }
  }

  public getStageOrder(stageId: string): number {
    const stage = this.store.nodes().find(n => n.id === stageId);
    return stage ? stage.order : 0;
  }
}
