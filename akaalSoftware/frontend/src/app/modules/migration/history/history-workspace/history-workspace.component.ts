import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { HistoryWorkspaceService } from './history-workspace.service';
import { HistoryWorkspaceTab } from './history-workspace.models';

// Shell Components
import { HistoryWorkspaceHeaderComponent } from './components/history-workspace-header.component';
import { HistoryWorkspaceNavComponent } from './components/history-workspace-nav.component';

// All 10 Tab Components
import { TabHistoryOverviewComponent } from './tabs/tab-history-overview.component';
import { TabHistoryTimelineComponent } from './tabs/tab-history-timeline.component';
import { TabHistoryExecutionComponent } from './tabs/tab-history-execution.component';
import { TabHistoryPlanComponent } from './tabs/tab-history-plan.component';
import { TabHistoryGovernanceComponent } from './tabs/tab-history-governance.component';
import { TabHistoryValidationComponent } from './tabs/tab-history-validation.component';
import { TabHistoryCutoverComponent } from './tabs/tab-history-cutover.component';
import { TabHistoryRecoveryComponent } from './tabs/tab-history-recovery.component';
import { TabHistoryEvidenceComponent } from './tabs/tab-history-evidence.component';
import { TabHistoryAuditComponent } from './tabs/tab-history-audit.component';

@Component({
  selector: 'app-history-workspace',
  standalone: true,
  imports: [
    CommonModule,
    HistoryWorkspaceHeaderComponent,
    HistoryWorkspaceNavComponent,
    TabHistoryOverviewComponent,
    TabHistoryTimelineComponent,
    TabHistoryExecutionComponent,
    TabHistoryPlanComponent,
    TabHistoryGovernanceComponent,
    TabHistoryValidationComponent,
    TabHistoryCutoverComponent,
    TabHistoryRecoveryComponent,
    TabHistoryEvidenceComponent,
    TabHistoryAuditComponent
  ],
  template: `
    <div class="min-h-screen bg-slate-50 flex flex-col">
      
      <!-- Loading Skeleton View -->
      @if (hws.viewState() === 'LOADING') {
        <div class="p-6 space-y-4 max-w-7xl mx-auto w-full">
          <div class="h-24 bg-white rounded-lg border border-slate-200 animate-pulse"></div>
          <div class="h-10 bg-white rounded-lg border border-slate-200 animate-pulse"></div>
          <div class="h-96 bg-white rounded-lg border border-slate-200 animate-pulse"></div>
        </div>
      }

      <!-- Error View -->
      @else if (hws.viewState() === 'ERROR') {
        <div class="p-8 max-w-2xl mx-auto my-auto text-center">
          <div class="bg-white border border-rose-200 rounded-lg p-8 shadow-xs">
            <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-rose-100 text-rose-700 text-xl font-bold mb-3">&times;</div>
            <h2 class="text-base font-bold text-slate-900">Historical Record Unavailable</h2>
            <p class="text-xs text-slate-500 mt-1 mb-4">{{ hws.errorMessage() || 'Failed to load historical workspace.' }}</p>
            <div class="flex items-center justify-center gap-3">
              <button
                type="button"
                (click)="hws.retry()"
                class="h-8 px-4 rounded-md bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-colors cursor-pointer">
                Retry
              </button>
              <button
                type="button"
                (click)="navigateToHistoryHome()"
                class="h-8 px-4 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors cursor-pointer">
                Back to History Home
              </button>
            </div>
          </div>
        </div>
      }

      <!-- Ready State: Header, Tabs, and Selected Destination Panel -->
      @else if (hws.currentRecord()) {
        <!-- Top Authoritative Workspace Header -->
        <app-history-workspace-header />

        <!-- 10-Tab Navigation Bar -->
        <app-history-workspace-nav />

        <!-- Main Workspace Tab Content Container -->
        <div class="flex-1 px-6 py-6 max-w-7xl w-full mx-auto" role="region" aria-label="Historical Reconstruction Tab Content">
          
          <!-- Tab 1: Overview -->
          <div
            role="tabpanel"
            id="panel-overview"
            aria-labelledby="tab-overview"
            [hidden]="hws.activeTab() !== 'overview'">
            @if (hws.activeTab() === 'overview') {
              <app-tab-history-overview />
            }
          </div>

          <!-- Tab 2: Timeline -->
          <div
            role="tabpanel"
            id="panel-timeline"
            aria-labelledby="tab-timeline"
            [hidden]="hws.activeTab() !== 'timeline'">
            @if (hws.activeTab() === 'timeline') {
              <app-tab-history-timeline />
            }
          </div>

          <!-- Tab 3: Execution -->
          <div
            role="tabpanel"
            id="panel-execution"
            aria-labelledby="tab-execution"
            [hidden]="hws.activeTab() !== 'execution'">
            @if (hws.activeTab() === 'execution') {
              <app-tab-history-execution />
            }
          </div>

          <!-- Tab 4: Plan & Configuration -->
          <div
            role="tabpanel"
            id="panel-plan"
            aria-labelledby="tab-plan"
            [hidden]="hws.activeTab() !== 'plan'">
            @if (hws.activeTab() === 'plan') {
              <app-tab-history-plan />
            }
          </div>

          <!-- Tab 5: Approvals & Governance -->
          <div
            role="tabpanel"
            id="panel-governance"
            aria-labelledby="tab-governance"
            [hidden]="hws.activeTab() !== 'governance'">
            @if (hws.activeTab() === 'governance') {
              <app-tab-history-governance />
            }
          </div>

          <!-- Tab 6: Validation & Reconciliation -->
          <div
            role="tabpanel"
            id="panel-validation"
            aria-labelledby="tab-validation"
            [hidden]="hws.activeTab() !== 'validation'">
            @if (hws.activeTab() === 'validation') {
              <app-tab-history-validation />
            }
          </div>

          <!-- Tab 7: Cutover & Continuity -->
          <div
            role="tabpanel"
            id="panel-cutover"
            aria-labelledby="tab-cutover"
            [hidden]="hws.activeTab() !== 'cutover'">
            @if (hws.activeTab() === 'cutover') {
              <app-tab-history-cutover />
            }
          </div>

          <!-- Tab 8: Recovery -->
          <div
            role="tabpanel"
            id="panel-recovery"
            aria-labelledby="tab-recovery"
            [hidden]="hws.activeTab() !== 'recovery'">
            @if (hws.activeTab() === 'recovery') {
              <app-tab-history-recovery />
            }
          </div>

          <!-- Tab 9: Evidence -->
          <div
            role="tabpanel"
            id="panel-evidence"
            aria-labelledby="tab-evidence"
            [hidden]="hws.activeTab() !== 'evidence'">
            @if (hws.activeTab() === 'evidence') {
              <app-tab-history-evidence />
            }
          </div>

          <!-- Tab 10: Audit Trail -->
          <div
            role="tabpanel"
            id="panel-audit"
            aria-labelledby="tab-audit"
            [hidden]="hws.activeTab() !== 'audit'">
            @if (hws.activeTab() === 'audit') {
              <app-tab-history-audit />
            }
          </div>

        </div>
      }

    </div>
  `
})
export class HistoryWorkspaceComponent implements OnInit, OnDestroy {
  public hws = inject(HistoryWorkspaceService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  private subs: Subscription = new Subscription();

  ngOnInit(): void {
    // Subscribe to Route Param changes (migrationId and tab)
    this.subs.add(
      this.route.params.subscribe(params => {
        const migrationId = params['migrationId'] || 'mig-fin-core-01';
        this.hws.loadMigration(migrationId);

        const tab = params['tab'] as HistoryWorkspaceTab;
        if (tab && this.isValidTab(tab)) {
          this.hws.setActiveTab(tab);
        }
      })
    );

    // Subscribe to Query Param tab overrides (?tab=...)
    this.subs.add(
      this.route.queryParams.subscribe(qp => {
        const qpTab = qp['tab'] as HistoryWorkspaceTab;
        if (qpTab && this.isValidTab(qpTab)) {
          this.hws.setActiveTab(qpTab);
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  public navigateToHistoryHome(): void {
    const isMigrationPrefix = this.router.url.startsWith('/migration');
    this.router.navigate([isMigrationPrefix ? '/migration/history' : '/history']);
  }

  private isValidTab(tab: string): boolean {
    const validTabs: HistoryWorkspaceTab[] = [
      'overview',
      'timeline',
      'execution',
      'plan',
      'governance',
      'validation',
      'cutover',
      'recovery',
      'evidence',
      'audit'
    ];
    return validTabs.includes(tab as HistoryWorkspaceTab);
  }
}
