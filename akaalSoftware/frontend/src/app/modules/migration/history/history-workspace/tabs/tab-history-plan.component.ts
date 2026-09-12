import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { PlanRevision, PlanConfigSection, PlanDiffItem } from '../history-workspace.models';

@Component({
  selector: 'app-tab-history-plan',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-6">
        
        <!-- Plan Identity & Hash Fingerprint Header -->
        <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div class="flex items-center gap-2.5 flex-wrap">
                <h2 class="text-base font-bold text-slate-900">
                  Execution Plan: {{ record.planAndConfig.currentPlanId }}
                </h2>
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Active Execution Plan
                </span>
              </div>
              <div class="mt-2 text-xs text-slate-600 flex items-center gap-2 flex-wrap">
                <span class="font-semibold text-slate-500">Plan Fingerprint:</span>
                <span class="font-mono text-[11px] bg-slate-100 text-slate-800 px-2 py-0.5 rounded border border-slate-200 break-all select-all">
                  {{ record.planAndConfig.planFingerprint }}
                </span>
              </div>
            </div>

            <div class="text-xs text-slate-500 shrink-0">
              <div>Total Revisions: <strong class="text-slate-800">{{ record.planAndConfig.revisions.length }}</strong></div>
              <div class="mt-0.5">SHA-256 Plan Lock: <strong class="text-emerald-700 font-semibold">Enforced</strong></div>
            </div>
          </div>
        </div>

        <!-- Structured Configuration Sections -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          @for (section of record.planAndConfig.sections; track section.title) {
            <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
              <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1">
                {{ section.title }}
              </h3>
              <p class="text-xs text-slate-500 mb-3">{{ section.description }}</p>

              <dl class="divide-y divide-slate-100 text-xs">
                @for (entry of section.entries; track entry.label) {
                  <div class="py-2 flex items-center justify-between gap-4">
                    <dt class="text-slate-500 font-medium">{{ entry.label }}</dt>
                    <dd class="text-slate-900 text-right font-medium"
                      [ngClass]="entry.mono ? 'font-mono text-[11px]' : ''">
                      {{ entry.value }}
                    </dd>
                  </div>
                }
              </dl>
            </div>
          }
        </div>

        <!-- Plan Revision History & Semantic Diff Comparison -->
        <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4 pb-3 border-b border-slate-100">
            <div>
              <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Plan Revision Semantic Comparison
              </h3>
              <p class="text-xs text-slate-500 mt-0.5">Inspect structural changes and tuning diffs across plan iterations.</p>
            </div>

            <!-- Revision Diff Selector Controls -->
            <div class="flex items-center gap-2 text-xs">
              <span class="text-slate-500 font-medium">Compare Rev</span>
              <select
                [ngModel]="hws.selectedDiffRevA()"
                (ngModelChange)="hws.selectedDiffRevA.set($event)"
                class="h-8 px-2 text-xs bg-slate-50 border border-slate-300 rounded-md text-slate-800">
                @for (rev of record.planAndConfig.revisions; track rev.revisionNumber) {
                  <option [value]="rev.revisionNumber">Rev {{ rev.revisionNumber }}</option>
                }
              </select>
              <span class="text-slate-400">with</span>
              <select
                [ngModel]="hws.selectedDiffRevB()"
                (ngModelChange)="hws.selectedDiffRevB.set($event)"
                class="h-8 px-2 text-xs bg-slate-50 border border-slate-300 rounded-md text-slate-800">
                @for (rev of record.planAndConfig.revisions; track rev.revisionNumber) {
                  <option [value]="rev.revisionNumber">Rev {{ rev.revisionNumber }}</option>
                }
              </select>
            </div>
          </div>

          <!-- Diffs Table / List -->
          @if (record.planAndConfig.semanticDiffs.length > 0) {
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                    <th class="py-2.5 px-4">Parameter / Field</th>
                    <th class="py-2.5 px-4">Category</th>
                    <th class="py-2.5 px-4">Old Value (Rev {{ hws.selectedDiffRevA() }})</th>
                    <th class="py-2.5 px-4">New Value (Rev {{ hws.selectedDiffRevB() }})</th>
                    <th class="py-2.5 px-4 text-right">Impact</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (diff of record.planAndConfig.semanticDiffs; track diff.fieldName) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-3 px-4 font-mono text-slate-900 font-medium">{{ diff.fieldName }}</td>
                      <td class="py-3 px-4">{{ diff.category }}</td>
                      <td class="py-3 px-4 font-mono text-rose-700 bg-rose-50/50">{{ diff.oldValue }}</td>
                      <td class="py-3 px-4 font-mono text-emerald-700 bg-emerald-50/50">{{ diff.newValue }}</td>
                      <td class="py-3 px-4 text-right">
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border"
                          [ngClass]="getImpactBadgeClass(diff.impactLevel)">
                          {{ diff.impactLevel }}
                        </span>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <div class="py-8 text-center text-xs text-slate-500">
              <div class="font-medium text-slate-700">Zero Semantic Divergence</div>
              <p class="text-slate-400 mt-0.5">Execution plan executed strictly on immutable compiled revision 1 without in-flight parameter drift.</p>
            </div>
          }
        </div>

      </div>
    }
  `
})
export class TabHistoryPlanComponent {
  public hws = inject(HistoryWorkspaceService);

  public getImpactBadgeClass(impact: string): string {
    switch (impact) {
      case 'CRITICAL': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'MODERATE': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'INFORMATIONAL':
      default: return 'bg-blue-50 text-blue-700 border-blue-200';
    }
  }
}
