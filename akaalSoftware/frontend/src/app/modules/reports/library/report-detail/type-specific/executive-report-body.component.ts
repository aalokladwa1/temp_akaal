import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ExecutiveReportPayload } from '../../../models/report-payloads.models';
import { ReportsService } from '../../../services/reports.service';

@Component({
  selector: 'app-executive-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Program Milestone Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          PROGRAM PROGRESSION &amp; WORKLOAD POSTURE
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Program Progress</span>
            <span class="text-base font-bold font-mono text-blue-700">{{ payload.executive_summary.overall_completion_pct }}%</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Readiness Posture</span>
            <span class="text-base font-bold" [ngClass]="{
              'text-emerald-700': payload.executive_summary.readiness_status === 'ON_TRACK',
              'text-amber-700': payload.executive_summary.readiness_status === 'ATTENTION_REQUIRED',
              'text-rose-700': payload.executive_summary.readiness_status === 'BLOCKED'
            }">
              {{ payload.executive_summary.readiness_status }}
            </span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Total Workloads</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.executive_summary.total_workloads }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Certified Workloads</span>
            <span class="text-base font-bold font-mono text-emerald-700">{{ payload.executive_summary.certified_workloads }}</span>
          </div>
        </div>
      </div>

      <!-- Technical Domain Rollups Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          TECHNICAL DOMAIN ROLLUP &amp; REPORT DRILL-DOWN
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Technical Domain</th>
                <th class="py-3 px-4">Status</th>
                <th class="py-3 px-4 text-right">Findings Count</th>
                <th class="py-3 px-4 text-right">Technical Drill-Down</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (domain of payload.technical_domain_summaries; track domain.domain) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ domain.domain }}
                  </td>
                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': domain.status === 'SATISFIED',
                        'bg-amber-50 text-amber-800 border border-amber-200': domain.status === 'ATTENTION',
                        'bg-slate-100 text-slate-700': domain.status === 'PENDING'
                      }">
                      {{ domain.status }}
                    </span>
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono" [ngClass]="domain.findings_count > 0 ? 'text-amber-700 font-bold' : 'text-slate-400'">
                    {{ domain.findings_count }}
                  </td>
                  <td class="py-3.5 px-4 text-right">
                    <button
                      type="button"
                      (click)="drillDown(domain.linked_report_id)"
                      class="px-3 py-1 rounded bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs border border-slate-200 transition-colors cursor-pointer">
                      Open {{ domain.linked_report_id }}
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Risks & Exceptions (If applicable) -->
      @if (payload.risks_and_exceptions && payload.risks_and_exceptions.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            TECHNICAL RISKS &amp; EXCEPTIONS REQUIRING ATTENTION
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Headline</th>
                  <th class="py-3 px-4">Severity</th>
                  <th class="py-3 px-4">Mitigation Action</th>
                  <th class="py-3 px-4 text-right">Report Ref</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (risk of payload.risks_and_exceptions; track risk.risk_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ risk.headline }}
                    </td>
                    <td class="py-3.5 px-4">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-rose-50 text-rose-700 border border-rose-200': risk.severity === 'HIGH',
                          'bg-amber-50 text-amber-800 border border-amber-200': risk.severity === 'MEDIUM',
                          'bg-slate-100 text-slate-700': risk.severity === 'LOW'
                        }">
                        {{ risk.severity }}
                      </span>
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ risk.mitigation_action }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-500 text-[11px]">
                      {{ risk.linked_report_id || '—' }}
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
export class ExecutiveReportBodyComponent {
  @Input({ required: true }) public payload!: ExecutiveReportPayload;
  private rs = inject(ReportsService);

  public drillDown(reportId: string): void {
    if (reportId) {
      this.rs.openReportById(reportId);
    }
  }
}
