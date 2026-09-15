import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { M7DataOnlyExecutionTelemetry } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-mode-raw-data-ingest-telemetry',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (telemetry) {
      <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight">Data Only Pipeline Telemetry</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700">M7 Mode</span>
          </div>
          <span class="text-xs text-slate-500 font-mono">{{ telemetry.active_table }} ({{ telemetry.active_partition }})</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Rows Streamed</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.rows_transferred | number) || '0' }}</span>
            <span class="text-[11px] text-slate-400">{{ (telemetry.bytes_transferred / (1024*1024*1024)) | number:'1.1-2' }} GB</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Transfer Rate</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.transfer_rate_rows_per_sec | number) || '0' }} rows/s</span>
            <span class="text-[11px] text-emerald-600">Optimal pipeline flow</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Commit Latency</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ telemetry.target_commit_latency_ms }} ms</span>
            <span class="text-[11px] text-slate-400">Target sink commit</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Coercion Errors</span>
            <span class="text-base font-bold font-mono" [ngClass]="telemetry.coercion_errors_count === 0 ? 'text-emerald-700' : 'text-rose-700'">
              {{ telemetry.coercion_errors_count }}
            </span>
            <span class="text-[11px] text-slate-400">Type mapping valid</span>
          </div>
        </div>
      </div>
    }
  `
})
export class ModeRawDataIngestTelemetryComponent {
  @Input({ required: true }) telemetry!: M7DataOnlyExecutionTelemetry;
}
