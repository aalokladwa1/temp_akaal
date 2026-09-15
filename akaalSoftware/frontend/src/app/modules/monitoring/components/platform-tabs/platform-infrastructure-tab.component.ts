/**
 * AKAAL Monitoring — Part 3 of 4: Platform Infrastructure & Fleet Tab Component
 * Real-time inventory of compute nodes, worker assignments, cross-workspace deep links,
 * topology & locality, and distributed CAS fencing leases.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { PlatformMonitoringService } from '../../services/platform-monitoring.service';

@Component({
  selector: 'app-platform-infrastructure-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- Filter Toolbar -->
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        
        <!-- Search Input -->
        <div class="relative flex-1 min-w-[240px]">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </div>
          <input
            type="text"
            [ngModel]="pms.nodeSearchQuery()"
            (ngModelChange)="pms.setNodeSearch($event)"
            placeholder="Search compute nodes by hostname, node ID, or locality..."
            class="w-full h-9 pl-9 pr-3.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 focus:bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors">
        </div>

        <!-- Role Filter with CustomSelect -->
        <div class="w-44">
          <app-custom-select
            [options]="roleOptions"
            [value]="pms.nodeRoleFilter()"
            (valueChange)="pms.setNodeRoleFilter($event)"
            [placeholder]="'All Roles'"
            [size]="'sm'">
          </app-custom-select>
        </div>

      </div>

      <!-- 1. Compute Nodes Inventory Table -->
      <div class="rounded-2xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
        <div class="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Cluster Compute Nodes</h3>
          <span class="text-xs text-slate-500 font-medium">
            Showing {{ pms.filteredNodes().length }} of {{ pms.data().nodes.length }} nodes
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75 select-none">
                <th class="py-3 px-4 min-w-[200px]">Node Host / ID</th>
                <th class="py-3 px-4 min-w-[140px]">Role</th>
                <th class="py-3 px-4 min-w-[160px]">Locality / Cluster</th>
                <th class="py-3 px-4 min-w-[120px]">Slots (Busy/Total)</th>
                <th class="py-3 px-4 min-w-[130px]">CPU / Memory</th>
                <th class="py-3 px-4 min-w-[120px]">Health &amp; State</th>
                <th class="py-3 px-4 text-right min-w-[90px]">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (node of pms.filteredNodes(); track node.node_id) {
                <tr 
                  (click)="pms.selectNode(node.node_id)"
                  class="hover:bg-slate-50/75 transition-colors cursor-pointer group"
                  [ngClass]="{'bg-blue-50/30': pms.selectedNodeId() === node.node_id}">
                  
                  <!-- Host Name & Node ID -->
                  <td class="py-3.5 px-4">
                    <div class="font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                      {{ node.host_name }}
                    </div>
                    <div class="text-[11px] font-mono text-slate-400">
                      {{ node.node_id }}
                    </div>
                  </td>

                  <!-- Role -->
                  <td class="py-3.5 px-4 whitespace-nowrap">
                    <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700">
                      {{ pms.formatText(node.role) }}
                    </span>
                  </td>

                  <!-- Locality & Cluster -->
                  <td class="py-3.5 px-4 font-mono text-slate-700">
                    <div>{{ node.region_locality }}</div>
                    <div class="text-[11px] text-slate-400">{{ node.cluster_name }}</div>
                  </td>

                  <!-- Slots -->
                  <td class="py-3.5 px-4 font-mono">
                    <span class="font-bold text-blue-600">{{ node.active_workers }}</span>
                    <span class="text-slate-400"> / {{ node.allocated_slots }} slots</span>
                  </td>

                  <!-- CPU & Memory -->
                  <td class="py-3.5 px-4 font-mono">
                    <div class="font-semibold text-slate-800">{{ node.cpu_utilization_pct }}% CPU</div>
                    <div class="text-[11px] text-slate-400">{{ node.memory_used_mb }} / {{ node.memory_total_mb }} MB</div>
                  </td>

                  <!-- Health & Status -->
                  <td class="py-3.5 px-4 whitespace-nowrap">
                    <div class="flex items-center gap-2">
                      <span 
                        class="w-2.5 h-2.5 rounded-full shrink-0"
                        [ngClass]="{
                          'bg-emerald-500': node.health === 'HEALTHY',
                          'bg-amber-500': node.health === 'DEGRADED',
                          'bg-rose-500': node.health === 'UNHEALTHY',
                          'bg-slate-400': node.health === 'UNKNOWN'
                        }">
                      </span>
                      <span class="font-medium text-slate-800">{{ pms.formatText(node.status) }}</span>
                    </div>
                  </td>

                  <!-- Action -->
                  <td class="py-3.5 px-4 whitespace-nowrap text-right">
                    <button
                      type="button"
                      (click)="pms.selectNode(node.node_id); $event.stopPropagation()"
                      class="h-7 px-2.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs cursor-pointer shadow-2xs transition-colors">
                      Inspect
                    </button>
                  </td>

                </tr>
              }

              @if (pms.filteredNodes().length === 0) {
                <tr>
                  <td colspan="7" class="py-12 text-center text-slate-400 text-xs">
                    No compute nodes match the search or filter criteria.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- 2. Selected Node Detail (Lazy Drill-Down with Assigned Workers) -->
      @if (pms.selectedNode(); as node) {
        <div class="p-5 rounded-2xl bg-white border border-blue-200 shadow-sm flex flex-col gap-5 animate-in fade-in duration-100">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
              <div>
                <h3 class="text-base font-bold text-slate-900 tracking-tight font-heading">{{ node.host_name }}</h3>
                <span class="text-xs font-mono text-slate-500">{{ node.node_id }} • {{ node.region_locality }}</span>
              </div>
            </div>
            
            <button
              type="button"
              (click)="pms.selectNode(null)"
              class="h-7 px-2.5 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-medium cursor-pointer">
              Close Detail ✕
            </button>
          </div>

          <!-- Node Metrics Grid -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Node Role</span>
              <span class="font-semibold text-slate-900">{{ pms.formatText(node.role) }}</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Uptime</span>
              <span class="font-mono font-bold text-slate-900">{{ node.uptime_hours }} hours</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Slot Capacity</span>
              <span class="font-mono font-bold text-blue-600">{{ node.active_workers }} active / {{ node.allocated_slots }} max</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Heartbeat</span>
              <span class="font-mono text-slate-700">{{ node.last_heartbeat | date:'HH:mm:ss' }} (Current)</span>
            </div>
          </div>

          <!-- Allocated Workers on this Node -->
          <div class="flex flex-col gap-3 pt-2">
            <div class="flex items-center justify-between">
              <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Allocated Workers on this Node</h4>
              <span class="text-xs text-slate-500">{{ pms.selectedNodeWorkers().length }} assigned workers</span>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs text-slate-600">
                <thead>
                  <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                    <th class="py-2.5 px-3">Worker ID</th>
                    <th class="py-2.5 px-3">Assigned Migration</th>
                    <th class="py-2.5 px-3">Partition</th>
                    <th class="py-2.5 px-3">Processed</th>
                    <th class="py-2.5 px-3">Work Rate</th>
                    <th class="py-2.5 px-3 text-right">Deep Link</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  @for (w of pms.selectedNodeWorkers(); track w.worker_id) {
                    <tr class="hover:bg-slate-50/50 transition-colors">
                      <td class="py-2.5 px-3 font-mono font-bold text-slate-900">{{ w.worker_id }}</td>
                      <td class="py-2.5 px-3 font-medium text-slate-800">
                        {{ w.assigned_migration_name || 'Idle Standby' }}
                      </td>
                      <td class="py-2.5 px-3 font-mono text-slate-600">
                        {{ w.assigned_partition || '—' }}
                      </td>
                      <td class="py-2.5 px-3 font-mono font-semibold text-slate-800">
                        {{ w.rows_processed_count | number }}
                      </td>
                      <td class="py-2.5 px-3 font-mono text-slate-700">
                        {{ w.work_rate_label }}
                      </td>
                      <td class="py-2.5 px-3 text-right">
                        @if (w.assigned_migration_id) {
                          <a
                            [routerLink]="['/monitoring/migrations', w.assigned_migration_id, 'overview']"
                            class="font-semibold text-blue-600 hover:text-blue-700 cursor-pointer">
                            Inspect Migration →
                          </a>
                        } @else {
                          <span class="text-slate-400">Idle</span>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

        </div>
      }

      <!-- 3. Distributed Leases & CAS Fencing -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Distributed Leases &amp; CAS Fencing</h3>
          </div>
          <span class="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">All Leases Protected</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                <th class="py-2.5 px-3">Protected Resource</th>
                <th class="py-2.5 px-3">Owner Node</th>
                <th class="py-2.5 px-3">Fencing Epoch</th>
                <th class="py-2.5 px-3">Expires In</th>
                <th class="py-2.5 px-3 text-right">Lease Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (lease of pms.leases(); track lease.lease_id) {
                <tr class="hover:bg-slate-50/50 transition-colors">
                  <td class="py-2.5 px-3 font-mono font-bold text-slate-900">{{ lease.resource_name }}</td>
                  <td class="py-2.5 px-3 font-mono text-slate-700">{{ lease.owner_node_id }}</td>
                  <td class="py-2.5 px-3 font-mono font-semibold text-slate-800">Generation #{{ lease.fencing_epoch }}</td>
                  <td class="py-2.5 px-3 font-mono text-slate-600">{{ lease.expires_in_sec }}s (Duration: {{ lease.lease_duration_sec }}s)</td>
                  <td class="py-2.5 px-3 text-right whitespace-nowrap">
                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                      {{ lease.state }} • Active CAS
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
export class PlatformInfrastructureTabComponent {
  public pms = inject(PlatformMonitoringService);

  public roleOptions: CustomSelectOption[] = [
    { label: 'All Roles', value: 'ALL', desc: 'Show all cluster compute roles' },
    { label: 'Coordinator', value: 'COORDINATOR', desc: 'Orchestration & scheduling leader' },
    { label: 'Worker Node', value: 'WORKER_NODE', desc: 'Data stream & batch processing worker' },
    { label: 'Primary Compute', value: 'PRIMARY_COMPUTE', desc: 'High-memory transformation host' },
    { label: 'Edge Gateway', value: 'EDGE_GATEWAY', desc: 'Ingress & egress transport gateway' }
  ];
}
