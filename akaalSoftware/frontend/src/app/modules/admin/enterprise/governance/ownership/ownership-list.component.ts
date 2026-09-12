/**
 * AKAAL Administration — Resource Ownership List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-ownership-list',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Resource Ownership</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Custodian assignments, responsibility matrices, and cross-department transfers.
            </p>
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
            placeholder="Search ownership records by resource or owner..."
            class="w-full h-9 pl-9 pr-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
          />
        </div>

        <div class="flex items-center gap-2 w-60">
          <app-custom-select
            [options]="typeOptions"
            [(ngModel)]="selectedType"
            placeholder="Filter by resource type">
          </app-custom-select>
        </div>

        <div class="text-xs text-slate-500 font-medium">
          Showing <span class="font-bold text-slate-900">{{ filteredOwnerships().length }}</span> of {{ enterprise.resourceOwnerships().length }} Ownership Records
        </div>
      </div>

      <!-- Table View -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Resource</th>
              <th class="py-3 px-4">Type</th>
              <th class="py-3 px-4">Primary Owner</th>
              <th class="py-3 px-4">Secondary Owner</th>
              <th class="py-3 px-4">Assigned Team</th>
              <th class="py-3 px-4">Transfer Status</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let own of filteredOwnerships()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4 font-bold text-slate-900">
                <a [routerLink]="['/administration/enterprise/ownership', own.id]" class="hover:text-blue-600 transition-colors">
                  {{ own.resourceName }}
                </a>
              </td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ own.resourceType }}
                </span>
              </td>
              <td class="py-3 px-4">
                <div class="font-medium text-slate-900">{{ own.primaryOwnerName }}</div>
                <div class="text-[11px] text-slate-500">{{ own.primaryOwnerEmail }}</div>
              </td>
              <td class="py-3 px-4">
                <div class="font-medium text-slate-800">{{ own.secondaryOwnerName }}</div>
                <div class="text-[11px] text-slate-500">{{ own.secondaryOwnerEmail }}</div>
              </td>
              <td class="py-3 px-4 text-slate-700 font-medium">{{ own.assignedTeam }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  [ngClass]="own.transferPending ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'">
                  {{ own.transferPending ? 'TRANSFER PENDING' : 'SETTLED' }}
                </span>
              </td>
              <td class="py-3 px-4 text-right">
                <a
                  [routerLink]="['/administration/enterprise/ownership', own.id]"
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
export class OwnershipListComponent {
  public enterprise = inject(EnterpriseService);
  public searchQuery = '';
  public selectedType = 'ALL';

  public typeOptions: CustomSelectOption[] = [
    { label: 'All Resource Types', value: 'ALL' },
    { label: 'Organization', value: 'ORGANIZATION' },
    { label: 'Workspace', value: 'WORKSPACE' },
    { label: 'Project Boundary', value: 'PROJECT_BOUNDARY' },
    { label: 'Data Pipeline', value: 'DATA_PIPELINE' }
  ];

  public filteredOwnerships() {
    return this.enterprise.resourceOwnerships().filter(o => {
      const matchesSearch = !this.searchQuery ||
        o.resourceName.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        o.primaryOwnerEmail.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        o.assignedTeam.toLowerCase().includes(this.searchQuery.toLowerCase());
      const matchesType = this.selectedType === 'ALL' || o.resourceType === this.selectedType;
      return matchesSearch && matchesType;
    });
  }
}
