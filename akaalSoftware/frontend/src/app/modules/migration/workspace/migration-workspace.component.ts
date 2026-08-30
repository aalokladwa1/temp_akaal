import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ProgressBarModule } from 'primeng/progressbar';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { StatusBadgeComponent } from '../components/status-badge.component';
import { DagViewerComponent } from '../components/dag-viewer.component';
import { RiskConfirmationDialogComponent, ConfirmationTier } from '../components/risk-confirmation-dialog.component';

@Component({
  selector: 'app-migration-workspace',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    TableModule,
    TagModule,
    ProgressBarModule,
    LucideIconComponent,
    StatusBadgeComponent,
    DagViewerComponent,
    RiskConfirmationDialogComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto pb-20 font-sans select-none animate-in fade-in duration-150">
      
      <!-- =============================================================== -->
      <!-- TIER 1: IDENTITY, TELEMETRY RIBBON & LIFECYCLE CONTROLS (29)   -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
        
        <div class="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-slate-100">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <a routerLink="/migration" class="text-xs font-semibold text-blue-600 hover:underline">Migration Portfolio</a>
              <span class="text-slate-300">/</span>
              <span class="text-xs font-semibold text-slate-700">{{ activeMigration()?.projectName ?? 'Independent' }}</span>
            </div>
            <div class="flex items-center gap-3">
              <h1 class="text-xl font-bold font-heading text-slate-900">{{ activeMigration()?.name }}</h1>
              <app-status-badge [lifecycle]="currentLifecycleState()"></app-status-badge>
              <app-status-badge [mode]="activeMigration()?.mode"></app-status-badge>
            </div>
          </div>

          <!-- Lifecycle Action Controls Bar -->
          <div class="flex items-center gap-2">
            @if (currentLifecycleState() === 'ACTIVE' || currentLifecycleState() === 'RUNNING') {
              <button
                type="button"
                (click)="triggerLifecycleAction('PAUSE')"
                class="h-9 px-3.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-colors flex items-center gap-1.5 cursor-pointer">
                <app-lucide-icon name="pause" [size]="14"></app-lucide-icon>
                <span>Pause</span>
              </button>

              <button
                type="button"
                (click)="triggerLifecycleAction('CUTOVER')"
                class="h-9 px-4 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer">
                <app-lucide-icon name="lock" [size]="14"></app-lucide-icon>
                <span>Authorize Cutover</span>
              </button>
            } @else if (currentLifecycleState() === 'PAUSED') {
              <button
                type="button"
                (click)="triggerLifecycleAction('RESUME')"
                class="h-9 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer">
                <app-lucide-icon name="play" [size]="14"></app-lucide-icon>
                <span>Resume Execution</span>
              </button>
            }

            <button
              type="button"
              (click)="triggerLifecycleAction('TERMINATE')"
              class="h-9 px-3 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold border border-rose-200 transition-colors flex items-center gap-1.5 cursor-pointer">
              <app-lucide-icon name="square" [size]="13"></app-lucide-icon>
              <span>Terminate</span>
            </button>
          </div>
        </div>

        <!-- Mode-Specific Telemetry Ribbon -->
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-0.5">
            <span class="text-[10px] font-bold text-slate-500 uppercase">Throughput</span>
            <span class="text-base font-bold text-slate-900 font-mono">{{ currentLifecycleState() === 'PAUSED' ? '0 rows/s (Paused)' : '142,500 rows/s' }}</span>
          </div>
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-0.5">
            <span class="text-[10px] font-bold text-slate-500 uppercase">CDC Replica Lag</span>
            <span class="text-base font-bold text-emerald-600 font-mono">{{ cdcLag() }} ms (SLA &lt;500ms)</span>
          </div>
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-0.5">
            <span class="text-[10px] font-bold text-slate-500 uppercase">Spool Buffer</span>
            <span class="text-base font-bold text-slate-900 font-mono">14 MB / 2 GB</span>
          </div>
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-0.5">
            <span class="text-[10px] font-bold text-slate-500 uppercase">Checkpoint Age</span>
            <span class="text-base font-bold text-slate-900 font-mono">1.2s fresh</span>
          </div>
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-0.5">
            <span class="text-[10px] font-bold text-slate-500 uppercase">Active Workers</span>
            <span class="text-base font-bold text-blue-700 font-mono">{{ currentLifecycleState() === 'PAUSED' ? '0' : '16' }} / 16 threads</span>
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- TIER 2: LIVE EXECUTION DAG (CYTOSCAPE) (30)                     -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h2 class="text-sm font-bold text-slate-900">Live Execution DAG &amp; Barrier Topology</h2>
            <p class="text-xs text-slate-500 font-medium">Coordinated task execution graph with active ApprovalBarriers.</p>
          </div>
        </div>

        <app-dag-viewer [plan]="ms.activeExecutionPlan()"></app-dag-viewer>
      </div>

      <!-- =============================================================== -->
      <!-- TIER 3: ACTIVE OPERATION WORKBENCH (MORPHS BY MODE) (31)        -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h2 class="text-sm font-bold text-slate-900">Active Operation Stream: Bulk + CDC Catchup Pipeline</h2>
            <p class="text-xs text-slate-500 font-medium">Real-time partition status, LogMiner tailing stream, and write ring buffer.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
            <span class="font-bold text-slate-800">1. LogMiner Capture Engine</span>
            <span class="text-slate-500">Current SCN: 48291048201</span>
            <span class="text-emerald-700 font-bold">100% Caught Up</span>
          </div>
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
            <span class="font-bold text-slate-800">2. In-Memory Ring Buffer</span>
            <span class="text-slate-500">Queue Depth: 12 transactions</span>
            <span class="text-blue-700 font-bold">0% Spill to Disk</span>
          </div>
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
            <span class="font-bold text-slate-800">3. PostgreSQL Applier</span>
            <span class="text-slate-500">Target LSN: 0/1A8F290</span>
            <span class="text-emerald-700 font-bold">All 64 Partitions Active</span>
          </div>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- TIER 4: RUNTIME HEALTH METRICS (32)                             -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
          <span class="text-xs font-bold text-slate-500">Host Memory Pool</span>
          <span class="text-lg font-bold text-slate-900">2.4 GB / 8.0 GB</span>
        </div>
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
          <span class="text-xs font-bold text-slate-500">Spill Storage Headroom</span>
          <span class="text-lg font-bold text-slate-900">148 GB Free</span>
        </div>
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
          <span class="text-xs font-bold text-slate-500">Network IOPS</span>
          <span class="text-lg font-bold text-slate-900">18.4 MB/s</span>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- TIER 5: DIAGNOSTIC CONSOLE & LOG STREAM (33)                    -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-slate-200 shadow-xs flex flex-col gap-3 font-mono text-xs">
        <div class="flex items-center justify-between pb-2 border-b border-slate-800">
          <span class="font-bold text-slate-300">Live Diagnostic Stream</span>
          <span class="text-slate-500 text-[10px]">auto-scroll active</span>
        </div>

        <div class="flex flex-col gap-1.5 max-h-48 overflow-y-auto text-[11px] text-slate-400">
          @for (log of logMessages(); track log) {
            <p>{{ log }}</p>
          }
        </div>
      </div>

      <!-- Risk Confirmation Dialog -->
      <app-risk-confirmation-dialog
        [isOpen]="isRiskDialogOpen()"
        [tier]="riskTier"
        [title]="riskTitle"
        [description]="riskDesc"
        [impactDetails]="riskImpacts"
        (confirm)="onConfirmRisk()"
        (cancel)="isRiskDialogOpen.set(false)">
      </app-risk-confirmation-dialog>

    </div>
  `
})
export class MigrationWorkspaceComponent {
  public ms = inject(MigrationUiService);
  private route = inject(ActivatedRoute);

  public activeMigration = this.ms.activeMigration;
  public currentLifecycleState = signal<any>('ACTIVE');
  public cdcLag = signal<number>(12);
  public pendingAction = signal<string>('');

  public logMessages = signal<string[]>([
    '[09:32:01] [INFO] CDC tailer committed SCN 48291048201 to target WAL stream.',
    '[09:32:04] [INFO] Worker #4 flushed partition chunk 42 (100,000 rows committed).',
    '[09:32:08] [WARN] Cutover barrier awaiting second L4 signature from SecOps lead.'
  ]);

  public isRiskDialogOpen = signal<boolean>(false);
  public riskTier: ConfirmationTier = 'IMPORTANT';
  public riskTitle = '';
  public riskDesc = '';
  public riskImpacts: string[] = [];

  constructor() {
    this.route.params.subscribe(params => {
      if (params['migrationId']) {
        this.ms.selectedMigrationId.set(params['migrationId']);
        const mig = this.ms.activeMigration();
        if (mig) {
          this.currentLifecycleState.set(mig.lifecycleState);
        }
      }
    });
  }

  public triggerLifecycleAction(action: string): void {
    this.pendingAction.set(action);
    if (action === 'CUTOVER') {
      this.riskTier = 'GOVERNED';
      this.riskTitle = 'Authorize Final Cutover & Quiesce Source';
      this.riskDesc = 'This operation enforces source write quiescence, executes final catchup commit, and flips authority to PostgreSQL.';
      this.riskImpacts = [
        'Source database will enter read-only maintenance mode',
        'Final CDC transactions will flush to target in ~12ms',
        'Requires 2 L4 operator sign-offs'
      ];
      this.isRiskDialogOpen.set(true);
    } else if (action === 'PAUSE') {
      this.riskTier = 'NORMAL';
      this.riskTitle = 'Pause Migration Stream';
      this.riskDesc = 'Active worker partitions and CDC capture will pause checkpoints cleanly.';
      this.riskImpacts = ['No data loss', 'Can be resumed at any time'];
      this.isRiskDialogOpen.set(true);
    } else if (action === 'RESUME') {
      this.currentLifecycleState.set('ACTIVE');
      this.logMessages.update(msgs => [...msgs, `[${new Date().toLocaleTimeString()}] [INFO] Resumed execution stream across all 16 workers.`]);
      this.updatePortfolioState('ACTIVE');
    } else if (action === 'TERMINATE') {
      this.riskTier = 'DESTRUCTIVE';
      this.riskTitle = 'Terminate Migration Execution';
      this.riskDesc = 'Terminating will cancel active workers and abort replication.';
      this.riskImpacts = ['Worker pipelines will stop immediately', 'Target state will remain at last checkpoint'];
      this.isRiskDialogOpen.set(true);
    }
  }

  public onConfirmRisk(): void {
    this.isRiskDialogOpen.set(false);
    const action = this.pendingAction();
    if (action === 'PAUSE') {
      this.currentLifecycleState.set('PAUSED');
      this.logMessages.update(msgs => [...msgs, `[${new Date().toLocaleTimeString()}] [CHECKPOINT] Migration paused at Checkpoint #48,210.`]);
      this.updatePortfolioState('PAUSED');
    } else if (action === 'CUTOVER') {
      this.currentLifecycleState.set('COMPLETED');
      this.logMessages.update(msgs => [...msgs, `[${new Date().toLocaleTimeString()}] [SUCCESS] Cutover authorized and completed. Source quiesced, target promoted.`]);
      this.updatePortfolioState('COMPLETED');
    } else if (action === 'TERMINATE') {
      this.currentLifecycleState.set('FAILED');
      this.logMessages.update(msgs => [...msgs, `[${new Date().toLocaleTimeString()}] [ERROR] Migration terminated by operator.`]);
      this.updatePortfolioState('CANCELLED');
    }
  }

  private updatePortfolioState(state: any): void {
    const id = this.ms.selectedMigrationId();
    this.ms.portfolioMigrations.update(list =>
      list.map(m => m.id === id ? { ...m, lifecycleState: state } : m)
    );
  }
}
