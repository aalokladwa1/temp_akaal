import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PerformanceReportPayload } from '../../../models/report-payloads.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-performance-report-body',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Durable Execution Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          DURABLE PERFORMANCE &amp; THROUGHPUT TOTALS
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Elapsed Duration</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.summary.total_duration_seconds }}s</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Effective Rate (Records)</span>
            <span class="text-base font-bold font-mono text-blue-700">{{ payload.summary.effective_throughput_rows_sec | number }} rows/s</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Effective Rate (Volume)</span>
            <span class="text-base font-bold font-mono text-blue-700">{{ payload.summary.effective_throughput_mb_sec | number:'1.1-2' }} MB/s</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Total Volume</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ (payload.summary.total_volume_bytes / (1024*1024)) | number:'1.1-2' }} MB</span>
          </div>
        </div>
      </div>

      <!-- Stage Durations Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          STAGE DURATION BREAKDOWN
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Stage Name</th>
                <th class="py-3 px-4 text-right">Duration</th>
                <th class="py-3 px-4 text-right">Fraction of Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (stage of payload.stage_durations; track stage.stage_name) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ stage.stage_name }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                    {{ stage.duration_seconds }}s
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-600 text-[11px]">
                    {{ stage.percentage_of_total }}%
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Partition Latency / Throughput Table -->
      @if (payload.partition_throughput && payload.partition_throughput.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            PARTITION THROUGHPUT OBSERVATIONS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Partition ID</th>
                  <th class="py-3 px-4">Entity</th>
                  <th class="py-3 px-4 text-right">Rows</th>
                  <th class="py-3 px-4 text-right">Duration</th>
                  <th class="py-3 px-4 text-right">Throughput</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (p of payload.partition_throughput; track p.partition_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono text-slate-900 text-[11px]">
                      {{ p.partition_id }}
                    </td>
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ p.entity_name }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                      {{ p.row_count | number }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-500 text-[11px]">
                      {{ p.duration_seconds }}s
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-blue-700 font-semibold">
                      {{ p.rows_per_second | number }} rows/s
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Truthful Telemetry Notice & Notes (Zero-Fake Law) -->
      <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2 text-xs text-slate-600">
        <div class="flex items-center gap-2 text-slate-700 font-semibold">
          <app-lucide-icon name="info" [size]="14" class="text-slate-500"></app-lucide-icon>
          <span>Durable Telemetry Constraints</span>
        </div>
        <p class="text-[11px] text-slate-500 leading-relaxed">
          {{ payload.unavailable_telemetry_notice || 'High-resolution time-series metrics (P95/P99 latency curves, sub-second CPU/memory graphs) are ephemeral Monitoring telemetry and are not recorded in durable report archives.' }}
        </p>
      </div>

    </div>
  `
})
export class PerformanceReportBodyComponent {
  @Input({ required: true }) public payload!: PerformanceReportPayload;
}
