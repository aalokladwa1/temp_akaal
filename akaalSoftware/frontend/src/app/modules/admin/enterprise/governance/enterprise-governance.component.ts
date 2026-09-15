/**
 * AKAAL Administration — Enterprise Resource Governance Routing Hub
 */

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-enterprise-governance',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <div class="flex flex-col gap-2">
        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Resource Governance</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Project boundaries, RACI ownership assignments, capacity quotas, and administrative tag taxonomies.
            </p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        <a
          routerLink="/administration/enterprise/governance/boundaries"
          class="rounded-xl bg-white border border-slate-200 p-6 shadow-2xs hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group flex flex-col justify-between gap-6">
          <div class="flex flex-col gap-3">
            <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
              <app-lucide-icon name="network" [size]="20"></app-lucide-icon>
            </div>
            <h3 class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors font-heading">
              Projects &amp; Boundaries
            </h3>
            <p class="text-xs text-slate-500 font-medium leading-relaxed">
              Network boundaries, cross-tenant egress barriers, and data classification levels.
            </p>
          </div>
          <div class="flex items-center justify-between pt-3 border-t border-slate-100">
            <span class="text-xs font-semibold text-blue-600 group-hover:text-blue-700">Open Boundaries</span>
            <app-lucide-icon name="arrow-right" [size]="14" class="text-blue-600 group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
          </div>
        </a>

        <a
          routerLink="/administration/enterprise/governance/ownership"
          class="rounded-xl bg-white border border-slate-200 p-6 shadow-2xs hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group flex flex-col justify-between gap-6">
          <div class="flex flex-col gap-3">
            <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
              <app-lucide-icon name="user-check" [size]="20"></app-lucide-icon>
            </div>
            <h3 class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors font-heading">
              Ownership
            </h3>
            <p class="text-xs text-slate-500 font-medium leading-relaxed">
              Primary and secondary resource owners, engineering guild assignments, and transfer workflows.
            </p>
          </div>
          <div class="flex items-center justify-between pt-3 border-t border-slate-100">
            <span class="text-xs font-semibold text-blue-600 group-hover:text-blue-700">Open Ownership</span>
            <app-lucide-icon name="arrow-right" [size]="14" class="text-blue-600 group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
          </div>
        </a>

        <a
          routerLink="/administration/enterprise/governance/quotas"
          class="rounded-xl bg-white border border-slate-200 p-6 shadow-2xs hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group flex flex-col justify-between gap-6">
          <div class="flex flex-col gap-3">
            <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
              <app-lucide-icon name="gauge" [size]="20"></app-lucide-icon>
            </div>
            <h3 class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors font-heading">
              Quotas &amp; Limits
            </h3>
            <p class="text-xs text-slate-500 font-medium leading-relaxed">
              Concurrent migration caps, network bandwidth thresholds, and storage quotas.
            </p>
          </div>
          <div class="flex items-center justify-between pt-3 border-t border-slate-100">
            <span class="text-xs font-semibold text-blue-600 group-hover:text-blue-700">Open Quotas</span>
            <app-lucide-icon name="arrow-right" [size]="14" class="text-blue-600 group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
          </div>
        </a>

        <a
          routerLink="/administration/enterprise/governance/metadata"
          class="rounded-xl bg-white border border-slate-200 p-6 shadow-2xs hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group flex flex-col justify-between gap-6">
          <div class="flex flex-col gap-3">
            <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
              <app-lucide-icon name="tags" [size]="20"></app-lucide-icon>
            </div>
            <h3 class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors font-heading">
              Administrative Metadata
            </h3>
            <p class="text-xs text-slate-500 font-medium leading-relaxed">
              Mandatory cost centers, classification schemes, and resource tag taxonomies.
            </p>
          </div>
          <div class="flex items-center justify-between pt-3 border-t border-slate-100">
            <span class="text-xs font-semibold text-blue-600 group-hover:text-blue-700">Open Metadata</span>
            <app-lucide-icon name="arrow-right" [size]="14" class="text-blue-600 group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
          </div>
        </a>

      </div>

    </div>
  `
})
export class EnterpriseGovernanceComponent {}
