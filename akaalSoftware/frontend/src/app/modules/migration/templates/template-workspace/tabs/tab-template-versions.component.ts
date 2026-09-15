import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-tab-template-versions',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 text-xs font-sans animate-in fade-in duration-150">
      
      @if (ws.template(); as tmpl) {
        
        <!-- SECTION 1: CURRENT ACTIVE REVISION CARD -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex items-center gap-2.5">
              <span class="font-bold text-slate-900 text-sm">Current Active Revision</span>
              <span class="px-2.5 py-0.5 text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
                {{ tmpl.versionLabel }}
              </span>
              <span class="px-2 py-0.5 text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md">
                {{ tmpl.lifecycle }}
              </span>
            </div>

            <button
              type="button"
              (click)="ws.openNewVersionDialog()"
              class="h-8 px-4 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors cursor-pointer shadow-2xs">
              Create new version
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Revision Number</span>
              <span class="font-bold text-slate-900 text-xs">Revision {{ tmpl.revisionNumber }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Published At</span>
              <span class="font-medium text-slate-800">{{ tmpl.updatedAt | date:'medium' }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Published By</span>
              <span class="font-medium text-slate-800">{{ tmpl.lastUpdatedBy }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Materialized Migrations</span>
              <span class="font-mono font-bold text-slate-900">{{ tmpl.usage.migrationCount }} migrations active</span>
            </div>
          </div>
        </div>

        <!-- SECTION 2: VERSION HISTORY TABLE -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <div class="flex flex-col">
              <span class="font-bold text-slate-900 text-sm">Version Lineage & History</span>
              <span class="text-xs text-slate-500 font-normal">Immutable audit records of all historical revisions of this template.</span>
            </div>
            <span class="text-[10px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
              {{ tmpl.versions.length }} Revisions Recorded
            </span>
          </div>

          <div class="overflow-x-auto border border-slate-200 rounded-md">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase">
                  <th class="px-3 py-2.5">Version / Revision</th>
                  <th class="px-3 py-2.5">Lifecycle State</th>
                  <th class="px-3 py-2.5">Created Date</th>
                  <th class="px-3 py-2.5">Author</th>
                  <th class="px-3 py-2.5">Change Summary</th>
                  <th class="px-3 py-2.5 text-right">Migrations</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (v of tmpl.versions; track v.versionLabel) {
                  <tr class="hover:bg-slate-50/70 transition-colors">
                    <td class="px-3 py-2.5 font-mono font-bold text-slate-900 flex items-center gap-2">
                      <span>{{ v.versionLabel }}</span>
                      @if (v.isCurrent) {
                        <span class="px-1.5 py-0.2 text-[9px] font-bold bg-blue-50 text-blue-700 border border-blue-200 rounded">
                          CURRENT
                        </span>
                      }
                    </td>
                    <td class="px-3 py-2.5">
                      <span
                        class="px-2 py-0.5 text-[10px] font-bold rounded-md"
                        [class.bg-emerald-50]="v.lifecycle === 'PUBLISHED'"
                        [class.text-emerald-700]="v.lifecycle === 'PUBLISHED'"
                        [class.border-emerald-200]="v.lifecycle === 'PUBLISHED'"
                        [class.bg-slate-100]="v.lifecycle === 'ARCHIVED'"
                        [class.text-slate-700]="v.lifecycle === 'ARCHIVED'"
                        [class.border-slate-200]="v.lifecycle === 'ARCHIVED'">
                        {{ v.lifecycle }}
                      </span>
                    </td>
                    <td class="px-3 py-2.5 text-slate-600">{{ v.createdAt | date:'mediumDate' }}</td>
                    <td class="px-3 py-2.5 text-slate-700 font-medium">{{ v.createdBy }}</td>
                    <td class="px-3 py-2.5 text-slate-600">{{ v.changeSummary }}</td>
                    <td class="px-3 py-2.5 text-right font-mono font-bold text-slate-900">{{ v.usageCount }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <!-- SECTION 3: INTERACTIVE VERSION COMPARISON & SEMANTIC DIFF -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-3">
            <div class="flex flex-col">
              <span class="font-bold text-slate-900 text-sm">Semantic Configuration Diff Engine</span>
              <span class="text-xs text-slate-500 font-normal">Compare configuration parameters between any two template revisions.</span>
            </div>

            <!-- Version Selectors -->
            <div class="flex items-center gap-2">
              <div class="w-56">
                <app-custom-select
                  size="sm"
                  [options]="versionOptions"
                  [ngModel]="ws.selectedBaseVersion()"
                  (ngModelChange)="ws.selectedBaseVersion.set($event)">
                </app-custom-select>
              </div>

              <span class="text-slate-500 font-bold">&rarr;</span>

              <div class="w-56">
                <app-custom-select
                  size="sm"
                  [options]="versionOptions"
                  [ngModel]="ws.selectedCompareVersion()"
                  (ngModelChange)="ws.selectedCompareVersion.set($event)">
                </app-custom-select>
              </div>
            </div>
          </div>

          <!-- Diff Metric Strip -->
          @if (ws.diffResult(); as diff) {
            <div class="flex items-center gap-3">
              <span class="text-xs font-bold text-slate-700">Comparing {{ diff.baseVersion }} vs {{ diff.compareVersion }}:</span>
              <span class="px-2 py-0.5 text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">
                +{{ diff.totalAdded }} added
              </span>
              <span class="px-2 py-0.5 text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 rounded">
                ~{{ diff.totalModified }} modified
              </span>
              <span class="px-2 py-0.5 text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200 rounded">
                -{{ diff.totalRemoved }} removed
              </span>
            </div>

            <!-- Diff Table -->
            <div class="overflow-x-auto border border-slate-200 rounded-md">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase">
                    <th class="px-3 py-2">Category</th>
                    <th class="px-3 py-2">Parameter</th>
                    <th class="px-3 py-2">Base ({{ diff.baseVersion }})</th>
                    <th class="px-3 py-2">Compare ({{ diff.compareVersion }})</th>
                    <th class="px-3 py-2 text-right">Change</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  @for (c of diff.changes; track c.fieldLabel) {
                    <tr class="hover:bg-slate-50/70 transition-colors">
                      <td class="px-3 py-2 font-semibold text-slate-800">{{ c.category }}</td>
                      <td class="px-3 py-2 font-medium text-slate-900">{{ c.fieldLabel }}</td>
                      <td class="px-3 py-2 font-mono text-slate-500 bg-slate-50/50">{{ c.oldValue }}</td>
                      <td class="px-3 py-2 font-mono font-semibold text-slate-900 bg-blue-50/30">{{ c.newValue }}</td>
                      <td class="px-3 py-2 text-right">
                        <span
                          class="px-2 py-0.5 text-[9px] font-bold rounded"
                          [class.bg-emerald-50]="c.changeType === 'ADDED'"
                          [class.text-emerald-700]="c.changeType === 'ADDED'"
                          [class.bg-amber-50]="c.changeType === 'MODIFIED'"
                          [class.text-amber-700]="c.changeType === 'MODIFIED'"
                          [class.bg-rose-50]="c.changeType === 'REMOVED'"
                          [class.text-rose-700]="c.changeType === 'REMOVED'">
                          {{ c.changeType }}
                        </span>
                      </td>
                    </tr>
                  }
                  @if (diff.changes.length === 0) {
                    <tr>
                      <td colspan="5" class="py-4 text-center text-slate-400 text-xs">
                        No configuration differences detected between {{ diff.baseVersion }} and {{ diff.compareVersion }}.
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }

        </div>

      }

    </div>
  `
})
export class TabTemplateVersionsComponent {
  public ws = inject(TemplateWorkspaceService);

  public get versionOptions(): CustomSelectOption[] {
    const tmpl = this.ws.template();
    if (!tmpl || !tmpl.versions) return [];
    return tmpl.versions.map(v => ({
      label: `${v.versionLabel} (${v.lifecycle})`,
      value: v.versionLabel
    }));
  }
}
