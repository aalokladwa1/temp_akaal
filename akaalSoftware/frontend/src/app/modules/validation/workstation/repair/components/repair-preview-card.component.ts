import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from '../validation-repair.service';
import { ProposedAttributeChange, AttributeValueKind, RepairRiskLevel } from '../validation-repair.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-preview-card',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 lg:p-7 shadow-2xs flex flex-col gap-6">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-slate-100">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0">
            <app-lucide-icon name="arrow-left-right" [size]="15"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-0.5">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              3. Impact &amp; Target Preview (Source &harr; Current Target &rarr; Proposed Target)
            </h2>
            <p class="text-[11.5px] text-slate-500">
              Strict 3-way before-and-after comparison showing source baseline, observed target, and compensating proposed value
            </p>
          </div>
        </div>

        @if (store.impact(); as imp) {
          <div class="flex items-center gap-2">
            <span [ngClass]="getRiskBadgeClass(imp.riskLevel)"
                  class="px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider border flex items-center gap-1.5">
              <app-lucide-icon [name]="getRiskIcon(imp.riskLevel)" [size]="12"></app-lucide-icon>
              <span>{{ formatRiskLevel(imp.riskLevel) }}</span>
            </span>
          </div>
        }
      </div>

      <!-- 3-Way Before -> Proposed After Comparison Table -->
      @if (store.proposal()?.proposedChanges?.length) {
        <div class="border border-slate-200/80 rounded-xl overflow-hidden shadow-2xs">
          
          <!-- Table Header Legend -->
          <div class="p-4 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between flex-wrap gap-3 text-xs">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="table-properties" [size]="14" class="text-slate-500"></app-lucide-icon>
              <span class="font-bold text-slate-800">Logical Attribute Level Changes ({{ store.proposal()!.proposedChanges.length }} Attributes)</span>
            </div>
            <div class="flex items-center gap-4 text-[11px] text-slate-500 font-medium">
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-xs bg-slate-300 border border-slate-400/40"></span> Source Canonical</span>
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-xs bg-amber-300 border border-amber-400/40"></span> Current Observed Target</span>
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-xs bg-blue-300 border border-blue-400/40"></span> Proposed Target</span>
            </div>
          </div>

          <!-- Table Viewport (Table-Local Scroll Viewport) -->
          <div class="overflow-x-auto max-h-[380px] min-w-0 max-w-full relative">
            <table class="w-full text-left text-xs border-collapse">
              <thead class="sticky top-0 z-10 bg-slate-50 border-b border-slate-200 text-[10.5px] font-bold text-slate-500 uppercase tracking-wider shadow-2xs">
                <tr>
                  <th class="py-3.5 px-4.5 min-w-[180px] bg-slate-50">
                    <div class="flex items-center gap-1.5">
                      <app-lucide-icon name="table" [size]="12" class="text-slate-400"></app-lucide-icon>
                      <span>Attribute / Field</span>
                    </div>
                  </th>
                  <th class="py-3.5 px-4.5 min-w-[220px] bg-slate-50 text-slate-700">
                    <div class="flex items-center gap-1.5">
                      <app-lucide-icon name="database" [size]="12" class="text-slate-500"></app-lucide-icon>
                      <span>Source (Canonical)</span>
                    </div>
                  </th>
                  <th class="py-3.5 px-4.5 min-w-[220px] bg-amber-50/70 text-amber-900 border-l border-r border-amber-200/60">
                    <div class="flex items-center gap-1.5">
                      <app-lucide-icon name="server" [size]="12" class="text-amber-700"></app-lucide-icon>
                      <span>Current Target (Observed)</span>
                    </div>
                  </th>
                  <th class="py-3.5 px-4.5 min-w-[240px] bg-blue-50/70 text-blue-900">
                    <div class="flex items-center gap-1.5">
                      <app-lucide-icon name="sparkles" [size]="12" class="text-blue-700"></app-lucide-icon>
                      <span>Proposed Target (If Applied)</span>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (attr of store.proposal()!.proposedChanges; track attr.attributeName) {
                  <tr class="hover:bg-slate-50/80 transition-colors group">
                    
                    <!-- Attribute Name -->
                    <td class="py-3.5 px-4.5 min-w-[180px]">
                      <div class="flex flex-col gap-1">
                        <div class="flex items-center gap-1.5 flex-wrap">
                          <span class="font-mono font-bold text-slate-900">{{ attr.attributeName }}</span>
                          @if (attr.isKey) {
                            <span class="px-1.5 py-0.5 rounded-md text-[9.5px] font-bold font-mono bg-blue-100 text-blue-800 border border-blue-200">
                              KEY
                            </span>
                          }
                          @if (attr.isSensitive) {
                            <span class="px-1.5 py-0.5 rounded-md text-[9.5px] font-bold font-mono bg-amber-100 text-amber-800 border border-amber-200">
                              PROTECTED
                            </span>
                          }
                        </div>
                        @if (attr.sourceType) {
                          <span class="font-mono text-[10px] text-slate-400">{{ attr.sourceType }}</span>
                        }
                        @if (attr.transformationNote) {
                          <span class="text-[10.5px] text-slate-500 italic">{{ attr.transformationNote }}</span>
                        }
                      </div>
                    </td>

                    <!-- Source Value -->
                    <td class="py-3.5 px-4.5 min-w-[220px]">
                      <div class="flex items-center justify-between gap-2 group/src">
                        <div class="min-w-0">
                          @if (attr.sourceValueKind === 'NULL') {
                            <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 font-mono text-[11px] font-semibold border border-slate-200">NULL</span>
                          } @else if (attr.sourceValueKind === 'ABSENT') {
                            <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-400 font-mono text-[11px] italic border border-slate-200">Absent</span>
                          } @else if (attr.sourceValueKind === 'PROTECTED') {
                            <span class="font-mono text-slate-700 select-none bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200 font-bold tracking-widest text-[11px]">{{ attr.sourceValue }}</span>
                          } @else {
                            <span class="font-mono text-slate-800 break-all select-text font-medium">{{ attr.sourceValue }}</span>
                          }
                        </div>
                        @if (attr.sourceValue !== null && attr.sourceValueKind !== 'ABSENT' && !attr.isSensitive) {
                          <button
                            type="button"
                            (click)="copyValue(attr.attributeName + '_src', attr.sourceValue)"
                            class="opacity-0 group-hover/src:opacity-100 p-1 text-slate-400 hover:text-slate-700 transition-opacity cursor-pointer shrink-0 rounded hover:bg-slate-100"
                            title="Copy source value">
                            <app-lucide-icon [name]="copiedKey === attr.attributeName + '_src' ? 'check' : 'copy'" [size]="12"></app-lucide-icon>
                          </button>
                        }
                      </div>
                    </td>

                    <!-- Current Target Value (Observed) -->
                    <td class="py-3.5 px-4.5 min-w-[220px] bg-amber-50/30 border-l border-r border-amber-200/40">
                      <div class="flex items-center justify-between gap-2 group/cur">
                        <div class="min-w-0">
                          @if (attr.currentTargetValueKind === 'NULL') {
                            <span class="px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 font-mono text-[11px] font-semibold border border-amber-200">NULL</span>
                          } @else if (attr.currentTargetValueKind === 'ABSENT') {
                            <span class="px-2 py-0.5 rounded-md bg-rose-100 text-rose-800 font-mono text-[11px] font-semibold border border-rose-200">Missing on Target</span>
                          } @else if (attr.currentTargetValueKind === 'PROTECTED') {
                            <span class="font-mono text-amber-900 select-none bg-amber-100 px-2 py-0.5 rounded-md border border-amber-200 font-bold tracking-widest text-[11px]">{{ attr.currentTargetValue }}</span>
                          } @else {
                            <span class="font-mono text-amber-950 break-all select-text font-medium">{{ attr.currentTargetValue }}</span>
                          }
                        </div>
                        @if (attr.currentTargetValue !== null && attr.currentTargetValueKind !== 'ABSENT' && !attr.isSensitive) {
                          <button
                            type="button"
                            (click)="copyValue(attr.attributeName + '_cur', attr.currentTargetValue)"
                            class="opacity-0 group-hover/cur:opacity-100 p-1 text-amber-600 hover:text-amber-900 transition-opacity cursor-pointer shrink-0 rounded hover:bg-amber-100/60"
                            title="Copy current target value">
                            <app-lucide-icon [name]="copiedKey === attr.attributeName + '_cur' ? 'check' : 'copy'" [size]="12"></app-lucide-icon>
                          </button>
                        }
                      </div>
                    </td>

                    <!-- Proposed Target Value (If Applied) -->
                    <td class="py-3.5 px-4.5 min-w-[240px] bg-blue-50/30">
                      <div class="flex items-center justify-between gap-2 group/prop">
                        <div class="min-w-0">
                          @if (attr.proposedTargetValueKind === 'NULL') {
                            <span class="px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 font-mono text-[11px] font-semibold border border-blue-200">NULL</span>
                          } @else if (attr.proposedTargetValueKind === 'ABSENT') {
                            <span class="px-2 py-0.5 rounded-md bg-red-100 text-red-800 font-mono text-[11px] font-semibold border border-red-200">Deleted on Target</span>
                          } @else if (attr.proposedTargetValueKind === 'PROTECTED') {
                            <span class="font-mono text-blue-900 select-none bg-blue-100 px-2 py-0.5 rounded-md border border-blue-200 font-bold tracking-widest text-[11px]">{{ attr.proposedTargetValue }}</span>
                          } @else {
                            <span class="font-mono text-blue-950 break-all select-text font-bold">{{ attr.proposedTargetValue }}</span>
                          }
                        </div>
                        @if (attr.proposedTargetValue !== null && attr.proposedTargetValueKind !== 'ABSENT' && !attr.isSensitive) {
                          <button
                            type="button"
                            (click)="copyValue(attr.attributeName + '_prop', attr.proposedTargetValue)"
                            class="opacity-0 group-hover/prop:opacity-100 p-1 text-blue-600 hover:text-blue-900 transition-opacity cursor-pointer shrink-0 rounded hover:bg-blue-100/60"
                            title="Copy proposed target value">
                            <app-lucide-icon [name]="copiedKey === attr.attributeName + '_prop' ? 'check' : 'copy'" [size]="12"></app-lucide-icon>
                          </button>
                        }
                      </div>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>

        </div>
      }

      <!-- Impact Metrics & Risk Callout Grid -->
      @if (store.impact(); as imp) {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          
          <!-- Impact Metric 1: Objects & Records -->
          <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-2.5 shadow-2xs">
            <div class="flex items-center gap-2 text-slate-600">
              <app-lucide-icon name="layers" [size]="14"></app-lucide-icon>
              <span class="text-xs font-bold uppercase tracking-wider font-heading">Affected Scope</span>
            </div>
            <div class="flex items-center gap-2 text-xs font-bold text-slate-900 mt-0.5">
              <span class="font-mono text-sm text-blue-600">{{ imp.affectedObjectsCount }}</span>
              <span>Objects</span>
              <span class="text-slate-400">&bull;</span>
              <span class="font-mono text-sm text-blue-600">{{ imp.affectedRecordsCount }}</span>
              <span>Records</span>
            </div>
            <span class="text-xs text-slate-500 leading-relaxed">{{ imp.estimatedWriteScope }}</span>
          </div>

          <!-- Impact Metric 2: Target Endpoint -->
          <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-2.5 shadow-2xs">
            <div class="flex items-center gap-2 text-slate-600">
              <app-lucide-icon name="server" [size]="14"></app-lucide-icon>
              <span class="text-xs font-bold uppercase tracking-wider font-heading">Target System</span>
            </div>
            <span class="text-xs font-bold text-slate-900 leading-snug break-words mt-0.5" [title]="imp.targetSystem">
              {{ imp.targetSystem }}
            </span>
            <span class="text-[11px] font-mono text-slate-500 break-all leading-normal" [title]="imp.targetLocation">
              {{ imp.targetLocation }}
            </span>
          </div>

          <!-- Impact Metric 3: Protected Data -->
          <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-2.5 shadow-2xs">
            <div class="flex items-center gap-2 text-slate-600">
              <app-lucide-icon name="shield" [size]="14"></app-lucide-icon>
              <span class="text-xs font-bold uppercase tracking-wider font-heading">Protected Data Control</span>
            </div>
            <div class="flex items-center gap-2 text-xs font-bold mt-0.5">
              @if (imp.protectedDataInvolved) {
                <app-lucide-icon name="shield-alert" [size]="14" class="text-amber-600"></app-lucide-icon>
                <span class="text-amber-800">Sensitive Data Involved</span>
              } @else {
                <app-lucide-icon name="shield-check" [size]="14" class="text-emerald-600"></app-lucide-icon>
                <span class="text-emerald-800">No Sensitive Data</span>
              }
            </div>
            <span class="text-xs text-slate-500 leading-relaxed">
              {{ imp.protectedDataInvolved ? 'Fail-closed masking enforced' : 'Standard schema attributes' }}
            </span>
          </div>

          <!-- Impact Metric 4: Revalidation Obligation -->
          <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-2.5 shadow-2xs">
            <div class="flex items-center gap-2 text-slate-600">
              <app-lucide-icon name="refresh-cw" [size]="14"></app-lucide-icon>
              <span class="text-xs font-bold uppercase tracking-wider font-heading">Revalidation Obligation</span>
            </div>
            <span class="text-xs font-bold text-slate-900 leading-relaxed break-words mt-0.5">
              {{ imp.revalidationObligation }}
            </span>
            <span class="text-[11px] text-slate-500">Mandatory return to Validation #11</span>
          </div>

        </div>

        <!-- Risk Level Detail Banner -->
        <div [ngClass]="getRiskBannerClass(imp.riskLevel)" class="p-4.5 sm:p-5 rounded-xl border flex items-start gap-3.5">
          <div class="shrink-0 mt-0.5">
            <app-lucide-icon [name]="getRiskIcon(imp.riskLevel)" [size]="20"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-xs font-bold font-heading uppercase tracking-wider">
              Risk Evaluation: {{ formatRiskLevel(imp.riskLevel) }}
            </span>
            <p class="text-xs leading-relaxed opacity-90 font-normal">
              {{ imp.riskExplanation }}
            </p>
          </div>
        </div>
      }

    </section>
  `
})
export class RepairPreviewCardComponent {
  readonly store = inject(ValidationRepairService);
  copiedKey: string | null = null;

  copyValue(key: string, val: any): void {
    if (navigator?.clipboard && val !== null && val !== undefined) {
      navigator.clipboard.writeText(String(val));
      this.copiedKey = key;
      setTimeout(() => { this.copiedKey = null; }, 2000);
    }
  }

  formatRiskLevel(risk: RepairRiskLevel): string {
    switch (risk) {
      case 'LOW': return 'Low Consequence';
      case 'MEDIUM': return 'Moderate Consequence';
      case 'HIGH': return 'High Consequence';
      case 'CONSEQUENTIAL_DESTRUCTIVE': return 'Destructive Action (Permanent Deletion)';
      default: return risk;
    }
  }

  getRiskBadgeClass(risk: RepairRiskLevel): string {
    switch (risk) {
      case 'LOW': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'MEDIUM': return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'HIGH': return 'bg-amber-50 border-amber-200 text-amber-800';
      case 'CONSEQUENTIAL_DESTRUCTIVE': return 'bg-red-50 border-red-200 text-red-800';
      default: return 'bg-slate-100 border-slate-200 text-slate-700';
    }
  }

  getRiskIcon(risk: RepairRiskLevel): string {
    switch (risk) {
      case 'LOW': return 'shield-check';
      case 'MEDIUM': return 'info';
      case 'HIGH': return 'alert-triangle';
      case 'CONSEQUENTIAL_DESTRUCTIVE': return 'trash-2';
      default: return 'shield';
    }
  }

  getRiskBannerClass(risk: RepairRiskLevel): string {
    switch (risk) {
      case 'LOW': return 'bg-emerald-50/60 border-emerald-200 text-emerald-900';
      case 'MEDIUM': return 'bg-blue-50/60 border-blue-200 text-blue-900';
      case 'HIGH': return 'bg-amber-50/60 border-amber-200 text-amber-900';
      case 'CONSEQUENTIAL_DESTRUCTIVE': return 'bg-red-50/60 border-red-200 text-red-900';
      default: return 'bg-slate-50 border-slate-200 text-slate-800';
    }
  }
}
