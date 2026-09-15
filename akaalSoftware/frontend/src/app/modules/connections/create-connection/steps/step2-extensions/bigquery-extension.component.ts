import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionDraft } from '../../create-connection.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-bigquery-extension',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-4 select-none">
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Google Cloud Project ID -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Google Cloud Project ID <span class="text-rose-500">*</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.bigqueryProjectId"
            placeholder="enterprise-analytics-prod-01"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          <span class="text-[11px] text-slate-400">
            The GCP project hosting BigQuery datasets and storage API jobs.
          </span>
        </div>

        <!-- Default Dataset (Optional at Connection Level) -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Default Dataset <span class="text-slate-400 font-normal">(Optional)</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.bigqueryDataset"
            placeholder="financial_ledger"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          <span class="text-[11px] text-slate-400">
            Optional default dataset. Migration scope discovery will enumerate all datasets.
          </span>
        </div>

      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Location / Multi-Region Selector -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Dataset Processing Location <span class="text-rose-500">*</span>
          </label>
          <app-custom-select
            [options]="locationOptions"
            [value]="draft.bigqueryLocation"
            (valueChange)="onLocationChange($event)">
          </app-custom-select>
          <span class="text-[11px] text-slate-400">
            Regional or multi-region data residency locality.
          </span>
        </div>

        <!-- Billing Project Override (Optional) -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Billing Project Override <span class="text-slate-400 font-normal">(Optional)</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.bigqueryBillingProject"
            placeholder="central-billing-hub-prod"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          <span class="text-[11px] text-slate-400">
            Override project billed for query slots and Storage Read/Write APIs.
          </span>
        </div>

      </div>

      <!-- Storage Read API & Advanced Options Card -->
      <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Storage Read API Toggle -->
        <div class="flex flex-col justify-center gap-1.5">
          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              [(ngModel)]="draft.bigqueryUseStorageReadApi"
              class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
            <span class="text-xs font-semibold text-slate-800">
              Enable High-Throughput BigQuery Storage Read API
            </span>
          </label>
          <span class="text-[11px] text-slate-500 pl-6">
            Bypasses SQL REST pagination via direct gRPC Avro/Arrow streaming.
          </span>
        </div>

        <!-- Request Timeout -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Query / Job Timeout (seconds)
          </label>
          <input
            type="number"
            [(ngModel)]="draft.bigqueryRequestTimeoutSec"
            placeholder="60"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
        </div>

      </div>

    </div>
  `
})
export class BigQueryExtensionComponent {
  @Input() draft!: CreateConnectionDraft;

  public locationOptions: CustomSelectOption[] = [
    { label: 'US (Multi-Region)', value: 'US' },
    { label: 'EU (European Union Multi-Region)', value: 'EU' },
    { label: 'us-central1 (Iowa)', value: 'us-central1' },
    { label: 'us-east1 (South Carolina)', value: 'us-east1' },
    { label: 'us-west1 (Oregon)', value: 'us-west1' },
    { label: 'europe-west1 (Belgium)', value: 'europe-west1' },
    { label: 'europe-west3 (Frankfurt)', value: 'europe-west3' },
    { label: 'asia-south1 (Mumbai)', value: 'asia-south1' },
    { label: 'asia-southeast1 (Singapore)', value: 'asia-southeast1' },
    { label: 'asia-northeast1 (Tokyo)', value: 'asia-northeast1' }
  ];

  public onLocationChange(val: string): void {
    this.draft.bigqueryLocation = val;
  }
}
