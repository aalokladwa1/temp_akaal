/**
 * AKAAL Administration — Edit Enterprise Settings
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../services/enterprise.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-enterprise-settings-edit',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/enterprise/settings" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Enterprise Settings
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Edit Enterprise Settings</h1>
            <p class="text-sm font-medium text-slate-600">
              Update tenant baseline parameters, compliance tier, and session thresholds.
            </p>
          </div>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Legal Entity Name</label>
            <input
              type="text"
              [(ngModel)]="legalEntityName"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Primary Domain</label>
            <input
              type="text"
              [(ngModel)]="primaryDomain"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Global Compliance Tier</label>
            <app-custom-select
              [options]="complianceOptions"
              [(ngModel)]="globalComplianceTier">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Session Timeout (Minutes)</label>
            <input
              type="number"
              [(ngModel)]="sessionTimeoutMinutes"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/enterprise/settings"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
            Cancel
          </a>
          <button
            (click)="save()"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs cursor-pointer">
            Save Settings
          </button>
        </div>
      </div>
    </div>
  `
})
export class EnterpriseSettingsEditComponent {
  private router = inject(Router);
  public enterprise = inject(EnterpriseService);

  public legalEntityName = '';
  public primaryDomain = '';
  public globalComplianceTier: any = 'FINANCIAL_STRICT_SOC2_PCI';
  public sessionTimeoutMinutes = 60;

  public complianceOptions: CustomSelectOption[] = [
    { label: 'Financial Strict SOC2 & PCI', value: 'FINANCIAL_STRICT_SOC2_PCI' },
    { label: 'Healthcare HIPAA', value: 'HEALTHCARE_HIPAA' },
    { label: 'Gov Cloud FedRAMP', value: 'GOV_CLOUD_FEDRAMP' },
    { label: 'Enterprise Standard', value: 'ENTERPRISE_STANDARD' }
  ];

  constructor() {
    const s = this.enterprise.settings();
    this.legalEntityName = s.legalEntityName;
    this.primaryDomain = s.primaryDomain;
    this.globalComplianceTier = s.globalComplianceTier;
    this.sessionTimeoutMinutes = s.securityBaseline.sessionTimeoutMinutes;
  }

  public save() {
    this.enterprise.updateSettings({
      legalEntityName: this.legalEntityName,
      primaryDomain: this.primaryDomain,
      globalComplianceTier: this.globalComplianceTier,
      securityBaseline: {
        ...this.enterprise.settings().securityBaseline,
        sessionTimeoutMinutes: this.sessionTimeoutMinutes
      }
    });
    this.router.navigate(['/administration/enterprise/settings']);
  }
}
