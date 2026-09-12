import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { M2BulkCdcExecutionTelemetry } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-mode-bulk-cdc-telemetry',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (telemetry) {
      <div class="flex flex-col gap-5 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs">
        
        <!-- Header with Phase Indicator -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight">Bulk + CDC Phased Execution Telemetry</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700">M2 Mode</span>
          </div>

          <!-- Phase Progress Badges -->
          <div class="flex items-center gap-1.5 text-xs">
            <span 
              class="px-2 py-0.5 rounded font-medium"
              [ngClass]="telemetry.bulk_progress_pct === 100 ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'bg-blue-50 text-blue-700'">
              1. Bulk Load
            </span>
            <span class="text-slate-300">→</span>
            <span 
              class="px-2 py-0.5 rounded font-medium"
              [ngClass]="telemetry.current_phase === 'CDC_CATCHUP' ? 'bg-blue-600 text-white font-semibold' : (telemetry.current_phase === 'CONTINUOUS_SYNC' || telemetry.current_phase === 'CUTOVER_READINESS' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500')">
              2. CDC Catchup
            </span>
            <span class="text-slate-300">→</span>
            <span 
              class="px-2 py-0.5 rounded font-medium"
              [ngClass]="telemetry.current_phase === 'CONTINUOUS_SYNC' ? 'bg-blue-600 text-white font-semibold' : (telemetry.current_phase === 'CUTOVER_READINESS' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500')">
              3. Continuous Sync
            </span>
            <span class="text-slate-300">→</span>
            <span 
              class="px-2 py-0.5 rounded font-medium"
              [ngClass]="telemetry.current_phase === 'CUTOVER_READINESS' ? 'bg-blue-600 text-white font-semibold' : 'bg-slate-100 text-slate-500'">
              4. Cutover Readiness
            </span>
          </div>
        </div>

        <!-- Telemetry Metrics Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">CDC Replication Lag</span>
            <span class="text-lg font-bold font-mono" [ngClass]="telemetry.cdc_replication_lag_ms < 100 ? 'text-emerald-700' : 'text-amber-700'">
              {{ telemetry.cdc_replication_lag_ms }} ms
            </span>
            <span class="text-[11px] text-slate-400">Target SLA: &lt; 100ms</span>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Stream Backlog</span>
            <span class="text-lg font-bold text-slate-900 font-mono">{{ (telemetry.cdc_backlog_rows | number) || '0' }}</span>
            <span class="text-[11px] text-slate-400">Unapplied change events</span>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">CDC Capture Rate</span>
            <span class="text-lg font-bold text-slate-900 font-mono">{{ (telemetry.cdc_capture_rate_per_sec | number) || '0' }}</span>
            <span class="text-[11px] text-slate-400">Source log events/sec</span>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">CDC Apply Rate</span>
            <span class="text-lg font-bold text-slate-900 font-mono">{{ (telemetry.cdc_apply_rate_per_sec | number) || '0' }}</span>
            <span class="text-[11px] text-slate-400">Target write events/sec</span>
          </div>
        </div>

        <!-- Cutover Readiness Signals Matrix -->
        <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-800 uppercase tracking-wider">Cutover Readiness Verification</span>
            <span 
              class="px-2 py-0.5 rounded text-[11px] font-semibold"
              [ngClass]="telemetry.cutover_readiness_signals.current_lag_ms < 100 && telemetry.cutover_readiness_signals.schema_barriers_count === 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'">
              {{ telemetry.cutover_readiness_signals.current_lag_ms < 100 && telemetry.cutover_readiness_signals.schema_barriers_count === 0 ? 'Cutover Ready' : 'Pending Convergence' }}
            </span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div class="flex items-center justify-between p-2 rounded bg-white border border-slate-200">
              <span class="text-slate-600">Pending Backlog:</span>
              <span class="font-mono font-bold text-slate-900">{{ telemetry.cutover_readiness_signals.remaining_backlog_rows }} rows</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-white border border-slate-200">
              <span class="text-slate-600">Schema Barriers:</span>
              <span class="font-mono font-bold" [ngClass]="telemetry.cutover_readiness_signals.schema_barriers_count === 0 ? 'text-emerald-700' : 'text-rose-700'">
                {{ telemetry.cutover_readiness_signals.schema_barriers_count }}
              </span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-white border border-slate-200">
              <span class="text-slate-600">Quarantine Items:</span>
              <span class="font-mono font-bold" [ngClass]="telemetry.cutover_readiness_signals.quarantined_events_count === 0 ? 'text-emerald-700' : 'text-rose-700'">
                {{ telemetry.cutover_readiness_signals.quarantined_events_count }}
              </span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-white border border-slate-200">
              <span class="text-slate-600">Endpoints Status:</span>
              <span class="font-bold text-emerald-700 flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Nominal
              </span>
            </div>
          </div>
        </div>

      </div>
    }
  `
})
export class ModeBulkCdcTelemetryComponent {
  @Input({ required: true }) telemetry!: M2BulkCdcExecutionTelemetry;
}
