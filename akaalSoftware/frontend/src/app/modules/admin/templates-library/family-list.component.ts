/**
 * AKAAL Administration — Asset Family List
 */

import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TemplatesConfigService } from '../services/templates-config.service';
import { AssetFamily, TemplateAsset } from '../models/templates-config.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../shared/components/custom-select.component';

@Component({
  selector: 'app-family-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/templates-library" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Template Library
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ pageTitle }}</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              {{ pageDescription }}
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              routerLink="/administration/templates-library/create"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs">
              Create {{ singularName }}
            </a>
          </div>
        </div>
      </div>

      <!-- Filters Toolbar -->
      <div class="flex items-center justify-between gap-4 flex-wrap bg-white p-3.5 border border-slate-200 rounded-xl shadow-2xs">
        <div class="relative flex-1 min-w-[240px] max-w-md">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </div>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search assets by name, code, or tag..."
            class="w-full h-9 pl-9 pr-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
          />
        </div>

        <div class="flex items-center gap-2 w-52">
          <app-custom-select
            [options]="tierFilterOptions"
            [(ngModel)]="selectedTier"
            placeholder="Filter by tier">
          </app-custom-select>
        </div>

        <div class="text-xs text-slate-500 font-medium">
          Showing <span class="font-bold text-slate-900">{{ filteredAssets().length }}</span> of {{ allFamilyAssets().length }} Assets
        </div>
      </div>

      <!-- Assets Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Asset Name</th>
              <th class="py-3 px-4">Code</th>
              <th class="py-3 px-4">Version</th>
              <th class="py-3 px-4">Environment Tier</th>
              <th class="py-3 px-4">Author</th>
              <th class="py-3 px-4">Usages</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let asset of filteredAssets()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4">
                <a [routerLink]="['/administration/templates-library/asset', asset.id]" class="font-bold text-slate-900 hover:text-blue-600 transition-colors">
                  {{ asset.name }}
                </a>
                <div class="text-[11px] text-slate-500 mt-0.5 line-clamp-1">{{ asset.description }}</div>
              </td>
              <td class="py-3 px-4 font-mono font-medium text-slate-700">{{ asset.code }}</td>
              <td class="py-3 px-4 font-mono font-semibold text-slate-900">v{{ asset.currentVersion }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  [ngClass]="{
                    'bg-emerald-50 text-emerald-700 border border-emerald-200': asset.environmentTier === 'PRODUCTION',
                    'bg-amber-50 text-amber-700 border border-amber-200': asset.environmentTier === 'STAGING',
                    'bg-slate-100 text-slate-700 border border-slate-200': asset.environmentTier === 'DEVELOPMENT'
                  }">
                  {{ asset.environmentTier }}
                </span>
              </td>
              <td class="py-3 px-4">
                <div class="text-slate-900 font-medium">{{ asset.authorName }}</div>
                <div class="text-[10px] text-slate-400">{{ asset.authorEmail }}</div>
              </td>
              <td class="py-3 px-4 font-bold text-slate-800">{{ asset.usages.length }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  [ngClass]="{
                    'bg-emerald-50 text-emerald-700 border border-emerald-200': asset.status === 'PUBLISHED',
                    'bg-amber-50 text-amber-700 border border-amber-200': asset.status === 'DEPRECATED',
                    'bg-slate-100 text-slate-700 border border-slate-200': asset.status === 'DRAFT'
                  }">
                  {{ asset.status }}
                </span>
              </td>
              <td class="py-3 px-4 text-right">
                <a
                  [routerLink]="['/administration/templates-library/asset', asset.id]"
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
export class FamilyListComponent implements OnInit {
  private route = inject(ActivatedRoute);
  public library = inject(TemplatesConfigService);

  public family: AssetFamily = 'MIGRATION_TEMPLATE';
  public pageTitle = 'Migration Templates';
  public pageDescription = 'DDL blueprints, database conversion rules, and CDC synchronization strategies.';
  public singularName = 'Template';

  public searchQuery = '';
  public selectedTier = 'ALL';

  public tierFilterOptions: CustomSelectOption[] = [
    { label: 'All Tiers', value: 'ALL' },
    { label: 'Production', value: 'PRODUCTION' },
    { label: 'Staging', value: 'STAGING' },
    { label: 'Development', value: 'DEVELOPMENT' }
  ];

  ngOnInit(): void {
    const routeFamily = this.route.snapshot.data['family'] as AssetFamily;
    if (routeFamily) {
      this.family = routeFamily;
      this.resolveMetadata();
    }
  }

  private resolveMetadata(): void {
    switch (this.family) {
      case 'MIGRATION_TEMPLATE':
        this.pageTitle = 'Migration Templates';
        this.pageDescription = 'DDL blueprints, database conversion rules, and CDC synchronization strategies.';
        this.singularName = 'Migration Template';
        break;
      case 'MAPPING_TEMPLATE':
        this.pageTitle = 'Mapping Templates';
        this.pageDescription = 'Field-level transformations, schema translations, and canonical domain mappings.';
        this.singularName = 'Mapping Template';
        break;
      case 'TRANSFORMATION_TEMPLATE':
        this.pageTitle = 'Transformation Templates';
        this.pageDescription = 'Cleansing pipelines, regex parsing steps, and stream normalization recipes.';
        this.singularName = 'Transformation Template';
        break;
      case 'PRIVACY_POLICY':
        this.pageTitle = 'Privacy Policies';
        this.pageDescription = 'PII masking, format-preserving encryption, tokenization, and hashing rules.';
        this.singularName = 'Privacy Policy';
        break;
      case 'DATA_QUALITY_POLICY':
        this.pageTitle = 'Data Quality Policies';
        this.pageDescription = 'Assertion tests, integrity gates, null constraints, and statistical anomaly checks.';
        this.singularName = 'Quality Policy';
        break;
      case 'CONFIGURATION_PROFILE':
        this.pageTitle = 'Configuration Profiles';
        this.pageDescription = 'Runtime memory tuning, cluster worker budgets, and execution parameters.';
        this.singularName = 'Configuration Profile';
        break;
    }
  }

  public allFamilyAssets(): TemplateAsset[] {
    return this.library.getAssetsByFamily(this.family);
  }

  public filteredAssets(): TemplateAsset[] {
    return this.allFamilyAssets().filter(a => {
      const matchesSearch = !this.searchQuery ||
        a.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        a.code.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        a.tags.some(t => t.toLowerCase().includes(this.searchQuery.toLowerCase()));
      const matchesTier = this.selectedTier === 'ALL' || a.environmentTier === this.selectedTier;
      return matchesSearch && matchesTier;
    });
  }
}
