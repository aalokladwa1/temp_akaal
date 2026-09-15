/**
 * AKAAL Administration — 5.9 Audit Export
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-audit-export',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/audit"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">AUDIT</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">DATA EXPORT</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Audit Export</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Package and export filtered administrative and operational audit records into standardized archival formats.
          </p>
        </div>
      </div>

      <!-- Export Trigger Panel -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
        <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Request New Export Package</h2>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Format</label>
            <app-custom-select
              [options]="formatOptions"
              [value]="selectedFormat"
              (valueChange)="selectedFormat = $event">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Date Range Window</label>
            <input
              type="text"
              [(ngModel)]="dateRange"
              placeholder="e.g. 2026-02-01 to 2026-02-18"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>

          <div>
            <button
              type="button"
              (click)="onGenerate()"
              class="h-10 px-5 w-full rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
              Generate Export Package
            </button>
          </div>
        </div>
      </div>

      <!-- Historical Exports Table -->
      <div class="flex flex-col gap-3">
        <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Generated Export Packages</h2>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
                <th class="py-3.5 px-4">Export ID</th>
                <th class="py-3.5 px-4">Date Range Scope</th>
                <th class="py-3.5 px-4">Format</th>
                <th class="py-3.5 px-4">Record Count</th>
                <th class="py-3.5 px-4">Package Size</th>
                <th class="py-3.5 px-4">Requested By</th>
                <th class="py-3.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 text-xs">
              @for (exp of auditService.exportRequests(); track exp.id) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ exp.id }}</td>
                  <td class="py-3.5 px-4 text-slate-700">{{ exp.dateRange }}</td>
                  <td class="py-3.5 px-4 font-mono text-[11px] text-slate-700">{{ exp.format }}</td>
                  <td class="py-3.5 px-4 font-semibold text-slate-900">{{ exp.recordCount.toLocaleString() }}</td>
                  <td class="py-3.5 px-4 text-slate-600">{{ exp.downloadSize }}</td>
                  <td class="py-3.5 px-4 text-slate-600">{{ exp.requestedBy }}</td>
                  <td class="py-3.5 px-4">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {{ exp.status }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class AuditExportComponent {
  public auditService = inject(AuditService);

  public selectedFormat: 'JSON' | 'CSV' | 'ZIP' = 'JSON';
  public dateRange = 'Last 30 Days';

  public formatOptions: SelectOption[] = [
    { label: 'Structured JSON Package (.json)', value: 'JSON' },
    { label: 'Comma-Separated Values (.csv)', value: 'CSV' },
    { label: 'Compressed Evidence Archive (.zip)', value: 'ZIP' }
  ];

  public onGenerate(): void {
    this.auditService.triggerExport(this.selectedFormat, this.dateRange);
  }
}
