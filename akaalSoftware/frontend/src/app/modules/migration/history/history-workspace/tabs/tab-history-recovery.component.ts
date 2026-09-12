import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { CheckpointRecord, RecoveryExecutionRecord } from '../history-workspace.models';

@Component({
  selector: 'app-tab-history-recovery',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-6">
        
        <!-- Recovery Posture & Fault Context Banner -->
        <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-100">
            <div>
              <div class="flex items-center gap-2.5">
                <h2 class="text-base font-bold text-slate-900">
                  Checkpoint Lineage &amp; Recovery State
                </h2>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-semibold border"
                  [ngClass]="record.recovery.hasRecoveryOccurred ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'">
                  {{ record.recovery.hasRecoveryOccurred ? 'Recovery Invoked' : 'Zero Recoveries Required' }}
                </span>
              </div>
              <div class="text-xs text-slate-500 mt-1">
                Active Fencing Token: <strong class="font-mono text-slate-800">Epoch {{ record.recovery.fenceEpoch }}</strong>
              </div>
            </div>

            <!-- Total Checkpoints Metric -->
            <div class="flex items-center gap-3 bg-slate-50 px-4 py-2 rounded-md border border-slate-200 self-start md:self-auto">
              <div class="text-right">
                <div class="text-[10px] font-bold uppercase text-slate-500">Persistent Checkpoints</div>
                <div class="text-xs font-bold text-slate-900">
                  {{ record.recovery.checkpoints.length }} State Snapshots Preserved
                </div>
              </div>
            </div>
          </div>

          <!-- Data Safety & Idempotency Attestation -->
          <div class="mt-4 p-3.5 bg-slate-50 rounded-md border border-slate-200 text-xs text-slate-700 flex items-start gap-3">
            <span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 font-bold shrink-0 mt-0.5">&check;</span>
            <div>
              <div class="font-bold text-slate-900">Data Safety &amp; Non-Duplicate Delivery Attestation</div>
              <p class="text-slate-600 mt-0.5">{{ record.recovery.dataSafetyAttestation }}</p>
            </div>
          </div>

          <!-- Fault Trigger Context if Recovery Occurred -->
          @if (record.recovery.hasRecoveryOccurred && record.recovery.recoveryTriggerReason) {
            <div class="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-900">
              <div class="font-bold">Fault Trigger Diagnostic:</div>
              <div class="mt-0.5 font-mono text-[11px]">{{ record.recovery.recoveryTriggerReason }}</div>
              <div class="text-[11px] text-amber-700 mt-1">Triggered at {{ formatTimestamp(record.recovery.recoveryTriggeredAt) }} &bull; Recovered at {{ formatTimestamp(record.recovery.recoveredAt) }}</div>
            </div>
          }
        </div>

        <!-- Checkpoint Lineage Inventory -->
        <div class="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
          <div class="px-5 py-3.5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Checkpoint Lineage ({{ record.recovery.checkpoints.length }})
            </h3>
            <span class="text-xs text-slate-500">Deterministic recovery boundaries</span>
          </div>

          @if (record.recovery.checkpoints.length > 0) {
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse min-w-[700px]">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/50 text-[11px] font-bold text-slate-600 uppercase tracking-wider select-none">
                    <th class="py-2.5 px-4">Checkpoint ID</th>
                    <th class="py-2.5 px-4">Generation</th>
                    <th class="py-2.5 px-4">Associated Pipeline Stage</th>
                    <th class="py-2.5 px-4">Fence Epoch</th>
                    <th class="py-2.5 px-4">Committed Watermark</th>
                    <th class="py-2.5 px-4 text-right">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (chk of record.recovery.checkpoints; track chk.checkpointId) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-3 px-4 font-mono font-medium text-slate-900">
                        {{ chk.checkpointId }}
                      </td>
                      <td class="py-3 px-4 font-medium text-slate-800">Gen {{ chk.generation }}</td>
                      <td class="py-3 px-4 text-slate-700">{{ chk.associatedStage }}</td>
                      <td class="py-3 px-4 font-mono text-slate-600">Epoch {{ chk.fenceEpoch }}</td>
                      <td class="py-3 px-4 font-mono text-slate-800">{{ chk.committedRowsWatermark.toLocaleString() }} rows</td>
                      <td class="py-3 px-4 text-right">
                        @if (chk.isSelectedForResume) {
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                            Selected for Resume
                          </span>
                        } @else if (chk.isSuperseded) {
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500 border border-slate-200">
                            Superseded
                          </span>
                        } @else {
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Valid State
                          </span>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <div class="py-8 text-center text-xs text-slate-500">
              <div class="font-medium text-slate-700">Zero State Checkpoints Logged</div>
              <p class="text-slate-400 mt-0.5">Execution ran as a single atomic transaction without intermediate stage checkpoints.</p>
            </div>
          }
        </div>

      </div>
    }
  `
})
export class TabHistoryRecoveryComponent {
  public hws = inject(HistoryWorkspaceService);

  public formatTimestamp(ts: string | null): string {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  }
}
