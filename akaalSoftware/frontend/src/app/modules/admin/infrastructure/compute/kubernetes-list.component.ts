/**
 * AKAAL Administration — 5.7 Kubernetes Configurations List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-kubernetes-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/compute-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Compute
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Kubernetes Configurations</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Configured Kubernetes clusters hosting containerized AKAAL data migration worker pods.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <a
              routerLink="/administration/infrastructure/compute/kubernetes/create"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs inline-flex items-center gap-1.5 cursor-pointer">
              Configure Kubernetes
            </a>
          </div>
        </div>
      </div>

      <!-- Clusters Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Cluster Name</th>
              <th class="py-3 px-4">API Endpoint</th>
              <th class="py-3 px-4">Auth Type</th>
              <th class="py-3 px-4">Namespace</th>
              <th class="py-3 px-4">Proof Level</th>
              <th class="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.kubernetesConfigs(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">
                  <div class="flex flex-col">
                    <span>{{ item.name }}</span>
                    <span class="text-[11px] font-mono text-slate-500 font-normal">{{ item.clusterName }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600 truncate max-w-xs">{{ item.apiEndpoint }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-700">{{ item.authType }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-800">{{ item.defaultNamespace }}</td>
                <td class="py-3.5 px-4">
                  <span
                    [ngClass]="{
                      'bg-emerald-50 text-emerald-700 border-emerald-200': item.proofLevel === 'LIVE_PROVEN',
                      'bg-blue-50 text-blue-700 border-blue-200': item.proofLevel === 'INTEGRATION_PROVEN',
                      'bg-slate-50 text-slate-700 border-slate-200': item.proofLevel === 'UNIT_PROVEN'
                    }"
                    class="px-2 py-0.5 rounded text-[10px] font-mono font-bold border uppercase">
                    {{ item.proofLevel }}
                  </span>
                </td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ item.status }}
                  </span>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class KubernetesListComponent {
  public service = inject(InfrastructureService);
}
