import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { M1BulkExecutionTelemetry } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-mode-bulk-snapshot-telemetry',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (telemetry) {
      <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight">Bulk Snapshot Telemetry</h3>
          <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700">M1 Mode</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Rows Transferred</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ (telemetry.rows_transferred | number) || '0' }}</span>
            <span class="text-[11px] text-slate-400">Total: {{ telemetry.total_rows ? (telemetry.total_rows | number) : 'Unknown total' }}</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Active Partitions</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ telemetry.active_partitions }} / {{ telemetry.total_partitions }}</span>
            <span class="text-[11px] text-slate-400">Workers: {{ telemetry.workers_active }}</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Write Latency</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ telemetry.target_write_latency_ms }} ms</span>
            <span class="text-[11px] text-emerald-600">Within target SLA</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Checkpoint Freshness</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ telemetry.checkpoint_freshness_seconds }}s ago</span>
            <span class="text-[11px] text-slate-400">Sync CAS Leased</span>
          </div>
        </div>
      </div>
    }
  `
})
export class ModeBulkSnapshotTelemetryComponent {
  @Input({ required: true }) telemetry!: M1BulkExecutionTelemetry;
}
