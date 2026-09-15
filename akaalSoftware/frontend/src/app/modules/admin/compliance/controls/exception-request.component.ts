/**
 * AKAAL Administration — 5.8 Request Compliance Exception
 * Centered single-task request form.
 */

import { Component, inject, Optional, signal } from '@angular/core';
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

        <!-- Error alert banner -->
        @if (submissionError()) {
          <div class="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-amber-900 animate-in fade-in duration-150">
            <div class="w-6 h-6 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 mt-0.5">
              <app-lucide-icon name="alert-triangle" [size]="15"></app-lucide-icon>
            </div>
            <div class="flex flex-col gap-0.5 text-xs">
              <span class="font-bold">Governance Engine Unavailable</span>
              <span class="text-amber-800 font-sans">{{ submissionError() }}</span>
            </div>
          </div>
        }

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
            [disabled]="!isValid() || isSubmitting()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            @if (!isSubmitting()) {
              <span>Submit Exception Request</span>
            } @else {
              <span>Submitting...</span>
            }
          </button>
        </div>

      </div>

    </div>
  `
})
export class ExceptionRequestComponent {
  private complianceService?: ComplianceService;
  private router?: Router;

  constructor(
    @Optional() complianceService?: ComplianceService,
    @Optional() router?: Router
  ) {
    if (complianceService) {
      this.complianceService = complianceService;
    } else {
      try {
        this.complianceService = inject(ComplianceService, { optional: true }) || undefined;
      } catch {
        this.complianceService = undefined;
      }
    }

    if (router) {
      this.router = router;
    } else {
      try {
        this.router = inject(Router, { optional: true }) || undefined;
      } catch {
        this.router = undefined;
      }
    }
  }

  public title = '';
  public controlCode = '';
  public validUntil = '2026-12-31';
  public scope = '';
  public reason = '';
  public justification = '';

  public submissionError = signal<string | null>(null);
  public isSubmitting = signal<boolean>(false);

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
    this.isSubmitting.set(true);
    this.submissionError.set(null);

    setTimeout(() => {
      this.isSubmitting.set(false);
      // Fail closed when backend governance engine is unavailable:
      this.submissionError.set('Compliance exception submission requires active governance engine connectivity.');
    }, 400);
  }
}
