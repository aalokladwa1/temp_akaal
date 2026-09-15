/**
 * AKAAL Administration — 5.11 Add SIEM Integration
 * Centered single-task form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { IntegrationsService } from '../../services/integrations.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-siem-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/integrations/enterprise/siem"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">SIEM INTEGRATIONS</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">NEW COLLECTOR</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Add SIEM Integration</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Register an external SIEM endpoint for real-time security event streaming and regulatory audit aggregation.
          </p>
        </div>
      </div>

      <!-- Centered Form -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Integration Name</label>
          <input
            type="text"
            [(ngModel)]="name"
            placeholder="e.g. Corporate Splunk Cloud HEC"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">SIEM Platform Provider</label>
            <app-custom-select
              [options]="platformOptions"
              [value]="selectedPlatform"
              (valueChange)="selectedPlatform = $event">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Transport Protocol</label>
            <app-custom-select
              [options]="protocolOptions"
              [value]="selectedProtocol"
              (valueChange)="selectedProtocol = $event">
            </app-custom-select>
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Ingest Endpoint URL / Address</label>
          <input
            type="text"
            [(ngModel)]="endpointUrl"
            placeholder="e.g. https://http-inputs-akaal.splunkcloud.com:8088/services/collector/raw"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Vault Credential Reference</label>
          <input
            type="text"
            [(ngModel)]="credentialRef"
            placeholder="vault://secret/siem/hec-token-ref"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          <span class="text-[11px] text-slate-500">
            Encapsulate secrets within Vault. Plaintext tokens or API keys are strictly prohibited in product UI.
          </span>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/integrations/enterprise/siem"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Add SIEM Integration
          </button>
        </div>

      </div>

    </div>
  `
})
export class SiemCreateComponent {
  private integrationsService = inject(IntegrationsService);
  private router = inject(Router);

  public name = '';
  public selectedPlatform: 'SPLUNK' | 'DATADOG' | 'GENERIC_SYSLOG' | 'ELASTICSEARCH' = 'SPLUNK';
  public selectedProtocol: 'HTTPS_POST' | 'TLS_TCP' = 'HTTPS_POST';
  public endpointUrl = '';
  public credentialRef = '';

  public platformOptions: SelectOption[] = [
    { label: 'Splunk Enterprise Cloud (HEC)', value: 'SPLUNK' },
    { label: 'Datadog Security & Log Intake', value: 'DATADOG' },
    { label: 'Elasticsearch Logstash Endpoint', value: 'ELASTICSEARCH' },
    { label: 'Generic RFC-5424 TLS Syslog Daemon', value: 'GENERIC_SYSLOG' }
  ];

  public protocolOptions: SelectOption[] = [
    { label: 'HTTPS POST (JSON / Raw)', value: 'HTTPS_POST' },
    { label: 'Mutual TLS Encrypted TCP (Port 6514)', value: 'TLS_TCP' }
  ];

  public isValid(): boolean {
    return this.name.trim().length > 0 && this.endpointUrl.trim().length > 0;
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    this.integrationsService.createSiemIntegration({
      name: this.name.trim(),
      siemType: this.selectedPlatform,
      endpointUrl: this.endpointUrl.trim(),
      protocol: this.selectedProtocol,
      credentialRef: this.credentialRef.trim() || undefined
    });
    this.router.navigate(['/administration/integrations/enterprise/siem']);
  }
}
