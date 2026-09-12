import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { HistoryMode, HistoryOutcome, ValidationReconciliationState } from '../../history-home.models';

@Component({
  selector: 'app-tab-history-overview',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-6">
        
        <!-- Top Row: 3 Primary Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
          
          <!-- Card 1: Execution Outcome & Performance -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-3">
                <span class="text-xs font-bold uppercase tracking-wider text-slate-600">Execution Outcome</span>
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold border"
                  [ngClass]="getOutcomeBadgeClass(record.outcome)">
                  {{ record.outcome }}
                </span>
              </div>
              <div class="text-2xl font-bold text-slate-900 tracking-tight">
                {{ record.totalRowsProcessed.toLocaleString() }}
                <span class="text-xs font-normal text-slate-500">total rows</span>
              </div>
              <p class="text-xs text-slate-500 mt-1">
                Completed in <span class="font-semibold text-slate-700">{{ record.durationString }}</span> at average throughput of <span class="font-semibold text-slate-700">{{ record.throughputFormatted }}</span>.
              </p>
            </div>

            @if (record.errorMessage) {
              <div class="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-md text-xs text-rose-800">
                <div class="font-bold text-rose-900">Execution Error:</div>
                <div class="font-mono text-[11px] mt-0.5">{{ record.errorMessage }}</div>
              </div>
            } @else {
              <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>Lifecycle State:</span>
                <span class="font-semibold text-slate-800">{{ record.lifecycleState }}</span>
              </div>
            }
          </div>

          <!-- Card 2: Validation & Reconciliation Verdict -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-3">
                <span class="text-xs font-bold uppercase tracking-wider text-slate-600">Validation Verdict</span>
                @if (getLatestValidation(record); as val) {
                  <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border"
                    [ngClass]="getValidationBadgeClass(val.verdict)">
                    {{ getValidationLabel(val.verdict) }}
                  </span>
                } @else {
                  <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                    Not Recorded
                  </span>
                }
              </div>

              @if (getLatestValidation(record); as val) {
                <div class="text-2xl font-bold text-slate-900 tracking-tight">
                  {{ val.discrepancyCount }}
                  <span class="text-xs font-normal text-slate-500">discrepancies detected</span>
                </div>
                <p class="text-xs text-slate-500 mt-1">
                  Merkle Tree Parity: 
                  <span class="font-semibold" [ngClass]="val.merkleTreeRootMatch ? 'text-emerald-700' : 'text-rose-700'">
                    {{ val.merkleTreeRootMatch ? 'Exact Hash Match (100%)' : 'Root Hash Mismatch' }}
                  </span>
                </p>
              } @else {
                <div class="text-sm font-medium text-slate-700">Zero Validation Runs</div>
                <p class="text-xs text-slate-400 mt-1">No independent validation assurance was executed.</p>
              }
            </div>

            <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Validation Scope:</span>
              <button 
                type="button" 
                (click)="hws.setActiveTab('validation')" 
                class="font-semibold text-blue-600 hover:text-blue-800 transition-colors cursor-pointer">
                View Details &rarr;
              </button>
            </div>
          </div>

          <!-- Card 3: Evidence & Cryptographic Integrity -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-3">
                <span class="text-xs font-bold uppercase tracking-wider text-slate-600">Evidence Seal</span>
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  SHA-256 Verified
                </span>
              </div>
              <div class="text-2xl font-bold text-slate-900 tracking-tight">
                {{ record.evidence.artifacts.length }}
                <span class="text-xs font-normal text-slate-500">sealed artifacts</span>
              </div>
              <p class="text-xs text-slate-500 mt-1 truncate" [title]="record.evidence.identitySeal.fingerprintSha256">
                Root Digest: <span class="font-mono text-[11px] text-slate-700">{{ record.evidence.identitySeal.fingerprintSha256 }}</span>
              </p>
            </div>

            <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Manifest Completeness:</span>
              <span class="font-semibold text-emerald-700">{{ record.evidence.completeness }}</span>
            </div>
          </div>

        </div>

        <!-- Middle Row: 2 Grouped Detail Cards -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
          
          <!-- Detail Card 1: Migration Identity & Topology Context -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 pb-2 border-b border-slate-100">
              Execution Identity &amp; Topology Context
            </h2>

            <dl class="grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
              <div>
                <dt class="text-slate-600">Migration ID</dt>
                <dd class="font-mono font-medium text-slate-900 mt-0.5">{{ record.migrationId }}</dd>
              </div>
              <div>
                <dt class="text-slate-600">Execution Invocation ID</dt>
                <dd class="font-mono font-medium text-slate-900 mt-0.5">{{ record.executionId }}</dd>
              </div>
              <div>
                <dt class="text-slate-600">Project / Initiative</dt>
                <dd class="font-medium text-slate-900 mt-0.5">{{ record.projectName }}</dd>
              </div>
              <div>
                <dt class="text-slate-600">Lead Operator</dt>
                <dd class="font-medium text-slate-900 mt-0.5">{{ record.operator }}</dd>
              </div>
              <div>
                <dt class="text-slate-600">Source Provider</dt>
                <dd class="font-medium text-slate-900 mt-0.5">{{ record.sourceProvider }}</dd>
              </div>
              <div>
                <dt class="text-slate-600">Target Provider</dt>
                <dd class="font-medium text-slate-900 mt-0.5">{{ record.targetProvider }}</dd>
              </div>
              <div>
                <dt class="text-slate-600">Execution Mode</dt>
                <dd class="font-semibold text-slate-900 mt-0.5">{{ record.mode }}</dd>
              </div>
              <div>
                <dt class="text-slate-600">Started / Completed</dt>
                <dd class="font-medium text-slate-800 mt-0.5">
                  {{ formatDate(record.startedAt) }} &rarr; {{ formatDate(record.completedAt) }}
                </dd>
              </div>
            </dl>
          </div>

          <!-- Detail Card 2: Continuity, Governance & Recovery Posture -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 pb-2 border-b border-slate-100">
              Continuity, Governance &amp; Recovery Posture
            </h2>

            <dl class="grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
              <div>
                <dt class="text-slate-600">Cutover State</dt>
                <dd class="font-medium mt-0.5" [ngClass]="record.cutover.isApplicableToMode ? 'text-slate-900 font-semibold' : 'text-slate-600'">
                  {{ record.cutover.isApplicableToMode ? record.cutover.cutoverStatus : 'Not Applicable to Mode' }}
                </dd>
              </div>
              <div>
                <dt class="text-slate-600">Cutover Downtime</dt>
                <dd class="font-medium text-slate-900 mt-0.5">
                  {{ record.cutover.downtimeSeconds !== null ? record.cutover.downtimeSeconds + ' seconds' : 'N/A' }}
                </dd>
              </div>
              <div>
                <dt class="text-slate-600">Governance Quorum</dt>
                <dd class="font-medium text-slate-900 mt-0.5">
                  @if (record.governance.length > 0) {
                    <span class="text-emerald-700 font-semibold">
                      {{ record.governance[0].quorumSatisfied }}/{{ record.governance[0].quorumRequired }} Dual-Control Satisfied
                    </span>
                  } @else {
                    <span class="text-slate-600">Direct Execution</span>
                  }
                </dd>
              </div>
              <div>
                <dt class="text-slate-600">Recovery Fence Epoch</dt>
                <dd class="font-mono font-medium text-slate-900 mt-0.5">Epoch {{ record.recovery.fenceEpoch }}</dd>
              </div>
              <div>
                <dt class="text-slate-600">Checkpoints Generated</dt>
                <dd class="font-medium text-slate-900 mt-0.5">{{ record.recovery.checkpoints.length }} checkpoints recorded</dd>
              </div>
              <div>
                <dt class="text-slate-600">Failback Preparedness</dt>
                <dd class="font-medium mt-0.5" [ngClass]="record.cutover.failbackReady ? 'text-emerald-700' : 'text-slate-600'">
                  {{ record.cutover.failbackReady ? 'Failback Plan Active' : 'N/A' }}
                </dd>
              </div>
            </dl>
          </div>

        </div>

        <!-- Bottom Row: Material Exceptions or Clean Attestation Banner -->
        @if (record.materialExceptions && record.materialExceptions.length > 0) {
          <div class="bg-rose-50 border border-rose-200 rounded-lg p-4">
            <div class="flex items-center gap-2 text-rose-900 font-bold text-xs uppercase tracking-wider mb-2">
              <span>Material Exceptions &amp; Blockers ({{ record.materialExceptions.length }})</span>
            </div>
            <ul class="divide-y divide-rose-100 text-xs text-rose-800">
              @for (exc of record.materialExceptions; track exc) {
                <li class="py-1.5 font-mono text-[11px]">{{ exc }}</li>
              }
            </ul>
          </div>
        } @else {
          <div class="bg-slate-50 border border-slate-200 rounded-lg p-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">&check;</span>
              <div>
                <div class="text-xs font-bold text-slate-800">Zero Material Exceptions Recorded</div>
                <div class="text-[11px] text-slate-500">Pipeline execution completed within all strict SLA, data safety, and schema parity boundaries.</div>
              </div>
            </div>
            <button 
              type="button" 
              (click)="hws.setActiveTab('evidence')" 
              class="h-7 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 text-xs font-medium transition-colors cursor-pointer">
              Inspect Evidence Manifest
            </button>
          </div>
        }

      </div>
    }
  `
})
export class TabHistoryOverviewComponent {
  public hws = inject(HistoryWorkspaceService);

  public getOutcomeBadgeClass(outcome: HistoryOutcome): string {
    switch (outcome) {
      case 'SUCCEEDED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAILED':
      case 'ABORTED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'RUNNING': return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  public getValidationBadgeClass(state: ValidationReconciliationState): string {
    switch (state) {
      case 'PASSED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'RECONCILED': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'MISMATCHES_DETECTED': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getValidationLabel(state: ValidationReconciliationState): string {
    switch (state) {
      case 'PASSED': return 'Passed';
      case 'RECONCILED': return 'Reconciled';
      case 'MISMATCHES_DETECTED': return 'Mismatch';
      case 'FAILED': return 'Failed';
      case 'SKIPPED': return 'Skipped';
      case 'NOT_CONFIGURED': return 'Not Configured';
      case 'IN_PROGRESS': return 'In Progress';
      default: return state;
    }
  }

  public getLatestValidation(record: any) {
    if (record.validationRuns && record.validationRuns.length > 0) {
      return record.validationRuns[0];
    }
    return null;
  }

  public formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return dateStr;
    }
  }
}
