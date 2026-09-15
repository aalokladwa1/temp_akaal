/**
 * AKAAL Administration — 5.7 Hybrid Environments
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-hybrid-environments',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Hybrid Environments</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Administrative relationships binding on-premises datacenters, direct-connect interconnects, and cloud environments.
            </p>
          </div>
        </div>
      </div>

      <!-- Hybrid Trunks Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Interconnect Name</th>
              <th class="py-3 px-4">Interconnect Type</th>
              <th class="py-3 px-4">Cloud Environment</th>
              <th class="py-3 px-4">Execution Site</th>
              <th class="py-3 px-4">MTU</th>
              <th class="py-3 px-4">Allocated Bandwidth</th>
              <th class="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.hybridEnvironments(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">{{ item.name }}</td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-slate-100 text-slate-800 border border-slate-200">
                    {{ item.interconnectType }}
                  </span>
                </td>
                <td class="py-3.5 px-4 font-mono text-slate-700">{{ item.cloudEnvId }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-700">{{ item.executionSiteId }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-800">{{ item.mtu }} bytes</td>
                <td class="py-3.5 px-4 font-mono font-bold text-slate-900">{{ item.bandwidthMbps / 1000 }} Gbps</td>
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
export class HybridEnvironmentsComponent {
  public service = inject(InfrastructureService);
}
