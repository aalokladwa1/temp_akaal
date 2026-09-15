import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InfrastructureFleetReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-infrastructure-fleet-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Fleet Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          INFRASTRUCTURE &amp; FLEET INVENTORY SUMMARY
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Cluster Nodes</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.fleet_summary.total_nodes }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Active Workers</span>
            <span class="text-base font-bold font-mono text-emerald-700">{{ payload.fleet_summary.active_workers }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Draining Nodes</span>
            <span class="text-base font-bold font-mono" [ngClass]="payload.fleet_summary.draining_nodes > 0 ? 'text-amber-700' : 'text-slate-900'">
              {{ payload.fleet_summary.draining_nodes }}
            </span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Capacity Utilization</span>
            <span class="text-base font-bold font-mono text-blue-700">{{ payload.fleet_summary.cluster_capacity_utilization_pct }}%</span>
          </div>
        </div>
      </div>

      <!-- Node Inventory Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          WORKER NODE INVENTORY
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Node ID</th>
                <th class="py-3 px-4">Role</th>
                <th class="py-3 px-4 text-right">Assigned Workloads</th>
                <th class="py-3 px-4 text-right">CPU Load</th>
                <th class="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (node of payload.node_inventory; track node.node_id) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-mono font-semibold text-slate-900 text-[11px]">
                    {{ node.node_id }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                    {{ node.role }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-900">
                    {{ node.assigned_workloads }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                    {{ node.cpu_utilization_pct }}%
                  </td>
                  <td class="py-3.5 px-4 text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': node.status === 'HEALTHY',
                        'bg-amber-50 text-amber-800 border border-amber-200': node.status === 'DEGRADED',
                        'bg-rose-50 text-rose-700 border border-rose-200': node.status === 'OFFLINE'
                      }">
                      {{ node.status }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Workload Placement Table (If applicable) -->
      @if (payload.workload_placement && payload.workload_placement.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            WORKLOAD PLACEMENT &amp; LEASE BINDINGS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Workload Name</th>
                  <th class="py-3 px-4">Assigned Worker Node</th>
                  <th class="py-3 px-4 text-right">Lease Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (wp of payload.workload_placement; track wp.workload_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ wp.workload_name }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px]">
                      {{ wp.assigned_node }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border border-emerald-200': wp.lease_status === 'ACTIVE',
                          'bg-amber-50 text-amber-800 border border-amber-200': wp.lease_status === 'EXPIRED',
                          'bg-rose-50 text-rose-700 border border-rose-200': wp.lease_status === 'FENCED'
                        }">
                        {{ wp.lease_status }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

    </div>
  `
})
export class InfrastructureFleetReportBodyComponent {
  @Input({ required: true }) public payload!: InfrastructureFleetReportPayload;
}
