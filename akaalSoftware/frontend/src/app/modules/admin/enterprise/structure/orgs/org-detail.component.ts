/**
 * AKAAL Administration — Organization Detail
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-org-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="org()">
      
      <!-- Back Link & Breadcrumbs -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/enterprise/organizations" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Organizations
        
          </a>
        </div>

        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">{{ org()?.tier }}</span>
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">{{ org()?.status }}</span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ org()?.name }}</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              {{ org()?.description }}
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              [routerLink]="['/administration/enterprise/organizations', org()?.id, 'edit']"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Edit Organization
            </a>
          </div>
        </div>
      </div>

      <!-- Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">ORGANIZATION CODE</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ org()?.code }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">COST CENTER</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ org()?.costCenterCode }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">PRIMARY CONTACT</span>
          <span class="text-sm font-semibold text-slate-900 truncate">{{ org()?.primaryContactName }}</span>
          <span class="text-xs text-slate-500 truncate">{{ org()?.primaryContactEmail }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">DEFAULT REGION</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ org()?.defaultRegion }}</span>
        </div>
      </div>

      <!-- Workspaces Under Org -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <div class="p-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">Attached Workspaces</h2>
            <p class="text-xs text-slate-500">Workspaces scoped under this organization entity.</p>
          </div>
          <a
            routerLink="/administration/enterprise/workspaces/create"
            class="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
            Create Workspace
          </a>
        </div>

        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Workspace Name</th>
              <th class="py-3 px-4">Code</th>
              <th class="py-3 px-4">Tier</th>
              <th class="py-3 px-4">Owner</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr *ngFor="let ws of workspaces()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4 font-bold text-slate-900">
                <a [routerLink]="['/administration/enterprise/workspaces', ws.id]" class="hover:text-blue-600 transition-colors">
                  {{ ws.name }}
                </a>
              </td>
              <td class="py-3 px-4 font-mono text-slate-700">{{ ws.code }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">{{ ws.tier }}</span>
              </td>
              <td class="py-3 px-4 text-slate-700">{{ ws.ownerEmail }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">{{ ws.status }}</span>
              </td>
              <td class="py-3 px-4 text-right">
                <a [routerLink]="['/administration/enterprise/workspaces', ws.id]" class="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
                  View
                </a>
              </td>
            </tr>
            <tr *ngIf="workspaces().length === 0">
              <td colspan="6" class="py-6 text-center text-slate-500 font-medium">No workspaces configured under this organization.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `
})
export class OrgDetailComponent {
  private route = inject(ActivatedRoute);
  public enterprise = inject(EnterpriseService);

  public orgId = '';

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.orgId = params.get('id') || '';
    });
  }

  public org() {
    return this.enterprise.organizations().find(o => o.id === this.orgId);
  }

  public workspaces() {
    return this.enterprise.workspaces().filter(w => w.orgId === this.orgId);
  }
}
