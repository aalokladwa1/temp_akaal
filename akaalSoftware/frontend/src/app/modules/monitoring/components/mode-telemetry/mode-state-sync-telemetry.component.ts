import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { M5StateSyncExecutionTelemetry } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-mode-state-sync-telemetry',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (telemetry) {
      <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight">State-Based Sync & Reconciliation Telemetry</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700">M5 Mode</span>
          </div>
          <span class="text-xs text-slate-500 font-mono">Scan Cycle #{{ telemetry.scan_cycle_number }}</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Entities Scanned</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.entities_scanned | number) || '0' }}</span>
            <span class="text-[11px] text-slate-400">Scan duration: {{ (telemetry.scan_duration_ms / 1000) | number:'1.1-2' }}s</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Drift Discovered</span>
            <span class="text-base font-bold font-mono" [ngClass]="telemetry.drift_detected_count > 0 ? 'text-amber-700' : 'text-emerald-700'">
              {{ (telemetry.drift_detected_count | number) || '0' }} items
            </span>
            <span class="text-[11px] text-slate-400">Differences detected</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Reconciliation Rate</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.reconciliation_apply_rate_per_sec | number) || '0' }} /s</span>
            <span class="text-[11px] text-slate-400">Apply throughput</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Pending Resolution</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.unresolved_differences | number) || '0' }}</span>
            <span class="text-[11px]" [ngClass]="telemetry.unresolved_differences === 0 ? 'text-emerald-600' : 'text-amber-600 font-semibold'">
              {{ telemetry.unresolved_differences === 0 ? 'State synchronized' : 'Resolving drift' }}
            </span>
          </div>
        </div>
      </div>
    }
  `
})
export class ModeStateSyncTelemetryComponent {
  @Input({ required: true }) telemetry!: M5StateSyncExecutionTelemetry;
}
