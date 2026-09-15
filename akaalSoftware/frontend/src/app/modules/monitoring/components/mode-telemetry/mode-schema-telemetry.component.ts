import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { M6SchemaExecutionTelemetry } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-mode-schema-telemetry',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (telemetry) {
      <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight">Schema DDL Execution Telemetry</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700">M6 Mode</span>
          </div>
          <span class="text-xs text-slate-500 font-mono">Current: {{ telemetry.current_object_name }}</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">DDL Objects Applied</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ telemetry.objects_applied }} / {{ telemetry.objects_discovered }}</span>
            <span class="text-[11px] text-slate-400">Converted: {{ telemetry.objects_converted }}</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">DDL Work Rate</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ telemetry.ddl_work_rate_per_sec }} obj/s</span>
            <span class="text-[11px] text-slate-400">Avg latency: {{ telemetry.average_ddl_latency_ms }} ms</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Blocked Dependencies</span>
            <span class="text-base font-bold font-mono" [ngClass]="telemetry.blocked_dependencies_count === 0 ? 'text-emerald-700' : 'text-rose-700'">
              {{ telemetry.blocked_dependencies_count }}
            </span>
            <span class="text-[11px] text-slate-400">DAG unblocked</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Manual Review Items</span>
            <span class="text-base font-bold font-mono" [ngClass]="telemetry.manual_review_required_count === 0 ? 'text-emerald-700' : 'text-amber-700'">
              {{ telemetry.manual_review_required_count }}
            </span>
            <span class="text-[11px] text-slate-400">Unsupported: {{ telemetry.unsupported_objects_count }}</span>
          </div>
        </div>
      </div>
    }
  `
})
export class ModeSchemaTelemetryComponent {
  @Input({ required: true }) telemetry!: M6SchemaExecutionTelemetry;
}
