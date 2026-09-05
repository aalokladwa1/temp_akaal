import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { IpcService } from '../../core/services/ipc.service';
import { MetricSurfaceComponent } from './components/metric-surface.component';
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
      <div class="flex items-start justify-between gap-6 pb-4 border-b border-slate-200 flex-wrap">
        
        <!-- Left: Local Time Greeting & State Phrase -->
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">
            {{ ds.greetingContext().greeting }}
          </h1>
          <p class="text-sm text-slate-600 font-medium">
            {{ ds.greetingContext().statePhrase }}
          </p>
        </div>

        <!-- Right: Contextual Live Meta (Formatted with comma, year, and GDS Live Badge) -->
        <div class="flex items-center gap-3 pt-1 text-sm">
          <span class="text-slate-600 font-medium text-xs">{{ ds.greetingContext().formattedDate }}</span>
          <span class="text-slate-300 font-bold">&middot;</span>
          <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-semibold select-none shadow-2xs"
            [class.bg-emerald-50]="ipc.connectionState() === 'connected'"
            [class.text-emerald-700]="ipc.connectionState() === 'connected'"
            [class.border]="ipc.connectionState() === 'connected'"
            [class.border-emerald-200]="ipc.connectionState() === 'connected'"
            [class.bg-amber-50]="ipc.connectionState() === 'connecting'"
            [class.text-amber-700]="ipc.connectionState() === 'connecting'"
            [class.border-amber-200]="ipc.connectionState() === 'connecting'"
            [class.bg-rose-50]="ipc.connectionState() === 'disconnected'"
            [class.text-rose-700]="ipc.connectionState() === 'disconnected'"
            [class.border-rose-200]="ipc.connectionState() === 'disconnected'">
            <span class="w-1.5 h-1.5 rounded-full" 
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
          [value]="ds.dashboardData().runningCount !== null ? ds.dashboardData().runningCount! : '—'"
          subtext="Active pipelines"
          [isAccent]="(ds.dashboardData().runningCount ?? 0) > 0"
          targetRoute="/migration">
        </app-metric-surface>

        <app-metric-surface
          label="Scheduled"
          [value]="ds.dashboardData().scheduledCount !== null ? ds.dashboardData().scheduledCount! : '—'"
          subtext="Maintenance windows"
          targetRoute="/migration">
        </app-metric-surface>

        <app-metric-surface
          label="Need Attention"
          [value]="ds.dashboardData().attentionCount !== null ? ds.dashboardData().attentionCount! : '—'"
          subtext="Actionable barriers"
          [isWarning]="(ds.dashboardData().attentionCount ?? 0) > 0"
          targetRoute="/migration">
        </app-metric-surface>

        <app-metric-surface
          label="Completed Today"
          [value]="ds.dashboardData().completedTodayCount !== null ? ds.dashboardData().completedTodayCount! : '—'"
          subtext="100% verified"
          targetRoute="/migration">
        </app-metric-surface>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 2: ACTIVE MIGRATIONS (8fr) & NEEDS YOUR ATTENTION (4fr)     -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-12 gap-6 items-stretch">
        <div class="col-span-12 lg:col-span-8 flex flex-col">
          <app-active-migrations
            [migrations]="ds.dashboardData().activeMigrations"
            class="flex-1">
          </app-active-migrations>
        </div>

        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <app-attention-queue
            [items]="ds.dashboardData().attentionItems"
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
            [subsystems]="ds.dashboardData().subsystems"
            class="flex-1">
          </app-platform-status>
        </div>

        <div class="flex flex-col">
          <app-pending-approvals
            [approvals]="ds.dashboardData().pendingApprovals"
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
            [metrics]="ds.dashboardData().capacityMetrics"
            class="flex-1">
          </app-capacity-summary>
        </div>

        <div class="flex flex-col">
          <app-alerts-incidents
            [incidents]="ds.dashboardData().incidents"
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
            [fleet]="ds.dashboardData().fleet"
            class="flex-1">
          </app-fleet-cluster>
        </div>

        <div class="flex flex-col">
          <app-security-compliance
            [security]="ds.dashboardData().security"
            class="flex-1">
          </app-security-compliance>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 6: RECENT ACTIVITY TIMELINE (COMPACT & BOUNDED)             -->
      <!-- =============================================================== -->
      <app-recent-activity
        [events]="ds.dashboardData().recentEvents">
      </app-recent-activity>

    </div>
  `
})
export class DashboardComponent {
  public ds = inject(DashboardService);
  public ipc = inject(IpcService);
}
