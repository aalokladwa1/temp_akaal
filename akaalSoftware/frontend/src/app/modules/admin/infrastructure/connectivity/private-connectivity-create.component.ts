/**
 * AKAAL Administration — 5.7 Configure Private Connectivity
 * Dedicated centered form page for registering a private endpoint.
 */

import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { PrivateConnectivityMechanism } from '../../models/infrastructure.models';

@Component({
  selector: 'app-private-connectivity-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Navigation -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/connectivity/private" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Private Connectivity
          </a>
        </div>

        <div class="pb-5 border-b border-slate-200">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Configure Private Connectivity</h1>
          <p class="text-sm font-medium text-slate-600 mt-1">
            Establish a zero-trust private link endpoint into cloud VPCs, subnets, or dedicated service gateways.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <form (ngSubmit)="onSubmit()" class="flex flex-col gap-5">
          
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Endpoint Display Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.name"
              name="name"
              required
              placeholder="e.g. AWS PrivateLink to Snowflake Internal VPC"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Transit Mechanism <span class="text-rose-500">*</span>
              </label>
              <app-custom-select
                [options]="mechanismOptions"
                [value]="selectedMechanism()"
                (valueChange)="selectedMechanism.set($event)"
                placeholder="Select Mechanism">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Target VPC / VNet Identifier <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.targetVpcOrVnet"
                name="targetVpcOrVnet"
                required
                placeholder="e.g. vpc-09941a8bb20"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Subnet CIDR Block <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.cidrBlock"
                name="cidrBlock"
                required
                placeholder="10.0.128.0/20"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Service DNS Endpoint <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.endpointServiceDns"
                name="endpointServiceDns"
                required
                placeholder="com.amazonaws.vpce.us-east-1.vpce-svc-091924aa19"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <a
              routerLink="/administration/infrastructure/connectivity/private"
              class="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer">
              Cancel
            </a>
            <button
              type="submit"
              [disabled]="!formData.name || !formData.targetVpcOrVnet || !formData.endpointServiceDns"
              class="px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-2xs transition-colors cursor-pointer">
              Configure Private Link
            </button>
          </div>

        </form>
      </div>

    </div>
  `
})
export class PrivateConnectivityCreateComponent {
  private service = inject(InfrastructureService);
  private router = inject(Router);

  public selectedMechanism = signal<string>('AWS_PRIVATELINK');

  public mechanismOptions: SelectOption[] = [
    { label: 'AWS PrivateLink Endpoint', value: 'AWS_PRIVATELINK' },
    { label: 'Azure Private Endpoint', value: 'AZURE_PRIVATE_ENDPOINT' },
    { label: 'Google Private Service Connect (PSC)', value: 'GCP_PSC' },
    { label: 'IPSec Site-to-Site VPN Tunnel', value: 'IPSEC_VPN' }
  ];

  public formData = {
    name: '',
    targetVpcOrVnet: '',
    cidrBlock: '10.0.0.0/20',
    endpointServiceDns: ''
  };

  public onSubmit(): void {
    if (!this.formData.name || !this.formData.targetVpcOrVnet) return;

    this.service.createPrivateLink({
      name: this.formData.name,
      mechanism: this.selectedMechanism() as PrivateConnectivityMechanism,
      targetVpcOrVnet: this.formData.targetVpcOrVnet,
      cidrBlock: this.formData.cidrBlock,
      endpointServiceDns: this.formData.endpointServiceDns
    });

    this.router.navigate(['/administration/infrastructure/connectivity/private']);
  }
}
