import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';
import { MigrationMonitoringService } from './services/migration-monitoring.service';
import { MigrationFleetListComponent } from './components/migration-fleet-list.component';
import { SelectedMigrationHeaderComponent } from './components/selected-migration-header.component';
import { SelectedMigrationNavComponent } from './components/selected-migration-nav.component';
import { MigrationOverviewTabComponent } from './components/tabs/migration-overview-tab.component';
import { MigrationExecutionTabComponent } from './components/tabs/migration-execution-tab.component';
import { MigrationPerformanceTabComponent } from './components/tabs/migration-performance-tab.component';
import { MigrationResourcesTabComponent } from './components/tabs/migration-resources-tab.component';
import { MigrationHealthTabComponent } from './components/tabs/migration-health-tab.component';
import { MigrationReliabilityTabComponent } from './components/tabs/migration-reliability-tab.component';
import { MigrationAlertsTabComponent } from './components/tabs/migration-alerts-tab.component';
import { MigrationDiagnosticsTabComponent } from './components/tabs/migration-diagnostics-tab.component';
import { MigrationTabKey } from './models/migration-monitoring.models';

@Component({
  selector: 'app-migration-monitoring-home',
  standalone: true,
  imports: [
    CommonModule,
    LucideIconComponent,
    MigrationFleetListComponent,
    SelectedMigrationHeaderComponent,
    SelectedMigrationNavComponent,
    MigrationOverviewTabComponent,
    MigrationExecutionTabComponent,
    MigrationPerformanceTabComponent,
    MigrationResourcesTabComponent,
    MigrationHealthTabComponent,
    MigrationReliabilityTabComponent,
    MigrationAlertsTabComponent,
    MigrationDiagnosticsTabComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- =============================================================== -->
      <!-- TOP HEADER (Only rendered in Fleet View)                        -->
      <!-- =============================================================== -->
      @if (!mms.selectedMigrationId()) {
        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">OPERATIONS</span>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Migration Operations</h1>
            <p class="text-sm font-medium text-slate-600">
              Live observability, DAG stage execution telemetry, and runtime health across the active migration fleet.
            </p>
          </div>

          <div class="flex items-center gap-3 pt-1">
            <button
              type="button"
              (click)="mms.refresh()"
              [disabled]="mms.isRefreshing()"
              class="h-9 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 font-medium text-xs inline-flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-2xs disabled:opacity-50 select-none">
              <app-lucide-icon 
                name="refresh-cw" 
                [size]="14" 
                [class.animate-spin]="mms.isRefreshing()">
              </app-lucide-icon>
              <span>{{ mms.isRefreshing() ? 'Refreshing...' : 'Refresh Telemetry' }}</span>
            </button>
          </div>
        </div>
      }

      <!-- Engine / State Unavailable Notice -->
      @if (mms.isUnavailable()) {
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold">{{ mms.errorMessage() || 'Migration telemetry is currently unavailable.' }}</span>
          </div>
          <button
            type="button"
            (click)="mms.initializeState()"
            class="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs cursor-pointer">
            Retry Connection
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- VIEW 1: FLEET LIST VIEW (When No Migration Selected)             -->
      <!-- =============================================================== -->
      @if (!mms.selectedMigrationId()) {
        <app-migration-fleet-list></app-migration-fleet-list>
      }

      <!-- =============================================================== -->
      <!-- VIEW 2: SELECTED MIGRATION WORKSPACE (With 8 Investigation Tabs)-->
      <!-- =============================================================== -->
      @if (mms.selectedMigrationId() && mms.selectedMigration()) {
        <div class="flex flex-col gap-6">
          
          <!-- Contextual Header -->
          <app-selected-migration-header 
            [header]="mms.selectedMigration()!.header">
          </app-selected-migration-header>

          <!-- 8 Investigation Area Navigation Tabs -->
          <app-selected-migration-nav
            [migrationId]="mms.selectedMigrationId()!"
            [alertCount]="mms.selectedMigration()!.alerts.active_alerts.length">
          </app-selected-migration-nav>

          <!-- Active Investigation Tab Body -->
          <div class="pt-2">
            @switch (mms.selectedTab()) {
              @case ('overview') {
                <app-migration-overview-tab
                  [overview]="mms.selectedMigration()!.overview"
                  [header]="mms.selectedMigration()!.header">
                </app-migration-overview-tab>
              }
              @case ('execution') {
                <app-migration-execution-tab
                  [execution]="mms.selectedMigration()!.execution"
                  [header]="mms.selectedMigration()!.header">
                </app-migration-execution-tab>
              }
              @case ('performance') {
                <app-migration-performance-tab
                  [performance]="mms.selectedMigration()!.performance">
                </app-migration-performance-tab>
              }
              @case ('resources') {
                <app-migration-resources-tab
                  [resources]="mms.selectedMigration()!.resources">
                </app-migration-resources-tab>
              }
              @case ('health') {
                <app-migration-health-tab
                  [health]="mms.selectedMigration()!.health">
                </app-migration-health-tab>
              }
              @case ('reliability') {
                <app-migration-reliability-tab
                  [reliability]="mms.selectedMigration()!.reliability">
                </app-migration-reliability-tab>
              }
              @case ('alerts') {
                <app-migration-alerts-tab
                  [alerts]="mms.selectedMigration()!.alerts">
                </app-migration-alerts-tab>
              }
              @case ('diagnostics') {
                <app-migration-diagnostics-tab
                  [diagnostics]="mms.selectedMigration()!.diagnostics">
                </app-migration-diagnostics-tab>
              }
            }
          </div>

        </div>
      }

    </div>
  `
})
export class MigrationMonitoringHomeComponent implements OnInit, OnDestroy {
  public mms = inject(MigrationMonitoringService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private sub?: Subscription;

  ngOnInit(): void {
    this.sub = this.route.params.subscribe(params => {
      const migrationId = params['migrationId'];
      const tab = params['tab'] as MigrationTabKey;

      if (migrationId) {
        this.mms.selectMigration(migrationId);
        if (tab) {
          this.mms.selectTab(tab);
        } else {
          this.mms.selectTab('overview');
        }
      } else {
        this.mms.selectMigration(null);
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
