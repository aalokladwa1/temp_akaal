import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ValidationExecutionState, ValidationVerdict } from '../validation-workstation.models';

@Component({
  selector: 'app-workstation-status-panel',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      
      <!-- Top Zone: Status Glance & Action Bar -->
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-5 pb-5 border-b border-slate-100">
        
        <!-- Left: Status Icon & Descriptive State -->
        <div class="flex items-start gap-4">
          <div [ngClass]="getStatusIconBgClasses()" class="w-12 h-12 rounded-lg flex items-center justify-center shrink-0 border">
            <app-lucide-icon [name]="getStatusIconName()" [size]="22" [class]="getStatusIconColorClasses()" />
          </div>
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2.5 flex-wrap">
              <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">
                {{ getStatusHeading() }}
              </h2>
              <span class="text-slate-300">&middot;</span>
              <span class="text-xs font-semibold text-slate-600">
                {{ getPhaseSubtitle() }}
              </span>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-500">
              <span class="font-medium text-slate-400">Current Phase:</span>
              <span class="font-mono text-slate-800">{{ getTaskDescription() }}</span>
            </div>
          </div>
        </div>

        <!-- Right: Execution Safety Controls -->
        <div class="flex items-center gap-2.5 flex-wrap self-start lg:self-center">
          
          <!-- Run / Start Control -->
          <button
            type="button"
            (click)="store.triggerAction('RUN')"
            [disabled]="store.isProductionDefault() || store.executionState() === 'RUNNING'"
            [ngClass]="store.isProductionDefault() 
              ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer shadow-xs'"
            class="h-9 px-4 text-xs font-semibold rounded-lg border transition-all flex items-center gap-1.5"
            [title]="store.isProductionDefault() ? 'Disabled: Backend engine link pending' : 'Run validation mission'">
            <app-lucide-icon name="play" [size]="13" />
            <span>Run Mission</span>
          </button>

          <!-- Pause Control -->
          <button
            type="button"
            (click)="store.triggerAction('PAUSE')"
            [disabled]="store.isProductionDefault() || store.executionState() !== 'RUNNING'"
            class="h-9 px-3.5 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:border-slate-300 text-slate-700 transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            [title]="store.isProductionDefault() ? 'Disabled: Backend engine link pending' : 'Pause in-flight validation'">
            <app-lucide-icon name="pause" [size]="13" />
            <span>Pause</span>
          </button>

          <!-- Abort / Cancel Control -->
          <button
            type="button"
            (click)="store.triggerAction('ABORT')"
            [disabled]="store.isProductionDefault() || (store.executionState() !== 'RUNNING' && store.executionState() !== 'PAUSED')"
            class="h-9 px-3.5 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:border-rose-300 hover:bg-rose-50 text-slate-700 hover:text-rose-700 transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            [title]="store.isProductionDefault() ? 'Disabled: Backend engine link pending' : 'Abort validation execution'">
            <app-lucide-icon name="x-circle" [size]="13" />
            <span>Abort</span>
          </button>

          <!-- Export Evidence Report Control -->
          <button
            type="button"
            (click)="store.triggerAction('EXPORT')"
            [disabled]="store.isProductionDefault() && !store.state().technicalDrawer.evidenceHash"
            class="h-9 px-3.5 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50 text-slate-700 hover:text-blue-700 transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
            <app-lucide-icon name="file-text" [size]="13" />
            <span>Export Evidence</span>
          </button>
        </div>
      </div>

      <!-- Action Feedback / Boundary Alert Banner -->
      @if (store.actionFeedback(); as feedback) {
        <div class="px-4 py-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-900 text-xs flex items-center gap-2.5 animate-in fade-in duration-150">
          <app-lucide-icon name="info" [size]="15" class="text-blue-600 shrink-0" />
          <span class="font-medium">{{ feedback }}</span>
        </div>
      }

      <!-- Bottom Zone: Collapsible Metric Cards (Rendered ONLY when present) -->
      @if (hasTelemetryMetrics()) {
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          
          <!-- Elapsed Time -->
          @if (store.state().elapsedFormatted) {
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Elapsed Time</span>
              <span class="font-mono text-sm font-bold text-slate-900">{{ store.state().elapsedFormatted }}</span>
            </div>
          }

          <!-- Live Throughput -->
          @if (store.state().throughputFormatted) {
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Verification Rate</span>
              <span class="font-mono text-sm font-bold text-blue-700">{{ store.state().throughputFormatted }}</span>
            </div>
          }

          <!-- Estimated Time Remaining / ETA -->
          @if (store.state().etaFormatted) {
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Progress / ETA</span>
              <span class="font-mono text-sm font-bold text-slate-800">{{ store.state().etaFormatted }}</span>
            </div>
          }

          <!-- Active Parallel Workers -->
          @if (store.state().activeWorkers !== undefined) {
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Worker Threads</span>
              <span class="font-mono text-sm font-bold text-slate-800">{{ store.state().activeWorkers }} Workers</span>
            </div>
          }

          <!-- Checkpoints Completed -->
          @if (store.state().checkpointsCount !== undefined) {
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Checkpoints</span>
              <span class="font-mono text-sm font-bold text-slate-800">{{ store.state().checkpointsCount }} Saved</span>
            </div>
          }
        </div>
      } @else {
        <!-- Truthful notice when no telemetry is connected -->
        <div class="px-4 py-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 text-xs flex items-center justify-between">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="info" [size]="14" class="text-slate-400 shrink-0" />
            <span>Telemetry streaming is inactive. Metric ribbon will display throughput, worker concurrency, and checkpoints when connected to engine.</span>
          </div>
          <span class="text-[11px] font-mono text-slate-400 font-medium">P7D Boundary</span>
        </div>
      }
    </section>
  `
})
export class WorkstationStatusPanelComponent {
  readonly store = inject(ValidationWorkstationService);

  hasTelemetryMetrics(): boolean {
    const s = this.store.state();
    return !!(s.elapsedFormatted || s.throughputFormatted || s.etaFormatted || s.activeWorkers !== undefined || s.checkpointsCount !== undefined);
  }

  getStatusIconBgClasses(): string {
    switch (this.store.executionState()) {
      case 'NOT_CONNECTED': return 'bg-slate-100 border-slate-200';
      case 'QUEUED': return 'bg-blue-50 border-blue-200';
      case 'RUNNING': return 'bg-blue-50 border-blue-200';
      case 'PAUSED': return 'bg-amber-50 border-amber-200';
      case 'INTERRUPTED': return 'bg-amber-50 border-amber-200';
      case 'RECOVERING': return 'bg-purple-50 border-purple-200';
      case 'BLOCKED': return 'bg-rose-50 border-rose-200';
      case 'COMPLETED': return 'bg-emerald-50 border-emerald-200';
    }
  }

  getStatusIconColorClasses(): string {
    switch (this.store.executionState()) {
      case 'NOT_CONNECTED': return 'text-slate-500';
      case 'QUEUED': return 'text-blue-600';
      case 'RUNNING': return 'text-blue-600';
      case 'PAUSED': return 'text-amber-600';
      case 'INTERRUPTED': return 'text-amber-600';
      case 'RECOVERING': return 'text-purple-600';
      case 'BLOCKED': return 'text-rose-600';
      case 'COMPLETED': return 'text-emerald-600';
    }
  }

  getStatusIconName(): string {
    switch (this.store.executionState()) {
      case 'NOT_CONNECTED': return 'activity';
      case 'QUEUED': return 'clock';
      case 'RUNNING': return 'activity';
      case 'PAUSED': return 'pause';
      case 'INTERRUPTED': return 'alert-triangle';
      case 'RECOVERING': return 'refresh-cw';
      case 'BLOCKED': return 'shield-alert';
      case 'COMPLETED': return 'shield-check';
    }
  }

  getStatusHeading(): string {
    switch (this.store.executionState()) {
      case 'NOT_CONNECTED': return 'Validation Standby (Engine Disconnected)';
      case 'QUEUED': return 'Validation Queued for Execution';
      case 'RUNNING': return 'Streaming Validation in Progress';
      case 'PAUSED': return 'Validation Execution Paused';
      case 'INTERRUPTED': return 'Validation Execution Interrupted';
      case 'RECOVERING': return 'Recovering from Checkpoint';
      case 'BLOCKED': return 'Validation Blocked';
      case 'COMPLETED': return 'Validation Execution Concluded';
    }
  }

  getPhaseSubtitle(): string {
    switch (this.store.executionState()) {
      case 'NOT_CONNECTED': return 'Awaiting Canonical Link';
      case 'QUEUED': return 'Worker Allocation Pending';
      case 'RUNNING': return 'Multi-Tier Proof Evaluation';
      case 'PAUSED': return 'Operator Hold';
      case 'INTERRUPTED': return 'Partial Scope Evaluated';
      case 'RECOVERING': return 'State Reconciliation';
      case 'BLOCKED': return 'Configuration Constraint Unmet';
      case 'COMPLETED': return 'Evidence Signed & Sealed';
    }
  }

  getTaskDescription(): string {
    switch (this.store.executionState()) {
      case 'NOT_CONNECTED': return 'Ready for engine daemon initialization via P7D backend.';
      case 'QUEUED': return 'Orchestrator scheduling partition reader tasks.';
      case 'RUNNING': return 'Streaming partition chunks across source and target endpoints.';
      case 'PAUSED': return 'Worker threads safely parked at consistent checkpoint boundaries.';
      case 'INTERRUPTED': return 'Session stopped by operator. No dirty state written.';
      case 'RECOVERING': return 'Verifying WAL checkpoint consistency before resuming.';
      case 'BLOCKED': return 'Action required: Missing endpoint table correspondence mapping.';
      case 'COMPLETED': return 'All scheduled verification tiers executed to completion.';
    }
  }
}
