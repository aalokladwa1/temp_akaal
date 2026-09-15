/**
 * AKAAL Administration — Environments List
 */

import { Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-env-list',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Environments</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Deployment lifecycle targets, isolated execution runtimes, and cluster configurations.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              routerLink="/administration/enterprise/environments/create"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Create Environment
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
            placeholder="Search environments by name or tier..."
            class="w-full h-9 pl-9 pr-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
          />
        </div>

        <div class="flex items-center gap-2 w-60">
          <app-custom-select
            [options]="workspaceOptions()"
            [(ngModel)]="selectedWorkspace"
            placeholder="Filter by workspace">
          </app-custom-select>
        </div>

        <div class="text-xs text-slate-500 font-medium">
          Showing <span class="font-bold text-slate-900">{{ filteredEnvs().length }}</span> of {{ enterprise.environments().length }} Environments
        </div>
      </div>

      <!-- Table View -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Environment Name</th>
              <th class="py-3 px-4">Workspace</th>
              <th class="py-3 px-4">Tier</th>
              <th class="py-3 px-4">Isolation Status</th>
              <th class="py-3 px-4">Data Masking</th>
              <th class="py-3 px-4">Connections</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let env of filteredEnvs()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4 font-bold text-slate-900">
                <a [routerLink]="['/administration/enterprise/environments', env.id]" class="hover:text-blue-600 transition-colors">
                  {{ env.name }}
                </a>
              </td>
              <td class="py-3 px-4 text-slate-700 font-medium">{{ env.workspaceName }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ env.tier }}
                </span>
              </td>
              <td class="py-3 px-4 font-mono text-slate-700">{{ env.isolationBarrierStatus }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  [ngClass]="env.dataMaskingEnforced ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-700 border border-slate-200'">
                  {{ env.dataMaskingEnforced ? 'ENFORCED' : 'OFF' }}
                </span>
              </td>
              <td class="py-3 px-4 font-semibold text-slate-800">{{ env.activeConnectionsCount }}</td>
              <td class="py-3 px-4 text-right">
                <a
                  [routerLink]="['/administration/enterprise/environments', env.id]"
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
export class EnvListComponent {
  public enterprise = inject(EnterpriseService);
  public searchQuery = '';
  public selectedWorkspace = 'ALL';

  public workspaceOptions = computed<CustomSelectOption[]>(() => [
    { label: 'All Workspaces', value: 'ALL' },
    ...this.enterprise.workspaces().map(w => ({ label: w.name, value: w.id }))
  ]);

  public filteredEnvs() {
    return this.enterprise.environments().filter(e => {
      const matchesSearch = !this.searchQuery ||
        e.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        e.tier.toLowerCase().includes(this.searchQuery.toLowerCase());
      const matchesWs = this.selectedWorkspace === 'ALL' || e.workspaceId === this.selectedWorkspace;
      return matchesSearch && matchesWs;
    });
  }
}
