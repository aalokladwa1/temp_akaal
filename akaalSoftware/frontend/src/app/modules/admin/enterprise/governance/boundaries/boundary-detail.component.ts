/**
 * AKAAL Administration — Boundary Detail
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-boundary-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="boundary()">
      
      <!-- Back Link & Breadcrumbs -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/enterprise/boundaries" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Resource Boundaries
        
          </a>
        </div>

        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">{{ boundary()?.dataClassification }}</span>
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {{ boundary()?.isolationPolicy }}
              </span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ boundary()?.name }}</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Bound to workspace {{ boundary()?.workspaceName }} under lead owner {{ boundary()?.leadOwnerName }}.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              [routerLink]="['/administration/enterprise/boundaries', boundary()?.id, 'edit']"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Edit Boundary
            </a>
          </div>
        </div>
      </div>

      <!-- Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">BOUNDARY CODE</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ boundary()?.code }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">LEAD OWNER</span>
          <span class="text-sm font-semibold text-slate-900">{{ boundary()?.leadOwnerName }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">CROSS-BOUNDARY ACCESS</span>
          <span class="text-sm font-semibold" [ngClass]="boundary()?.crossBoundaryAllowed ? 'text-amber-700' : 'text-slate-700'">
            {{ boundary()?.crossBoundaryAllowed ? 'ALLOWED (FEDERATED)' : 'BLOCKED (ISOLATED)' }}
          </span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">ATTACHED CONNECTIONS</span>
          <span class="text-base font-bold text-slate-900">{{ boundary()?.boundConnectionsCount }}</span>
        </div>
      </div>
    </div>
  `
})
export class BoundaryDetailComponent {
  private route = inject(ActivatedRoute);
  public enterprise = inject(EnterpriseService);

  public bId = '';

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.bId = params.get('id') || '';
    });
  }

  public boundary() {
    return this.enterprise.boundaries().find(b => b.id === this.bId);
  }
}
