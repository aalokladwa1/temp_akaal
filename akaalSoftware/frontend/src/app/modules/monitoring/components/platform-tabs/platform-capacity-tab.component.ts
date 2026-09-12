/**
 * AKAAL Monitoring — Part 3 of 4: Platform Capacity & Utilization Tab Component
 * Real-time cluster resource consumption, storage domains breakdown,
 * network bandwidth, queue backpressure, and advisory capacity runway.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PlatformMonitoringService } from '../../services/platform-monitoring.service';

@Component({
  selector: 'app-platform-capacity-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. CPU & Memory Cluster Utilization -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- CPU Utilization Card -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Cluster CPU Capacity &amp; Utilization</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              {{ pms.capacity().cpu.status }}
            </span>
          </div>

          <div class="flex items-baseline gap-3">
            <span class="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{{ pms.capacity().cpu.used_pct }}%</span>
            <span class="text-sm font-medium text-slate-500">of {{ pms.capacity().cpu.total_cores }} cores utilized</span>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div 
              class="bg-blue-600 h-full rounded-full transition-all"
              [style.width.%]="pms.capacity().cpu.used_pct">
            </div>
          </div>

          <div class="flex items-center justify-between text-xs text-slate-500 pt-1 font-mono">
            <span>Allocated: <strong>{{ (pms.capacity().cpu.total_cores * pms.capacity().cpu.used_pct / 100).toFixed(1) }} cores</strong></span>
            <span>Headroom: <strong class="text-emerald-700">{{ pms.capacity().cpu.headroom_pct }}% free</strong></span>
          </div>
        </div>

        <!-- Memory Utilization Card -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Cluster Memory Footprint</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              {{ pms.capacity().memory.status }}
            </span>
          </div>

          <div class="flex items-baseline gap-3">
            <span class="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">{{ (pms.capacity().memory.used_mb / 1024).toFixed(1) }} GB</span>
            <span class="text-sm font-medium text-slate-500">of {{ (pms.capacity().memory.total_mb / 1024).toFixed(0) }} GB allocated</span>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div 
              class="bg-blue-600 h-full rounded-full transition-all"
              [style.width.%]="pms.capacity().memory.used_pct">
            </div>
          </div>

          <div class="flex items-center justify-between text-xs text-slate-500 pt-1 font-mono">
            <span>Utilization: <strong>{{ pms.capacity().memory.used_pct }}%</strong></span>
            <span>Headroom: <strong class="text-emerald-700">{{ (pms.capacity().memory.headroom_mb / 1024).toFixed(1) }} GB free</strong></span>
          </div>
        </div>

      </div>

      <!-- 2. Storage Domains Breakdown -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Storage Domain Capacity</h3>
          <span class="text-xs text-slate-500 font-medium">{{ pms.capacity().storage_domains.length }} isolated domains</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          @for (dom of pms.capacity().storage_domains; track dom.domain) {
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between gap-3 text-xs">
              <div class="flex flex-col gap-1">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-slate-900">{{ dom.domain }}</span>
                  <span class="font-mono font-bold text-slate-800">{{ dom.used_pct }}%</span>
                </div>
                <p class="text-[11px] text-slate-500">{{ dom.description }}</p>
              </div>

              <!-- Storage Bar -->
              <div class="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div 
                  class="bg-blue-600 h-full rounded-full transition-all"
                  [style.width.%]="dom.used_pct">
                </div>
              </div>

              <div class="flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>Used: <strong>{{ (dom.used_mb / 1024).toFixed(2) }} GB</strong></span>
                <span>Capacity: <strong>{{ (dom.capacity_mb / 1024).toFixed(0) }} GB</strong></span>
              </div>
            </div>
          }
        </div>
      </div>

      <!-- 3. Network & Queue Flow Capacity -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Network Bandwidth -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Network Bandwidth Ingress / Egress</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              {{ pms.capacity().network.status }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Ingress Bandwidth</span>
              <span class="text-xl font-bold font-mono text-slate-900">{{ pms.capacity().network.current_ingress_mbps }} Mbps</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Egress Bandwidth</span>
              <span class="text-xl font-bold font-mono text-slate-900">{{ pms.capacity().network.current_egress_mbps }} Mbps</span>
            </div>
          </div>

          <div class="text-[11px] font-mono text-slate-500">
            Interface Bandwidth Capacity: <strong>{{ (pms.capacity().network.bandwidth_capacity_mbps / 1000).toFixed(0) }} Gbps Full-Duplex</strong>
          </div>
        </div>

        <!-- Queue & Spool Pressure -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Queue Buffers &amp; Spool Saturation</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              Backpressure: {{ pms.capacity().queues.backpressure_level }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Ring Buffer Utilization</span>
              <span class="text-xl font-bold font-mono text-slate-900">{{ pms.capacity().queues.ring_buffer_pct }}%</span>
              <span class="text-[11px] text-slate-400">Zero-copy memory ring</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Spool Disk Allocation</span>
              <span class="text-xl font-bold font-mono text-slate-900">{{ pms.capacity().queues.spool_disk_pct }}%</span>
              <span class="text-[11px] text-slate-400">WAL staging spillover</span>
            </div>
          </div>

          <div class="text-[11px] text-slate-500">
            Flow Status: <strong class="text-emerald-700">All stream consumers keeping pace with ingestion rate</strong>
          </div>
        </div>

      </div>

      <!-- 4. Capacity Runway & Forecast -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-3">
        <div class="flex items-center justify-between pb-2 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Capacity Runway &amp; Horizon Analysis</h3>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700">Advisory Horizon</span>
          </div>
          <span class="text-xs text-slate-500 font-mono">{{ pms.capacity().forecasting.sample_window }}</span>
        </div>

        <p class="text-xs text-slate-700 leading-relaxed">{{ pms.capacity().forecasting.advisory_notice }}</p>
      </div>

    </div>
  `
})
export class PlatformCapacityTabComponent {
  public pms = inject(PlatformMonitoringService);
}
