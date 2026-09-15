/**
 * AKAAL Administration — 5.8 Create Custom Framework Form
 * Centered single-task creation form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-custom-framework-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/compliance/frameworks/custom"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">CUSTOM FRAMEWORKS</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">NEW SPECIFICATION</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Create Custom Framework</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Register an enterprise policy standard, jurisdictional baseline, or sovereign audit checklist.
          </p>
        </div>
      </div>

      <!-- Centered Form Container -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Framework Name</label>
          <input
            type="text"
            [(ngModel)]="name"
            placeholder="e.g. Sovereign Healthcare Ingestion Standard"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Specification Code</label>
            <input
              type="text"
              [(ngModel)]="code"
              placeholder="e.g. CORP-HEALTH-SEC-01"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Specification Version</label>
            <input
              type="text"
              [(ngModel)]="version"
              placeholder="e.g. 1.0.0"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Authoritative Owner</label>
          <input
            type="text"
            [(ngModel)]="authorityOwner"
            placeholder="e.g. Enterprise Security Architecture Council"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Description & Scope</label>
          <textarea
            rows="4"
            [(ngModel)]="description"
            placeholder="Provide technical rationale, applicability boundaries, and audit intent..."
            class="p-3 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"></textarea>
        </div>

        <!-- Form Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/compliance/frameworks/custom"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Create Framework
          </button>
        </div>

      </div>

    </div>
  `
})
export class CustomFrameworkCreateComponent {
  private complianceService = inject(ComplianceService);
  private router = inject(Router);

  public name = '';
  public code = '';
  public version = '1.0.0';
  public authorityOwner = '';
  public description = '';

  public isValid(): boolean {
    return this.name.trim().length > 0 && this.code.trim().length > 0 && this.authorityOwner.trim().length > 0;
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    this.complianceService.createCustomFramework({
      name: this.name.trim(),
      code: this.code.trim().toUpperCase(),
      version: this.version.trim(),
      authorityOwner: this.authorityOwner.trim(),
      description: this.description.trim(),
      controlsCount: 0
    });
    this.router.navigate(['/administration/compliance/frameworks/custom']);
  }
}
