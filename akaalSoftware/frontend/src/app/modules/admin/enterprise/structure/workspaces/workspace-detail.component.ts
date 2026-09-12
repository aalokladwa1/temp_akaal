/**
 * AKAAL Administration — Workspace Detail
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-workspace-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="workspace()">
      
      <!-- Back Link & Breadcrumbs -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/enterprise/workspaces" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Workspaces
        
          </a>
        </div>

        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">{{ workspace()?.tier }}</span>
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">{{ workspace()?.status }}</span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ workspace()?.name }}</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              {{ workspace()?.description }}
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              [routerLink]="['/administration/enterprise/workspaces', workspace()?.id, 'edit']"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Edit Workspace
            </a>
          </div>
        </div>
      </div>

      <!-- Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">WORKSPACE CODE</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ workspace()?.code }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">PARENT ORGANIZATION</span>
          <span class="text-sm font-semibold text-slate-900 truncate">{{ workspace()?.orgName }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">OWNER</span>
          <span class="text-sm font-semibold text-slate-900 truncate">{{ workspace()?.ownerName }}</span>
          <span class="text-xs text-slate-500 truncate">{{ workspace()?.ownerEmail }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">RESIDENCY REGION</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ workspace()?.residencyRegion }}</span>
        </div>
      </div>

      <!-- Environments in Workspace -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <div class="p-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">Environments</h2>
            <p class="text-xs text-slate-500">Execution targets and clusters bound to this workspace.</p>
          </div>
          <a
            routerLink="/administration/enterprise/environments/create"
            class="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
            Create Environment
          </a>
        </div>

        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Environment Name</th>
              <th class="py-3 px-4">Tier</th>
              <th class="py-3 px-4">Isolation Status</th>
              <th class="py-3 px-4">Active Connections</th>
              <th class="py-3 px-4">Data Masking</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr *ngFor="let env of environments()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4 font-bold text-slate-900">
                <a [routerLink]="['/administration/enterprise/environments', env.id]" class="hover:text-blue-600 transition-colors">
                  {{ env.name }}
                </a>
              </td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">{{ env.tier }}</span>
              </td>
              <td class="py-3 px-4 font-mono text-slate-700">{{ env.isolationBarrierStatus }}</td>
              <td class="py-3 px-4 font-semibold text-slate-800">{{ env.activeConnectionsCount }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  [ngClass]="env.dataMaskingEnforced ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-700 border border-slate-200'">
                  {{ env.dataMaskingEnforced ? 'ENFORCED' : 'OPTIONAL' }}
                </span>
              </td>
              <td class="py-3 px-4 text-right">
                <a [routerLink]="['/administration/enterprise/environments', env.id]" class="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
                  View
                </a>
              </td>
            </tr>
            <tr *ngIf="environments().length === 0">
              <td colspan="6" class="py-6 text-center text-slate-500 font-medium">No environments configured under this workspace.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `
})
export class WorkspaceDetailComponent {
  private route = inject(ActivatedRoute);
  public enterprise = inject(EnterpriseService);

  public wsId = '';

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.wsId = params.get('id') || '';
    });
  }

  public workspace() {
    return this.enterprise.workspaces().find(w => w.id === this.wsId);
  }

  public environments() {
    return this.enterprise.environments().filter(e => e.workspaceId === this.wsId);
  }
}
