import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { M4IncrementalExecutionTelemetry } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-mode-incremental-telemetry',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (telemetry) {
      <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight">Incremental Polling Telemetry</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700">M4 Mode</span>
          </div>
          <span class="text-xs text-slate-500 font-mono">Watermark: {{ telemetry.watermark_field }}</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Current Watermark</span>
            <span class="text-sm font-bold text-slate-900 font-mono truncate" [title]="telemetry.watermark_current_value">
              {{ telemetry.watermark_current_value }}
            </span>
            <span class="text-[11px] text-slate-400">Cadence: {{ telemetry.polling_cadence_seconds }}s</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Last Poll Latency</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ telemetry.last_poll_latency_ms }} ms</span>
            <span class="text-[11px] text-slate-400">Timestamp: {{ telemetry.last_poll_timestamp | date:'HH:mm:ss' }}</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Delta Discovered</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.delta_rows_discovered | number) || '0' }}</span>
            <span class="text-[11px] text-slate-400">Applied: {{ (telemetry.delta_rows_applied | number) || '0' }}</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Batch Buffer</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.batch_size | number) || '0' }}</span>
            <span class="text-[11px]" [ngClass]="telemetry.is_stale ? 'text-amber-600 font-semibold' : 'text-emerald-600'">
              {{ telemetry.is_stale ? 'Stale watermark alert' : 'Fresh watermark' }}
            </span>
          </div>
        </div>
      </div>
    }
  `
})
export class ModeIncrementalTelemetryComponent {
  @Input({ required: true }) telemetry!: M4IncrementalExecutionTelemetry;
}
