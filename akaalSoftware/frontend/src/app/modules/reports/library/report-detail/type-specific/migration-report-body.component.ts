import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-migration-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Execution Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          EXECUTION METRICS &amp; VOLUME
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Transferred Records</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.execution_summary.total_rows | number }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Transferred Volume</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ (payload.execution_summary.total_bytes / (1024*1024)) | number:'1.1-2' }} MB</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Elapsed Time</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.execution_summary.elapsed_seconds }}s</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Effective Throughput</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.execution_summary.average_throughput_rows_sec | number }} rows/s</span>
          </div>
        </div>

        @if (payload.execution_summary.checkpoint_lsn_or_scn) {
          <div class="pt-3 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-600">
            <span class="font-medium text-slate-500">Checkpoint Position:</span>
            <code class="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-800">{{ payload.execution_summary.checkpoint_lsn_or_scn }}</code>
          </div>
        }
      </div>

      <!-- Stage Execution Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          STAGE EXECUTION TIMELINE
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Stage</th>
                <th class="py-3 px-4">Status</th>
                <th class="py-3 px-4">Duration</th>
                <th class="py-3 px-4 text-right">Rows</th>
                <th class="py-3 px-4 text-right">Volume</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (stage of payload.stages; track stage.stage_number) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ stage.stage_number }}. {{ stage.stage_name }}
                  </td>
                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': stage.status === 'COMPLETED',
                        'bg-blue-50 text-blue-700 border border-blue-200': stage.status === 'IN_PROGRESS',
                        'bg-rose-50 text-rose-700 border border-rose-200': stage.status === 'FAILED',
                        'bg-slate-100 text-slate-700': stage.status === 'SKIPPED'
                      }">
                      {{ stage.status }}
                    </span>
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px]">
                    {{ stage.duration_seconds }}s
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                    {{ stage.transferred_rows | number }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                    {{ (stage.transferred_bytes / 1024) | number:'1.0-0' }} KB
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Table Transfers / Object Results -->
      @if (payload.table_transfers && payload.table_transfers.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            TABLE &amp; OBJECT PARTITION TRANSFERS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Table / Entity</th>
                  <th class="py-3 px-4">Schema</th>
                  <th class="py-3 px-4 text-right">Row Count</th>
                  <th class="py-3 px-4 text-right">Duration</th>
                  <th class="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (item of payload.table_transfers; track item.table_name) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ item.table_name }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                      {{ item.schema_name }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-900">
                      {{ item.row_count | number }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-500 text-[11px]">
                      {{ item.duration_seconds }}s
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border border-emerald-200': item.status === 'COMPLETED',
                          'bg-rose-50 text-rose-700 border border-rose-200': item.status === 'FAILED',
                          'bg-blue-50 text-blue-700 border border-blue-200': item.status === 'IN_PROGRESS'
                        }">
                        {{ item.status }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Failures & Retries (If any) -->
      @if (payload.failures_and_retries && payload.failures_and_retries.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            FAILURES &amp; RETRY HISTORY
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Object</th>
                  <th class="py-3 px-4">Attempt</th>
                  <th class="py-3 px-4">Error Code</th>
                  <th class="py-3 px-4">Error Description</th>
                  <th class="py-3 px-4 text-right">Resolved</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (failure of payload.failures_and_retries; track failure.object_name + failure.attempt) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ failure.object_name }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-600">
                      #{{ failure.attempt }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-rose-700 text-[11px]">
                      {{ failure.error_code }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ failure.error_message }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="failure.resolved ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                        {{ failure.resolved ? 'RESOLVED' : 'UNRESOLVED' }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

    </div>
  `
})
export class MigrationReportBodyComponent {
  @Input({ required: true }) public payload!: MigrationReportPayload;
}
