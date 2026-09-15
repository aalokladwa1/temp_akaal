import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GovernanceApprovalReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-governance-approval-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Governance Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          GOVERNANCE &amp; APPROVAL BARRIER STATE
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Plan Version</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.governance_summary.plan_name }} (v{{ payload.governance_summary.plan_version }})</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Barrier Status</span>
            <span class="text-base font-bold" [ngClass]="payload.governance_summary.barrier_status === 'CLEARED' ? 'text-emerald-700' : 'text-amber-700'">
              {{ payload.governance_summary.barrier_status }}
            </span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Required Quorum</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.governance_summary.required_quorum_count }} Approvers</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Approvals Recorded</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.governance_summary.received_approvals_count }}</span>
          </div>
        </div>
      </div>

      <!-- Decision Records Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          APPROVER ROLES &amp; APPROVAL DECISION RECORDS
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Approver Name</th>
                <th class="py-3 px-4">Role / Title</th>
                <th class="py-3 px-4">Barrier ID</th>
                <th class="py-3 px-4">Decided At</th>
                <th class="py-3 px-4 text-right">Decision</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (rec of payload.decision_records; track rec.record_id) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ rec.approver_name }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                    {{ rec.approver_role }}
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                    {{ rec.barrier_id }}
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                    {{ rec.decided_at | date:'yyyy-MM-dd HH:mm' }}
                  </td>
                  <td class="py-3.5 px-4 text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="rec.decision === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                      {{ rec.decision }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Conditions & Expiration (If applicable) -->
      @if (payload.conditions_and_expiry && payload.conditions_and_expiry.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            GOVERNANCE CONDITIONS &amp; EXPIRATION POLICIES
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Condition ID</th>
                  <th class="py-3 px-4">Condition Description</th>
                  <th class="py-3 px-4">Expiration</th>
                  <th class="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (cond of payload.conditions_and_expiry; track cond.condition_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono font-semibold text-slate-900 text-[11px]">
                      {{ cond.condition_id }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-700">
                      {{ cond.description }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ cond.expires_at ? (cond.expires_at | date:'yyyy-MM-dd HH:mm') : 'None' }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="cond.satisfied ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-800 border border-amber-200'">
                        {{ cond.satisfied ? 'SATISFIED' : 'PENDING' }}
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
export class GovernanceApprovalReportBodyComponent {
  @Input({ required: true }) public payload!: GovernanceApprovalReportPayload;
}
