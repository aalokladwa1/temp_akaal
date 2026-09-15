import { Component, Input, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationReconciliationReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-validation-reconciliation-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Validation Scope Summary -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          VALIDATION SCOPE &amp; RECONCILIATION SUMMARY
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Entities Validated</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.validation_scope.entities_validated }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Source Records</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.validation_scope.total_source_rows | number }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Target Records</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.validation_scope.total_target_rows | number }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Row Discrepancies</span>
            <span class="text-base font-bold font-mono" [ngClass]="payload.validation_scope.mismatch_rows > 0 ? 'text-rose-700' : 'text-emerald-700'">
              {{ payload.validation_scope.mismatch_rows | number }}
            </span>
          </div>
        </div>

        @if (payload.validation_scope.checksum_algorithm) {
          <div class="pt-3 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-600">
            <span class="font-medium text-slate-500">Verification Algorithm:</span>
            <span class="font-mono text-slate-800 text-[11px]">{{ payload.validation_scope.checksum_algorithm }}</span>
          </div>
        }
      </div>

      <!-- Count Reconciliation Table -->
      <div class="flex flex-col gap-3">
        <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
          ROW COUNT RECONCILIATION
        </span>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Entity / Table</th>
                <th class="py-3 px-4 text-right">Source Count</th>
                <th class="py-3 px-4 text-right">Target Count</th>
                <th class="py-3 px-4 text-right">Delta</th>
                <th class="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (item of payload.count_reconciliation; track item.entity_name) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-semibold text-slate-900">
                    {{ item.entity_name }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                    {{ item.source_count | number }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                    {{ item.target_count | number }}
                  </td>
                  <td class="py-3.5 px-4 text-right font-mono" [ngClass]="item.delta !== 0 ? 'text-rose-700 font-bold' : 'text-slate-400'">
                    {{ item.delta > 0 ? '+' : '' }}{{ item.delta | number }}
                  </td>
                  <td class="py-3.5 px-4 text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="item.status === 'MATCHED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                      {{ item.status }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Checksum / Merkle Results Table (If applicable) -->
      @if (payload.checksum_results && payload.checksum_results.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            CRYPTOGRAPHIC HASH &amp; CHECKSUM RESULTS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Entity</th>
                  <th class="py-3 px-4">Source Digest</th>
                  <th class="py-3 px-4">Target Digest</th>
                  <th class="py-3 px-4 text-right">Integrity</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (item of payload.checksum_results; track item.entity_name) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ item.entity_name }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600">
                      {{ item.source_checksum }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600">
                      {{ item.target_checksum }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="item.matched ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                        {{ item.matched ? 'MATCHED' : 'HASH_MISMATCH' }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Detailed Findings (Paginated) -->
      @if (payload.discrepancies && payload.discrepancies.length > 0) {
        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
                DISCREPANCY FINDINGS
              </span>
              <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200">
                {{ payload.discrepancies.length }} Total Findings
              </span>
            </div>

            <!-- Simple Pagination -->
            <div class="flex items-center gap-2 text-xs text-slate-500">
              <span>Showing {{ paginatedDiscrepancies().length }} of {{ payload.discrepancies.length }}</span>
              @if (totalPages() > 1) {
                <div class="flex items-center gap-1">
                  <button 
                    type="button" 
                    [disabled]="currentPage() === 1"
                    (click)="currentPage.set(currentPage() - 1)"
                    class="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 disabled:opacity-40 text-slate-700 cursor-pointer">
                    &larr;
                  </button>
                  <span class="font-mono text-slate-700">{{ currentPage() }} / {{ totalPages() }}</span>
                  <button 
                    type="button" 
                    [disabled]="currentPage() === totalPages()"
                    (click)="currentPage.set(currentPage() + 1)"
                    class="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 disabled:opacity-40 text-slate-700 cursor-pointer">
                    &rarr;
                  </button>
                </div>
              }
            </div>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Entity</th>
                  <th class="py-3 px-4">Primary Key / Record</th>
                  <th class="py-3 px-4">Mismatch Type</th>
                  <th class="py-3 px-4">Source Value</th>
                  <th class="py-3 px-4">Target Value</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (d of paginatedDiscrepancies(); track d.id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ d.entity_name }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-[11px] text-slate-700">
                      {{ d.primary_key_val }}
                    </td>
                    <td class="py-3.5 px-4">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                        {{ d.mismatch_type }}
                      </span>
                    </td>
                    <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600">
                      {{ d.source_val || '—' }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600">
                      {{ d.target_val || '—' }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Repair & Revalidation Results (If applicable) -->
      @if (payload.repair_results && payload.repair_results.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            REPAIR &amp; REVALIDATION RESULTS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Entity</th>
                  <th class="py-3 px-4 text-right">Discrepancies</th>
                  <th class="py-3 px-4 text-right">Resolved</th>
                  <th class="py-3 px-4 text-right">Revalidation Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (repair of payload.repair_results; track repair.repair_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ repair.entity_name }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-700">
                      {{ repair.discrepancy_count }}
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-emerald-700 font-semibold">
                      {{ repair.resolved_count }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border border-emerald-200': repair.revalidation_status === 'VERIFIED',
                          'bg-rose-50 text-rose-700 border border-rose-200': repair.revalidation_status === 'FAILED',
                          'bg-amber-50 text-amber-800 border border-amber-200': repair.revalidation_status === 'PENDING'
                        }">
                        {{ repair.revalidation_status }}
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
export class ValidationReconciliationReportBodyComponent {
  @Input({ required: true }) public payload!: ValidationReconciliationReportPayload;

  public currentPage = signal<number>(1);
  public pageSize = 5;

  public totalPages = computed(() => {
    if (!this.payload?.discrepancies) return 1;
    return Math.max(1, Math.ceil(this.payload.discrepancies.length / this.pageSize));
  });

  public paginatedDiscrepancies = computed(() => {
    if (!this.payload?.discrepancies) return [];
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.payload.discrepancies.slice(start, start + this.pageSize);
  });
}
