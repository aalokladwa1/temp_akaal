/**
 * AKAAL Monitoring — Part 3 of 4: Platform Performance Tab Component
 * Systemic throughput, end-to-end latency breakdowns (dispatch, IPC, queue, sink),
 * worker concurrency skew, and evidence-based bottleneck observations.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PlatformMonitoringService } from '../../services/platform-monitoring.service';

@Component({
  selector: 'app-platform-performance-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Platform Work Rate & Latency Profile -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Work Rate Card -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Systemic Work Rate &amp; Throughput</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              {{ pms.performance().work_rate.trend }}
            </span>
          </div>

          <div class="flex items-baseline gap-2">
            <span class="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{{ pms.performance().work_rate.total_rows_per_sec | number }}</span>
            <span class="text-sm font-medium text-slate-500">ops/sec</span>
          </div>

          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[11px] text-slate-500">Aggregate Bandwidth</span>
              <span class="font-bold font-mono text-slate-800">{{ pms.performance().work_rate.total_bytes_per_sec_label }}</span>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[11px] text-slate-500">Event Stream Velocity</span>
              <span class="font-bold font-mono text-slate-800">{{ pms.performance().work_rate.total_events_per_sec | number }} events/s</span>
            </div>
          </div>
        </div>

        <!-- Latency Profile Card -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Systemic Latency Breakdown</h3>
            <span class="text-xs text-slate-500 font-mono">P50 / P95 / P99</span>
          </div>

          <div class="grid grid-cols-4 gap-2 text-center text-xs">
            <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[10.5px] text-slate-500">Dispatch</span>
              <span class="text-sm font-bold font-mono text-slate-800">{{ pms.performance().latencies.runtime_dispatch_ms }}ms</span>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[10.5px] text-slate-500">IPC</span>
              <span class="text-sm font-bold font-mono text-slate-800">{{ pms.performance().latencies.ipc_transit_ms }}ms</span>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[10.5px] text-slate-500">Queue</span>
              <span class="text-sm font-bold font-mono text-slate-800">{{ pms.performance().latencies.queue_buffer_ms }}ms</span>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
              <span class="text-[10.5px] text-slate-500">Sink</span>
              <span class="text-sm font-bold font-mono text-amber-700">{{ pms.performance().latencies.sink_apply_ms }}ms</span>
            </div>
          </div>

          <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 border border-slate-100 text-xs text-slate-600 font-mono">
            <span>P50: <strong>{{ pms.performance().latencies.p50_ms }}ms</strong></span>
            <span>•</span>
            <span>P95: <strong>{{ pms.performance().latencies.p95_ms }}ms</strong></span>
            <span>•</span>
            <span>P99: <strong>{{ pms.performance().latencies.p99_ms }}ms</strong></span>
          </div>
        </div>

      </div>

      <!-- 2. Fleet Worker Concurrency & Skew -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Fleet Worker Concurrency &amp; Skew Distribution</h3>
          <span class="text-xs text-slate-500 font-medium">{{ pms.performance().worker_skew.total_workers }} active workers</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Balanced Execution</span>
            <span class="text-xl font-bold font-mono text-emerald-700">{{ pms.performance().worker_skew.balanced_workers }} workers</span>
            <span class="text-[11px] text-slate-400">Processing within nominal variance</span>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Elevated Load</span>
            <span class="text-xl font-bold font-mono text-amber-700">{{ pms.performance().worker_skew.elevated_workers }} worker</span>
            <span class="text-[11px] text-slate-400">Large partition chunk processing</span>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Stragglers / Stalled</span>
            <span class="text-xl font-bold font-mono text-slate-900">{{ pms.performance().worker_skew.stragglers }} workers</span>
            <span class="text-[11px] text-emerald-600">Zero pipeline stalls</span>
          </div>
        </div>

        <p class="text-xs text-slate-600 leading-relaxed pt-2 border-t border-slate-100">
          {{ pms.performance().worker_skew.skew_summary }}
        </p>
      </div>

      <!-- 3. Systemic Bottleneck Observations -->
      @if (pms.performance().systemic_bottlenecks.length > 0) {
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Systemic Bottleneck Observations</h3>
            <span class="text-xs text-slate-500 font-medium">{{ pms.performance().systemic_bottlenecks.length }} observations</span>
          </div>

          <div class="flex flex-col gap-3">
            @for (btn of pms.performance().systemic_bottlenecks; track btn.id) {
              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1.5 text-xs">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-slate-900">{{ btn.subsystem }}</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700">
                    {{ btn.severity }}
                  </span>
                </div>
                <p class="text-slate-700">{{ btn.description }}</p>
                <div class="text-[11px] text-slate-500 font-mono pt-1 border-t border-slate-200/60">
                  Observed Evidence: {{ btn.evidence }}
                </div>
              </div>
            }
          </div>
        </div>
      }

    </div>
  `
})
export class PlatformPerformanceTabComponent {
  public pms = inject(PlatformMonitoringService);
}
