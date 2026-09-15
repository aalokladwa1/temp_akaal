import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ComplianceReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-compliance-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Compliance Control Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          TECHNICAL CONTROL EXECUTION SUMMARY
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Controls Evaluated</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.compliance_scope.controls_evaluated }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Controls Satisfied</span>
            <span class="text-base font-bold font-mono text-emerald-700">{{ payload.compliance_scope.controls_passed }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Exceptions Recorded</span>
            <span class="text-base font-bold font-mono" [ngClass]="payload.compliance_scope.controls_with_exceptions > 0 ? 'text-amber-700' : 'text-slate-900'">
              {{ payload.compliance_scope.controls_with_exceptions }}
            </span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Framework Scope</span>
            <span class="text-base font-bold text-slate-800 text-[11px] truncate">{{ payload.compliance_scope.framework_mapping_name }}</span>
          </div>
        </div>
      </div>

      <!-- Technical Controls Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          TECHNICAL CONTROLS &amp; EXECUTION EVIDENCE
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Control ID</th>
                <th class="py-3 px-4">Control Name</th>
                <th class="py-3 px-4">Domain</th>
                <th class="py-3 px-4">Evidence Reference</th>
                <th class="py-3 px-4 text-right">Result</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (ctrl of payload.technical_controls; track ctrl.control_id) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-mono font-semibold text-slate-900 text-[11px]">
                    {{ ctrl.control_id }}
                  </td>
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ ctrl.control_name }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-500 text-[11px]">
                    {{ ctrl.domain }}
                  </td>
                  <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px]">
                    {{ ctrl.evidence_reference }}
                  </td>
                  <td class="py-3.5 px-4 text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': ctrl.evaluation_result === 'SATISFIED',
                        'bg-amber-50 text-amber-800 border border-amber-200': ctrl.evaluation_result === 'EXCEPTION_RECORDED',
                        'bg-slate-100 text-slate-700': ctrl.evaluation_result === 'NOT_APPLICABLE'
                      }">
                      {{ ctrl.evaluation_result }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Separation of Duties (If applicable) -->
      @if (payload.separation_of_duties_records && payload.separation_of_duties_records.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            SEPARATION OF DUTIES VERIFICATION
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Activity Type</th>
                  <th class="py-3 px-4">Primary Operator</th>
                  <th class="py-3 px-4">Reviewer / Approver</th>
                  <th class="py-3 px-4 text-right">Independence Verified</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (sod of payload.separation_of_duties_records; track sod.activity_type) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ sod.activity_type }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-700">
                      {{ sod.operator_a }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-700">
                      {{ sod.operator_b }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="sod.verified_independent ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                        {{ sod.verified_independent ? 'VERIFIED' : 'CONFLICT' }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Exceptions Log (If applicable) -->
      @if (payload.exceptions && payload.exceptions.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            FORMAL CONTROL EXCEPTIONS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Exception ID</th>
                  <th class="py-3 px-4">Control</th>
                  <th class="py-3 px-4">Description</th>
                  <th class="py-3 px-4">Approved By</th>
                  <th class="py-3 px-4 text-right">Valid Until</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (ex of payload.exceptions; track ex.exception_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono font-semibold text-slate-900 text-[11px]">
                      {{ ex.exception_id }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px]">
                      {{ ex.control_id }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-700">
                      {{ ex.description }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ ex.approved_by }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-500 text-[11px]">
                      {{ ex.valid_until | date:'yyyy-MM-dd' }}
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
export class ComplianceReportBodyComponent {
  @Input({ required: true }) public payload!: ComplianceReportPayload;
}
