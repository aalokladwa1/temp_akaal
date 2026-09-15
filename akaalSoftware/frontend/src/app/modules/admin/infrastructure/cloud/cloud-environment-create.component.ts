/**
 * AKAAL Administration — 5.7 Create Cloud Environment
 * Dedicated centered form page for registering a cloud environment.
 */

import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { CloudProviderType } from '../../models/infrastructure.models';

@Component({
  selector: 'app-cloud-environment-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Navigation -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/cloud/environments" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Cloud Environments
          </a>
        </div>

        <div class="pb-5 border-b border-slate-200">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Create Cloud Environment</h1>
          <p class="text-sm font-medium text-slate-600 mt-1">
            Register a cloud account tenancy, provider credentials reference, and default regional placement zone.
          </p>
        </div>
      </div>

      <!-- Create Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <form (ngSubmit)="onSubmit()" class="flex flex-col gap-5">
          
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Cloud Provider Platform <span class="text-rose-500">*</span>
            </label>
            <app-custom-select
              [options]="providerOptions"
              [value]="selectedProvider()"
              (valueChange)="selectedProvider.set($event)"
              placeholder="Select Cloud Provider">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Environment Display Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.name"
              name="name"
              required
              placeholder="e.g. AWS Secondary Regional Disaster Recovery"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Account ID / Tenancy OCID / Subscription <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.accountIdOrTenant"
                name="accountIdOrTenant"
                required
                placeholder="e.g. 12-digit AWS Account or UUID"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Default Region Code <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.defaultRegion"
                name="defaultRegion"
                required
                placeholder="e.g. us-east-1, eastus2, europe-west3"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Vault Credential Secret Reference <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.credentialRef"
              name="credentialRef"
              required
              placeholder="vault://secret/cloud/aws/dr-role-arn"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            <span class="text-[11px] text-slate-500">Provide the canonical HashiCorp Vault URI reference. Plaintext secret entries are strictly prohibited.</span>
          </div>

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <a
              routerLink="/administration/infrastructure/cloud/environments"
              class="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer">
              Cancel
            </a>
            <button
              type="submit"
              [disabled]="!formData.name || !formData.accountIdOrTenant || !formData.defaultRegion || !formData.credentialRef"
              class="px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-2xs transition-colors cursor-pointer">
              Register Cloud Environment
            </button>
          </div>

        </form>
      </div>

    </div>
  `
})
export class CloudEnvironmentCreateComponent {
  private service = inject(InfrastructureService);
  private router = inject(Router);

  public selectedProvider = signal<string>('AWS');

  public providerOptions: SelectOption[] = [
    { label: 'Amazon Web Services (AWS)', value: 'AWS' },
    { label: 'Microsoft Azure', value: 'AZURE' },
    { label: 'Google Cloud Platform (GCP)', value: 'GCP' },
    { label: 'Oracle Cloud Infrastructure (OCI)', value: 'OCI' }
  ];

  public formData = {
    name: '',
    accountIdOrTenant: '',
    defaultRegion: 'us-east-1',
    credentialRef: 'vault://secret/cloud/aws/role-arn'
  };

  public onSubmit(): void {
    if (!this.formData.name || !this.formData.accountIdOrTenant) return;

    this.service.createCloudEnvironment({
      name: this.formData.name,
      provider: this.selectedProvider() as CloudProviderType,
      accountIdOrTenant: this.formData.accountIdOrTenant,
      defaultRegion: this.formData.defaultRegion,
      credentialRef: this.formData.credentialRef,
      configuredRegions: [this.formData.defaultRegion],
      executionSiteIds: [],
      tags: ['Production', this.selectedProvider()]
    });

    this.router.navigate(['/administration/infrastructure/cloud/environments']);
  }
}
