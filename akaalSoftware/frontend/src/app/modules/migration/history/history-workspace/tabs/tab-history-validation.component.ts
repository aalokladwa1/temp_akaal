import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { ValidationRunRecord, DiscrepancyItem } from '../history-workspace.models';
import { ValidationReconciliationState } from '../../history-home.models';

@Component({
  selector: 'app-tab-history-validation',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-6">
        
        <!-- Multi-Run / Phase Selector -->
        @if (record.validationRuns.length > 1) {
          <div class="bg-white border border-slate-200 rounded-lg p-3 shadow-xs flex items-center gap-2 overflow-x-auto">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider px-2">Validation Phase:</span>
            @for (val of record.validationRuns; track val.validationRunId) {
              <button
                type="button"
                (click)="hws.selectValidationRun(val.validationRunId)"
                class="px-3 py-1.5 rounded-md text-xs font-medium border transition-colors flex items-center gap-2 cursor-pointer"
                [ngClass]="{
                  'bg-white text-slate-900 font-bold border-slate-300 shadow-xs ring-1 ring-slate-200': hws.currentValidationRun()?.validationRunId === val.validationRunId,
                  'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 hover:text-slate-900': hws.currentValidationRun()?.validationRunId !== val.validationRunId
                }">
                <span>{{ getPhaseLabel(val.phase) }}</span>
                <span class="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-semibold border"
                  [ngClass]="getValidationBadgeClass(val.verdict)">
                  {{ val.verdict }}
                </span>
                <span class="text-[11px] text-slate-500 font-mono">{{ val.duration }}</span>
              </button>
            }
          </div>
        }

        @if (hws.currentValidationRun(); as val) {
          
          <!-- Validation Verdict Banner -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
            <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <div class="flex items-center gap-2.5 flex-wrap">
                  <h2 class="text-base font-bold text-slate-900">
                    {{ getPhaseLabel(val.phase) }} Validation Assurance
                  </h2>
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-semibold border"
                    [ngClass]="getValidationBadgeClass(val.verdict)">
                    {{ val.verdict }}
                  </span>
                  <span class="font-mono text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    {{ val.validationRunId }}
                  </span>
                </div>
                <div class="text-xs text-slate-500 mt-1">
                  Completed in <strong class="text-slate-800">{{ val.duration }}</strong> at {{ formatTimestamp(val.completedAt) }}
                </div>
              </div>

              <!-- Merkle Root Match Indicator -->
              <div class="flex items-center gap-3 bg-slate-50 px-4 py-2 rounded-md border border-slate-200 self-start md:self-auto">
                <div class="text-right">
                  <div class="text-[10px] font-bold uppercase text-slate-500">Merkle Root Parity</div>
                  <div class="text-xs font-bold" [ngClass]="val.merkleTreeRootMatch ? 'text-emerald-700' : 'text-rose-700'">
                    {{ val.merkleTreeRootMatch ? '100% Cryptographic Match' : 'Root Hash Mismatch' }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Parity Metric Counters -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 text-xs">
              <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                <div class="text-slate-500 font-medium">Source Row Count</div>
                <div class="text-base font-bold text-slate-900 mt-0.5">{{ val.rowCountSource.toLocaleString() }}</div>
              </div>
              <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                <div class="text-slate-500 font-medium">Target Row Count</div>
                <div class="text-base font-bold text-slate-900 mt-0.5">{{ val.rowCountTarget.toLocaleString() }}</div>
              </div>
              <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                <div class="text-slate-500 font-medium">Row Count Delta</div>
                <div class="text-base font-bold font-mono mt-0.5" [ngClass]="val.rowCountDelta === 0 ? 'text-emerald-700' : 'text-rose-700'">
                  {{ val.rowCountDelta }}
                </div>
              </div>
              <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                <div class="text-slate-500 font-medium">Discrepancies Logged</div>
                <div class="text-base font-bold font-mono mt-0.5" [ngClass]="val.discrepancyCount === 0 ? 'text-emerald-700' : 'text-amber-700'">
                  {{ val.discrepancyCount }}
                </div>
              </div>
            </div>
          </div>

          <!-- Discrepancy Progression Table -->
          @if (val.discrepancies.length > 0) {
            <div class="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
              <div class="px-5 py-3.5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
                <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Discrepancy Progression &amp; Resolution ({{ val.discrepancies.length }})
                </h3>
                <span class="text-xs text-slate-500">Forensic discrepancy trace</span>
              </div>

              <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse min-w-[750px]">
                  <thead>
                    <tr class="border-b border-slate-200 bg-slate-50/50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                      <th class="py-2.5 px-4">Object / Primary Key</th>
                      <th class="py-2.5 px-4">Discrepancy Type</th>
                      <th class="py-2.5 px-4">Source Value</th>
                      <th class="py-2.5 px-4">Target Value</th>
                      <th class="py-2.5 px-4">Progression Status</th>
                      <th class="py-2.5 px-4 text-right">Resolution Snippet</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                    @for (disc of val.discrepancies; track disc.id) {
                      <tr class="hover:bg-slate-50/80 transition-colors">
                        <td class="py-3 px-4 font-mono font-medium text-slate-900">
                          <div>{{ disc.tableName }}</div>
                          <div class="text-[11px] text-slate-500 font-normal">{{ disc.primaryKey }}</div>
                        </td>
                        <td class="py-3 px-4 whitespace-nowrap">
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                            {{ disc.discrepancyType }}
                          </span>
                        </td>
                        <td class="py-3 px-4 font-mono text-[11px] text-slate-800 bg-slate-50">{{ disc.sourceValue }}</td>
                        <td class="py-3 px-4 font-mono text-[11px] text-rose-700 bg-rose-50/30">{{ disc.targetValue }}</td>
                        <td class="py-3 px-4 whitespace-nowrap">
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border"
                            [ngClass]="getProgressionClass(disc.progression)">
                            {{ disc.progression }}
                          </span>
                        </td>
                        <td class="py-3 px-4 text-right">
                          @if (disc.repairScriptSnippet) {
                            <code class="text-[10px] font-mono text-slate-600 bg-slate-100 px-2 py-1 rounded border border-slate-200 block truncate max-w-[200px] ml-auto" [title]="disc.repairScriptSnippet">
                              {{ disc.repairScriptSnippet }}
                            </code>
                          } @else {
                            <span class="text-slate-400">—</span>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          } @else {
            <!-- Zero Discrepancies State -->
            <div class="bg-white border border-slate-200 rounded-lg p-10 text-center text-xs text-slate-500 shadow-xs">
              <span class="inline-flex items-center justify-center w-10 h-10 rounded-full bg-emerald-100 text-emerald-800 text-base font-bold mb-3">&check;</span>
              <div class="text-sm font-bold text-slate-900">100% Table &amp; Row Cryptographic Parity</div>
              <p class="text-slate-400 mt-1 max-w-md mx-auto">
                No discrepancies, schema drifts, or data truncation detected between source and target datasets.
              </p>
            </div>
          }

        }
      </div>
    }
  `
})
export class TabHistoryValidationComponent {
  public hws = inject(HistoryWorkspaceService);

  public getPhaseLabel(phase: string): string {
    switch (phase) {
      case 'PRE_MIGRATION': return 'Pre-Migration Baseline';
      case 'IN_FLIGHT': return 'In-Flight Stream Check';
      case 'POST_MIGRATION': return 'Post-Migration Parity';
      case 'REVALIDATION': return 'Revalidation Audit';
      default: return phase;
    }
  }

  public getValidationBadgeClass(verdict: ValidationReconciliationState): string {
    switch (verdict) {
      case 'PASSED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'RECONCILED': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'MISMATCHES_DETECTED': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getProgressionClass(prog: string): string {
    switch (prog) {
      case 'RESOLVED':
      case 'REVALIDATED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'REPAIRED':
      case 'REVIEWED': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'LOCALIZED':
      case 'DETECTED': return 'bg-amber-50 text-amber-700 border-amber-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

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
