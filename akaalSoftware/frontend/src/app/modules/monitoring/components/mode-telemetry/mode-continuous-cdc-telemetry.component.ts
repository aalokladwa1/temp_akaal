import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { M3CdcExecutionTelemetry } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-mode-continuous-cdc-telemetry',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (telemetry) {
      <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight">Continuous Change Stream Telemetry</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700">M3 Mode</span>
          </div>
          <span class="text-xs text-slate-500 font-mono">{{ telemetry.commit_position_label }}</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Replication Lag</span>
            <span class="text-base font-bold font-mono" [ngClass]="telemetry.replication_lag_ms < 200 ? 'text-emerald-700' : 'text-amber-700'">
              {{ telemetry.replication_lag_ms }} ms
            </span>
            <span class="text-[11px] text-slate-400">Stream latency</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Stream Throughput</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.apply_rate_per_sec | number) || '0' }} /s</span>
            <span class="text-[11px] text-slate-400">Capture: {{ (telemetry.capture_rate_per_sec | number) || '0' }}/s</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Ring Buffer Fill</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ telemetry.ring_buffer_fill_pct }}%</span>
            <span class="text-[11px]" [ngClass]="telemetry.ring_buffer_fill_pct < 75 ? 'text-emerald-600' : 'text-amber-600'">
              {{ telemetry.ring_buffer_fill_pct < 75 ? 'Optimal capacity' : 'Elevated fill' }}
            </span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Event Backlog</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.backlog_events | number) || '0' }}</span>
            <span class="text-[11px] text-slate-400">Conflicts: {{ telemetry.conflicts_detected }}</span>
          </div>
        </div>
      </div>
    }
  `
})
export class ModeContinuousCdcTelemetryComponent {
  @Input({ required: true }) telemetry!: M3CdcExecutionTelemetry;
}
