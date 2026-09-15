import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CDCReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-cdc-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- CDC Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          CDC REPLICATION &amp; STREAMING SUMMARY
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Capture State</span>
            <span class="text-base font-bold text-slate-900">{{ payload.summary.capture_status }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Apply State</span>
            <span class="text-base font-bold text-slate-900">{{ payload.summary.apply_status }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Transactions Captured</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.summary.total_transactions_captured | number }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Transactions Applied</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.summary.total_transactions_applied | number }}</span>
          </div>
        </div>
      </div>

      <!-- Boundary Positions -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          STREAM BOUNDARY POSITIONS &amp; REPLICATION LAG
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Stream Name</th>
                <th class="py-3 px-4">Provider</th>
                <th class="py-3 px-4">Position Label</th>
                <th class="py-3 px-4 font-mono">Current Position</th>
                <th class="py-3 px-4 font-mono">Committed Position</th>
                <th class="py-3 px-4 text-right">Lag (Records)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (bound of payload.boundary_positions; track bound.stream_name) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ bound.stream_name }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-600">
                    {{ bound.provider_type }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                    {{ bound.position_label }}
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-800 text-[11px]">
                    {{ bound.current_position }}
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-800 text-[11px]">
                    {{ bound.committed_position }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono font-bold" [ngClass]="bound.lag_records > 0 ? 'text-amber-700' : 'text-emerald-700'">
                    {{ bound.lag_records | number }}
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Transaction Totals by Op -->
      @if (payload.transaction_totals && payload.transaction_totals.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            TRANSACTION TOTALS BY DML / DDL OPERATION
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Operation Type</th>
                  <th class="py-3 px-4 text-right">Total Count</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (op of payload.transaction_totals; track op.operation) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900 font-mono text-[11px]">
                      {{ op.operation }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-800">
                      {{ op.count | number }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Conflicts & Quarantine (If any) -->
      @if (payload.conflicts_and_quarantine && payload.conflicts_and_quarantine.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            CDC CONFLICTS &amp; QUARANTINED EVENTS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Event ID</th>
                  <th class="py-3 px-4">Table</th>
                  <th class="py-3 px-4">Conflict Type</th>
                  <th class="py-3 px-4 font-mono">Stream Position</th>
                  <th class="py-3 px-4">Occurred At</th>
                  <th class="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (evt of payload.conflicts_and_quarantine; track evt.event_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono text-slate-700 text-[11px]">
                      {{ evt.event_id }}
                    </td>
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ evt.table_name }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                      {{ evt.conflict_type }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px]">
                      {{ evt.position }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ evt.occurred_at | date:'yyyy-MM-dd HH:mm:ss' }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        {{ evt.status }}
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
export class CdcReportBodyComponent {
  @Input({ required: true }) public payload!: CDCReportPayload;
}
export { CdcReportBodyComponent as CDCReportBodyComponent };
