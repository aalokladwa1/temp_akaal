import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FleetClusterSummary } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-fleet-cluster',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200/90 flex flex-col gap-6 shadow-xs h-full">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="server" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Fleet / Cluster</h2>
        </div>
        <span class="text-xs text-slate-600 font-semibold">Topology</span>
      </div>

      @if (!fleet) {
        <div class="py-12 flex flex-col items-center justify-center text-center gap-2">
          <app-lucide-icon name="server" [size]="24" class="text-slate-400"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-800">Fleet information is not available yet</span>
          <p class="text-[11px] text-slate-600 font-medium">Detailed fleet operations will live under Monitoring.</p>
        </div>
      } @else {
        <div class="grid grid-cols-3 gap-4 text-xs">
          <div class="p-4 rounded-xl bg-slate-50/80 border border-slate-200/60 flex flex-col gap-1">
            <span class="text-xs text-slate-600 font-semibold">Nodes</span>
            <span class="text-xl font-bold text-slate-900">{{ fleet.nodeCount ?? '—' }}</span>
          </div>

          <div class="p-4 rounded-xl bg-slate-50/80 border border-slate-200/60 flex flex-col gap-1">
            <span class="text-xs text-slate-600 font-semibold">Active Workers</span>
            <span class="text-xl font-bold text-slate-900">{{ fleet.activeWorkers ?? '—' }}</span>
          </div>

          <div class="p-4 rounded-xl bg-slate-50/80 border border-slate-200/60 flex flex-col gap-1">
            <span class="text-xs text-slate-600 font-semibold">Total Cores</span>
            <span class="text-xl font-bold text-slate-900">{{ fleet.totalCapacityCores ?? '—' }}</span>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2 text-xs text-slate-600 font-medium border-t border-slate-100">
          <span>Topology: {{ fleet.detail }}</span>
          <span 
            class="px-2.5 py-0.5 rounded-full text-xs font-bold"
            [class.bg-emerald-50]="fleet.clusterState === 'healthy'"
            [class.text-emerald-700]="fleet.clusterState === 'healthy'"
            [class.border]="fleet.clusterState === 'healthy'"
            [class.border-emerald-200]="fleet.clusterState === 'healthy'"
            [class.bg-slate-100]="fleet.clusterState !== 'healthy'"
            [class.text-slate-700]="fleet.clusterState !== 'healthy'">
            {{ fleet.clusterState | uppercase }}
          </span>
        </div>
      }

    </div>
  `
})
export class FleetClusterComponent {
  @Input() public fleet: FleetClusterSummary | null = null;
}
