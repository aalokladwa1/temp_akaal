/**
 * AKAAL Administration — 5.7 Register Execution Site
 * Dedicated centered form page for registering a compute execution site.
 */

import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { ExecutionSiteType } from '../../models/infrastructure.models';

@Component({
  selector: 'app-site-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Navigation -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/compute/sites" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Execution Sites
          </a>
        </div>

        <div class="pb-5 border-b border-slate-200">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Register Execution Site</h1>
          <p class="text-sm font-medium text-slate-600 mt-1">
            Specify worker placement boundaries, maximum concurrency limits, and regional placement for execution fleets.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <form (ngSubmit)="onSubmit()" class="flex flex-col gap-5">
          
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Site Display Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.name"
              name="name"
              required
              placeholder="e.g. AWS eu-central-1 Frankfurt Dedicated Fleet"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Site Deployment Type <span class="text-rose-500">*</span>
              </label>
              <app-custom-select
                [options]="typeOptions"
                [value]="selectedType()"
                (valueChange)="selectedType.set($event)"
                placeholder="Select Site Type">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Placement Region Code <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.region"
                name="region"
                required
                placeholder="e.g. eu-central-1"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Provider / Datacenter Name <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.providerOrDatacenter"
                name="providerOrDatacenter"
                required
                placeholder="e.g. AWS Frankfurt VPC or Equinix FR2"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Max Parallel Worker Limit <span class="text-rose-500">*</span>
              </label>
              <input
                type="number"
                [(ngModel)]="formData.maxParallelJobs"
                name="maxParallelJobs"
                min="1"
                max="128"
                required
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <a
              routerLink="/administration/infrastructure/compute/sites"
              class="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer">
              Cancel
            </a>
            <button
              type="submit"
              [disabled]="!formData.name || !formData.region || !formData.providerOrDatacenter"
              class="px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-2xs transition-colors cursor-pointer">
              Register Execution Site
            </button>
          </div>

        </form>
      </div>

    </div>
  `
})
export class SiteCreateComponent {
  private service = inject(InfrastructureService);
  private router = inject(Router);

  public selectedType = signal<string>('CLOUD_HOSTED');

  public typeOptions: SelectOption[] = [
    { label: 'Cloud Hosted Fleet (AWS/Azure/GCP/OCI)', value: 'CLOUD_HOSTED' },
    { label: 'Customer Dedicated VPC / VNet', value: 'CUSTOMER_VPC' },
    { label: 'On-Premises Enterprise Datacenter', value: 'ON_PREMISES_DATACENTER' }
  ];

  public formData = {
    name: '',
    region: 'us-east-1',
    providerOrDatacenter: '',
    maxParallelJobs: 32
  };

  public onSubmit(): void {
    if (!this.formData.name || !this.formData.providerOrDatacenter) return;

    this.service.createExecutionSite({
      name: this.formData.name,
      siteType: this.selectedType() as ExecutionSiteType,
      region: this.formData.region,
      providerOrDatacenter: this.formData.providerOrDatacenter,
      maxParallelJobs: this.formData.maxParallelJobs
    });

    this.router.navigate(['/administration/infrastructure/compute/sites']);
  }
}
