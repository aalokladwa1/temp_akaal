import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { IpcService } from '../../core/services/ipc.service';
import { MetricSurfaceComponent } from '../../shared/components/metric-surface.component';
import { ActiveMigrationsComponent } from './components/active-migrations.component';
import { AttentionQueueComponent } from './components/attention-queue.component';
import { PlatformStatusComponent } from './components/platform-status.component';
import { PendingApprovalsComponent } from './components/pending-approvals.component';
import { CapacitySummaryComponent } from './components/capacity-summary.component';
import { AlertsIncidentsComponent } from './components/alerts-incidents.component';
import { FleetClusterComponent } from './components/fleet-cluster.component';
import { SecurityComplianceComponent } from './components/security-compliance.component';
import { RecentActivityComponent } from './components/recent-activity.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MetricSurfaceComponent,
    ActiveMigrationsComponent,
    AttentionQueueComponent,
    PlatformStatusComponent,
    PendingApprovalsComponent,
    CapacitySummaryComponent,
    AlertsIncidentsComponent,
    FleetClusterComponent,
    SecurityComplianceComponent,
    RecentActivityComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 transition-all duration-300 ease-in-out">
      
      <!-- =============================================================== -->
      <!-- TOP GREETING AREA (PREMIUM REFINED WITH GDS BADGE)              -->
      <!-- =============================================================== -->
      <div class="flex items-start justify-between gap-6 pb-4 border-b border-slate-200 dark:border-white/[0.08] flex-wrap animate-in fade-in duration-200">
        
        <!-- Left: Local Time Greeting & State Phrase -->
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold font-heading text-slate-900 dark:text-slate-100 tracking-tight">
            {{ ds.greetingContext().greeting }}
          </h1>
          <p class="text-xs sm:text-sm text-slate-600 dark:text-slate-400 font-medium">
            {{ ds.greetingContext().statePhrase }}
          </p>
        </div>

        <!-- Right: Contextual Live Meta (Formatted with comma, year, and GDS Live Badge) -->
        <div class="flex items-center gap-3 pt-1 text-sm">
          <span class="text-slate-600 dark:text-slate-400 font-medium text-xs">{{ ds.greetingContext().formattedDate }}</span>
          <span class="text-slate-300 dark:text-slate-600 font-bold">&middot;</span>
          <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-semibold select-none shadow-2xs border"
            [ngClass]="{
              'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800/40': ipc.connectionState() === 'connected',
              'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800/40': ipc.connectionState() === 'connecting',
              'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-800/40': ipc.connectionState() === 'disconnected'
            }">
            <span class="w-1.5 h-1.5 rounded-full animate-pulse" 
              [class.bg-emerald-500]="ipc.connectionState() === 'connected'" 
              [class.bg-amber-500]="ipc.connectionState() === 'connecting'" 
              [class.bg-rose-500]="ipc.connectionState() === 'disconnected'">
            </span>
            <span>{{ ipc.connectionState() === 'connected' ? 'Live' : (ipc.connectionState() === 'connecting' ? 'Connecting' : 'Offline') }}</span>
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- ROW 1: FOUR ESTATE SUMMARY METRICS (GDS OPTION C)               -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <app-metric-surface
          label="Running"
          [value]="ds.dashboardData()?.runningCount !== null && ds.dashboardData()?.runningCount !== undefined ? ds.dashboardData()!.runningCount! : '—'"
          [isAccent]="(ds.dashboardData()?.runningCount ?? 0) > 0"
          targetRoute="/migration">
        </app-metric-surface>

        <app-metric-surface
          label="Scheduled"
          [value]="ds.dashboardData()?.scheduledCount !== null && ds.dashboardData()?.scheduledCount !== undefined ? ds.dashboardData()!.scheduledCount! : '—'"
          targetRoute="/migration">
        </app-metric-surface>

        <app-metric-surface
          label="Need Attention"
          [value]="ds.dashboardData()?.attentionCount !== null && ds.dashboardData()?.attentionCount !== undefined ? ds.dashboardData()!.attentionCount! : '—'"
          [isWarning]="(ds.dashboardData()?.attentionCount ?? 0) > 0"
          targetRoute="/migration">
        </app-metric-surface>

        <app-metric-surface
          label="Completed Today"
          [value]="ds.dashboardData()?.completedTodayCount !== null && ds.dashboardData()?.completedTodayCount !== undefined ? ds.dashboardData()!.completedTodayCount! : '—'"
          targetRoute="/migration">
        </app-metric-surface>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 2: ACTIVE MIGRATIONS (8fr) & NEEDS YOUR ATTENTION (4fr)     -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-12 gap-6 items-stretch">
        <div class="col-span-12 lg:col-span-8 flex flex-col">
          <app-active-migrations
            [migrations]="ds.dashboardData()?.activeMigrations ?? []"
            class="flex-1">
          </app-active-migrations>
        </div>

        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <app-attention-queue
            [items]="ds.dashboardData()?.attentionItems ?? []"
            class="flex-1">
          </app-attention-queue>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 3: PLATFORM STATUS & PENDING APPROVALS (EQUAL HEIGHT 1:1)   -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        <div class="flex flex-col">
          <app-platform-status
            [subsystems]="ds.dashboardData()?.subsystems ?? []"
            class="flex-1">
          </app-platform-status>
        </div>

        <div class="flex flex-col">
          <app-pending-approvals
            [approvals]="ds.dashboardData()?.pendingApprovals ?? []"
            class="flex-1">
          </app-pending-approvals>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 4: CAPACITY & ALERTS / INCIDENTS (EQUAL HEIGHT 1:1)         -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        <div class="flex flex-col">
          <app-capacity-summary
            [metrics]="ds.dashboardData()?.capacityMetrics ?? []"
            class="flex-1">
          </app-capacity-summary>
        </div>

        <div class="flex flex-col">
          <app-alerts-incidents
            [incidents]="ds.dashboardData()?.incidents ?? []"
            class="flex-1">
          </app-alerts-incidents>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 5: FLEET / CLUSTER & SECURITY / COMPLIANCE (EQUAL HEIGHT)   -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        <div class="flex flex-col">
          <app-fleet-cluster
            [fleet]="ds.dashboardData()?.fleet ?? null"
            class="flex-1">
          </app-fleet-cluster>
        </div>

        <div class="flex flex-col">
          <app-security-compliance
            [security]="ds.dashboardData()?.security ?? null"
            class="flex-1">
          </app-security-compliance>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 6: RECENT ACTIVITY TIMELINE (COMPACT & BOUNDED)             -->
      <!-- =============================================================== -->
      <app-recent-activity
        [events]="ds.dashboardData()?.recentEvents ?? []">
      </app-recent-activity>

    </div>
  `
})
export class DashboardComponent implements OnInit {
  public ds = inject(DashboardService);
  public ipc = inject(IpcService);

  ngOnInit(): void {
    this.ds.refreshDashboard();
  }
}
