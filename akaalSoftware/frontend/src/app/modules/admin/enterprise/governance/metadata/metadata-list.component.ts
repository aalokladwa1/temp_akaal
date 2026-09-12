/**
 * AKAAL Administration — Enterprise Metadata List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-metadata-list',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Enterprise Metadata</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Schema taxonomies, custom resource attributes, and regulatory tagging policies.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              routerLink="/administration/enterprise/metadata/create"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Create Attribute
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
            placeholder="Search metadata keys or categories..."
            class="w-full h-9 pl-9 pr-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
          />
        </div>

        <div class="flex items-center gap-2 w-60">
          <app-custom-select
            [options]="categoryOptions"
            [(ngModel)]="selectedCategory"
            placeholder="Filter by category">
          </app-custom-select>
        </div>

        <div class="text-xs text-slate-500 font-medium">
          Showing <span class="font-bold text-slate-900">{{ filteredTags().length }}</span> of {{ enterprise.metadataTags().length }} Attributes
        </div>
      </div>

      <!-- Table View -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Tag Key</th>
              <th class="py-3 px-4">Category</th>
              <th class="py-3 px-4">Value Schema</th>
              <th class="py-3 px-4">Requirement</th>
              <th class="py-3 px-4">Applied Resources</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let t of filteredTags()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4">
                <a [routerLink]="['/administration/enterprise/metadata', t.id]" class="font-mono font-bold text-slate-900 hover:text-blue-600 transition-colors">
                  {{ t.key }}
                </a>
                <div class="text-[11px] text-slate-500 mt-0.5">{{ t.description }}</div>
              </td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ t.category }}
                </span>
              </td>
              <td class="py-3 px-4 font-mono text-slate-700">{{ t.valueSchema }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  [ngClass]="t.isMandatory ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-slate-100 text-slate-700 border border-slate-200'">
                  {{ t.isMandatory ? 'MANDATORY' : 'OPTIONAL' }}
                </span>
              </td>
              <td class="py-3 px-4 font-semibold text-slate-800">{{ t.appliedResourceCount }}</td>
              <td class="py-3 px-4 text-right">
                <a
                  [routerLink]="['/administration/enterprise/metadata', t.id]"
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
export class MetadataListComponent {
  public enterprise = inject(EnterpriseService);
  public searchQuery = '';
  public selectedCategory = 'ALL';

  public categoryOptions: CustomSelectOption[] = [
    { label: 'All Categories', value: 'ALL' },
    { label: 'Cost Center', value: 'COST_CENTER' },
    { label: 'Data Governance', value: 'DATA_GOVERNANCE' },
    { label: 'Security Classification', value: 'SECURITY_CLASSIFICATION' },
    { label: 'Operational Tier', value: 'OPERATIONAL_TIER' }
  ];

  public filteredTags() {
    return this.enterprise.metadataTags().filter(t => {
      const matchesSearch = !this.searchQuery ||
        t.key.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        t.description.toLowerCase().includes(this.searchQuery.toLowerCase());
      const matchesCat = this.selectedCategory === 'ALL' || t.category === this.selectedCategory;
      return matchesSearch && matchesCat;
    });
  }
}
