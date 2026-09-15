import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-audit-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Audit Scope Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          AUDIT JOURNAL SCOPE
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Total Actions</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.audit_scope.total_events_recorded | number }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Privileged Actions</span>
            <span class="text-base font-bold font-mono text-amber-700">{{ payload.audit_scope.privileged_actions_count }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Failed Operations</span>
            <span class="text-base font-bold font-mono" [ngClass]="payload.audit_scope.failed_operations_count > 0 ? 'text-rose-700' : 'text-slate-900'">
              {{ payload.audit_scope.failed_operations_count }}
            </span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Time Window</span>
            <span class="text-xs font-mono text-slate-700 leading-snug">
              {{ payload.audit_scope.time_window_start | date:'MM/dd HH:mm' }} &ndash; {{ payload.audit_scope.time_window_end | date:'MM/dd HH:mm' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Audit Records Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          OPERATOR ACTION JOURNAL
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Timestamp</th>
                <th class="py-3 px-4">Actor</th>
                <th class="py-3 px-4">Action</th>
                <th class="py-3 px-4">Target Resource</th>
                <th class="py-3 px-4">Context</th>
                <th class="py-3 px-4 text-right">Result</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (rec of payload.records; track rec.timestamp + rec.actor) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                    {{ rec.timestamp | date:'yyyy-MM-dd HH:mm:ss' }}
                  </td>
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ rec.actor }}
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-700 text-[11px]">
                    {{ rec.action }}
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                    {{ rec.target }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-600">
                    {{ rec.context }}
                  </td>
                  <td class="py-3.5 px-4 text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': rec.result === 'SUCCESS',
                        'bg-rose-50 text-rose-700 border border-rose-200': rec.result === 'FAILURE' || rec.result === 'DENIED'
                      }">
                      {{ rec.result }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Privileged Actions Log (If applicable) -->
      @if (payload.privileged_actions && payload.privileged_actions.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            PRIVILEGED ACTIONS LOG
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Timestamp</th>
                  <th class="py-3 px-4">Actor</th>
                  <th class="py-3 px-4">Elevated Action</th>
                  <th class="py-3 px-4">Justification</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (p of payload.privileged_actions; track p.timestamp + p.actor) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ p.timestamp | date:'yyyy-MM-dd HH:mm:ss' }}
                    </td>
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ p.actor }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-amber-800 font-semibold text-[11px]">
                      {{ p.elevated_action }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ p.justification }}
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
export class AuditReportBodyComponent {
  @Input({ required: true }) public payload!: AuditReportPayload;
}
