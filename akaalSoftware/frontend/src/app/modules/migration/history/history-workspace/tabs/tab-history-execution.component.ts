import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { ExecutionRunDetail, ExecutionNodeStage, ExecutionAttempt } from '../history-workspace.models';
import { HistoryOutcome } from '../../history-home.models';

@Component({
  selector: 'app-tab-history-execution',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-6">
        
        <!-- Run Selector (if multiple historical runs exist) -->
        @if (record.executionRuns.length > 1) {
          <div class="bg-white border border-slate-200 rounded-lg p-3 shadow-xs flex items-center gap-2 overflow-x-auto">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider px-2">Historical Runs:</span>
            @for (run of record.executionRuns; track run.runId) {
              <button
                type="button"
                (click)="hws.selectExecutionRun(run.runId)"
                class="px-3 py-1.5 rounded-md text-xs font-medium border transition-colors flex items-center gap-2 cursor-pointer"
                [ngClass]="{
                  'bg-white text-slate-900 font-bold border-slate-300 shadow-xs ring-1 ring-slate-200': hws.currentExecutionRun()?.runId === run.runId,
                  'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 hover:text-slate-900': hws.currentExecutionRun()?.runId !== run.runId
                }">
                <span>Run {{ run.runNumber }}</span>
                <span class="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-bold border"
                  [ngClass]="getOutcomeBadgeClass(run.outcome)">
                  {{ run.outcome }}
                </span>
                <span class="text-[11px] text-slate-500 font-mono">{{ run.duration }}</span>
              </button>
            }
          </div>
        }

        @if (hws.currentExecutionRun(); as run) {
          
          <!-- Run Summary Header Strip -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
            <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <div class="flex items-center gap-2.5">
                  <h2 class="text-base font-bold text-slate-900">
                    Execution Run #{{ run.runNumber }}
                  </h2>
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-bold border"
                    [ngClass]="getOutcomeBadgeClass(run.outcome)">
                    {{ run.outcome }}
                  </span>
                  <span class="font-mono text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    {{ run.executionId }}
                  </span>
                </div>
                <div class="text-xs text-slate-500 mt-1">
                  Started: <span class="font-medium text-slate-800">{{ formatTimestamp(run.startedAt) }}</span>
                  &bull;
                  Completed: <span class="font-medium text-slate-800">{{ formatTimestamp(run.completedAt) }}</span>
                  &bull;
                  Duration: <span class="font-semibold text-slate-900">{{ run.duration }}</span>
                </div>
              </div>

              <!-- Quick Metrics -->
              <div class="flex items-center gap-6 text-xs bg-slate-50 px-4 py-2 rounded-md border border-slate-200">
                <div>
                  <div class="text-[10px] uppercase font-bold text-slate-500">Rows Processed</div>
                  <div class="font-bold text-slate-900">{{ run.totalRowsProcessed.toLocaleString() }}</div>
                </div>
                <div class="h-6 w-px bg-slate-200"></div>
                <div>
                  <div class="text-[10px] uppercase font-bold text-slate-500">Volume</div>
                  <div class="font-bold text-slate-900">{{ run.totalBytesProcessed }}</div>
                </div>
                <div class="h-6 w-px bg-slate-200"></div>
                <div>
                  <div class="text-[10px] uppercase font-bold text-slate-500">Throughput</div>
                  <div class="font-bold text-slate-900">{{ run.avgThroughput }}</div>
                </div>
              </div>
            </div>

            <!-- Error Banner if Run Failed -->
            @if (run.errorMessage) {
              <div class="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-md text-xs text-rose-800">
                <span class="font-bold text-rose-900">Failure Diagnostic:</span>
                <span class="font-mono ml-1.5">{{ run.errorMessage }}</span>
              </div>
            }
          </div>

          <!-- Execution Stages Table -->
          <div class="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
            <div class="px-5 py-3.5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
              <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Pipeline Stages Breakdown ({{ run.stages.length }})
              </h3>
              <span class="text-xs text-slate-500">Chronological stage execution</span>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse min-w-[700px]">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/50 text-[11px] font-bold text-slate-600 uppercase tracking-wider select-none">
                    <th class="py-2.5 px-4">Stage Name</th>
                    <th class="py-2.5 px-4">Type</th>
                    <th class="py-2.5 px-4">Status</th>
                    <th class="py-2.5 px-4">Duration</th>
                    <th class="py-2.5 px-4 text-right">Rows In / Out</th>
                    <th class="py-2.5 px-4 text-right">Throughput</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (stage of run.stages; track stage.id) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-3 px-4 font-medium text-slate-900">
                        <div>{{ stage.name }}</div>
                        @if (stage.errorMessage) {
                          <div class="text-[11px] text-rose-600 font-mono mt-0.5">{{ stage.errorMessage }}</div>
                        }
                      </td>
                      <td class="py-3 px-4 whitespace-nowrap">
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          {{ stage.stageType }}
                        </span>
                      </td>
                      <td class="py-3 px-4 whitespace-nowrap">
                        <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold border"
                          [ngClass]="getStageStatusBadgeClass(stage.status)">
                          {{ stage.status }}
                        </span>
                      </td>
                      <td class="py-3 px-4 font-mono text-slate-800 whitespace-nowrap">{{ stage.duration }}</td>
                      <td class="py-3 px-4 text-right font-mono text-slate-800 whitespace-nowrap">
                        {{ stage.rowsIn.toLocaleString() }} / {{ stage.rowsOut.toLocaleString() }}
                      </td>
                      <td class="py-3 px-4 text-right font-mono text-slate-800 whitespace-nowrap">{{ stage.throughput }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <!-- Invocations & Attempts Stream -->
          <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
              Execution Invocations &amp; Attempts ({{ run.attempts.length }})
            </h3>

            <div class="space-y-3">
              @for (att of run.attempts; track att.invocationId) {
                <div class="p-3.5 rounded-md border border-slate-200 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                  <div class="flex items-center gap-3">
                    <span class="font-bold text-slate-800">Attempt #{{ att.attemptNumber }}</span>
                    <span class="font-mono text-[11px] text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                      {{ att.invocationId }}
                    </span>
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border"
                      [ngClass]="att.state === 'SUCCEEDED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'">
                      {{ att.state }}
                    </span>
                  </div>

                  <div class="flex items-center gap-4 text-slate-600 flex-wrap">
                    <span>Fence Epoch: <strong class="font-mono text-slate-800">{{ att.fenceEpoch }}</strong></span>
                    @if (att.checkpointResumeId) {
                      <span>Resumed from: <strong class="font-mono text-slate-800">{{ att.checkpointResumeId }}</strong></span>
                    }
                    <span>Duration: <strong class="text-slate-800">{{ att.duration }}</strong></span>
                  </div>
                </div>
              }
            </div>
          </div>

          <!-- Mode-Specific Streaming / Engine Telemetry -->
          @if (run.watermarkProgression || run.cdcBacklogSeconds !== null) {
            <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
              <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
                Streaming &amp; Watermark Progression Telemetry
              </h3>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                @if (run.watermarkProgression) {
                  <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                    <div class="text-[11px] font-semibold text-slate-500">Watermark Boundary</div>
                    <div class="font-mono font-medium text-slate-900 mt-1">{{ run.watermarkProgression }}</div>
                  </div>
                }
                @if (run.cdcBacklogSeconds !== null && run.cdcBacklogSeconds !== undefined) {
                  <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                    <div class="text-[11px] font-semibold text-slate-500">Final CDC Replication Lag</div>
                    <div class="font-mono font-medium text-slate-900 mt-1">{{ run.cdcBacklogSeconds }}s (Real-time Synced)</div>
                  </div>
                }
                @if (run.cdcEventsProcessed !== null && run.cdcEventsProcessed !== undefined) {
                  <div class="p-3 bg-slate-50 rounded-md border border-slate-200">
                    <div class="text-[11px] font-semibold text-slate-500">Streaming CDC Events</div>
                    <div class="font-mono font-medium text-slate-900 mt-1">{{ run.cdcEventsProcessed.toLocaleString() }} events captured</div>
                  </div>
                }
              </div>
            </div>
          }

        }
      </div>
    }
  `
})
export class TabHistoryExecutionComponent {
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

  public getStageStatusBadgeClass(status: string): string {
    switch (status) {
      case 'COMPLETED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'RUNNING': return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      case 'SKIPPED': return 'bg-slate-100 text-slate-500 border-slate-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
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
