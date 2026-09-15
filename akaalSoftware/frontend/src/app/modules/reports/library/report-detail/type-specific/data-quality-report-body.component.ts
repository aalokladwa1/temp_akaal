import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DataQualityReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-data-quality-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Quality Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          DATA QUALITY ASSESSMENT SUMMARY
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Rules Evaluated</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.quality_summary.rules_evaluated }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Rules Satisfied</span>
            <span class="text-base font-bold font-mono text-emerald-700">{{ payload.quality_summary.rules_passed }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Rules Violated</span>
            <span class="text-base font-bold font-mono" [ngClass]="payload.quality_summary.rules_failed > 0 ? 'text-rose-700' : 'text-slate-900'">
              {{ payload.quality_summary.rules_failed }}
            </span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Quarantined Records</span>
            <span class="text-base font-bold font-mono" [ngClass]="payload.quality_summary.quarantined_records > 0 ? 'text-amber-700' : 'text-slate-900'">
              {{ payload.quality_summary.quarantined_records | number }}
            </span>
          </div>
        </div>
      </div>

      <!-- Rule Evaluations Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          CONSTRAINT &amp; INTEGRITY RULE EVALUATIONS
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Rule Name</th>
                <th class="py-3 px-4">Target Entity</th>
                <th class="py-3 px-4">Category</th>
                <th class="py-3 px-4 text-right">Violations</th>
                <th class="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (rule of payload.rule_evaluations; track rule.rule_id) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ rule.rule_name }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                    {{ rule.entity_name }}
                  </td>
                  <td class="py-3.5 px-4 text-slate-500 text-[11px]">
                    {{ rule.rule_type }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono" [ngClass]="rule.violation_count > 0 ? 'text-rose-700 font-bold' : 'text-slate-400'">
                    {{ rule.violation_count | number }}
                  </td>
                  <td class="py-3.5 px-4 text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="rule.status === 'PASSED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                      {{ rule.status }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Cleansing & Standardization Outcomes (If applicable) -->
      @if (payload.cleansing_outcomes && payload.cleansing_outcomes.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            CLEANSING &amp; STANDARDIZATION TRANSFORMATIONS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Entity</th>
                  <th class="py-3 px-4">Field / Column</th>
                  <th class="py-3 px-4">Transformation Type</th>
                  <th class="py-3 px-4 text-right">Records Transformed</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (item of payload.cleansing_outcomes; track item.entity_name + item.field_name) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ item.entity_name }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px]">
                      {{ item.field_name }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-700">
                      {{ item.transform_type }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-900">
                      {{ item.records_transformed | number }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Quarantine Records (If applicable) -->
      @if (payload.quarantine_records && payload.quarantine_records.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            QUARANTINE DISPOSITION
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Quarantine ID</th>
                  <th class="py-3 px-4">Entity</th>
                  <th class="py-3 px-4">Quarantine Reason</th>
                  <th class="py-3 px-4">Timestamp</th>
                  <th class="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (q of payload.quarantine_records; track q.quarantine_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono text-slate-800 text-[11px]">
                      {{ q.quarantine_id }}
                    </td>
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ q.entity_name }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ q.reason }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ q.quarantine_timestamp | date:'yyyy-MM-dd HH:mm' }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-amber-50 text-amber-800 border border-amber-200': q.status === 'QUARANTINED',
                          'bg-emerald-50 text-emerald-700 border border-emerald-200': q.status === 'RELEASED',
                          'bg-slate-100 text-slate-700': q.status === 'DISCARDED'
                        }">
                        {{ q.status }}
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
export class DataQualityReportBodyComponent {
  @Input({ required: true }) public payload!: DataQualityReportPayload;
}
