import { Component, inject, signal, computed, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import {
  ValidationReadinessStatus,
  ValidationReadinessDomain,
  CheckEvaluationStatus,
  ReadinessCheckItem,
  DomainCategoryGroup,
  RequiredActionItem,
  OperationalAcknowledgement,
  OverallValidationReadiness,
  Step7VisualFixture
} from './step7-readiness.models';

@Component({
  selector: 'app-step7-readiness',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full font-sans select-none text-xs pb-12">
      
      <!-- ========================================================================= -->
      <!-- CLEAN PAGE HEADING                                                        -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-1 border-b border-slate-200/60 pb-2">
        <div class="flex items-center justify-between">
          <h1 class="text-base font-bold text-slate-900 tracking-tight m-0">
            Governance &amp; Readiness
          </h1>
          
          <!-- Re-evaluate All Control (Restrained Action) -->
          <button
            type="button"
            (click)="handleReevaluateAll()"
            class="h-7 px-3 text-xs font-medium text-slate-700 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs">
            <app-lucide-icon name="refresh-cw" [size]="12" [class.animate-spin]="isEvaluating()"></app-lucide-icon>
            <span>Re-evaluate Readiness</span>
          </button>
        </div>
        <p class="text-xs text-slate-500 font-normal m-0">
          Pre-execution verification across connectivity, scope correspondence, baseline legitimacy, and operational conditions.
        </p>
      </div>

      <!-- Live Service Connection Status Notice (When Not Connected) -->
      @if (!activeReadiness().isEvaluationConnected) {
        <div class="rounded-xl bg-slate-50 border border-slate-200 p-4 flex items-start gap-3 text-xs text-slate-700 animate-in fade-in duration-100">
          <app-lucide-icon name="info" [size]="16" class="text-slate-500 shrink-0 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-1 flex-1">
            <span class="font-bold text-slate-900">Readiness Evaluation Service Not Connected</span>
            <span class="text-[11.5px] leading-relaxed text-slate-600">
              Live transport verification, credential attestation, target schema discovery, and baseline stability checks have not been evaluated.
              Local configuration structure is complete. Full readiness evaluation executes during engine initialization.
            </span>
          </div>
        </div>
      }

      <!-- Re-evaluation notice toast -->
      @if (evaluationMessage()) {
        <div class="p-3 bg-blue-50 border border-blue-200 text-blue-900 rounded-lg flex items-center justify-between text-xs animate-in fade-in duration-100">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="info" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
            <span>{{ evaluationMessage() }}</span>
          </div>
          <button
            type="button"
            (click)="evaluationMessage.set(null)"
            class="text-blue-600 hover:text-blue-800 cursor-pointer">
            <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
          </button>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- SECTION 1: OVERALL READINESS CARD                                         -->
      <!-- ========================================================================= -->
      <section
        class="bg-white border rounded-xl p-4 flex flex-col gap-3.5 shadow-2xs transition-colors"
        [class.border-emerald-300]="activeReadiness().status === 'READY'"
        [class.border-amber-300]="activeReadiness().status === 'READY_WITH_ATTENTION' || activeReadiness().status === 'AWAITING_GOVERNANCE'"
        [class.border-rose-300]="activeReadiness().status === 'BLOCKED'"
        [class.border-slate-200]="activeReadiness().status === 'NOT_EVALUATED' || activeReadiness().status === 'STALE' || activeReadiness().status === 'EVALUATION_UNAVAILABLE'">
        
        <div class="flex items-center justify-between gap-4 flex-wrap">
          
          <div class="flex items-center gap-3">
            <span
              class="px-2.5 py-1 rounded-md text-xs font-bold border flex items-center gap-1.5"
              [class.bg-emerald-50]="activeReadiness().status === 'READY'"
              [class.text-emerald-700]="activeReadiness().status === 'READY'"
              [class.border-emerald-200]="activeReadiness().status === 'READY'"
              [class.bg-amber-50]="activeReadiness().status === 'READY_WITH_ATTENTION' || activeReadiness().status === 'AWAITING_GOVERNANCE'"
              [class.text-amber-800]="activeReadiness().status === 'READY_WITH_ATTENTION' || activeReadiness().status === 'AWAITING_GOVERNANCE'"
              [class.border-amber-200]="activeReadiness().status === 'READY_WITH_ATTENTION' || activeReadiness().status === 'AWAITING_GOVERNANCE'"
              [class.bg-rose-50]="activeReadiness().status === 'BLOCKED'"
              [class.text-rose-700]="activeReadiness().status === 'BLOCKED'"
              [class.border-rose-200]="activeReadiness().status === 'BLOCKED'"
              [class.bg-slate-50]="activeReadiness().status === 'NOT_EVALUATED' || activeReadiness().status === 'STALE' || activeReadiness().status === 'EVALUATION_UNAVAILABLE'"
              [class.text-slate-700]="activeReadiness().status === 'NOT_EVALUATED' || activeReadiness().status === 'STALE' || activeReadiness().status === 'EVALUATION_UNAVAILABLE'"
              [class.border-slate-200]="activeReadiness().status === 'NOT_EVALUATED' || activeReadiness().status === 'STALE' || activeReadiness().status === 'EVALUATION_UNAVAILABLE'">
              <app-lucide-icon
                [name]="getStatusIcon(activeReadiness().status)"
                [size]="14">
              </app-lucide-icon>
              <span>{{ activeReadiness().statusLabel }}</span>
            </span>

            <p class="text-xs text-slate-600 m-0 font-medium">
              {{ activeReadiness().summaryText }}
            </p>
          </div>

          <div class="flex items-center gap-4 shrink-0 text-xs">
            <div class="flex items-center gap-1.5">
              <span class="text-slate-500">Domains:</span>
              <span class="font-bold font-mono text-slate-800">
                {{ activeReadiness().domainsCount }} / 5 Evaluated
              </span>
            </div>

            <span class="h-3 w-[1px] bg-slate-200"></span>

            <div class="flex items-center gap-1.5">
              <span class="text-slate-500">Checks:</span>
              <span class="font-bold font-mono"
                [class.text-emerald-700]="activeReadiness().passedChecksCount > 0"
                [class.text-slate-600]="activeReadiness().passedChecksCount === 0">
                {{ activeReadiness().passedChecksCount }} / {{ activeReadiness().totalChecksCount }} Passed
              </span>
            </div>

            <span class="h-3 w-[1px] bg-slate-200"></span>

            <div class="flex items-center gap-1.5">
              <span class="text-slate-500">Actions:</span>
              <span class="font-bold font-mono"
                [class.text-rose-700]="activeReadiness().requiredActionCount > 0"
                [class.text-slate-600]="activeReadiness().requiredActionCount === 0">
                {{ activeReadiness().requiredActionCount }} Required
              </span>
            </div>
          </div>

        </div>

      </section>

      <!-- ========================================================================= -->
      <!-- SECTION 2: REQUIRED ACTIONS (CONDITIONAL)                                 -->
      <!-- ========================================================================= -->
      @if (activeActions().length > 0) {
        <section class="flex flex-col gap-3 animate-in fade-in duration-150">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 m-0 flex items-center gap-2">
              <span>Required Actions</span>
              <span class="px-2 py-0.5 rounded text-[10.5px] font-bold bg-rose-100 text-rose-900 border border-rose-200">
                {{ activeActions().length }}
              </span>
            </h2>
            <p class="text-xs text-slate-500 m-0">
              Prerequisites and formal decisions that must be resolved before proceeding to Step 8 Review.
            </p>
          </div>

          <div class="bg-white border border-rose-200 rounded-xl divide-y divide-slate-100 overflow-hidden shadow-2xs">
            @for (action of activeActions(); track action.id) {
              <div class="p-3.5 flex items-start justify-between gap-4">
                <div class="flex items-start gap-2.5 min-w-0">
                  <app-lucide-icon
                    [name]="action.severity === 'BLOCKER' ? 'alert-octagon' : (action.severity === 'ACKNOWLEDGEMENT_REQUIRED' ? 'shield-alert' : 'alert-triangle')"
                    [size]="15"
                    [class]="action.severity === 'BLOCKER' ? 'text-rose-600 shrink-0 mt-0.5' : (action.severity === 'ACKNOWLEDGEMENT_REQUIRED' ? 'text-amber-600 shrink-0 mt-0.5' : 'text-blue-600 shrink-0 mt-0.5')">
                  </app-lucide-icon>
                  <div class="flex flex-col gap-0.5">
                    <span class="font-bold text-slate-900 text-xs">{{ action.title }}</span>
                    <p class="text-[11.5px] text-slate-600 m-0">{{ action.description }}</p>
                  </div>
                </div>

                <button
                  type="button"
                  (click)="handleActionClick(action)"
                  class="h-7 px-3 rounded text-[11px] font-bold flex items-center gap-1 shrink-0 cursor-pointer transition-colors"
                  [class.bg-rose-50]="action.severity === 'BLOCKER'"
                  [class.text-rose-800]="action.severity === 'BLOCKER'"
                  [class.border]="action.severity === 'BLOCKER'"
                  [class.border-rose-200]="action.severity === 'BLOCKER'"
                  [class.hover:bg-rose-100]="action.severity === 'BLOCKER'"
                  [class.bg-amber-50]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'"
                  [class.text-amber-900]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'"
                  [class.border]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'"
                  [class.border-amber-200]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'"
                  [class.hover:bg-amber-100]="action.severity === 'ACKNOWLEDGEMENT_REQUIRED'">
                  <span>{{ action.actionLabel }}</span>
                </button>
              </div>
            }
          </div>
        </section>
      }

      <!-- ========================================================================= -->
      <!-- SECTION 3: 5 SCALABLE READINESS DOMAINS (ACCORDIONS)                      -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex flex-col gap-0.5">
          <h2 class="text-sm font-bold text-slate-900 m-0">Readiness Domains &amp; Checks</h2>
          <p class="text-xs text-slate-500 m-0">
            Systematic pre-execution verification across connectivity, scope correspondence, baseline legitimacy, and operational conditions.
          </p>
        </div>

        <div class="flex flex-col gap-3">
          @for (group of activeDomains(); track group.id) {
            <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
              
              <!-- Accordion Header -->
              <div
                (click)="toggleDomainExpansion(group.id)"
                class="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between cursor-pointer select-none hover:bg-slate-100/80 transition-colors">
                
                <div class="flex items-center gap-2.5">
                  <app-lucide-icon
                    [name]="group.hasBlockers ? 'alert-octagon' : (group.hasWarnings ? 'alert-triangle' : (group.passedCount > 0 ? 'check-circle-2' : 'circle'))"
                    [size]="15"
                    [class]="group.hasBlockers ? 'text-rose-600' : (group.hasWarnings ? 'text-amber-600' : (group.passedCount > 0 ? 'text-emerald-600' : 'text-slate-400'))">
                  </app-lucide-icon>

                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900 text-xs">{{ group.title }}</span>
                    <span class="text-[11px] text-slate-500">{{ group.description }}</span>
                  </div>
                </div>

                <div class="flex items-center gap-3">
                  <span class="px-2 py-0.5 rounded text-[10.5px] font-bold border"
                    [class.bg-emerald-50]="group.passedCount > 0 && group.passedCount === group.totalCount"
                    [class.text-emerald-700]="group.passedCount > 0 && group.passedCount === group.totalCount"
                    [class.border-emerald-200]="group.passedCount > 0 && group.passedCount === group.totalCount"
                    [class.bg-rose-50]="group.hasBlockers"
                    [class.text-rose-700]="group.hasBlockers"
                    [class.border-rose-200]="group.hasBlockers"
                    [class.bg-slate-50]="group.passedCount === 0 && !group.hasBlockers"
                    [class.text-slate-600]="group.passedCount === 0 && !group.hasBlockers"
                    [class.border-slate-200]="group.passedCount === 0 && !group.hasBlockers">
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
                          [name]="check.status === 'READY' ? 'check-circle' : (check.status === 'WARNING' ? 'alert-triangle' : (check.status === 'BLOCKER' ? 'alert-octagon' : 'clock'))"
                          [size]="14"
                          [class]="check.status === 'READY' ? 'text-emerald-600 mt-0.5 shrink-0' : (check.status === 'WARNING' ? 'text-amber-600 mt-0.5 shrink-0' : (check.status === 'BLOCKER' ? 'text-rose-600 mt-0.5 shrink-0' : 'text-slate-400 mt-0.5 shrink-0'))">
                        </app-lucide-icon>

                        <div class="flex flex-col gap-0.5 min-w-0">
                          <div class="flex items-center gap-2">
                            <span class="font-bold text-slate-900 text-xs">{{ check.name }}</span>
                            @if (check.affectedResources.length > 0) {
                              <span class="text-[10px] text-slate-400 font-mono">
                                {{ check.affectedResources.join(', ') }}
                              </span>
                            }
                          </div>
                          <p class="text-[11.5px] text-slate-600 m-0">{{ check.observation }}</p>
                        </div>
                      </div>

                      <div class="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          (click)="openInspectDrawer(check)"
                          class="h-6 px-2.5 rounded bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 text-[11px] font-semibold cursor-pointer transition-colors">
                          Inspect
                        </button>

                        <button
                          type="button"
                          (click)="handleReevaluateCheck(check.id)"
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
      <!-- SECTION 4: OPERATOR-OWNED OPERATIONAL ACKNOWLEDGEMENTS                   -->
      <!-- ========================================================================= -->
      @if (activeAcknowledgements().length > 0) {
        <section class="flex flex-col gap-3">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 m-0">Operational Conditions</h2>
            <p class="text-xs text-slate-500 m-0">
              Conditions declared or coordinated by the operator for this validation mission.
            </p>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden shadow-2xs">
            @for (ack of activeAcknowledgements(); track ack.id) {
              <div class="p-4 flex flex-col gap-2.5">
                <div class="flex items-start justify-between gap-3">
                  <div class="flex items-start gap-2.5">
                    <app-lucide-icon name="shield-alert" [size]="15" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
                    <div class="flex flex-col gap-0.5">
                      <span class="font-bold text-slate-900 text-xs">{{ ack.title }}</span>
                      <p class="text-xs text-slate-600 m-0 leading-relaxed">{{ ack.summary }}</p>
                    </div>
                  </div>

                  <label class="flex items-center gap-2 cursor-pointer shrink-0">
                    <input
                      type="checkbox"
                      [checked]="ack.isAcknowledged"
                      (change)="toggleAcknowledgement(ack.id)"
                      class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-4 w-4" />
                    <span class="text-xs font-semibold text-slate-700">Acknowledge</span>
                  </label>
                </div>
              </div>
            }
          </div>
        </section>
      }

      <!-- ========================================================================= -->
      <!-- SLIDE-OVER DRAWER: INSPECT CHECK DETAILS                                  -->
      <!-- ========================================================================= -->
      @if (selectedCheck(); as check) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex justify-end bg-slate-900/40 animate-in fade-in duration-100"
          (click)="closeInspectDrawer()">
          <div
            class="w-full max-w-md h-full bg-white border-l border-slate-200 shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-150"
            (click)="$event.stopPropagation()">
            
            <!-- Drawer Header -->
            <div class="p-5 border-b border-slate-200 flex items-start justify-between gap-3 bg-slate-50/50">
              <div class="flex items-start gap-2.5">
                <app-lucide-icon
                  [name]="check.status === 'READY' ? 'check-circle' : (check.status === 'WARNING' ? 'alert-triangle' : (check.status === 'BLOCKER' ? 'alert-octagon' : 'clock'))"
                  [size]="18"
                  [class]="check.status === 'READY' ? 'text-emerald-600 shrink-0 mt-0.5' : (check.status === 'WARNING' ? 'text-amber-600 shrink-0 mt-0.5' : (check.status === 'BLOCKER' ? 'text-rose-600 shrink-0 mt-0.5' : 'text-slate-400 shrink-0 mt-0.5'))">
                </app-lucide-icon>
                <div class="flex flex-col">
                  <h3 class="text-sm font-bold text-slate-900 m-0">{{ check.name }}</h3>
                  <span class="text-[11px] text-slate-500 font-mono mt-0.5">{{ check.domain }}</span>
                </div>
              </div>

              <button
                type="button"
                (click)="closeInspectDrawer()"
                class="p-1 text-slate-400 hover:text-slate-600 rounded hover:bg-slate-100 cursor-pointer">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <!-- Drawer Body -->
            <div class="p-5 overflow-y-auto flex-1 flex flex-col gap-4 text-xs">
              
              <!-- Evaluation Status -->
              <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
                <span class="text-slate-500 font-medium">Evaluation Status</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono border"
                  [class.bg-emerald-50]="check.status === 'READY'"
                  [class.text-emerald-700]="check.status === 'READY'"
                  [class.border-emerald-200]="check.status === 'READY'"
                  [class.bg-rose-50]="check.status === 'BLOCKER'"
                  [class.text-rose-700]="check.status === 'BLOCKER'"
                  [class.border-rose-200]="check.status === 'BLOCKER'"
                  [class.bg-slate-50]="check.status === 'NOT_EVALUATED'"
                  [class.text-slate-600]="check.status === 'NOT_EVALUATED'"
                  [class.border-slate-200]="check.status === 'NOT_EVALUATED'">
                  {{ check.status }}
                </span>
              </div>

              <!-- Observation -->
              <div class="flex flex-col gap-1.5">
                <span class="text-[10.5px] font-bold uppercase tracking-wider text-slate-400">Observation</span>
                <p class="text-xs text-slate-800 leading-relaxed font-normal bg-slate-50 p-3 rounded-lg border border-slate-200 m-0">
                  {{ check.observation }}
                </p>
              </div>

              <!-- Affected Resources -->
              @if (check.affectedResources.length > 0) {
                <div class="flex flex-col gap-1.5">
                  <span class="text-[10.5px] font-bold uppercase tracking-wider text-slate-400">Affected Resources</span>
                  <div class="flex flex-col gap-1">
                    @for (res of check.affectedResources; track res) {
                      <div class="px-3 py-1.5 bg-slate-50 rounded border border-slate-200 font-mono text-[11px] text-slate-700">
                        {{ res }}
                      </div>
                    }
                  </div>
                </div>
              }

              <!-- Technical Rationale -->
              @if (check.technicalDetail) {
                <div class="flex flex-col gap-1.5">
                  <span class="text-[10.5px] font-bold uppercase tracking-wider text-slate-400">Technical Rationale</span>
                  <p class="text-xs text-slate-600 leading-relaxed font-normal m-0">
                    {{ check.technicalDetail }}
                  </p>
                </div>
              }

              <!-- Remediation Guidance -->
              @if (check.remediationGuidance) {
                <div class="p-3 bg-amber-50 border border-amber-200 rounded-lg flex flex-col gap-1 text-xs text-amber-900">
                  <span class="font-bold flex items-center gap-1.5">
                    <app-lucide-icon name="shield-alert" [size]="13" class="text-amber-600"></app-lucide-icon>
                    <span>Remediation Guidance</span>
                  </span>
                  <span class="text-[11.5px] leading-relaxed">{{ check.remediationGuidance }}</span>
                </div>
              }

            </div>

            <!-- Drawer Footer -->
            <div class="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2">
              <button
                type="button"
                (click)="closeInspectDrawer()"
                class="h-8 px-4 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-md cursor-pointer transition-colors">
                Close
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class Step7ReadinessComponent {
  public vs: ValidationUiService;

  // Optional visual fixture override (used exclusively in isolated unit/visual test scripts)
  public fixtureSignal = signal<Step7VisualFixture | undefined>(undefined);
  @Input() set visualFixture(val: Step7VisualFixture | undefined) {
    this.fixtureSignal.set(val);
  }
  get visualFixture(): Step7VisualFixture | undefined {
    return this.fixtureSignal();
  }

  // Drawer & evaluation UI state
  public selectedCheck = signal<ReadinessCheckItem | null>(null);
  public isEvaluating = signal<boolean>(false);
  public evaluationMessage = signal<string | null>(null);
  public expandedDomainIds = signal<Set<ValidationReadinessDomain>>(new Set([
    'CONNECTIVITY_ACCESS',
    'SCOPE_CORRESPONDENCE',
    'BASELINE_LEGITIMACY',
    'ASSURANCE_COMPATIBILITY',
    'GOVERNANCE_OPERATIONAL'
  ]));

  // Local acknowledgement overrides
  public acknowledgedIds = signal<Set<string>>(new Set());

  // --------------------------------------------------------------------------
  // PRODUCTION DEFAULT: NOT_EVALUATED / READINESS_NOT_CONNECTED
  // Angular does NOT calculate canonical readiness from draft state!
  // --------------------------------------------------------------------------
  public productionDefaultReadiness: OverallValidationReadiness = {
    status: 'NOT_EVALUATED',
    statusLabel: 'Not Evaluated',
    summaryText: 'Readiness evaluation service is not currently connected. Live verification will execute at initialization.',
    domainsCount: 5,
    passedChecksCount: 0,
    totalChecksCount: 10,
    requiredActionCount: 0,
    isEvaluationConnected: false
  };

  public productionDefaultDomains: DomainCategoryGroup[] = [
    {
      id: 'CONNECTIVITY_ACCESS',
      title: '1. Connectivity & Access',
      description: 'Physical transport, endpoint reachability, TLS configuration, and authentication credentials.',
      passedCount: 0,
      totalCount: 4,
      hasBlockers: false,
      hasWarnings: false,
      isExpanded: true,
      checks: [
        {
          id: 'conn-src-reach',
          domain: 'CONNECTIVITY_ACCESS',
          name: 'Source Endpoint Reachability',
          status: 'NOT_EVALUATED',
          observation: 'Live network probe not performed in client draft.',
          affectedResources: ['Source Endpoint'],
          technicalDetail: 'Requires live TCP/TLS ping from the execution daemon.'
        },
        {
          id: 'conn-tgt-reach',
          domain: 'CONNECTIVITY_ACCESS',
          name: 'Target Endpoint Reachability',
          status: 'NOT_EVALUATED',
          observation: 'Live network probe not performed in client draft.',
          affectedResources: ['Target Endpoint'],
          technicalDetail: 'Requires live TCP/TLS ping from the execution daemon.'
        },
        {
          id: 'conn-tls-policy',
          domain: 'CONNECTIVITY_ACCESS',
          name: 'TLS Transport Security Policy',
          status: 'NOT_EVALUATED',
          observation: 'Parameter configuration specified; live cipher negotiation pending.',
          affectedResources: ['Transport Layer']
        },
        {
          id: 'conn-read-perms',
          domain: 'CONNECTIVITY_ACCESS',
          name: 'Read-Only Permission Attestation',
          status: 'NOT_EVALUATED',
          observation: 'Zero-mutation read permissions will be attested before scanning.',
          affectedResources: ['Source & Target Catalog']
        }
      ]
    },
    {
      id: 'SCOPE_CORRESPONDENCE',
      title: '2. Scope & Target Correspondence',
      description: 'Comparison units, catalog namespace bindings, and target catalog object discovery.',
      passedCount: 0,
      totalCount: 3,
      hasBlockers: false,
      hasWarnings: false,
      isExpanded: true,
      checks: [
        {
          id: 'scope-unit-manifest',
          domain: 'SCOPE_CORRESPONDENCE',
          name: 'Comparison Unit Manifest',
          status: 'NOT_EVALUATED',
          observation: 'Comparison unit count resolved from Step 4 draft scope.',
          affectedResources: ['Scoped Tables & Views']
        },
        {
          id: 'scope-correspondence-rule',
          domain: 'SCOPE_CORRESPONDENCE',
          name: 'Target Correspondence Rule',
          status: 'NOT_EVALUATED',
          observation: 'Correspondence rule specified; catalog counterpart discovery pending.',
          affectedResources: ['Target Catalog Namespace']
        },
        {
          id: 'scope-catalog-observation',
          domain: 'SCOPE_CORRESPONDENCE',
          name: 'Target Catalog Discovery Observation',
          status: 'NOT_EVALUATED',
          observation: 'Validation Law 6: Missing target objects remain in validation scope as planned observations.',
          affectedResources: ['Target Catalog']
        }
      ]
    },
    {
      id: 'BASELINE_LEGITIMACY',
      title: '3. Comparison Baseline Legitimacy',
      description: 'Logical alignment and physical stability basis between comparison endpoints.',
      passedCount: 0,
      totalCount: 2,
      hasBlockers: false,
      hasWarnings: false,
      isExpanded: true,
      checks: [
        {
          id: 'base-alignment',
          domain: 'BASELINE_LEGITIMACY',
          name: 'Logical Alignment Basis',
          status: 'NOT_EVALUATED',
          observation: 'Comparison baseline intent declared in Step 5.',
          affectedResources: ['Consistency Frontier']
        },
        {
          id: 'base-stability',
          domain: 'BASELINE_LEGITIMACY',
          name: 'Stability Basis & Isolation',
          status: 'NOT_EVALUATED',
          observation: 'Provider-native consistent read mechanism will be engaged at execution time.',
          affectedResources: ['Read Isolation']
        }
      ]
    },
    {
      id: 'ASSURANCE_COMPATIBILITY',
      title: '4. Assurance Strategy Compatibility',
      description: 'Selected assurance tier, datatype widening compatibility, and sampling boundaries.',
      passedCount: 0,
      totalCount: 2,
      hasBlockers: false,
      hasWarnings: false,
      isExpanded: true,
      checks: [
        {
          id: 'assur-tier-compat',
          domain: 'ASSURANCE_COMPATIBILITY',
          name: 'Assurance Tier Executability',
          status: 'NOT_EVALUATED',
          observation: 'Assurance requirement selected in Step 6.',
          affectedResources: ['Hashing & Scanning Engine']
        },
        {
          id: 'assur-exceptions',
          domain: 'ASSURANCE_COMPATIBILITY',
          name: 'Scoped Exception Overrides',
          status: 'NOT_EVALUATED',
          observation: 'Exception rules recorded; physical column-level type safety checked at runtime.',
          affectedResources: ['Exception Scope']
        }
      ]
    },
    {
      id: 'GOVERNANCE_OPERATIONAL',
      title: '5. Governance & Operational Conditions',
      description: 'Platform invariants and operator-declared maintenance coordination.',
      passedCount: 0,
      totalCount: 2,
      hasBlockers: false,
      hasWarnings: false,
      isExpanded: true,
      checks: [
        {
          id: 'gov-read-only-invariant',
          domain: 'GOVERNANCE_OPERATIONAL',
          name: 'Read-Only Non-Mutating Execution Guarantee',
          status: 'NOT_EVALUATED',
          observation: 'Engine Invariant: AKAAL executes exclusively read-only SELECT and metadata queries.',
          affectedResources: ['Validation Engine Execution Graph']
        },
        {
          id: 'gov-workload-coordination',
          domain: 'GOVERNANCE_OPERATIONAL',
          name: 'Operational Maintenance Declaration',
          status: 'NOT_EVALUATED',
          observation: 'Declared operational condition from Step 5.',
          affectedResources: ['Workload Frontier']
        }
      ]
    }
  ];

  // --------------------------------------------------------------------------
  // REACTIVE COMPUTED PRESENTATIONS
  // --------------------------------------------------------------------------
  public activeReadiness = computed<OverallValidationReadiness>(() => {
    const fix = this.fixtureSignal();
    if (fix) {
      return {
        status: fix.status,
        statusLabel: fix.statusLabel,
        summaryText: fix.summaryText,
        domainsCount: fix.domains.length,
        passedChecksCount: fix.domains.reduce((acc, d) => acc + d.passedCount, 0),
        totalChecksCount: fix.domains.reduce((acc, d) => acc + d.totalCount, 0),
        requiredActionCount: fix.actions.length,
        isEvaluationConnected: fix.isEvaluationConnected
      };
    }
    return this.productionDefaultReadiness;
  });

  public activeDomains = computed<DomainCategoryGroup[]>(() => {
    const fix = this.fixtureSignal();
    if (fix) {
      const expanded = this.expandedDomainIds();
      return fix.domains.map(d => ({
        ...d,
        isExpanded: expanded.has(d.id)
      }));
    }
    const expanded = this.expandedDomainIds();
    return this.productionDefaultDomains.map(d => ({
      ...d,
      isExpanded: expanded.has(d.id)
    }));
  });

  public activeActions = computed<RequiredActionItem[]>(() => {
    const fix = this.fixtureSignal();
    if (fix) {
      return fix.actions;
    }
    // In production default, no synthetic blockers are manufactured
    return [];
  });

  public activeAcknowledgements = computed<OperationalAcknowledgement[]>(() => {
    const fix = this.fixtureSignal();
    if (fix) {
      const acked = this.acknowledgedIds();
      return fix.acknowledgements.map(a => ({
        ...a,
        isAcknowledged: acked.has(a.id) || a.isAcknowledged
      }));
    }
    // If Step 5 declared a maintenance coordination condition, present as operator-owned condition
    const draft = this.vs.newValidationDraft();
    if (draft.baselineIntent === 'MAINTENANCE_COORDINATED' && draft.maintenanceCondition === 'WRITES_STOPPED_DECLARED') {
      const acked = this.acknowledgedIds();
      return [
        {
          id: 'ack-writes-stopped',
          title: 'Declared Maintenance Condition: Writes Stopped',
          summary: 'Operator confirms that source and target transaction workloads will be halted prior to validation execution.',
          isAcknowledged: acked.has('ack-writes-stopped')
        }
      ];
    }
    return [];
  });

  constructor(vs?: ValidationUiService) {
    if (vs) {
      this.vs = vs;
    } else {
      try { this.vs = inject(ValidationUiService); } catch { this.vs = new ValidationUiService(); }
    }
  }

  // --------------------------------------------------------------------------
  // USER ACTIONS
  // --------------------------------------------------------------------------
  public toggleDomainExpansion(domainId: ValidationReadinessDomain): void {
    const set = new Set(this.expandedDomainIds());
    if (set.has(domainId)) {
      set.delete(domainId);
    } else {
      set.add(domainId);
    }
    this.expandedDomainIds.set(set);
  }

  public openInspectDrawer(check: ReadinessCheckItem): void {
    this.selectedCheck.set(check);
  }

  public closeInspectDrawer(): void {
    this.selectedCheck.set(null);
  }

  public toggleAcknowledgement(id: string): void {
    const set = new Set(this.acknowledgedIds());
    if (set.has(id)) {
      set.delete(id);
    } else {
      set.add(id);
    }
    this.acknowledgedIds.set(set);
  }

  public handleActionClick(action: RequiredActionItem): void {
    if (action.ackId) {
      this.toggleAcknowledgement(action.ackId);
      return;
    }
    if (action.upstreamStep) {
      this.vs.updateDraft({ currentStep: action.upstreamStep });
    }
  }

  public handleReevaluateAll(): void {
    this.isEvaluating.set(true);
    setTimeout(() => {
      this.isEvaluating.set(false);
      this.evaluationMessage.set('Readiness evaluation service is not currently connected in this build. Live verification executes upon backend initialization.');
      setTimeout(() => this.evaluationMessage.set(null), 5000);
    }, 400);
  }

  public handleReevaluateCheck(checkId: string): void {
    this.evaluationMessage.set(`Re-evaluating ${checkId}: Live evaluation daemon is not currently connected.`);
    setTimeout(() => this.evaluationMessage.set(null), 3000);
  }

  public getStatusIcon(status: ValidationReadinessStatus): string {
    switch (status) {
      case 'READY':
        return 'check-circle-2';
      case 'READY_WITH_ATTENTION':
      case 'AWAITING_GOVERNANCE':
        return 'shield-alert';
      case 'BLOCKED':
        return 'alert-octagon';
      default:
        return 'clock';
    }
  }
}
