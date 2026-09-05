import { Component, Input, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FleetClusterSummary } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-fleet-cluster',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between gap-6 shadow-xs h-full flex-1 overflow-hidden">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="server" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Fleet / Cluster</h2>
        </div>
        <span class="text-xs text-slate-500 font-medium">Topology</span>
      </div>

      <!-- Main Content -->
      @if (!fleet) {
        <div class="py-8 flex flex-col items-center justify-center text-center gap-2 my-auto">
          <app-lucide-icon name="server" [size]="24" class="text-slate-400"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-800">Fleet information unavailable</span>
          <p class="text-[11px] text-slate-500 font-medium">Detailed fleet operations are configured in Monitoring.</p>
        </div>
      } @else {
        <!-- Flattened 3-Column Inline Stats -->
        <div class="grid grid-cols-3 divide-x divide-slate-200 p-4 rounded-xl bg-slate-50/70 border border-slate-200 text-center my-auto">
          <div class="px-3 flex flex-col items-center gap-1">
            <span class="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Nodes</span>
            <span class="text-2xl font-bold font-mono text-slate-900 tabular-nums">{{ fleet.nodeCount ?? '—' }}</span>
          </div>

          <div class="px-3 flex flex-col items-center gap-1">
            <span class="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Workers</span>
            <span class="text-2xl font-bold font-mono text-slate-900 tabular-nums">{{ fleet.activeWorkers ?? '—' }}</span>
          </div>

          <div class="px-3 flex flex-col items-center gap-1">
            <span class="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Cores</span>
            <span class="text-2xl font-bold font-mono text-slate-900 tabular-nums">{{ fleet.totalCapacityCores ?? '—' }}</span>
          </div>
        </div>

        <!-- Distinct Separated Summary Footer Bar -->
        <div class="flex items-center justify-between text-xs text-slate-600 font-medium border-t border-slate-200 bg-slate-50/70 -mx-7 -mb-7 px-7 py-3 rounded-b-2xl">
          <div class="flex items-center gap-2 truncate max-w-[280px]">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Topology</span>
            <span class="text-xs text-slate-700 font-medium truncate">{{ fleet.detail }}</span>
          </div>
          
          @if (fleet.clusterState === 'healthy') {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 select-none">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Healthy</span>
            </span>
          } @else if (fleet.clusterState === 'degraded') {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 select-none">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
              <span>Degraded</span>
            </span>
          } @else {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 select-none">
              <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
              <span>Unconfigured</span>
            </span>
          }
        </div>
      }

    </div>
  `
})
export class FleetClusterComponent {
  @HostBinding('class') public hostClass = 'flex flex-col h-full flex-1';
  @Input() public fleet: FleetClusterSummary | null = null;
}
