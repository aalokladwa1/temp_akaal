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
    <div class="flex flex-col gap-8 lg:gap-9 w-full max-w-[1680px] mx-auto font-sans pb-16 transition-all duration-300 ease-in-out">
      
      <!-- =============================================================== -->
      <!-- TOP GREETING AREA (PREMIUM REFINED)                             -->
      <!-- =============================================================== -->
      <div class="flex items-start justify-between gap-6 pb-4 border-b border-slate-200 flex-wrap">
        
        <!-- Left: Local Time Greeting & Deterministic Curated Phrase -->
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">
            {{ ds.greetingContext().greeting }}
          </h1>
          <p class="text-sm text-slate-600 font-medium">
            {{ ds.greetingContext().statePhrase }}
          </p>
        </div>

        <!-- Right: Contextual Live Meta -->
        <div class="flex items-center gap-3.5 pt-1 text-sm">
          <span class="text-slate-600 font-medium text-xs">{{ ds.greetingContext().formattedDate }}</span>
          <span class="text-slate-300">&bull;</span>
          <div class="flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-slate-200/90 text-xs font-semibold text-slate-800 shadow-2xs">
            <span class="w-2 h-2 rounded-full" [class.bg-emerald-500]="ipc.connectionState() === 'connected'" [class.bg-amber-500]="ipc.connectionState() === 'connecting'" [class.bg-rose-500]="ipc.connectionState() === 'disconnected'"></span>
            <span>{{ ipc.connectionState() === 'connected' ? 'Live' : (ipc.connectionState() === 'connecting' ? 'Connecting' : 'Offline') }}</span>
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- ROW 1: FOUR ESTATE SUMMARY METRICS                             -->
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
      <!-- ROW 2: ACTIVE MIGRATIONS (2fr) & NEEDS YOUR ATTENTION (1fr)     -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-12 gap-6 items-start">
        <div class="col-span-12 lg:col-span-8">
          <app-active-migrations
            [migrations]="ds.dashboardData().activeMigrations">
          </app-active-migrations>
        </div>

        <div class="col-span-12 lg:col-span-4">
          <app-attention-queue
            [items]="ds.dashboardData().attentionItems">
          </app-attention-queue>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 3: PLATFORM STATUS (2fr) & PENDING APPROVALS (1fr)          -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-12 gap-6 items-start">
        <div class="col-span-12 lg:col-span-7">
          <app-platform-status
            [subsystems]="ds.dashboardData().subsystems">
          </app-platform-status>
        </div>

        <div class="col-span-12 lg:col-span-5">
          <app-pending-approvals
            [approvals]="ds.dashboardData().pendingApprovals">
          </app-pending-approvals>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 4: CAPACITY (2fr) & ALERTS / INCIDENTS (1fr)                -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-12 gap-6 items-start">
        <div class="col-span-12 lg:col-span-7">
          <app-capacity-summary
            [metrics]="ds.dashboardData().capacityMetrics">
          </app-capacity-summary>
        </div>

        <div class="col-span-12 lg:col-span-5">
          <app-alerts-incidents
            [incidents]="ds.dashboardData().incidents">
          </app-alerts-incidents>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 5: FLEET / CLUSTER (2fr) & SECURITY / COMPLIANCE (1fr)      -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-12 gap-6 items-start">
        <div class="col-span-12 lg:col-span-6">
          <app-fleet-cluster
            [fleet]="ds.dashboardData().fleet">
          </app-fleet-cluster>
        </div>

        <div class="col-span-12 lg:col-span-6">
          <app-security-compliance
            [security]="ds.dashboardData().security">
          </app-security-compliance>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- ROW 6: RECENT ACTIVITY TIMELINE (FULL WIDTH)                    -->
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
