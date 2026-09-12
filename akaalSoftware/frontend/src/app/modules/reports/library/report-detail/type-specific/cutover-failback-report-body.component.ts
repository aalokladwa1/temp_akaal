import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CutoverFailbackReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-cutover-failback-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Cutover Decision Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          CUTOVER DECISION &amp; TRANSITION STATE
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Decision State</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.cutover_summary.decision_state }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Final Catch-up Lag</span>
            <span class="text-base font-bold font-mono text-emerald-700">{{ payload.cutover_summary.final_catchup_lag_seconds }}s</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Readiness Assessment</span>
            <span class="text-base font-bold text-slate-800">{{ payload.cutover_summary.readiness_score_or_status }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Operator In Charge</span>
            <span class="text-base font-bold text-slate-900">{{ payload.cutover_summary.operator_in_charge }}</span>
          </div>
        </div>
      </div>

      <!-- Readiness Evidence Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          CUTOVER READINESS PREREQUISITES
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Prerequisite Check</th>
                <th class="py-3 px-4">Category</th>
                <th class="py-3 px-4">Verified Timestamp</th>
                <th class="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (item of payload.readiness_evidence; track item.check_item) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ item.check_item }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-500 text-[11px]">
                    {{ item.category }}
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px]">
                    {{ item.verified_at ? (item.verified_at | date:'yyyy-MM-dd HH:mm') : '—' }}
                  </td>
                  <td class="py-3.5 px-4 text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': item.status === 'SATISFIED',
                        'bg-rose-50 text-rose-700 border border-rose-200': item.status === 'BLOCKED',
                        'bg-amber-50 text-amber-800 border border-amber-200': item.status === 'PENDING'
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

      <!-- Approval Gates Table -->
      @if (payload.approval_gates && payload.approval_gates.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            DUAL-CONTROL APPROVAL GATES
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Gate Name</th>
                  <th class="py-3 px-4">Approver Role</th>
                  <th class="py-3 px-4">Decided At</th>
                  <th class="py-3 px-4 text-right">Decision</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (gate of payload.approval_gates; track gate.gate_name) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ gate.gate_name }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                      {{ gate.approver_role }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ gate.decided_at ? (gate.decided_at | date:'yyyy-MM-dd HH:mm') : '—' }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border border-emerald-200': gate.decision === 'APPROVED',
                          'bg-rose-50 text-rose-700 border border-rose-200': gate.decision === 'REJECTED',
                          'bg-amber-50 text-amber-800 border border-amber-200': gate.decision === 'PENDING'
                        }">
                        {{ gate.decision }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Failback Readiness Block -->
      <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2 text-xs text-slate-700">
        <span class="font-semibold text-slate-900">Failback Safety &amp; Reverse Replication Status</span>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-600 mt-1">
          <div>Reverse CDC Stream: <strong class="text-slate-800">{{ payload.failback_readiness.reverse_cdc_stream_configured ? 'Configured & Verified' : 'Unconfigured' }}</strong></div>
          <div>Target Snapshot: <strong class="text-slate-800">{{ payload.failback_readiness.target_snapshot_available ? 'Available' : 'None' }}</strong></div>
        </div>
      </div>

    </div>
  `
})
export class CutoverFailbackReportBodyComponent {
  @Input({ required: true }) public payload!: CutoverFailbackReportPayload;
}
