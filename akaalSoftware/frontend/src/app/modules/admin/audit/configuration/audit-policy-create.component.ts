/**
 * AKAAL Administration — 5.9 Create Audit Policy
 * Centered single-task form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { AuditPolicyCategory, AuditSeverityFilter } from '../../models/audit.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-audit-policy-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/audit/policies"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">AUDIT POLICIES</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">NEW POLICY</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Create Audit Policy</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Configure audit event scope, filter severity thresholds, and mandatory retention windows.
          </p>
        </div>
      </div>

      <!-- Centered Form -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Policy Name</label>
          <input
            type="text"
            [(ngModel)]="name"
            placeholder="e.g. Identity & Secret Access Mutation Audit"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Audit Category</label>
            <app-custom-select
              [options]="categoryOptions"
              [value]="selectedCategory"
              (valueChange)="selectedCategory = $event">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Severity Filter</label>
            <app-custom-select
              [options]="severityOptions"
              [value]="selectedSeverity"
              (valueChange)="selectedSeverity = $event">
            </app-custom-select>
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Retention Duration (Days)</label>
          <input
            type="number"
            [(ngModel)]="retentionDays"
            min="30"
            max="3650"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Policy Rationale & Description</label>
          <textarea
            rows="3"
            [(ngModel)]="description"
            placeholder="Specify regulatory or security compliance reason for this audit capture profile..."
            class="p-3 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"></textarea>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/audit/policies"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Create Policy
          </button>
        </div>

      </div>

    </div>
  `
})
export class AuditPolicyCreateComponent {
  private auditService = inject(AuditService);
  private router = inject(Router);

  public name = '';
  public selectedCategory: AuditPolicyCategory = 'ADMIN_ACTIONS';
  public selectedSeverity: AuditSeverityFilter = 'ALL';
  public retentionDays = 730;
  public description = '';

  public categoryOptions: SelectOption[] = [
    { label: 'Administrative Actions', value: 'ADMIN_ACTIONS' },
    { label: 'Data Access Operations', value: 'DATA_ACCESS' },
    { label: 'Security Operations & KMS', value: 'SECURITY_OPERATIONS' },
    { label: 'Pipeline Execution & Flow', value: 'PIPELINE_EXECUTION' }
  ];

  public severityOptions: SelectOption[] = [
    { label: 'All Events (Informational & Above)', value: 'ALL' },
    { label: 'Warning & Above Only', value: 'WARNING_AND_ABOVE' },
    { label: 'Errors & Critical Anomalies Only', value: 'ERROR_ONLY' }
  ];

  public isValid(): boolean {
    return this.name.trim().length > 0 && this.retentionDays >= 30;
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    this.auditService.createAuditPolicy({
      name: this.name.trim(),
      category: this.selectedCategory,
      severityFilter: this.selectedSeverity,
      retentionDays: this.retentionDays,
      destinations: ['adest-syslog-01'],
      description: this.description.trim()
    });
    this.router.navigate(['/administration/audit/policies']);
  }
}
