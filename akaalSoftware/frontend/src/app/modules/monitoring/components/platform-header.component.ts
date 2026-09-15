/**
 * AKAAL Monitoring — Part 3 of 4: Platform Header Component
 * Restrained contextual header for Platform Operations with status indicators,
 * telemetry freshness, deep links to Migration Fleet, and Refresh action.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { PlatformMonitoringService } from '../services/platform-monitoring.service';

@Component({
  selector: 'app-platform-header',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs select-none">
      
      <!-- Top Row: Breadcrumbs & Global Workspace Deep Links -->
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-2 text-xs text-slate-400">
          <a routerLink="/monitoring" class="text-slate-600 hover:text-blue-600 transition-colors font-medium">Monitoring</a>
          <span>/</span>
          <span class="text-slate-900 font-semibold">Platform Operations</span>
        </div>

        <!-- Deep Links & Telemetry Refresh -->
        <div class="flex items-center gap-2.5 flex-wrap">
          <a
            routerLink="/monitoring"
            class="h-8 px-3 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
            <app-lucide-icon name="layout-dashboard" [size]="13" class="text-slate-600"></app-lucide-icon>
            <span>Monitoring Home</span>
          </a>

          <a
            routerLink="/monitoring/migrations"
            class="h-8 px-3 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
            <app-lucide-icon name="layers" [size]="13" class="text-blue-600"></app-lucide-icon>
            <span>Migration Fleet</span>
          </a>

          <a
            routerLink="/monitoring/alerts"
            class="h-8 px-3 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
            <app-lucide-icon name="bell" [size]="13" class="text-slate-600"></app-lucide-icon>
            <span>Alerts</span>
          </a>

          <button
            type="button"
            (click)="pms.refresh()"
            [disabled]="pms.isRefreshing()"
            class="h-8 px-3 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs disabled:opacity-50">
            <app-lucide-icon 
              name="refresh-cw" 
              [size]="13" 
              [class.animate-spin]="pms.isRefreshing()">
            </app-lucide-icon>
            <span>{{ pms.isRefreshing() ? 'Refreshing' : 'Refresh' }}</span>
          </button>
        </div>
      </div>

      <!-- Middle Row: Title, Health Indicator & State Badges -->
      <div class="flex items-start justify-between gap-6 flex-wrap pt-1 border-t border-slate-100">
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center gap-3 flex-wrap">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Platform Operations</h1>
            
            <!-- Overall Health Dot -->
            <div class="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
              <span 
                class="w-2.5 h-2.5 rounded-full shrink-0"
                [ngClass]="{
                  'bg-emerald-500': pms.summary().overall_health === 'HEALTHY',
                  'bg-amber-500': pms.summary().overall_health === 'DEGRADED',
                  'bg-rose-500': pms.summary().overall_health === 'UNHEALTHY',
                  'bg-slate-400': pms.summary().overall_health === 'UNKNOWN'
                }">
              </span>
              <span>Platform {{ pms.formatText(pms.summary().overall_health) }}</span>
            </div>

            <!-- Readiness Badge (Rectangular, clean) -->
            <span class="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
              {{ pms.summary().readiness_state }}
            </span>

            <!-- Liveness Badge -->
            <span class="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              {{ pms.summary().liveness_state }}
            </span>
          </div>

          <p class="text-xs text-slate-500">
            Internal runtime services, multi-engine connectivity, execution fleet, capacity utilization, and system diagnostics.
          </p>
        </div>

        <!-- Telemetry Freshness & Confidence -->
        <div class="flex flex-col items-end gap-1 text-right">
          <div class="flex items-center gap-1.5 text-xs text-slate-500">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Observed {{ pms.lastObservedAt() | date:'HH:mm:ss' }}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 uppercase">
              {{ pms.summary().freshness }}
            </span>
          </div>
          <div class="text-[11px] font-mono text-slate-400">
            Telemetry Confidence: <strong class="text-emerald-600 uppercase font-semibold">{{ pms.telemetryConfidence() }}</strong>
          </div>
        </div>
      </div>

    </div>
  `
})
export class PlatformHeaderComponent {
  public pms = inject(PlatformMonitoringService);
}
