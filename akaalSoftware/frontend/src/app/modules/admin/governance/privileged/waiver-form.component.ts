import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { GovernanceService } from '../../services/governance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { GovernanceWaiver } from '../../models/governance.models';

@Component({
  selector: 'app-waiver-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/governance-centre/waivers" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Waivers
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Request Governance Waiver</h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Submit a formal policy exception request requiring SecOps review and cryptographic signing.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="saveWaiver()" class="flex flex-col gap-5 text-xs">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Target Policy *</label>
              <app-custom-select
                [options]="policyOptions()"
                [(ngModel)]="formData.targetPolicy"
                name="targetPolicy">
              </app-custom-select>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Target Resource ARN *</label>
              <input type="text" [(ngModel)]="formData.targetResource" name="targetResource" required placeholder="e.g. database/finance_ledger" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Business Justification *</label>
            <textarea [(ngModel)]="formData.justification" name="justification" rows="4" required placeholder="Describe why standard policy compliance cannot be satisfied..." class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white"></textarea>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Submit Waiver Request
            </button>
            <a routerLink="/administration/governance-centre/waivers" class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>
        </form>
      </div>

    </div>
  `
})
export class WaiverFormComponent {
  private router = inject(Router);
  public govService = inject(GovernanceService);

  public policyOptions = computed<CustomSelectOption[]>(() => {
    return this.govService.policies().map(p => ({ label: `${p.name} (${p.code})`, value: p.code }));
  });

  public formData: Partial<GovernanceWaiver> = {
    targetPolicy: 'POL-MASK-001',
    targetResource: '',
    beneficiaryPrincipal: 'Aalok Ladwa',
    justification: ''
  };

  public saveWaiver(): void {
    this.govService.createWaiver(this.formData);
    this.router.navigate(['/administration/governance-centre/waivers']);
  }
}