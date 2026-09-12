/**
 * AKAAL Administration — 5.8 Request Compliance Exception
 * Centered single-task request form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-exception-request',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/compliance/controls/exceptions"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">COMPLIANCE EXCEPTIONS</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">REQUEST WAIVER</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Request Compliance Exception</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Formal submission for a time-bounded exception to a regulatory control requirement.
          </p>
        </div>
      </div>

      <!-- Centered Form Container -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Exception Title</label>
          <input
            type="text"
            [(ngModel)]="title"
            placeholder="e.g. Legacy Ingestion Service Certificate Authentication"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Control Code Reference</label>
            <input
              type="text"
              [(ngModel)]="controlCode"
              placeholder="e.g. HIPAA-164.312(a)"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Proposed Expiration Date</label>
            <input
              type="date"
              [(ngModel)]="validUntil"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Scope & Affected Workloads</label>
          <input
            type="text"
            [(ngModel)]="scope"
            placeholder="e.g. Service Account: svc-batch-importer-01 under VPC-01"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Reason for Non-Compliance</label>
          <textarea
            rows="3"
            [(ngModel)]="reason"
            placeholder="Explain why standard control requirements cannot be satisfied currently..."
            class="p-3 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"></textarea>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Compensating Technical Safeguards & Justification</label>
          <textarea
            rows="3"
            [(ngModel)]="justification"
            placeholder="Detail alternative controls in place that mitigate the underlying security risk..."
            class="p-3 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"></textarea>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/compliance/controls/exceptions"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Submit Exception Request
          </button>
        </div>

      </div>

    </div>
  `
})
export class ExceptionRequestComponent {
  private complianceService = inject(ComplianceService);
  private router = inject(Router);

  public title = '';
  public controlCode = '';
  public validUntil = '2026-12-31';
  public scope = '';
  public reason = '';
  public justification = '';

  public isValid(): boolean {
    return (
      this.title.trim().length > 0 &&
      this.controlCode.trim().length > 0 &&
      this.scope.trim().length > 0 &&
      this.justification.trim().length > 0
    );
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    this.complianceService.createException({
      code: `EXC-2026-${Math.floor(100 + Math.random() * 900)}`,
      title: this.title.trim(),
      frameworkId: 'fw-hipaa',
      controlCode: this.controlCode.trim().toUpperCase(),
      reason: this.reason.trim(),
      scope: this.scope.trim(),
      justification: this.justification.trim(),
      approvedBy: 'Pending Security Review',
      validUntil: this.validUntil
    });
    this.router.navigate(['/administration/compliance/controls/exceptions']);
  }
}
