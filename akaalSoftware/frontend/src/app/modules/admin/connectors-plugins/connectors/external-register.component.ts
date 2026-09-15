/**
 * AKAAL Administration — 5.6 Register External Connector
 * Dedicated centered form page for registering a custom connector binary.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-external-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Navigation -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/connectors/external" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to External Connectors
          </a>
        </div>

        <div class="pb-5 border-b border-slate-200">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Register External Connector</h1>
          <p class="text-sm font-medium text-slate-600 mt-1">
            Specify the local runtime binary path, canonical provider identifier, and cryptographic checksum for external driver registration.
          </p>
        </div>
      </div>

      <!-- Registration Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <form (ngSubmit)="onSubmit()" class="flex flex-col gap-5">
          
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Connector Display Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.name"
              name="name"
              required
              placeholder="e.g. Custom SAP HANA Egress Engine"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Provider Identifier <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.providerIdentifier"
                name="providerIdentifier"
                required
                placeholder="e.g. sap_hana_custom"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Protocol Version <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.protocolVersion"
                name="protocolVersion"
                required
                placeholder="e.g. v2.4"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Binary Executable Path <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.binaryPath"
              name="binaryPath"
              required
              placeholder="/opt/akaal/connectors/ext/custom-connector.so"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            <span class="text-[11px] text-slate-500">Absolute path accessible to the AKAAL local runtime daemon process.</span>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              SHA-256 Digest Checksum <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.sha256Checksum"
              name="sha256Checksum"
              required
              placeholder="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <!-- Proof Level Notification -->
          <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-3 text-xs text-slate-600">
            <app-lucide-icon name="info" [size]="16" class="text-slate-400 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="flex flex-col gap-0.5">
              <span class="font-bold text-slate-800">Validation Protocol Notice</span>
              <span class="text-slate-500">Registered external binaries receive initial proof classification UNIT_PROVEN until probed against real execution workloads.</span>
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <a
              routerLink="/administration/connectors/external"
              class="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer">
              Cancel
            </a>
            <button
              type="submit"
              [disabled]="!formData.name || !formData.providerIdentifier || !formData.binaryPath || !formData.sha256Checksum"
              class="px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-2xs transition-colors cursor-pointer">
              Register Connector
            </button>
          </div>

        </form>
      </div>

    </div>
  `
})
export class ExternalRegisterComponent {
  private service = inject(ConnectorsPluginsService);
  private router = inject(Router);

  public formData = {
    name: '',
    providerIdentifier: '',
    protocolVersion: 'v2.4',
    binaryPath: '',
    sha256Checksum: ''
  };

  public onSubmit(): void {
    if (!this.formData.name || !this.formData.providerIdentifier) return;

    this.service.registerExternalConnector({
      name: this.formData.name,
      providerIdentifier: this.formData.providerIdentifier,
      protocolVersion: this.formData.protocolVersion,
      binaryPath: this.formData.binaryPath,
      sha256Checksum: this.formData.sha256Checksum
    });

    this.router.navigate(['/administration/connectors/external']);
  }
}
