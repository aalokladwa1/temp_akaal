/**
 * AKAAL Administration — 5.7 Private Connectivity List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-private-connectivity-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/connectivity-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Connectivity
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Private Connectivity</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Configured zero-trust private link endpoints securing traffic between execution workers and data stores.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <a
              routerLink="/administration/infrastructure/connectivity/private/create"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs inline-flex items-center gap-1.5 cursor-pointer">
              Configure Private Link
            </a>
          </div>
        </div>
      </div>

      <!-- Private Links Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Endpoint Name</th>
              <th class="py-3 px-4">Mechanism</th>
              <th class="py-3 px-4">Target VPC / VNet</th>
              <th class="py-3 px-4">CIDR Block</th>
              <th class="py-3 px-4">Service DNS</th>
              <th class="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.privateLinks(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">{{ item.name }}</td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-slate-100 text-slate-800 border border-slate-200">
                    {{ item.mechanism }}
                  </span>
                </td>
                <td class="py-3.5 px-4 font-mono text-slate-700">{{ item.targetVpcOrVnet }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-600">{{ item.cidrBlock }}</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600 truncate max-w-xs">{{ item.endpointServiceDns }}</td>
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
export class PrivateConnectivityListComponent {
  public service = inject(InfrastructureService);
}
