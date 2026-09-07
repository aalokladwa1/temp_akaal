import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { Step8GovernanceStoreService } from '../../../../core/services/step8-governance-store.service';
import { Step8ApprovalDrawerComponent } from './step8-approval-drawer.component';
import { Step8ReadinessDrawerComponent } from './step8-readiness-drawer.component';
import { Step8TechnicalModalComponent } from './step8-technical-modal.component';
import { Step8ActivityDrawerComponent } from './step8-activity-drawer.component';
import { ReadinessCheckPresentation, GovernanceGatePresentation, PolicyAcknowledgementPresentation } from './step8-governance.models';

@Component({
  selector: 'app-step8-governance',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    Step8ApprovalDrawerComponent,
    Step8ReadinessDrawerComponent,
    Step8TechnicalModalComponent,
    Step8ActivityDrawerComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full font-sans select-none text-xs pb-12">
      
      <!-- ========================================================================= -->
      <!-- CLEAN PAGE HEADING (NO BADGES, NO EXTRA PILLS)                           -->
      <!-- ========================================================================= -->
      <h1 class="text-xl font-bold text-slate-900 m-0 tracking-tight">Governance &amp; Readiness</h1>

      <!-- ========================================================================= -->
      <!-- SECTION 1: OVERALL READINESS CARD                                         -->
      <!-- ========================================================================= -->
      <section class="bg-white border rounded-xl p-4 flex flex-col gap-3.5"
        [class.border-emerald-300]="store.overallReadiness().status === 'READY'"
        [class.border-amber-300]="store.overallReadiness().status === 'AWAITING_APPROVALS'"
        [class.border-rose-300]="store.overallReadiness().status === 'ACTION_REQUIRED'"
        [class.border-slate-200]="store.overallReadiness().status === 'NOT_READY'">
        
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <span class="px-2.5 py-1 rounded-md text-xs font-bold border flex items-center gap-1.5"
              [class.bg-emerald-50]="store.overallReadiness().status === 'READY'"
              [class.text-emerald-700]="store.overallReadiness().status === 'READY'"
              [class.border-emerald-200]="store.overallReadiness().status === 'READY'"
              [class.bg-amber-50]="store.overallReadiness().status === 'AWAITING_APPROVALS'"
              [class.text-amber-800]="store.overallReadiness().status === 'AWAITING_APPROVALS'"
              [class.border-amber-200]="store.overallReadiness().status === 'AWAITING_APPROVALS'"
              [class.bg-rose-50]="store.overallReadiness().status === 'ACTION_REQUIRED'"
              [class.text-rose-700]="store.overallReadiness().status === 'ACTION_REQUIRED'"
              [class.border-rose-200]="store.overallReadiness().status === 'ACTION_REQUIRED'">
              <app-lucide-icon
                [name]="store.overallReadiness().status === 'READY' ? 'check-circle-2' : (store.overallReadiness().status === 'AWAITING_APPROVALS' ? 'shield-alert' : 'alert-octagon')"
                [size]="14">
              </app-lucide-icon>
              <span>{{ store.overallReadiness().statusLabel }}</span>
            </span>

            <p class="text-xs text-slate-600 m-0 font-medium">
              {{ store.overallReadiness().summaryText }}
            </p>
          </div>

          <div class="flex items-center gap-4 shrink-0 text-xs">
            <div class="flex items-center gap-1.5">
              <span class="text-slate-500">Governance:</span>
              <span class="font-bold font-mono"
                [class.text-emerald-700]="store.overallReadiness().governanceSummary.isSatisfied"
                [class.text-amber-800]="!store.overallReadiness().governanceSummary.isSatisfied">
                {{ store.overallReadiness().governanceSummary.approvedCount }} / {{ store.overallReadiness().governanceSummary.totalCount }} Gates
              </span>
            </div>

            <span class="h-3 w-[1px] bg-slate-200"></span>

            <div class="flex items-center gap-1.5">
              <span class="text-slate-500">Readiness:</span>
              <span class="font-bold font-mono text-emerald-700">
                {{ store.overallReadiness().readinessSummary.passedCount }} / {{ store.overallReadiness().readinessSummary.totalCount }} Passed
              </span>
            </div>

            <span class="h-3 w-[1px] bg-slate-200"></span>

            <div class="flex items-center gap-1.5">
              <span class="text-slate-500">Actions:</span>
              <span class="font-bold font-mono"
                [class.text-rose-700]="store.overallReadiness().requiredActionCount > 0"
                [class.text-slate-600]="store.overallReadiness().requiredActionCount === 0">
                {{ store.overallReadiness().requiredActionCount }} Required
              </span>
            </div>
          </div>
        </div>

      </section>

      <!-- ========================================================================= -->
      <!-- SECTION 2: REQUIRED ACTIONS (CONDITIONAL)                                 -->
      <!-- ========================================================================= -->
      @if (store.requiredActions().length > 0) {
        <section class="flex flex-col gap-3">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 m-0 flex items-center gap-2">
              <span>Required Actions</span>
              <span class="px-2 py-0.5 rounded text-[10.5px] font-bold bg-rose-100 text-rose-900 border border-rose-200">
                {{ store.requiredActions().length }}
              </span>
            </h2>
            <p class="text-xs text-slate-500 m-0">
              Prerequisites and formal decisions that must be resolved before proceeding to Step 9 Review.
            </p>
          </div>

          <div class="bg-white border border-rose-200 rounded-xl divide-y divide-slate-100 overflow-hidden">
            @for (action of store.requiredActions(); track action.id) {
              <div class="p-3.5 flex items-start justify-between gap-4">
                <div class="flex items-start gap-2.5 min-w-0">
                  <app-lucide-icon
                    [name]="action.severity === 'BLOCKER' ? 'alert-octagon' : (action.severity === 'APPROVAL_REQUIRED' ? 'shield-alert' : 'alert-triangle')"
                    [size]="15"
                    [class]="action.severity === 'BLOCKER' ? 'text-rose-600 shrink-0 mt-0.5' : (action.severity === 'APPROVAL_REQUIRED' ? 'text-amber-600 shrink-0 mt-0.5' : 'text-blue-600 shrink-0 mt-0.5')">
                  </app-lucide-icon>
                  <div class="flex flex-col gap-0.5">
                    <span class="font-bold text-slate-900 text-xs">{{ action.title }}</span>
                    <p class="text-[11.5px] text-slate-600 m-0">{{ action.description }}</p>
                  </div>
                </div>

                <button
                  type="button"
                  (click)="handleRequiredAction(action)"
                  class="h-7 px-3 rounded text-[11px] font-bold flex items-center gap-1 shrink-0 cursor-pointer transition-colors"
                  [class.bg-rose-50]="action.severity === 'BLOCKER'"
                  [class.text-rose-800]="action.severity === 'BLOCKER'"
                  [class.border]="action.severity === 'BLOCKER'"
                  [class.border-rose-200]="action.severity === 'BLOCKER'"
                  [class.hover:bg-rose-100]="action.severity === 'BLOCKER'"
                  [class.bg-amber-50]="action.severity === 'APPROVAL_REQUIRED'"
                  [class.text-amber-900]="action.severity === 'APPROVAL_REQUIRED'"
                  [class.border]="action.severity === 'APPROVAL_REQUIRED'"
                  [class.border-amber-200]="action.severity === 'APPROVAL_REQUIRED'"
                  [class.hover:bg-amber-100]="action.severity === 'APPROVAL_REQUIRED'"
                  [class.bg-blue-50]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'"
                  [class.text-blue-800]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'"
                  [class.border]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'"
                  [class.border-blue-200]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'"
                  [class.hover:bg-blue-100]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'">
                  <span>{{ action.actionLabel }}</span>
                </button>
              </div>
            }
          </div>
        </section>
      }

      <!-- ========================================================================= -->
      <!-- SECTION 3: GOVERNANCE & APPROVALS                                         -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex flex-col gap-0.5">
          <h2 class="text-sm font-bold text-slate-900 m-0">1. Governance &amp; Approvals</h2>
          <p class="text-xs text-slate-500 m-0">
            Execution barriers and sign-off policies established in Step 7. Approvals are recorded into the canonical audit ledger.
          </p>
        </div>

        @if (store.governanceGates().length === 0) {
          <!-- Zero-Approval Positive State Card -->
          <div class="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="check-circle-2" [size]="16"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <span class="font-bold text-slate-900 text-xs">No Approval Gates Configured</span>
                <span class="text-[11.5px] text-slate-500">Plan execution is pre-authorized under standard migration governance policies.</span>
              </div>
            </div>

            <span class="px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
              Pre-Authorized
            </span>
          </div>
        } @else {
          <!-- Configured Gates Table/List -->
          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold text-slate-600">
                  <th class="py-2.5 px-3.5">Gate Name &amp; Placement</th>
                  <th class="py-2.5 px-3">Signer Policy</th>
                  <th class="py-2.5 px-3">Status</th>
                  <th class="py-2.5 px-3">Signatory Context</th>
                  <th class="py-2.5 px-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-[11.5px]">
                @for (gate of store.governanceGates(); track gate.id) {
                  <tr class="hover:bg-slate-50">
                    
                    <td class="py-3 px-3.5">
                      <div class="flex flex-col gap-0.5">
                        <div class="flex items-center gap-2">
                          <span class="font-bold text-slate-900">{{ gate.gateName }}</span>
                          @if (gate.isMandatory) {
                            <span class="px-1.5 py-0.2 rounded bg-amber-100 text-amber-900 text-[9.5px] font-bold border border-amber-200">
                              Mandatory
                            </span>
                          }
                        </div>
                        <span class="text-[10.5px] text-slate-500 font-mono">{{ gate.stagePlacementLabel }}</span>
                      </div>
                    </td>

                    <td class="py-3 px-3">
                      <div class="flex flex-col gap-0.5">
                        <span class="font-semibold text-slate-800">{{ gate.signerPolicyLabel }}</span>
                        <span class="text-[10.5px] text-slate-500">{{ gate.currentSignatures }} of {{ gate.requiredSignatures }} signature(s)</span>
                      </div>
                    </td>

                    <td class="py-3 px-3">
                      <span class="px-2 py-0.5 rounded text-[10.5px] font-bold border inline-flex items-center gap-1"
                        [class.bg-emerald-50]="gate.status === 'APPROVED' || gate.status === 'SATISFIED'"
                        [class.text-emerald-700]="gate.status === 'APPROVED' || gate.status === 'SATISFIED'"
                        [class.border-emerald-200]="gate.status === 'APPROVED' || gate.status === 'SATISFIED'"
                        [class.bg-amber-50]="gate.status === 'PENDING_APPROVAL'"
                        [class.text-amber-800]="gate.status === 'PENDING_APPROVAL'"
                        [class.border-amber-200]="gate.status === 'PENDING_APPROVAL'"
                        [class.bg-rose-50]="gate.status === 'REJECTED'"
                        [class.text-rose-700]="gate.status === 'REJECTED'"
                        [class.border-rose-200]="gate.status === 'REJECTED'">
                        <app-lucide-icon
                          [name]="gate.status === 'APPROVED' ? 'check' : (gate.status === 'REJECTED' ? 'x' : 'clock')"
                          [size]="11">
                        </app-lucide-icon>
                        <span>{{ gate.status === 'APPROVED' ? 'Approved' : (gate.status === 'REJECTED' ? 'Rejected' : 'Pending Sign-off') }}</span>
                      </span>
                    </td>

                    <td class="py-3 px-3">
                      <div class="flex items-center gap-1.5 text-[11px]">
                        @if (gate.actorContext.isCurrentActorEligible) {
                          <span class="text-emerald-700 font-medium flex items-center gap-1">
                            <app-lucide-icon name="check-circle" [size]="12"></app-lucide-icon>
                            <span>Eligible ({{ gate.actorContext.currentActorRole }})</span>
                          </span>
                        } @else {
                          <span class="text-amber-800 font-medium flex items-center gap-1" title="{{ gate.actorContext.sodExplanation }}">
                            <app-lucide-icon name="shield-alert" [size]="12"></app-lucide-icon>
                            <span>SoD Restricted</span>
                          </span>
                        }
                      </div>
                    </td>

                    <td class="py-3 px-3.5 text-right">
                      <button
                        type="button"
                        (click)="store.openApprovalDrawer(gate)"
                        class="h-7 px-3 rounded bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs font-semibold cursor-pointer transition-colors">
                        {{ gate.status === 'APPROVED' ? 'View Decision' : 'Review & Sign' }}
                      </button>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </section>

      <!-- ========================================================================= -->
      <!-- SECTION 4: TECHNICAL READINESS CHECKS (6 ACCORDION GROUPS)                -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex flex-col gap-0.5">
          <h2 class="text-sm font-bold text-slate-900 m-0">2. Technical Readiness Checks</h2>
          <p class="text-xs text-slate-500 m-0">
            Systematic pre-execution verification across connectivity, schemas, replication pipelines, and resource allocations.
          </p>
        </div>

        <div class="flex flex-col gap-3">
          @for (group of store.readinessCategories(); track group.id) {
            <div class="bg-white border border-slate-200 rounded-xl overflow-hidden">
              
              <!-- Accordion Header -->
              <div
                (click)="store.toggleCategoryExpansion(group.id)"
                class="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between cursor-pointer select-none hover:bg-slate-100/80 transition-colors">
                
                <div class="flex items-center gap-2.5">
                  <app-lucide-icon
                    [name]="group.hasBlockers ? 'alert-octagon' : (group.hasWarnings ? 'alert-triangle' : 'check-circle-2')"
                    [size]="15"
                    [class]="group.hasBlockers ? 'text-rose-600' : (group.hasWarnings ? 'text-amber-600' : 'text-emerald-600')">
                  </app-lucide-icon>

                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900 text-xs">{{ group.title }}</span>
                    <span class="text-[11px] text-slate-500">{{ group.description }}</span>
                  </div>
                </div>

                <div class="flex items-center gap-3">
                  <span class="px-2 py-0.5 rounded text-[10.5px] font-bold border"
                    [class.bg-emerald-50]="group.passedCount === group.totalCount"
                    [class.text-emerald-700]="group.passedCount === group.totalCount"
                    [class.border-emerald-200]="group.passedCount === group.totalCount"
                    [class.bg-rose-50]="group.hasBlockers"
                    [class.text-rose-700]="group.hasBlockers"
                    [class.border-rose-200]="group.hasBlockers">
                    {{ group.passedCount }} / {{ group.totalCount }} Passed
                  </span>

                  <app-lucide-icon
                    [name]="group.isExpanded ? 'chevron-up' : 'chevron-down'"
                    [size]="14"
                    class="text-slate-400">
                  </app-lucide-icon>
                </div>
              </div>

              <!-- Accordion Body (Checks List) -->
              @if (group.isExpanded) {
                <div class="p-3.5 flex flex-col gap-3 divide-y divide-slate-100 animate-in fade-in duration-100">
                  @for (check of group.checks; track check.id) {
                    <div class="flex items-start justify-between gap-4 pt-3 first:pt-0">
                      
                      <div class="flex items-start gap-2.5 min-w-0">
                        <app-lucide-icon
                          [name]="check.status === 'READY' ? 'check-circle' : (check.status === 'WARNING' ? 'alert-triangle' : 'alert-circle')"
                          [size]="14"
                          [class]="check.status === 'READY' ? 'text-emerald-600 mt-0.5 shrink-0' : (check.status === 'WARNING' ? 'text-amber-600 mt-0.5 shrink-0' : 'text-rose-600 mt-0.5 shrink-0')">
                        </app-lucide-icon>

                        <div class="flex flex-col gap-0.5 min-w-0">
                          <div class="flex items-center gap-2">
                            <span class="font-bold text-slate-900 text-xs">{{ check.name }}</span>
                            <span class="text-[10px] text-slate-400 font-mono">
                              {{ check.affectedResources.join(', ') }}
                            </span>
                          </div>
                          <p class="text-[11.5px] text-slate-600 m-0">{{ check.observation }}</p>
                        </div>
                      </div>

                      <div class="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          (click)="store.openReadinessDrawer(check)"
                          class="h-6 px-2.5 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 text-[11px] font-semibold cursor-pointer transition-colors">
                          Inspect
                        </button>

                        <button
                          type="button"
                          (click)="store.retryCheck(check.id)"
                          [disabled]="store.isRetryingCheck()"
                          class="h-6 w-6 rounded bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 flex items-center justify-center cursor-pointer transition-colors"
                          title="Re-evaluate check">
                          <app-lucide-icon name="refresh-cw" [size]="12"></app-lucide-icon>
                        </button>
                      </div>

                    </div>
                  }
                </div>
              }

            </div>
          }
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- SECTION 5: POLICY ACKNOWLEDGEMENTS (CONDITIONAL)                          -->
      <!-- ========================================================================= -->
      @if (store.policyAcknowledgements().length > 0) {
        <section class="flex flex-col gap-3">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 m-0">3. Policy Acknowledgements</h2>
            <p class="text-xs text-slate-500 m-0">
              Permitted operational risk considerations requiring explicit operator acknowledgement before continuing.
            </p>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden">
            @for (ack of store.policyAcknowledgements(); track ack.id) {
              <div class="p-4 flex flex-col gap-2.5">
                <div class="flex items-start justify-between gap-3">
                  <div class="flex items-start gap-2.5">
                    <app-lucide-icon name="shield-alert" [size]="15" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
                    <div class="flex flex-col gap-0.5">
                      <span class="font-bold text-slate-900 text-xs">{{ ack.title }}</span>
                      <p class="text-[11.5px] text-slate-600 m-0">{{ ack.riskAssessment }}</p>
                      <span class="text-[10.5px] text-slate-400 font-mono">Reference: {{ ack.policyReference }}</span>
                    </div>
                  </div>

                  <span class="px-2 py-0.5 rounded text-[10px] font-bold border shrink-0"
                    [class.bg-emerald-50]="ack.isAcknowledged"
                    [class.text-emerald-700]="ack.isAcknowledged"
                    [class.border-emerald-200]="ack.isAcknowledged"
                    [class.bg-amber-50]="!ack.isAcknowledged"
                    [class.text-amber-800]="!ack.isAcknowledged"
                    [class.border-amber-200]="!ack.isAcknowledged">
                    {{ ack.isAcknowledged ? 'Acknowledged' : 'Pending Acknowledgement' }}
                  </span>
                </div>

                @if (!ack.isAcknowledged) {
                  <div class="pt-2 border-t border-slate-100 flex items-center justify-between gap-4">
                    <div class="flex items-center gap-2 flex-1">
                      <input
                        type="text"
                        #ackInput
                        placeholder="Enter operational rationale to acknowledge this condition..."
                        class="h-7 px-2.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 w-full" />
                    </div>

                    <button
                      type="button"
                      (click)="store.recordAcknowledgement(ack.id, ackInput.value)"
                      class="h-7 px-3 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold cursor-pointer transition-colors shrink-0">
                      Record Acknowledgement
                    </button>
                  </div>
                } @else {
                  <div class="text-[11px] text-slate-500 bg-slate-50 p-2 rounded border border-slate-200">
                    Recorded by {{ ack.acknowledgedBy || 'Operator' }} &middot; Rationale: "{{ ack.rationale || 'Acknowledged for migration run' }}"
                  </div>
                }
              </div>
            }
          </div>
        </section>
      }

      <!-- ========================================================================= -->
      <!-- SECTION 6: GOVERNED PLAN SNAPSHOT & ACTIONS                               -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-4">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 m-0">4. Governed Plan Snapshot</h2>
            <p class="text-xs text-slate-500 m-0">
              Immutable identity binding connecting this governance evaluation to runtime execution.
            </p>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <button
              type="button"
              (click)="store.openActivityDrawer()"
              class="h-8 px-3 rounded-lg bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors">
              <app-lucide-icon name="history" [size]="13"></app-lucide-icon>
              <span>Governance Activity</span>
            </button>

            <button
              type="button"
              (click)="store.openTechnicalModal()"
              class="h-8 px-3.5 rounded-lg bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors">
              <app-lucide-icon name="shield-check" [size]="13"></app-lucide-icon>
              <span>Technical Details</span>
            </button>
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-4 gap-4 text-xs">
          
          <div>
            <span class="text-[11px] text-slate-500">Plan Identifier:</span>
            <p class="font-mono font-bold text-slate-900 m-0 truncate">{{ store.governedPlanSnapshot().planId }}</p>
          </div>

          <div>
            <span class="text-[11px] text-slate-500">Plan Fingerprint:</span>
            <p class="font-mono font-semibold text-slate-700 m-0 truncate" title="{{ store.governedPlanSnapshot().fingerprint }}">
              {{ store.governedPlanSnapshot().fingerprint.substring(0, 16) }}...
            </p>
          </div>

          <div>
            <span class="text-[11px] text-slate-500">Governance State:</span>
            <p class="font-semibold text-emerald-700 m-0">{{ store.governedPlanSnapshot().governanceState }}</p>
          </div>

          <div>
            <span class="text-[11px] text-slate-500">Technical Readiness:</span>
            <p class="font-semibold text-emerald-700 m-0">{{ store.governedPlanSnapshot().readinessState }}</p>
          </div>

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- SLIDE-OVER DRAWERS & MODALS                                               -->
      <!-- ========================================================================= -->
      @if (store.selectedApprovalGate()) {
        <app-step8-approval-drawer />
      }

      @if (store.selectedReadinessCheck()) {
        <app-step8-readiness-drawer />
      }

      @if (store.isTechnicalModalOpen()) {
        <app-step8-technical-modal />
      }

      @if (store.isActivityDrawerOpen()) {
        <app-step8-activity-drawer />
      }

    </div>
  `
})
export class Step8GovernanceComponent {
  public store = inject(Step8GovernanceStoreService);
  public ms = inject(MigrationUiService);

  public handleRequiredAction(action: any): void {
    if (action.gateId) {
      const gate = this.store.governanceGates().find(g => g.id === action.gateId);
      if (gate) this.store.openApprovalDrawer(gate);
    } else if (action.checkId) {
      const check = this.store.readinessCategories().flatMap(c => c.checks).find(ch => ch.id === action.checkId);
      if (check) this.store.openReadinessDrawer(check);
    } else if (action.upstreamStep) {
      this.store.routeToUpstreamStep(action.upstreamStep);
    }
  }
}
