import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationHealthDTO } from '../../models/migration-monitoring.models';
import { formatSnakeToTitle } from '../../models/monitoring.models';

@Component({
  selector: 'app-migration-health-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. 7-Dimensional Composed State Matrix -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">7-Dimensional Composed Health Model</h3>
          </div>
          <span class="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">All Nominal</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          @for (dim of health.composed_states; track dim.dimension) {
            <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between gap-2">
              <div class="flex flex-col gap-1">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-bold text-slate-900">{{ dim.dimension }}</span>
                  <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                </div>
                <span class="text-xs font-semibold text-emerald-700">{{ dim.state_label }}</span>
              </div>
              <p class="text-[11px] text-slate-500 leading-relaxed">{{ dim.detail }}</p>
            </div>
          }
        </div>
      </div>

      <!-- 2. Source & Target Endpoint Health Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Source Endpoint -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 uppercase">Source</span>
              <h4 class="text-sm font-bold text-slate-900">{{ health.source_endpoint.provider }}</h4>
            </div>
            <span class="flex items-center gap-1.5 text-xs text-slate-700 font-medium">
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
              {{ health.source_endpoint.health }}
            </span>
          </div>

          <div class="flex flex-col gap-2 text-xs">
            <div class="flex items-center justify-between p-2 rounded bg-slate-50">
              <span class="text-slate-500">Instance:</span>
              <span class="font-mono font-semibold text-slate-800">{{ health.source_endpoint.instance }}</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-slate-50">
              <span class="text-slate-500">Driver &amp; Auth:</span>
              <span class="font-semibold text-slate-800">{{ health.source_endpoint.auth_status }} • {{ health.source_endpoint.reachability }}</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-slate-50">
              <span class="text-slate-500">Connection Pool:</span>
              <span class="font-mono font-semibold text-slate-800">{{ health.source_endpoint.pool_active_connections }} / {{ health.source_endpoint.pool_max_connections }}</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-slate-50">
              <span class="text-slate-500">Network RTT Latency:</span>
              <span class="font-mono font-bold text-emerald-700">{{ health.source_endpoint.rtt_latency_ms }} ms</span>
            </div>
          </div>
        </div>

        <!-- Target Endpoint -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase">Target</span>
              <h4 class="text-sm font-bold text-slate-900">{{ health.target_endpoint.provider }}</h4>
            </div>
            <span class="flex items-center gap-1.5 text-xs text-slate-700 font-medium">
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
              {{ health.target_endpoint.health }}
            </span>
          </div>

          <div class="flex flex-col gap-2 text-xs">
            <div class="flex items-center justify-between p-2 rounded bg-slate-50">
              <span class="text-slate-500">Instance:</span>
              <span class="font-mono font-semibold text-slate-800">{{ health.target_endpoint.instance }}</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-slate-50">
              <span class="text-slate-500">Driver &amp; Auth:</span>
              <span class="font-semibold text-slate-800">{{ health.target_endpoint.auth_status }} • {{ health.target_endpoint.reachability }}</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-slate-50">
              <span class="text-slate-500">Connection Pool:</span>
              <span class="font-mono font-semibold text-slate-800">{{ health.target_endpoint.pool_active_connections }} / {{ health.target_endpoint.pool_max_connections }}</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded bg-slate-50">
              <span class="text-slate-500">Network RTT Latency:</span>
              <span class="font-mono font-bold text-emerald-700">{{ health.target_endpoint.rtt_latency_ms }} ms</span>
            </div>
          </div>
        </div>

      </div>

      <!-- 3. External Dependencies -->
      @if (health.external_dependencies.length > 0) {
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">External Infrastructure Dependencies</h3>
            <span class="text-xs text-slate-500 font-medium">{{ health.external_dependencies.length }} dependencies</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            @for (dep of health.external_dependencies; track dep.id) {
              <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1.5 text-xs">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-slate-900">{{ dep.name }}</span>
                  <span class="flex items-center gap-1.5 text-slate-700 font-medium">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    {{ dep.health }}
                  </span>
                </div>
                <div class="text-[11px] font-medium text-slate-500">{{ formatText(dep.category) }}</div>
                <p class="text-slate-600 pt-1 border-t border-slate-100">{{ dep.summary }}</p>
              </div>
            }
          </div>
        </div>
      }

    </div>
  `
})
export class MigrationHealthTabComponent {
  @Input({ required: true }) health!: MigrationHealthDTO;

  public formatText = formatSnakeToTitle;
}

