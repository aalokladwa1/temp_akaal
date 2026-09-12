import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SchemaCompatibilityReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-schema-compatibility-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Assessment Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          SCHEMA ASSESSMENT SUMMARY
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Objects Scanned</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.assessment_summary.total_objects_scanned }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Directly Compatible</span>
            <span class="text-base font-bold font-mono text-emerald-700">{{ payload.assessment_summary.compatible_objects }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Requires Mapping</span>
            <span class="text-base font-bold font-mono text-amber-700">{{ payload.assessment_summary.partially_compatible }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Incompatible</span>
            <span class="text-base font-bold font-mono text-rose-700">{{ payload.assessment_summary.incompatible_objects }}</span>
          </div>
        </div>

        <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
          <div class="flex items-center gap-2">
            <span class="font-medium text-slate-500">Dialect Translation:</span>
            <span class="font-semibold text-slate-800">{{ payload.assessment_summary.source_dialect }} &rarr; {{ payload.assessment_summary.target_dialect }}</span>
          </div>
          @if (payload.assessment_summary.unsupported_features_count > 0) {
            <span class="text-amber-700 font-semibold">{{ payload.assessment_summary.unsupported_features_count }} unsupported feature(s) detected</span>
          }
        </div>
      </div>

      <!-- Object Inventory Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          OBJECT TYPE INVENTORY
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Object Type</th>
                <th class="py-3 px-4 text-right">Source Count</th>
                <th class="py-3 px-4 text-right">Target Compatible</th>
                <th class="py-3 px-4 text-right">Requires Manual Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (item of payload.object_inventory; track item.object_type) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ item.object_type }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                    {{ item.source_count }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-emerald-700 font-semibold">
                    {{ item.target_compatible_count }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono" [ngClass]="item.requires_manual_mapping > 0 ? 'text-amber-700 font-semibold' : 'text-slate-400'">
                    {{ item.requires_manual_mapping }}
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Datatype Mappings -->
      @if (payload.type_mappings && payload.type_mappings.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            DATATYPE TRANSLATION MAPPINGS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Source Datatype</th>
                  <th class="py-3 px-4">Target Datatype</th>
                  <th class="py-3 px-4">Precision Preserved</th>
                  <th class="py-3 px-4">Notes</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (mapping of payload.type_mappings; track mapping.source_type) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono font-semibold text-slate-900">
                      {{ mapping.source_type }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-blue-700">
                      {{ mapping.target_type }}
                    </td>
                    <td class="py-3.5 px-4">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="mapping.precision_preserved ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-800 border border-amber-200'">
                        {{ mapping.precision_preserved ? 'EXACT' : 'APPROXIMATED' }}
                      </span>
                    </td>
                    <td class="py-3.5 px-4 text-slate-500 text-[11px]">
                      {{ mapping.notes || '—' }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Unsupported / Action Items -->
      @if (payload.unsupported_findings && payload.unsupported_findings.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            UNSUPPORTED OBJECTS &amp; REMEDIATION ACTIONS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Object</th>
                  <th class="py-3 px-4">Type</th>
                  <th class="py-3 px-4">Finding</th>
                  <th class="py-3 px-4">Remediation Guidance</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (finding of payload.unsupported_findings; track finding.object_name) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ finding.object_name }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ finding.object_type }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-700">
                      {{ finding.issue_description }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ finding.remediation_guidance }}
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
export class SchemaCompatibilityReportBodyComponent {
  @Input({ required: true }) public payload!: SchemaCompatibilityReportPayload;
}
