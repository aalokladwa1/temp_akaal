/**
 * AKAAL Administration — 5.9 Add Audit Destination
 * Centered single-task form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-audit-destination-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/audit/destinations"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">AUDIT DESTINATIONS</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">NEW TARGET</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Add Audit Destination</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Register a remote SIEM ingest pipeline, TLS syslog target, or webhook endpoint for audit streaming.
          </p>
        </div>
      </div>

      <!-- Centered Form -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Destination Name</label>
          <input
            type="text"
            [(ngModel)]="name"
            placeholder="e.g. Corporate Datadog SIEM Forwarder"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Destination Type</label>
            <app-custom-select
              [options]="typeOptions"
              [value]="selectedType"
              (valueChange)="selectedType = $event">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Payload Format</label>
            <app-custom-select
              [options]="formatOptions"
              [value]="selectedFormat"
              (valueChange)="selectedFormat = $event">
            </app-custom-select>
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Endpoint Target URL / Host:Port</label>
          <input
            type="text"
            [(ngModel)]="endpointUrl"
            placeholder="e.g. syslog-tls.corp.internal:6514"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Vault Credential Reference (Optional)</label>
          <input
            type="text"
            [(ngModel)]="credentialRef"
            placeholder="vault://secret/siem/auth-token"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          <span class="text-[11px] text-slate-500">
            Encapsulate secrets within Vault or KMS. Plaintext tokens are forbidden.
          </span>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <input
            type="checkbox"
            id="tlsEnforced"
            [(ngModel)]="tlsEnforced"
            class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
          <label for="tlsEnforced" class="text-xs font-medium text-slate-700 cursor-pointer">
            Enforce Mutual TLS / Strict Certificate Verification
          </label>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/audit/destinations"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Add Destination
          </button>
        </div>

      </div>

    </div>
  `
})
export class AuditDestinationCreateComponent {
  private auditService = inject(AuditService);
  private router = inject(Router);

  public name = '';
  public selectedType: 'SYSLOG' | 'HTTP_WEBHOOK' | 'SIEM_COLLECTOR' = 'SYSLOG';
  public selectedFormat: 'CEF' | 'LEEF' | 'JSON_STRUCTURED' = 'CEF';
  public endpointUrl = '';
  public credentialRef = '';
  public tlsEnforced = true;

  public typeOptions: SelectOption[] = [
    { label: 'RFC-5424 Syslog Daemon', value: 'SYSLOG' },
    { label: 'HTTP / HTTPS Webhook Stream', value: 'HTTP_WEBHOOK' },
    { label: 'SIEM Dedicated Collector (HEC)', value: 'SIEM_COLLECTOR' }
  ];

  public formatOptions: SelectOption[] = [
    { label: 'Common Event Format (CEF)', value: 'CEF' },
    { label: 'Log Event Extended Format (LEEF)', value: 'LEEF' },
    { label: 'Structured JSON Schema v2', value: 'JSON_STRUCTURED' }
  ];

  public isValid(): boolean {
    return this.name.trim().length > 0 && this.endpointUrl.trim().length > 0;
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    this.auditService.createDestination({
      name: this.name.trim(),
      destinationType: this.selectedType,
      endpointUrl: this.endpointUrl.trim(),
      format: this.selectedFormat,
      credentialRef: this.credentialRef.trim() || undefined,
      tlsEnforced: this.tlsEnforced
    });
    this.router.navigate(['/administration/audit/destinations']);
  }
}
