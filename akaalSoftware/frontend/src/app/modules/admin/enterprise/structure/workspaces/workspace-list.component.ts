/**
 * AKAAL Administration — Workspaces List
 */

import { Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-workspace-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/enterprise" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Enterprise
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Workspaces</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Project containers, data domain boundaries, and operational partitioning.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              routerLink="/administration/enterprise/workspaces/create"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Create Workspace
            </a>
          </div>
        </div>
      </div>

      <!-- Search & Filters Toolbar -->
      <div class="flex items-center justify-between gap-4 flex-wrap bg-white p-3.5 border border-slate-200 rounded-xl shadow-2xs">
        <div class="relative flex-1 min-w-[240px] max-w-md">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </div>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search workspaces by name, code, or owner..."
            class="w-full h-9 pl-9 pr-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
          />
        </div>

        <div class="flex items-center gap-2 w-60">
          <app-custom-select
            [options]="orgOptions()"
            [(ngModel)]="selectedOrg"
            placeholder="Filter by organization">
          </app-custom-select>
        </div>

        <div class="text-xs text-slate-500 font-medium">
          Showing <span class="font-bold text-slate-900">{{ filteredWorkspaces().length }}</span> of {{ enterprise.workspaces().length }} Workspaces
        </div>
      </div>

      <!-- Table View -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Workspace Name</th>
              <th class="py-3 px-4">Code</th>
              <th class="py-3 px-4">Organization</th>
              <th class="py-3 px-4">Tier</th>
              <th class="py-3 px-4">Owner</th>
              <th class="py-3 px-4">Environments</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let ws of filteredWorkspaces()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4">
                <a [routerLink]="['/administration/enterprise/workspaces', ws.id]" class="font-bold text-slate-900 hover:text-blue-600 transition-colors">
                  {{ ws.name }}
                </a>
                <div class="text-[11px] text-slate-500 mt-0.5">{{ ws.description }}</div>
              </td>
              <td class="py-3 px-4 font-mono font-medium text-slate-700">{{ ws.code }}</td>
              <td class="py-3 px-4 text-slate-700 font-medium">{{ ws.orgName }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ ws.tier }}
                </span>
              </td>
              <td class="py-3 px-4">
                <div class="font-medium text-slate-800">{{ ws.ownerName }}</div>
                <div class="text-[11px] text-slate-500">{{ ws.ownerEmail }}</div>
              </td>
              <td class="py-3 px-4 font-semibold text-slate-800">{{ ws.environmentCount }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  [ngClass]="{
                    'bg-emerald-50 text-emerald-700 border border-emerald-200': ws.status === 'ACTIVE',
                    'bg-amber-50 text-amber-700 border border-amber-200': ws.status === 'MAINTENANCE',
                    'bg-slate-100 text-slate-700 border border-slate-200': ws.status === 'ARCHIVED'
                  }">
                  {{ ws.status }}
                </span>
              </td>
              <td class="py-3 px-4 text-right">
                <a
                  [routerLink]="['/administration/enterprise/workspaces', ws.id]"
                  class="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
                  View
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `
})
export class WorkspaceListComponent {
  public enterprise = inject(EnterpriseService);
  public searchQuery = '';
  public selectedOrg = 'ALL';

  public orgOptions = computed<CustomSelectOption[]>(() => [
    { label: 'All Organizations', value: 'ALL' },
    ...this.enterprise.organizations().map(o => ({ label: o.name, value: o.id }))
  ]);

  public filteredWorkspaces() {
    return this.enterprise.workspaces().filter(w => {
      const matchesSearch = !this.searchQuery ||
        w.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        w.code.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        w.ownerEmail.toLowerCase().includes(this.searchQuery.toLowerCase());
      const matchesOrg = this.selectedOrg === 'ALL' || w.orgId === this.selectedOrg;
      return matchesSearch && matchesOrg;
    });
  }
}
