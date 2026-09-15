/**
 * AKAAL Administration — 5.7 Configure Kubernetes Environment
 * Dedicated centered form page for registering a Kubernetes cluster configuration.
 */

import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { KubernetesAuthType } from '../../models/infrastructure.models';

@Component({
  selector: 'app-kubernetes-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Navigation -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/compute/kubernetes" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Kubernetes
          </a>
        </div>

        <div class="pb-5 border-b border-slate-200">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Configure Kubernetes</h1>
          <p class="text-sm font-medium text-slate-600 mt-1">
            Register Kubernetes cluster control plane endpoints, authentication token references, and worker namespace.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <form (ngSubmit)="onSubmit()" class="flex flex-col gap-5">
          
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Cluster Display Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.name"
              name="name"
              required
              placeholder="e.g. AWS EKS Secondary Processing Cluster"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Canonical Cluster Identifier <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.clusterName"
                name="clusterName"
                required
                placeholder="e.g. akaal-dr-eks-us-west-2"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Authentication Mechanism <span class="text-rose-500">*</span>
              </label>
              <app-custom-select
                [options]="authOptions"
                [value]="selectedAuthType()"
                (valueChange)="selectedAuthType.set($event)"
                placeholder="Select Auth Type">
              </app-custom-select>
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Kubernetes API Server Endpoint URL <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.apiEndpoint"
              name="apiEndpoint"
              required
              placeholder="https://B12809A1E04B4.gr7.us-east-1.eks.amazonaws.com"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Default Worker Namespace <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.defaultNamespace"
                name="defaultNamespace"
                required
                placeholder="akaal-workloads"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
                Cluster CIDR Block <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="formData.clusterCidr"
                name="clusterCidr"
                required
                placeholder="10.100.0.0/16"
                class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
              Vault Credential Reference Path <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formData.credentialRef"
              name="credentialRef"
              required
              placeholder="vault://secret/k8s/cluster-token-ref"
              class="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            <span class="text-[11px] text-slate-500">Service account token or kubeconfig credential path escrowed in HashiCorp Vault.</span>
          </div>

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <a
              routerLink="/administration/infrastructure/compute/kubernetes"
              class="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer">
              Cancel
            </a>
            <button
              type="submit"
              [disabled]="!formData.name || !formData.clusterName || !formData.apiEndpoint || !formData.credentialRef"
              class="px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-2xs transition-colors cursor-pointer">
              Configure Kubernetes
            </button>
          </div>

        </form>
      </div>

    </div>
  `
})
export class KubernetesCreateComponent {
  private service = inject(InfrastructureService);
  private router = inject(Router);

  public selectedAuthType = signal<string>('PROJECTED_SA');

  public authOptions: SelectOption[] = [
    { label: 'Projected Service Account Token', value: 'PROJECTED_SA' },
    { label: 'OIDC Federated Attestation', value: 'OIDC_FEDERATED' },
    { label: 'Kubeconfig Encrypted Escrow', value: 'KUBECONFIG_ESCROW' }
  ];

  public formData = {
    name: '',
    clusterName: '',
    apiEndpoint: '',
    defaultNamespace: 'akaal-workloads',
    clusterCidr: '10.100.0.0/16',
    credentialRef: 'vault://secret/k8s/cluster-token'
  };

  public onSubmit(): void {
    if (!this.formData.name || !this.formData.clusterName) return;

    this.service.createKubernetesConfig({
      name: this.formData.name,
      clusterName: this.formData.clusterName,
      apiEndpoint: this.formData.apiEndpoint,
      authType: this.selectedAuthType() as KubernetesAuthType,
      credentialRef: this.formData.credentialRef,
      defaultNamespace: this.formData.defaultNamespace,
      clusterCidr: this.formData.clusterCidr
    });

    this.router.navigate(['/administration/infrastructure/compute/kubernetes']);
  }
}
