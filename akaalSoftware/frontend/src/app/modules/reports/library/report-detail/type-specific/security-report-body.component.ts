import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SecurityReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-security-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Security Scope Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          SECURITY &amp; ACCESS CONTROL SCOPE
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Access Evaluations</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.security_scope.total_access_evaluations | number }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Denied Operations</span>
            <span class="text-base font-bold font-mono" [ngClass]="payload.security_scope.denied_operations_count > 0 ? 'text-rose-700' : 'text-slate-900'">
              {{ payload.security_scope.denied_operations_count }}
            </span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Active Identity Sessions</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.security_scope.active_identity_sessions }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Security Scope</span>
            <span class="text-base font-bold text-slate-800 text-[11px] truncate">{{ payload.security_scope.audit_scope_name }}</span>
          </div>
        </div>
      </div>

      <!-- Denied Operations (If any) -->
      @if (payload.denied_operations && payload.denied_operations.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            DENIED ACCESS ATTEMPTS &amp; POLICY BLOCKS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Timestamp</th>
                  <th class="py-3 px-4">Principal</th>
                  <th class="py-3 px-4">Action</th>
                  <th class="py-3 px-4">Resource</th>
                  <th class="py-3 px-4">Denial Reason</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (denied of payload.denied_operations; track denied.timestamp + denied.principal) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ denied.timestamp | date:'yyyy-MM-dd HH:mm:ss' }}
                    </td>
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ denied.principal }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-rose-700 font-semibold text-[11px]">
                      {{ denied.attempted_action }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px]">
                      {{ denied.resource }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ denied.denial_reason }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Authorization Activity Table -->
      @if (payload.authorization_activity && payload.authorization_activity.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            AUTHORIZATION ACTIVITY JOURNAL
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Timestamp</th>
                  <th class="py-3 px-4">Principal</th>
                  <th class="py-3 px-4">Action</th>
                  <th class="py-3 px-4">Resource</th>
                  <th class="py-3 px-4">Policy</th>
                  <th class="py-3 px-4 text-right">Decision</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (auth of payload.authorization_activity; track auth.timestamp + auth.principal) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ auth.timestamp | date:'yyyy-MM-dd HH:mm' }}
                    </td>
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ auth.principal }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-700 text-[11px]">
                      {{ auth.action }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ auth.resource }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ auth.policy_name }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="auth.decision === 'ALLOW' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                        {{ auth.decision }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Transport Security Evidence (If applicable) -->
      @if (payload.transport_security_evidence && payload.transport_security_evidence.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            TRANSPORT SECURITY (TLS) EVIDENCE
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Endpoint</th>
                  <th class="py-3 px-4">TLS Version</th>
                  <th class="py-3 px-4">Certificate Subject</th>
                  <th class="py-3 px-4 text-right">Valid Until</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (tls of payload.transport_security_evidence; track tls.endpoint) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono font-semibold text-slate-900 text-[11px]">
                      {{ tls.endpoint }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-700 text-[11px]">
                      {{ tls.tls_version }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600 text-[11px]">
                      {{ tls.certificate_subject }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-500 text-[11px]">
                      {{ tls.valid_until | date:'yyyy-MM-dd' }}
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
export class SecurityReportBodyComponent {
  @Input({ required: true }) public payload!: SecurityReportPayload;
}
