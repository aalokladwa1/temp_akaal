/**
 * AKAAL Monitoring — Part 4 of 4: Correlation Tab Component
 * Multi-dimensional signal chain, cross-entity relationships, correlated telemetry,
 * and temporal co-occurrence analysis.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AlertsMonitoringService } from '../../services/alerts-monitoring.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-alerts-correlation-tab',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Correlation Context Header Card -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-start justify-between gap-4 flex-wrap pb-3 border-b border-slate-100">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs font-mono font-bold text-purple-700 bg-purple-50 px-2.5 py-0.5 rounded border border-purple-200/60">
                Correlation ID: {{ ams.correlation().correlation_id }}
              </span>
              <span class="text-xs font-mono text-slate-500">
                Trace ID: {{ ams.correlation().trace_id }}
              </span>
            </div>
            <h2 class="text-lg font-bold text-slate-900 tracking-tight">Signal Correlation & Propagation Chain</h2>
          </div>

          <div class="flex items-center gap-2">
            <span class="px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              High Graph Confidence (96%)
            </span>
          </div>
        </div>

        <p class="text-xs text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
          {{ ams.correlation().correlation_summary }}
        </p>
      </div>

      <!-- 2. Multi-tier Signal Propagation Chain -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-5">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="git-branch" [size]="16" class="text-blue-600"></app-lucide-icon>
            <h3 class="text-sm font-bold text-slate-900">Cascade Signal Propagation Chain</h3>
          </div>
          <span class="text-[11px] text-slate-400 font-mono">Root Cause &rarr; Active Incident</span>
        </div>

        <!-- Node Sequence Strip -->
        <div class="grid grid-cols-1 md:grid-cols-5 gap-3 relative">
          @for (node of ams.correlation().signal_chain; track node.id; let idx = $index; let last = $last) {
            <div class="relative p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col justify-between gap-2 group hover:border-blue-300 transition-colors">
              
              <div class="flex items-center justify-between gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <span>Tier {{ idx + 1 }}: {{ node.level }}</span>
                <span 
                  class="w-2 h-2 rounded-full shrink-0"
                  [ngClass]="{
                    'bg-rose-500': node.status === 'CRITICAL' || node.status === 'SATURATED',
                    'bg-amber-500': node.status === 'DEGRADED' || node.status === 'WARNING' || node.status === 'FIRING',
                    'bg-blue-500': node.status === 'ACTIVE' || node.status === 'OPEN'
                  }">
                </span>
              </div>

              <div class="flex flex-col gap-0.5 my-1">
                <span class="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition-colors">{{ node.label }}</span>
                <span class="text-[11px] font-mono text-slate-500">{{ node.id }}</span>
              </div>

              <div class="pt-2 border-t border-slate-200/60 flex items-center justify-between">
                <span class="text-[10px] font-bold text-slate-700 bg-white px-1.5 py-0.5 rounded border border-slate-200">
                  {{ node.status }}
                </span>

                @if (node.deep_link) {
                  <button
                    type="button"
                    (click)="onNavigate(node.deep_link)"
                    class="text-[11px] font-bold text-blue-600 hover:text-blue-800 cursor-pointer">
                    Inspect &rarr;
                  </button>
                }
              </div>

            </div>
          }
        </div>
      </div>

      <!-- 3. Two-Column Split: Related Entities + Correlated Telemetry -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        <!-- Left: Correlated Entities Roster (6 Cols) -->
        <div class="lg:col-span-6 p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="layers" [size]="16" class="text-blue-600"></app-lucide-icon>
              <h3 class="text-sm font-bold text-slate-900">Correlated Topology Resources</h3>
            </div>
            <span class="text-xs font-mono font-bold text-slate-600">{{ ams.correlation().related_entities.length }} entities</span>
          </div>

          <div class="flex flex-col gap-2.5">
            @for (entity of ams.correlation().related_entities; track entity.id) {
              <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                  <span 
                    class="w-2.5 h-2.5 rounded-full shrink-0"
                    [ngClass]="{
                      'bg-emerald-500': entity.health === 'HEALTHY',
                      'bg-amber-500': entity.health === 'DEGRADED',
                      'bg-rose-500': entity.health === 'UNHEALTHY'
                    }">
                  </span>

                  <div class="flex flex-col gap-0.5">
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-bold text-slate-900">{{ entity.name }}</span>
                      <span class="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-slate-200 text-slate-700">
                        {{ ams.formatText(entity.type) }}
                      </span>
                    </div>
                    <span class="text-[11px] text-slate-500">{{ entity.role }}</span>
                  </div>
                </div>

                <button
                  type="button"
                  (click)="onNavigate(entity.deep_link)"
                  class="h-7 px-2.5 rounded-md bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold text-xs inline-flex items-center gap-1 cursor-pointer transition-colors shadow-2xs shrink-0">
                  <span>View</span>
                  <app-lucide-icon name="arrow-up-right" [size]="12"></app-lucide-icon>
                </button>
              </div>
            }
          </div>
        </div>

        <!-- Right: Correlated Telemetry & Temporal Co-occurrence (6 Cols) -->
        <div class="lg:col-span-6 flex flex-col gap-6">
          
          <!-- Telemetry Snapshots -->
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
            <div class="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="activity" [size]="16" class="text-amber-600"></app-lucide-icon>
                <h3 class="text-sm font-bold text-slate-900">Coincident Telemetry Metrics</h3>
              </div>
              <span class="text-xs font-mono text-slate-500">Live Snapshot</span>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs border-collapse">
                <thead>
                  <tr class="border-b border-slate-200 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <th class="py-2 px-3">Metric</th>
                    <th class="py-2 px-3">Observed Value</th>
                    <th class="py-2 px-3">Timestamp</th>
                    <th class="py-2 px-3">Anomaly</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  @for (tel of ams.correlation().related_telemetry; track tel.metric) {
                    <tr class="hover:bg-slate-50">
                      <td class="py-2.5 px-3 font-mono font-medium text-slate-800">{{ tel.metric }}</td>
                      <td class="py-2.5 px-3 font-mono font-bold" [ngClass]="tel.anomaly ? 'text-rose-600' : 'text-slate-700'">
                        {{ tel.value }}
                      </td>
                      <td class="py-2.5 px-3 font-mono text-slate-400 text-[11px]">{{ tel.timestamp | date:'HH:mm:ss' }}</td>
                      <td class="py-2.5 px-3">
                        @if (tel.anomaly) {
                          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">ANOMALOUS</span>
                        } @else {
                          <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">NOMINAL</span>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <!-- Temporal Events -->
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
            <div class="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="clock" [size]="16" class="text-slate-600"></app-lucide-icon>
                <h3 class="text-sm font-bold text-slate-900">Temporal Co-occurrence Sequence</h3>
              </div>
            </div>

            <div class="flex flex-col gap-2.5">
              @for (evt of ams.correlation().temporal_events; track evt.timestamp) {
                <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex items-start gap-3 text-xs">
                  <span 
                    class="w-2 h-2 rounded-full shrink-0 mt-1"
                    [ngClass]="{
                      'bg-rose-500': evt.severity === 'CRITICAL',
                      'bg-amber-500': evt.severity === 'WARNING',
                      'bg-blue-500': evt.severity === 'INFO'
                    }">
                  </span>
                  <div class="flex flex-col gap-0.5">
                    <div class="flex items-center gap-2 text-[11px]">
                      <span class="font-mono text-slate-400">{{ evt.timestamp | date:'HH:mm:ss' }}</span>
                      <span class="font-bold text-slate-700">{{ evt.source }}</span>
                    </div>
                    <span class="text-slate-600">{{ evt.message }}</span>
                  </div>
                </div>
              }
            </div>
          </div>

        </div>

      </div>

    </div>
  `
})
export class AlertsCorrelationTabComponent {
  public ams = inject(AlertsMonitoringService);
  private router = inject(Router);

  public onNavigate(route: string): void {
    if (route) {
      this.router.navigateByUrl(route);
    }
  }
}
