import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MonitoringService } from './services/monitoring.service';
import { MonitoringSummaryStripComponent } from './components/monitoring-summary-strip.component';
import { MonitoringWorkspaceNavComponent } from './components/monitoring-workspace-nav.component';
import { MonitoringNeedsAttentionComponent } from './components/monitoring-needs-attention.component';
import { MonitoringActiveMigrationsComponent } from './components/monitoring-active-migrations.component';
import { MonitoringPlatformHealthComponent } from './components/monitoring-platform-health.component';
import { MonitoringOperationalPressureComponent } from './components/monitoring-operational-pressure.component';
import { MonitoringAlertsComponent } from './components/monitoring-alerts.component';
import { MonitoringRecentEventsComponent } from './components/monitoring-recent-events.component';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-monitoring-home',
  standalone: true,
  imports: [
    CommonModule,
    LucideIconComponent,
    MonitoringSummaryStripComponent,
    MonitoringWorkspaceNavComponent,
    MonitoringNeedsAttentionComponent,
    MonitoringActiveMigrationsComponent,
    MonitoringPlatformHealthComponent,
    MonitoringOperationalPressureComponent,
    MonitoringAlertsComponent,
    MonitoringRecentEventsComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-200">
      
      <!-- =============================================================== -->
      <!-- 0. MONITORING HEADER & TELEMETRY CONTROLS                       -->
      <!-- =============================================================== -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 dark:border-white/[0.08] flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight font-heading">Monitoring Overview</h1>
          <p class="text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-400 max-w-3xl flex items-center gap-2 flex-wrap">
            <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Live Engine Telemetry</span>
            </span>
            <span>
              {{ ms.summary()?.headline_message || (ms.activeMigrationCount() + ' active workloads • All execution paths nominal') }}
            </span>
          </p>
        </div>

        <div class="flex items-center gap-3 pt-1">
          <!-- Refresh Telemetry Button (Secondary Action, Truthful Request) -->
          <button
            type="button"
            (click)="ms.refresh()"
            [disabled]="ms.isRefreshing()"
            class="h-9 px-3.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1a1b1e] hover:bg-slate-50 dark:hover:bg-[#202226] active:bg-slate-100 dark:active:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium text-xs inline-flex items-center justify-center gap-2 cursor-pointer transition-all duration-150 active:scale-[0.98] shadow-2xs disabled:opacity-50 select-none">
            <app-lucide-icon 
              name="refresh-cw" 
              [size]="14" 
              [class.animate-spin]="ms.isRefreshing()">
            </app-lucide-icon>
            <span>{{ ms.isRefreshing() ? 'Refreshing...' : 'Refresh Telemetry' }}</span>
          </button>
        </div>
      </div>

      <!-- Engine / State Unavailable Notice -->
      @if (ms.isUnavailable()) {
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold">{{ ms.errorMessage() || 'The monitoring telemetry engine is currently unavailable.' }}</span>
          </div>
          <button
            type="button"
            (click)="ms.initializeState()"
            class="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs cursor-pointer">
            Retry Connection
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 1. OPERATIONAL SUMMARY (Section 1)                              -->
      <!-- =============================================================== -->
      <app-monitoring-summary-strip></app-monitoring-summary-strip>

      <!-- =============================================================== -->
      <!-- 2. PRIMARY WORKSPACE NAVIGATION (Section 2 - Mandatory)          -->
      <!-- =============================================================== -->
      <app-monitoring-workspace-nav></app-monitoring-workspace-nav>

      <!-- =============================================================== -->
      <!-- 3. NEEDS ATTENTION (Section 3)                                  -->
      <!-- =============================================================== -->
      <app-monitoring-needs-attention></app-monitoring-needs-attention>

      <!-- =============================================================== -->
      <!-- 4. ACTIVE MIGRATIONS (Section 4 - M1-M7 Fleet)                  -->
      <!-- =============================================================== -->
      <app-monitoring-active-migrations></app-monitoring-active-migrations>

      <!-- =============================================================== -->
      <!-- 5. PLATFORM & DATA PATH HEALTH (Section 5)                      -->
      <!-- =============================================================== -->
      <app-monitoring-platform-health></app-monitoring-platform-health>

      <!-- =============================================================== -->
      <!-- 6. OPERATIONAL PRESSURE & HEADROOM (Section 6)                  -->
      <!-- =============================================================== -->
      <app-monitoring-operational-pressure></app-monitoring-operational-pressure>

      <!-- =============================================================== -->
      <!-- 7. INCIDENTS & ALERTS (Section 7)                               -->
      <!-- =============================================================== -->
      <app-monitoring-alerts></app-monitoring-alerts>

      <!-- =============================================================== -->
      <!-- 8. RECENT OPERATIONAL EVENTS (Section 8)                        -->
      <!-- =============================================================== -->
      <app-monitoring-recent-events></app-monitoring-recent-events>

    </div>
  `
})
export class MonitoringHomeComponent implements OnInit {
  public ms = inject(MonitoringService);

  ngOnInit(): void {
    if (this.ms.isLoading()) {
      this.ms.initializeState();
    }
  }
}
