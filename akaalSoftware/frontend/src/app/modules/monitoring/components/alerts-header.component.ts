/**
 * AKAAL Monitoring — Part 4 of 4: Alerts & Incidents Header Component
 * Contextual header for Alerts & Incidents workspace with status indicators,
 * telemetry freshness, global deep links, and Refresh action.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { AlertsMonitoringService } from '../services/alerts-monitoring.service';

@Component({
  selector: 'app-alerts-header',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs select-none">
      
      <!-- Top Row: Breadcrumbs & Global Workspace Deep Links -->
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-2 text-xs text-slate-400">
          <a routerLink="/monitoring" class="text-slate-600 hover:text-blue-600 transition-colors font-medium">Monitoring</a>
          <span>/</span>
          <span class="text-slate-900 font-semibold">Alerts & Incidents</span>
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
            routerLink="/monitoring/platform"
            class="h-8 px-3 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
            <app-lucide-icon name="server" [size]="13" class="text-slate-600"></app-lucide-icon>
            <span>Platform Operations</span>
          </a>

          <button
            type="button"
            (click)="ams.refreshTelemetry()"
            [disabled]="ams.isRefreshing()"
            class="h-8 px-3 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs disabled:opacity-50">
            <app-lucide-icon 
              name="refresh-cw" 
              [size]="13" 
              [class.animate-spin]="ams.isRefreshing()">
            </app-lucide-icon>
            <span>{{ ams.isRefreshing() ? 'Refreshing' : 'Refresh' }}</span>
          </button>
        </div>
      </div>

      <!-- Middle Row: Title, Health Indicator & State Badges -->
      <div class="flex items-start justify-between gap-6 flex-wrap pt-1 border-t border-slate-100">
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center gap-3 flex-wrap">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Alerts & Incidents</h1>
            
            <!-- Overall Health Dot -->
            <div class="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
              <span 
                class="w-2.5 h-2.5 rounded-full shrink-0"
                [ngClass]="{
                  'bg-rose-500': ams.summary().critical_alerts_count > 0,
                  'bg-amber-500': ams.summary().critical_alerts_count === 0 && ams.summary().warning_alerts_count > 0,
                  'bg-emerald-500': ams.summary().total_active_alerts === 0
                }">
              </span>
              <span>
                {{ ams.summary().critical_alerts_count > 0 ? 'Critical Alerts Firing' : (ams.summary().warning_alerts_count > 0 ? 'Warnings Active' : 'All Systems Nominal') }}
              </span>
            </div>

            <!-- Active Incidents Badge -->
            <span class="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200/60">
              {{ ams.summary().active_incidents_count }} Active Incidents
            </span>

            <!-- Active Alerts Badge -->
            <span class="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200/60">
              {{ ams.summary().total_active_alerts }} Active Alerts
            </span>

            <!-- Notification Rate Badge -->
            <span class="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
              {{ ams.summary().notification_success_rate_pct }}% Notification Dispatch
            </span>
          </div>

          <p class="text-xs text-slate-500">
            Real-time rule evaluation, correlated incident response, multi-channel dispatch delivery, and end-to-end operational timeline.
          </p>
        </div>

        <!-- Telemetry Freshness & Confidence -->
        <div class="flex flex-col items-end gap-1 text-right">
          <div class="flex items-center gap-1.5 text-xs text-slate-500">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Observed {{ ams.lastObservedAt() | date:'HH:mm:ss' }}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 uppercase">
              {{ ams.summary().telemetry_confidence }}
            </span>
          </div>
          <div class="text-[11px] font-mono text-slate-400">
            Evaluator Confidence: <strong class="text-emerald-600 uppercase font-semibold">{{ ams.telemetryConfidence() }}</strong>
          </div>
        </div>
      </div>

    </div>
  `
})
export class AlertsHeaderComponent {
  public ams = inject(AlertsMonitoringService);
}
