/**
 * AKAAL Administration — 5.9 Create Legal Hold
 * Centered single-task form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-legal-hold-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/audit/legal-hold"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">LEGAL HOLD</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">NEW PRESERVATION ORDER</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Create Legal Hold</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Impose a binding preservation lock over audit logs and evidence relating to formal litigation or regulatory inquiry.
          </p>
        </div>
      </div>

      <!-- Centered Form -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Matter / Investigation Title</label>
          <input
            type="text"
            [(ngModel)]="matterName"
            placeholder="e.g. SEC Ingestion Pipeline Compliance Inquiry"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Formal Case ID / Docket Reference</label>
            <input
              type="text"
              [(ngModel)]="caseId"
              placeholder="e.g. CIV-2026-9921"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Designated Legal Custodian</label>
            <input
              type="text"
              [(ngModel)]="custodian"
              placeholder="e.g. Office of the General Counsel"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Scope of Preservation</label>
          <textarea
            rows="4"
            [(ngModel)]="scopeDescription"
            placeholder="Detail affected systems, workspace boundaries, user accounts, and target date ranges..."
            class="p-3 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"></textarea>
        </div>

        <!-- Warning Alert Box -->
        <div class="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start gap-3">
          <app-lucide-icon name="alert-triangle" [size]="16" class="shrink-0 text-amber-600 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-1">
            <span class="font-bold">Consequential Legal Preservation Action</span>
            <span>
              Applying this legal hold immediately suspends all automated purge policies, cold disposition routines, and shredding schedules across the specified scope.
            </span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/audit/legal-hold"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Impose Legal Hold
          </button>
        </div>

      </div>

    </div>
  `
})
export class LegalHoldCreateComponent {
  private auditService = inject(AuditService);
  private router = inject(Router);

  public matterName = '';
  public caseId = '';
  public custodian = '';
  public scopeDescription = '';

  public isValid(): boolean {
    return (
      this.matterName.trim().length > 0 &&
      this.caseId.trim().length > 0 &&
      this.custodian.trim().length > 0 &&
      this.scopeDescription.trim().length > 0
    );
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    this.auditService.createLegalHold({
      matterName: this.matterName.trim(),
      caseId: this.caseId.trim().toUpperCase(),
      custodian: this.custodian.trim(),
      scopeDescription: this.scopeDescription.trim()
    });
    this.router.navigate(['/administration/audit/legal-hold']);
  }
}
