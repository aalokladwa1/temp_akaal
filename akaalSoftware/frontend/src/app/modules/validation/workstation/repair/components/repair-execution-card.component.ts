import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from '../validation-repair.service';
import { ExecutionDimension } from '../validation-repair.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-execution-card',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 lg:p-7 shadow-2xs flex flex-col gap-6">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-slate-100">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
            <app-lucide-icon name="play-circle" [size]="15"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-0.5">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              5. Controlled Execution &amp; Provider-Native Recovery
            </h2>
            <p class="text-[11.5px] text-slate-500">
              Governed mutating pipeline with atomic transaction fencing and P7B placement telemetry
            </p>
          </div>
        </div>

        @if (store.execution(); as exec) {
          <div class="flex items-center gap-2">
            <span [ngClass]="getExecutionBadgeClass(exec.state)"
                  class="px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider border flex items-center gap-1.5">
              <app-lucide-icon [name]="getExecutionIcon(exec.state)" [size]="12"></app-lucide-icon>
              <span>{{ formatExecutionState(exec.state) }}</span>
            </span>
          </div>
        }
      </div>

      <!-- Execution Content -->
      @if (store.execution(); as exec) {
        <div class="flex flex-col gap-6">
          
          <!-- UNKNOWN Commit Outcome Warning Banner (CRITICAL ARCHITECTURAL LAW) -->
          @if (exec.state === 'OUTCOME_UNKNOWN' || exec.providerCommitState === 'UNKNOWN') {
            <div class="p-5 rounded-xl bg-rose-50 border border-rose-200 flex flex-col gap-3.5 text-rose-900 shadow-2xs">
              <div class="flex items-start gap-3.5">
                <div class="w-10 h-10 rounded-xl bg-rose-100 border border-rose-300 flex items-center justify-center text-rose-700 shrink-0 mt-0.5">
                  <app-lucide-icon name="alert-triangle" [size]="22"></app-lucide-icon>
                </div>
                <div class="flex flex-col gap-1">
                  <h3 class="text-xs font-bold font-heading uppercase tracking-wider text-rose-800">
                    Critical Law: Ambiguous Target Commit Outcome
                  </h3>
                  <p class="text-xs leading-relaxed text-rose-900/90 font-medium">
                    {{ exec.unknownOutcomeWarning || 'The target mutation was submitted, but acknowledgement was lost. Automatic replay is withheld until provider-native verification resolves ambiguity.' }}
                  </p>
                </div>
              </div>

              <div class="p-3.5 rounded-lg bg-white/90 border border-rose-200 text-[11.5px] text-rose-800 flex flex-col gap-1.5">
                <div class="flex items-center gap-2">
                  <span class="font-bold">Execution Error:</span>
                  <span class="font-mono text-rose-950">{{ exec.errorMessage || 'Provider socket timeout during commit' }}</span>
                </div>
                <span class="italic text-rose-700 leading-relaxed">Blind retry prohibited: Replay without verification risks double-application of non-idempotent mutations.</span>
              </div>
            </div>
          }

          <!-- Execution Metrics Grid -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            
            <!-- Operations in Scope -->
            <div class="p-4 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-1.5">
              <div class="flex items-center gap-1.5 text-slate-600">
                <app-lucide-icon name="layers" [size]="13"></app-lucide-icon>
                <span class="text-[10.5px] font-bold uppercase tracking-wider">Total Operations</span>
              </div>
              <span class="text-xl font-mono font-bold text-slate-900">{{ exec.totalOperations }}</span>
              <span class="text-[10.5px] text-slate-400">Mutating actions</span>
            </div>

            <!-- Applied Successfully -->
            <div class="p-4 rounded-xl bg-emerald-50/40 border border-emerald-200 flex flex-col gap-1.5">
              <div class="flex items-center gap-1.5 text-emerald-800">
                <app-lucide-icon name="check-circle-2" [size]="13"></app-lucide-icon>
                <span class="text-[10.5px] font-bold uppercase tracking-wider">Applied Count</span>
              </div>
              <span class="text-xl font-mono font-bold text-emerald-700">{{ exec.appliedCount }}</span>
              <span class="text-[10.5px] text-emerald-600">Confirmed on provider</span>
            </div>

            <!-- Unresolved Count -->
            <div class="p-4 rounded-xl bg-amber-50/40 border border-amber-200 flex flex-col gap-1.5">
              <div class="flex items-center gap-1.5 text-amber-800">
                <app-lucide-icon name="clock" [size]="13"></app-lucide-icon>
                <span class="text-[10.5px] font-bold uppercase tracking-wider">Unresolved Operations</span>
              </div>
              <span class="text-xl font-mono font-bold text-amber-700">{{ exec.unresolvedCount }}</span>
              <span class="text-[10.5px] text-amber-600">Awaiting dispatch</span>
            </div>

            <!-- Unknown Outcome -->
            <div class="p-4 rounded-xl border flex flex-col gap-1.5"
                 [ngClass]="exec.unknownOutcomeCount > 0 ? 'bg-rose-50 border-rose-200 text-rose-900' : 'bg-slate-50/80 border-slate-200 text-slate-800'">
              <div class="flex items-center gap-1.5" [ngClass]="exec.unknownOutcomeCount > 0 ? 'text-rose-800' : 'text-slate-600'">
                <app-lucide-icon [name]="exec.unknownOutcomeCount > 0 ? 'alert-triangle' : 'shield-check'" [size]="13"></app-lucide-icon>
                <span class="text-[10.5px] font-bold uppercase tracking-wider">Unknown Outcome</span>
              </div>
              <span class="text-xl font-mono font-bold" [ngClass]="exec.unknownOutcomeCount > 0 ? 'text-rose-700' : 'text-slate-900'">
                {{ exec.unknownOutcomeCount }}
              </span>
              <span class="text-[10.5px]" [ngClass]="exec.unknownOutcomeCount > 0 ? 'text-rose-600' : 'text-slate-400'">
                Unverified commits
              </span>
            </div>

          </div>

          <!-- P7B Fabric Telemetry & Distributed Placement -->
          @if (exec.p7bContext; as p7b) {
            <div class="p-4.5 sm:p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-3.5 text-xs shadow-2xs">
              <div class="flex items-center justify-between flex-wrap gap-2 pb-2.5 border-b border-slate-200">
                <span class="font-bold text-slate-800 flex items-center gap-2">
                  <app-lucide-icon name="server" [size]="14" class="text-slate-500"></app-lucide-icon>
                  <span>P7B Distributed Placement &amp; Ownership Fencing</span>
                </span>
                <span class="font-mono text-[11px] text-slate-500">Status: {{ p7b.recoveryStatus }}</span>
              </div>

              <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-slate-700">
                <div class="flex flex-col gap-1">
                  <div class="flex items-center gap-1.5 text-slate-500">
                    <app-lucide-icon name="server" [size]="11"></app-lucide-icon>
                    <span class="text-[10px] uppercase font-bold tracking-wider">Execution Site</span>
                  </div>
                  <span class="font-mono font-bold text-slate-900 text-xs">{{ p7b.site }}</span>
                </div>
                <div class="flex flex-col gap-1">
                  <div class="flex items-center gap-1.5 text-slate-500">
                    <app-lucide-icon name="globe" [size]="11"></app-lucide-icon>
                    <span class="text-[10px] uppercase font-bold tracking-wider">Placement</span>
                  </div>
                  <span class="font-mono font-medium text-slate-800 text-xs">{{ p7b.placement }}</span>
                </div>
                <div class="flex flex-col gap-1">
                  <div class="flex items-center gap-1.5 text-slate-500">
                    <app-lucide-icon name="map-pin" [size]="11"></app-lucide-icon>
                    <span class="text-[10px] uppercase font-bold tracking-wider">Data Residency</span>
                  </div>
                  <span class="font-mono font-medium text-slate-800 text-xs">{{ p7b.residency }}</span>
                </div>
                <div class="flex flex-col gap-1">
                  <div class="flex items-center gap-1.5 text-slate-500">
                    <app-lucide-icon name="key" [size]="11"></app-lucide-icon>
                    <span class="text-[10px] uppercase font-bold tracking-wider">Ownership Lease</span>
                  </div>
                  <span class="font-mono text-[11px] text-blue-700 font-bold">{{ p7b.ownershipFencing }}</span>
                </div>
              </div>
            </div>
          }

          <!-- Consequential Action Bar -->
          <div class="p-4.5 sm:p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-2xs">
            <div class="flex flex-col gap-1">
              <span class="text-xs font-bold text-slate-900 font-heading">
                {{ canExecute() ? 'Authorized for Controlled Target Dispatch' : 'Target Execution Withheld' }}
              </span>
              <p class="text-[11.5px] text-slate-500">
                {{ getExecutionActionSubtext() }}
              </p>
            </div>

            <div class="flex items-center gap-3 shrink-0">
              @if (canExecute()) {
                <button
                  type="button"
                  (click)="store.openConfirmModal()"
                  [ngClass]="store.proposal()?.operationFamily === 'DELETE_EXTRA_TARGET' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'"
                  class="h-9 px-4 rounded-lg text-white text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors shadow-2xs">
                  <app-lucide-icon [name]="store.proposal()?.operationFamily === 'DELETE_EXTRA_TARGET' ? 'trash-2' : 'play'" [size]="13"></app-lucide-icon>
                  <span>{{ store.proposal()?.operationFamily === 'DELETE_EXTRA_TARGET' ? 'Execute Destructive Deletion' : 'Apply Controlled Repair' }}</span>
                </button>
              } @else if (exec.state === 'COMPLETED') {
                <span class="px-3.5 py-2 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold flex items-center gap-1.5">
                  <app-lucide-icon name="check-circle-2" [size]="14"></app-lucide-icon>
                  <span>Repair Dispatched &amp; Confirmed</span>
                </span>
              } @else {
                <button
                  type="button"
                  disabled
                  class="h-9 px-4 rounded-lg bg-slate-100 border border-slate-200 text-slate-400 text-xs font-semibold flex items-center gap-2 cursor-not-allowed opacity-75">
                  <app-lucide-icon name="lock" [size]="13"></app-lucide-icon>
                  <span>Apply Controlled Repair (Disabled)</span>
                </button>
              }
            </div>
          </div>

        </div>
      } @else {
        <!-- Execution Unavailable State -->
        <div class="p-10 rounded-xl bg-slate-50 border border-slate-200 text-center flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500">
            <app-lucide-icon name="play-circle" [size]="22"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800 font-heading">Controlled Repair Executor Unavailable</span>
          <p class="text-xs text-slate-500 max-w-md leading-relaxed">
            Controlled repair execution is not currently available. The current validation runtime is strictly read-only.
          </p>
        </div>
      }

    </section>
  `
})
export class RepairExecutionCardComponent {
  readonly store = inject(ValidationRepairService);

  canExecute(): boolean {
    const gov = this.store.governance();
    const exec = this.store.execution();
    const prop = this.store.proposal();
    return !!(gov?.isAuthorized && exec?.state === 'NOT_STARTED' && prop && exec?.providerCommitState !== 'UNKNOWN');
  }

  getExecutionActionSubtext(): string {
    const gov = this.store.governance();
    const exec = this.store.execution();
    if (exec?.state === 'COMPLETED') return 'Target mutation succeeded. Post-repair revalidation in Validation #11 is active.';
    if (exec?.state === 'OUTCOME_UNKNOWN') return 'Target commit state is unknown. Automatic execution replay is withheld.';
    if (gov?.state === 'REJECTED') return 'Proposal was rejected during governance review.';
    if (gov?.isAuthorized) return 'All preconditions and signatures verified. Ready for controlled execution.';
    return 'Execution requires cryptographic plan authorization and quorum satisfaction.';
  }

  formatExecutionState(state: ExecutionDimension): string {
    switch (state) {
      case 'COMPLETED': return 'Completed';
      case 'RUNNING': return 'Running';
      case 'SCHEDULED': return 'Scheduled';
      case 'INTERRUPTED': return 'Interrupted';
      case 'OUTCOME_UNKNOWN': return 'Outcome Unknown (Ambiguous)';
      case 'FAILED': return 'Execution Failed';
      case 'NOT_STARTED': return 'Not Started';
      default: return state;
    }
  }

  getExecutionBadgeClass(state: ExecutionDimension): string {
    switch (state) {
      case 'COMPLETED': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'RUNNING': return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'OUTCOME_UNKNOWN':
      case 'FAILED':
      case 'INTERRUPTED': return 'bg-rose-50 border-rose-200 text-rose-800';
      default: return 'bg-slate-100 border-slate-200 text-slate-700';
    }
  }

  getExecutionIcon(state: ExecutionDimension): string {
    switch (state) {
      case 'COMPLETED': return 'check-circle-2';
      case 'RUNNING': return 'play-circle';
      case 'OUTCOME_UNKNOWN':
      case 'FAILED':
      case 'INTERRUPTED': return 'alert-triangle';
      default: return 'clock';
    }
  }
}
