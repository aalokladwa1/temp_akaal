/**
 * AKAAL Administration — 5.7 Configure Route / Proxy / Bastion
 * Dedicated centered form page for configuring network routing.
 */

import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { NetworkRouteType } from '../../models/infrastructure.models';

@Component({
  selector: 'app-routing-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Navigation -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/connectivity/routing" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Network Routing
          </a>
        </div>

        <div class="pb-5 border-b border-slate-200">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Configure Route / Proxy / Bastion</h1>
          <p class="text-sm font-medium text-slate-600 mt-1">
            Register proxy gateways, reverse proxies, and SSH jump host bastions for transit isolation.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <form (ngSubmit)="onSubmit()" class="flex flex-col gap-5">
          
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Route Display Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.name"
              name="name"
              required
              placeholder="e.g. Corporate DMZ Forward Egress Proxy"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Routing Architecture Type <span class="text-rose-500">*</span>
              </label>
              <app-custom-select
                [options]="typeOptions"
                [value]="selectedType()"
                (valueChange)="selectedType.set($event)"
                placeholder="Select Routing Type">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Target Port <span class="text-rose-500">*</span>
              </label>
              <input
                type="number"
                [(ngModel)]="formData.targetPort"
                name="targetPort"
                min="1"
                max="65535"
                required
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Target Host FQDN or IP <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.targetHost"
              name="targetHost"
              required
              placeholder="proxy.corp.internal or 10.10.1.25"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Vault Credential Reference Path
            </label>
            <input
              type="text"
              [(ngModel)]="formData.credentialRef"
              name="credentialRef"
              placeholder="vault://secret/network/proxy-auth-token"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            <span class="text-[11px] text-slate-500">Required if the proxy or SSH bastion requires authentication. Stored securely in HashiCorp Vault.</span>
          </div>

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <a
              routerLink="/administration/infrastructure/connectivity/routing"
              class="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer">
              Cancel
            </a>
            <button
              type="submit"
              [disabled]="!formData.name || !formData.targetHost || !formData.targetPort"
              class="px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-2xs transition-colors cursor-pointer">
              Configure Route
            </button>
          </div>

        </form>
      </div>

    </div>
  `
})
export class RoutingCreateComponent {
  private service = inject(InfrastructureService);
  private router = inject(Router);

  public selectedType = signal<string>('FORWARD_PROXY');

  public typeOptions: SelectOption[] = [
    { label: 'Corporate Egress Forward Proxy', value: 'FORWARD_PROXY' },
    { label: 'Reverse Ingress Gateway Proxy', value: 'REVERSE_PROXY' },
    { label: 'SSH Jump Host Bastion', value: 'SSH_BASTION' },
    { label: 'Direct Unproxied Transit Route', value: 'DIRECT' }
  ];

  public formData = {
    name: '',
    targetHost: '',
    targetPort: 8080,
    credentialRef: 'vault://secret/network/proxy-token'
  };

  public onSubmit(): void {
    if (!this.formData.name || !this.formData.targetHost) return;

    this.service.createNetworkRoute({
      name: this.formData.name,
      routeType: this.selectedType() as NetworkRouteType,
      targetHost: this.formData.targetHost,
      targetPort: this.formData.targetPort,
      credentialRef: this.formData.credentialRef || undefined,
      bypassList: ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']
    });

    this.router.navigate(['/administration/infrastructure/connectivity/routing']);
  }
}
