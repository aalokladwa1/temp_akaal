import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionService } from '../create-connection.service';
import { ProviderCatalogItem, ManagedCloudProfile } from '../create-connection.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

export interface CategoryTabItem {
  id: string;
  label: string;
  count: number;
}

@Component({
  selector: 'app-step1-provider',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="max-w-5xl mx-auto w-full space-y-6 select-none animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header (Sibling to Migration Creation Steps) -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight">Choose Provider or System</h2>
        <p class="text-xs text-slate-500 font-normal">
          Select the data platform, streaming broker, object store, or managed cloud resolver for this connection profile.
        </p>
      </div>

      <!-- Search & Category Filters Bar -->
      <div class="flex flex-col gap-3">
        
        <!-- Search Input with Absolutely Positioned Icon -->
        <div class="relative w-full">
          <input
            type="text"
            [ngModel]="searchQuery()"
            (ngModelChange)="searchQuery.set($event)"
            placeholder="Search providers (e.g. PostgreSQL, Oracle, Snowflake, Kafka, S3, Salesforce, BigQuery)..."
            class="w-full h-10 pl-11 pr-4 bg-white border border-slate-200 focus:border-blue-600 rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors shadow-2xs" />
          <app-lucide-icon name="search" [size]="15" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
          @if (searchQuery()) {
            <button
              type="button"
              (click)="searchQuery.set('')"
              class="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer">
              <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
            </button>
          }
        </div>

        <!-- Clean Category Filter Tabs -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          @for (tab of categoryTabs(); track tab.id) {
            <button
              type="button"
              (click)="selectedCategoryTab.set(tab.id)"
              class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer shrink-0 border"
              [class]="selectedCategoryTab() === tab.id
                ? 'bg-blue-600 text-white border-blue-600 shadow-2xs'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'">
              <span>{{ tab.label }}</span>
              <span
                class="px-1.5 py-0.2 text-[9px] font-mono font-bold rounded"
                [class]="selectedCategoryTab() === tab.id
                  ? 'bg-blue-700 text-white'
                  : 'bg-slate-100 text-slate-500'">
                {{ tab.count }}
              </span>
            </button>
          }
        </div>

      </div>

      <!-- ========================================================================= -->
      <!-- VIEW 1: MANAGED CLOUD PROFILES PATH                                       -->
      <!-- ========================================================================= -->
      @if (selectedCategoryTab() === 'MANAGED_CLOUD') {
        <div class="space-y-4 animate-in fade-in duration-150">
          <div class="p-3.5 bg-blue-50/40 border border-blue-200 rounded-xl text-xs text-blue-900 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="cloud" [size]="16" class="text-blue-600 shrink-0"></app-lucide-icon>
              <span>
                <strong>Managed Cloud Resolvers:</strong> Discover and auto-configure VPC/IAM endpoints directly from your cloud account.
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            @for (cloud of cs.cloudProfiles(); track cloud.id) {
              <div class="p-4 bg-white border border-slate-200 rounded-xl flex flex-col gap-3 shadow-2xs">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-700">
                    <app-lucide-icon [name]="cloud.icon" [size]="20"></app-lucide-icon>
                  </div>
                  <div class="flex flex-col">
                    <span class="text-xs font-bold text-slate-900">{{ cloud.name }}</span>
                  </div>
                </div>

                <div class="flex flex-col gap-1.5 pt-2 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Select Managed Resource Type:</span>
                  <div class="grid grid-cols-1 gap-1.5">
                    @for (res of cloud.supportedResourceTypes; track res.value) {
                      <button
                        type="button"
                        (click)="cs.selectManagedCloudResource(cloud.id, res.value, res.physicalProviderId)"
                        class="px-3 py-2 text-left rounded-lg border text-xs font-medium flex items-center justify-between cursor-pointer transition-colors"
                        [class]="(cs.draft().managedCloudId === cloud.id && cs.draft().managedResourceType === res.value)
                          ? 'bg-blue-50/50 border-blue-500 text-blue-900 font-semibold'
                          : 'bg-slate-50/60 hover:bg-slate-100 border-slate-200 text-slate-700'">
                        <span>{{ res.label }}</span>
                        <span class="text-[10px] text-slate-400 font-mono">{{ res.physicalProviderId }}</span>
                      </button>
                    }
                  </div>
                </div>
              </div>
            }
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- VIEW 2: FILE DATASETS TRANSPORT PATH                                      -->
      <!-- ========================================================================= -->
      @else if (selectedCategoryTab() === 'FILES') {
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs animate-in fade-in duration-150">
          <div class="flex flex-col gap-1">
            <span class="text-xs font-bold text-slate-900">File Dataset Transport Driver</span>
            <p class="text-xs text-slate-500 font-normal">
              Direct high-throughput batch transport for tabular and analytical structured files on local/network mounts.
            </p>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            @for (fmt of ['CSV', 'JSONL', 'PARQUET']; track fmt) {
              <button
                type="button"
                (click)="cs.selectFileDataset(fmt === 'CSV' ? 'CSV' : (fmt === 'JSONL' ? 'JSONL' : 'PARQUET'))"
                class="p-4 border rounded-xl cursor-pointer text-left flex flex-col justify-between gap-3 transition-all"
                [class]="(cs.draft().selectedProviderId === 'file_dataset' && cs.draft().fileDatasetFormat === fmt)
                  ? 'border-blue-600 bg-blue-50/20 ring-2 ring-blue-600/30'
                  : 'border-slate-200 hover:border-blue-400 bg-white'">
                <div class="flex items-center justify-between">
                  <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                    <app-lucide-icon name="file-text" [size]="18"></app-lucide-icon>
                  </div>
                  <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-slate-100 text-slate-700 rounded border border-slate-200">
                    {{ fmt }}
                  </span>
                </div>
                <div class="flex flex-col gap-0.5">
                  <span class="text-xs font-bold text-slate-900">{{ fmt }} Format Dataset</span>
                  <span class="text-[11px] text-slate-400">
                    {{ fmt === 'CSV' ? 'Delimited text with header schema' : (fmt === 'JSONL' ? 'Line-delimited JSON objects' : 'Columnar compressed binary') }}
                  </span>
                </div>
              </button>
            }
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- VIEW 3: STANDARD 49-PROVIDER CATALOG GRID                                 -->
      <!-- ========================================================================= -->
      @else {
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          @for (provider of filteredProviders(); track provider.id) {
            @let isSelected = cs.draft().selectedProviderId === provider.id;

            <button
              type="button"
              (click)="cs.selectProvider(provider.id)"
              class="h-14 px-3.5 border rounded-xl cursor-pointer bg-white transition-all text-left flex items-center justify-between gap-3 group shadow-2xs"
              [class]="isSelected
                ? 'border-blue-600 ring-2 ring-blue-600/30 bg-blue-50/15'
                : 'border-slate-200 hover:border-blue-400 hover:bg-slate-50/50'">
              
              <!-- Left: Icon + Name Only -->
              <div class="flex items-center gap-3 min-w-0">
                <div
                  class="w-8 h-8 rounded-lg border flex items-center justify-center shrink-0 transition-colors"
                  [class]="isSelected
                    ? 'bg-blue-50 border-blue-200 text-blue-600'
                    : 'bg-slate-50 border-slate-200 text-slate-600 group-hover:text-blue-600 group-hover:bg-blue-50 group-hover:border-blue-200'">
                  <app-lucide-icon [name]="provider.icon" [size]="17"></app-lucide-icon>
                </div>
                <span
                  class="text-xs font-bold truncate transition-colors"
                  [class]="isSelected ? 'text-blue-600' : 'text-slate-900 group-hover:text-blue-600'">
                  {{ provider.name }}
                </span>
              </div>

              <!-- Right: Selection Check Indicator -->
              @if (isSelected) {
                <span class="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold shrink-0">
                  &check;
                </span>
              }

            </button>
          }

          @if (filteredProviders().length === 0) {
            <div class="col-span-full py-12 text-center text-slate-400 text-xs bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
              No database providers match your active search and category filters.
            </div>
          }
        </div>
      }

      <!-- Selected Provider Confirmation Banner -->
      @if (cs.selectedProvider(); as sel) {
        <div class="p-3.5 bg-emerald-50/40 border border-emerald-200 rounded-xl flex items-center justify-between gap-3 text-xs animate-in fade-in duration-100">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-7 h-7 rounded-lg bg-emerald-100/70 border border-emerald-300 flex items-center justify-center text-emerald-800 shrink-0">
              <app-lucide-icon [name]="sel.icon" [size]="15"></app-lucide-icon>
            </div>
            <div class="flex flex-col min-w-0">
              <span class="font-semibold text-emerald-900 truncate">
                Selected <strong class="font-bold text-slate-900">{{ sel.name }}</strong>
              </span>
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-white text-emerald-800 border border-emerald-300">
              Step 1 Ready
            </span>
          </div>
        </div>
      }

    </div>
  `
})
export class Step1ProviderComponent {
  public cs = inject(CreateConnectionService);

  public searchQuery = signal<string>('');
  public selectedCategoryTab = signal<string>('ALL');

  public categoryTabs = computed<CategoryTabItem[]>(() => {
    const list = this.cs.providerCatalog();
    return [
      { id: 'ALL', label: 'All Providers', count: list.length },
      { id: 'RELATIONAL', label: 'Relational & SQL', count: list.filter(p => p.family === 'RELATIONAL').length },
      { id: 'WAREHOUSE_LAKE', label: 'Warehouse & Lake', count: list.filter(p => p.family === 'WAREHOUSE_LAKE').length },
      { id: 'NOSQL_GRAPH', label: 'NoSQL & Graph', count: list.filter(p => p.family === 'NOSQL_GRAPH').length },
      { id: 'STREAMING', label: 'Streaming', count: list.filter(p => p.family === 'STREAMING').length },
      { id: 'OBJECT_STORAGE', label: 'Object Storage', count: list.filter(p => p.family === 'OBJECT_STORAGE').length },
      { id: 'TIME_SERIES', label: 'Time-Series', count: list.filter(p => p.family === 'TIME_SERIES').length },
      { id: 'APPLICATION', label: 'Applications', count: list.filter(p => p.family === 'APPLICATION').length },
      { id: 'MANAGED_CLOUD', label: 'Managed Cloud', count: this.cs.cloudProfiles().length },
      { id: 'FILES', label: 'Files / Datasets', count: 3 }
    ];
  });

  public filteredProviders = computed<ProviderCatalogItem[]>(() => {
    let list = this.cs.providerCatalog();
    const tab = this.selectedCategoryTab();
    const query = this.searchQuery().trim().toLowerCase();

    // 1. Family Filter
    if (tab !== 'ALL' && tab !== 'MANAGED_CLOUD' && tab !== 'FILES') {
      list = list.filter(p => p.family === tab);
    }

    // 2. Search Query
    if (query) {
      list = list.filter(p =>
        p.name.toLowerCase().includes(query) ||
        p.id.toLowerCase().includes(query) ||
        p.categoryLabel.toLowerCase().includes(query) ||
        p.vendorName.toLowerCase().includes(query) ||
        p.description.toLowerCase().includes(query)
      );
    }

    return list;
  });
}
