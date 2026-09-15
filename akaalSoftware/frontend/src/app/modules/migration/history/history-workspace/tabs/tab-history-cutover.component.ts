import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { CutoverContinuityRecord, CutoverEventChronology } from '../history-workspace.models';

@Component({
  selector: 'app-tab-history-cutover',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-6">
        
        <!-- Mode Inapplicability Guard -->
        @if (!record.cutover.isApplicableToMode) {
          <div class="bg-white border border-slate-200 rounded-lg p-10 text-center text-xs text-slate-500 shadow-xs">
            <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 text-slate-600 mb-3">
              <span class="text-sm font-bold">N/A</span>
            </div>
            <div class="text-base font-bold text-slate-900">
              Cutover &amp; Continuity Not Applicable
            </div>
            <p class="text-slate-500 mt-1 max-w-lg mx-auto">
              Mode <strong class="text-slate-800">{{ record.mode }}</strong> is a static/one-time execution or independent validation assurance profile. Live cutover synchronization, replication quiesce, and failback mechanisms apply exclusively to streaming and continuous sync topologies (M2, M3, M4, M5).
            </p>
          </div>
        } @else {
          
          <!-- Cutover Primary Summary Banner -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
            <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <div class="flex items-center gap-2.5">
                  <h2 class="text-base font-bold text-slate-900">
                    Production Cutover Execution
                  </h2>
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-bold border"
                    [ngClass]="getCutoverStatusClass(record.cutover.cutoverStatus)">
                    {{ record.cutover.cutoverStatus }}
                  </span>
                </div>
                <div class="text-xs text-slate-500 mt-1">
                  Executed at: <strong class="text-slate-800">{{ formatTimestamp(record.cutover.cutoverExecutedAt) }}</strong>
                </div>
              </div>

              <!-- Failback Posture Indicator -->
              <div class="flex items-center gap-2 bg-slate-50 px-3.5 py-2 rounded-md border border-slate-200 self-start md:self-auto">
                <div class="text-right">
                  <div class="text-[10px] font-bold uppercase text-slate-500">Failback Preparedness</div>
                  <div class="text-xs font-semibold" [ngClass]="record.cutover.failbackReady ? 'text-emerald-700' : 'text-slate-600'">
                    {{ record.cutover.failbackReady ? 'Failback Plan Armed' : 'Disabled' }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Key Cutover Telemetry Metrics -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 text-xs">
              <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                <div class="text-slate-500 font-medium">Actual Cutover Downtime</div>
                <div class="text-xl font-bold text-slate-900 mt-0.5">
                  {{ record.cutover.downtimeSeconds !== null ? record.cutover.downtimeSeconds + 's' : '0s' }}
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5">Total application write blackout window</div>
              </div>

              <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                <div class="text-slate-500 font-medium">Final CDC Synchronization Lag</div>
                <div class="text-xl font-bold font-mono text-emerald-700 mt-0.5">
                  {{ record.cutover.cdcFinalLagSeconds !== null ? record.cutover.cdcFinalLagSeconds + 's' : '0.0s' }}
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5">Lag threshold prior to target promotion</div>
              </div>

              <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                <div class="text-slate-500 font-medium">Post-Cutover Smoke Check</div>
                <div class="text-xl font-bold text-emerald-700 mt-0.5">
                  {{ record.cutover.postCutoverVerificationPassed ? 'Passed (100%)' : 'Failed' }}
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5">Automated target readiness attestation</div>
              </div>
            </div>
          </div>

          <!-- Cutover Chronology Stepper -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider mb-4 pb-2 border-b border-slate-100">
              Cutover Event Chronology ({{ record.cutover.chronology.length }} Stages)
            </h3>

            <div class="space-y-4">
              @for (step of record.cutover.chronology; track step.stepName) {
                <div class="p-3.5 rounded-md border border-slate-200 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-bold text-slate-900">{{ step.stepName }}</span>
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border"
                        [ngClass]="getStepStatusClass(step.status)">
                        {{ step.status }}
                      </span>
                    </div>
                    <div class="text-slate-600 text-xs mt-1">{{ step.details }}</div>
                  </div>

                  <div class="text-right text-[11px] text-slate-500 shrink-0">
                    <div>{{ formatTimestamp(step.timestamp) }}</div>
                    @if (step.duration) {
                      <div class="font-mono font-medium text-slate-700 mt-0.5">Duration: {{ step.duration }}</div>
                    }
                  </div>
                </div>
              }
            </div>
          </div>

        }

      </div>
    }
  `
})
export class TabHistoryCutoverComponent {
  public hws = inject(HistoryWorkspaceService);

  public getCutoverStatusClass(status: string): string {
    switch (status) {
      case 'COMPLETED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'IN_PROGRESS': return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  public getStepStatusClass(status: string): string {
    switch (status) {
      case 'COMPLETED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'IN_PROGRESS': return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public formatTimestamp(ts: string | null): string {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  }
}
