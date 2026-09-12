/**
 * AKAAL Administration — Quota Detail
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-quota-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="quota()">
      
      <!-- Back Link & Breadcrumbs -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/enterprise/quotas" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Resource Quotas
        
          </a>
        </div>

        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">{{ quota()?.scopeType }}</span>
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                ACTIVE ALLOCATION
              </span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ quota()?.scopeName }}</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Capacity allocations, peak throughput limits, and resource utilization policies.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              [routerLink]="['/administration/enterprise/quotas', quota()?.id, 'edit']"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Adjust Quota
            </a>
          </div>
        </div>
      </div>

      <!-- Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">CONCURRENT MIGRATIONS</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ quota()?.concurrentMigrationsUsed }} / {{ quota()?.concurrentMigrationsLimit }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">BANDWIDTH CAP</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ quota()?.bandwidthMbpsLimit }} Mbps</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">ACTIVE CONNECTIONS</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ quota()?.activeConnectionsUsed }} / {{ quota()?.maxActiveConnectionsLimit }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">STORAGE ALLOCATION</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ quota()?.storageUsedGb }} / {{ quota()?.storageQuotaGb }} GB</span>
        </div>
      </div>
    </div>
  `
})
export class QuotaDetailComponent {
  private route = inject(ActivatedRoute);
  public enterprise = inject(EnterpriseService);

  public qId = '';

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.qId = params.get('id') || '';
    });
  }

  public quota() {
    return this.enterprise.quotaAllocations().find(q => q.id === this.qId);
  }
}
