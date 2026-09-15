import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationPerformanceDTO } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-migration-performance-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Headline Throughput & Latency Breakdown -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Throughput Card -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Work Rate & Throughput</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              {{ performance.work_rate_trend }}
            </span>
          </div>

          <div class="flex items-baseline gap-2">
            <span class="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{{ performance.work_rate_label }}</span>
            <span class="text-sm font-medium text-slate-500">{{ performance.work_rate_unit }}</span>
          </div>

          <!-- Flow Saturation Strip -->
          <div class="grid grid-cols-3 gap-3 pt-2 text-xs">
            <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[11px] text-slate-500">Ring Buffer</span>
              <span class="font-bold font-mono text-slate-800">{{ performance.flow.ring_buffer_pct }}%</span>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[11px] text-slate-500">Spool Disk</span>
              <span class="font-bold font-mono text-slate-800">{{ performance.flow.spool_disk_pct }}%</span>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[11px] text-slate-500">Backpressure</span>
              <span class="font-bold text-emerald-700">{{ performance.flow.backpressure_level }}</span>
            </div>
          </div>
        </div>

        <!-- Latency Profile Card -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">End-to-End Latency Profile</h3>
            <span class="text-xs text-slate-500 font-mono">P50 / P95 / P99</span>
          </div>

          <div class="grid grid-cols-3 gap-3">
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-xs text-slate-500 font-medium">Source Read</span>
              <span class="text-base font-bold font-mono text-slate-800">{{ performance.latencies.source_read_ms }} ms</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-xs text-slate-500 font-medium">Queue / Buffer</span>
              <span class="text-base font-bold font-mono text-slate-800">{{ performance.latencies.queue_buffer_ms }} ms</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-xs text-slate-500 font-medium">Sink Apply</span>
              <span class="text-base font-bold font-mono text-slate-800">{{ performance.latencies.sink_apply_ms }} ms</span>
            </div>
          </div>

          <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 border border-slate-100 text-xs text-slate-600 font-mono">
            <span>P50: <strong>{{ performance.latencies.p50_ms }}ms</strong></span>
            <span>•</span>
            <span>P95: <strong>{{ performance.latencies.p95_ms }}ms</strong></span>
            <span>•</span>
            <span>P99: <strong>{{ performance.latencies.p99_ms }}ms</strong></span>
          </div>
        </div>

      </div>

      <!-- 2. Worker Concurrency & Skew Analysis -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Worker Concurrency &amp; Skew Analysis</h3>
          <span class="text-xs text-slate-500 font-medium">{{ performance.workers.length }} assigned workers</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                <th class="py-2.5 px-3">Worker / Role</th>
                <th class="py-2.5 px-3">Partition</th>
                <th class="py-2.5 px-3">Rows Processed</th>
                <th class="py-2.5 px-3">Work Rate</th>
                <th class="py-2.5 px-3">CPU / Memory</th>
                <th class="py-2.5 px-3 text-right">Skew State</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (w of performance.workers; track w.id) {
                <tr class="hover:bg-slate-50/50 transition-colors">
                  <td class="py-2.5 px-3 whitespace-nowrap">
                    <div class="font-bold text-slate-900">{{ w.name }}</div>
                    <div class="text-[11px] text-slate-500">{{ w.role }}</div>
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                    {{ w.assigned_partition }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono font-semibold text-slate-800">
                    {{ w.rows_processed | number }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                    {{ w.rate_label }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                    {{ w.cpu_percent }}% / {{ w.memory_mb }} MB
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-semibold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200/60': w.skew_state === 'BALANCED',
                        'bg-amber-50 text-amber-700 border border-amber-200/60': w.skew_state === 'ELEVATED',
                        'bg-rose-50 text-rose-700 border border-rose-200/60': w.skew_state === 'STRAGGLER'
                      }">
                      {{ w.skew_state }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- 3. Bottleneck Observations -->
      @if (performance.bottlenecks.length > 0) {
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-3">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Bottleneck Observations</h3>
            <span class="text-xs text-slate-500 font-medium">{{ performance.bottlenecks.length }} observations</span>
          </div>

          <div class="flex flex-col gap-3">
            @for (btn of performance.bottlenecks; track btn.id) {
              <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1.5 text-xs">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-slate-900">{{ btn.subsystem }}</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700">
                    {{ btn.severity }}
                  </span>
                </div>
                <p class="text-slate-700">{{ btn.description }}</p>
                <div class="text-[11px] text-slate-500 font-mono pt-1 border-t border-slate-100">
                  Evidence: {{ btn.evidence }}
                </div>
              </div>
            }
          </div>
        </div>
      }

    </div>
  `
})
export class MigrationPerformanceTabComponent {
  @Input({ required: true }) performance!: MigrationPerformanceDTO;
}
