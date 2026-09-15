import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MigrationResourcesDTO } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-migration-resources-tab',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Attributed vs Host-Wide Resources -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Attributed Resource Footprint</h3>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700">Strictly Attributed</span>
          </div>
          <span class="text-xs text-slate-500 font-medium">Host CPU: {{ resources.host_cpu_pct }}% • Host Mem: {{ resources.host_memory_mb }} MB</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Attributed CPU</span>
            <span class="text-xl font-bold font-mono text-slate-900">{{ resources.attributed_cpu_pct }}%</span>
            <span class="text-[11px] text-slate-400">Total host: {{ resources.host_cpu_pct }}%</span>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Attributed Memory</span>
            <span class="text-xl font-bold font-mono text-slate-900">{{ resources.attributed_memory_mb }} MB</span>
            <span class="text-[11px] text-slate-400">Total host: {{ resources.host_memory_mb }} MB</span>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Network Egress</span>
            <span class="text-xl font-bold font-mono text-slate-900">{{ resources.attributed_network_mbps }} Mbps</span>
            <span class="text-[11px] text-emerald-600">Bandwidth nominal</span>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
            <span class="text-xs font-medium text-slate-500">Spool / Disk</span>
            <span class="text-xl font-bold font-mono text-slate-900">{{ resources.attributed_storage_mb }} MB</span>
            <span class="text-[11px] text-slate-400">Local WAL storage</span>
          </div>
        </div>
      </div>

      <!-- 2. Assigned Compute Nodes (with Deep Links to Platform Operations) -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Assigned Compute Placement</h3>
          <span class="text-xs text-slate-500 font-medium">{{ resources.assigned_nodes.length }} compute hosts</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                <th class="py-2.5 px-3">Node / Host</th>
                <th class="py-2.5 px-3">Locality</th>
                <th class="py-2.5 px-3">Slots / Workers</th>
                <th class="py-2.5 px-3">Node CPU / Mem</th>
                <th class="py-2.5 px-3">Health</th>
                <th class="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (node of resources.assigned_nodes; track node.node_id) {
                <tr class="hover:bg-slate-50/50 transition-colors">
                  <td class="py-2.5 px-3 whitespace-nowrap">
                    <div class="font-bold text-slate-900">{{ node.host_name }}</div>
                    <div class="text-[11px] font-mono text-slate-400">{{ node.node_id }}</div>
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                    {{ node.region_locality }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                    {{ node.slots_allocated }} slots ({{ node.active_workers }} active)
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                    {{ node.migration_cpu_pct }}% / {{ node.migration_memory_mb }} MB
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap">
                    <span class="flex items-center gap-1.5 text-slate-800 font-medium">
                      <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                      {{ node.health }}
                    </span>
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap text-right">
                    <a
                      [routerLink]="node.platform_route"
                      class="text-xs font-semibold text-blue-600 hover:text-blue-700 cursor-pointer">
                      Inspect Node →
                    </a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- 3. Assigned Partitions -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Partition &amp; Worker Mapping</h3>
          <span class="text-xs text-slate-500 font-medium">{{ resources.assigned_partitions.length }} active partitions</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                <th class="py-2.5 px-3">Partition Name</th>
                <th class="py-2.5 px-3">Assigned Worker</th>
                <th class="py-2.5 px-3">Assigned Node</th>
                <th class="py-2.5 px-3">Row Count</th>
                <th class="py-2.5 px-3">Throughput</th>
                <th class="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (part of resources.assigned_partitions; track part.partition_id) {
                <tr class="hover:bg-slate-50/50 transition-colors">
                  <td class="py-2.5 px-3 whitespace-nowrap font-bold text-slate-900 font-mono">
                    {{ part.partition_name }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                    {{ part.worker_id }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-500">
                    {{ part.node_id }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-800 font-semibold">
                    {{ part.row_count | number }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                    {{ part.throughput_label }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-semibold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200/60': part.status === 'PROCESSING' || part.status === 'COMPLETED',
                        'bg-amber-50 text-amber-700 border border-amber-200/60': part.status === 'PAUSED' || part.status === 'WAITING'
                      }">
                      {{ part.status }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class MigrationResourcesTabComponent {
  @Input({ required: true }) resources!: MigrationResourcesDTO;
}
