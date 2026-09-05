import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import {
  PhysicalProviderId,
  ConnectionItem,
  TargetVerificationResult,
  NetworkRouteType,
  CollisionPolicyType
} from '../../../../core/models/migration-view.models';
import {
  ALL_28_PROVIDER_SCHEMAS,
  ProviderFormSchema,
  ProviderFormField
} from '../../../../core/models/provider-form-schemas';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { SegmentedControlComponent, SegmentedControlOption } from '../../../../shared/components/segmented-control.component';
import { AccordionComponent } from '../../../../shared/components/accordion.component';

export interface CatalogEngineItem {
  id: PhysicalProviderId;
  name: string;
  category: 'RELATIONAL' | 'WAREHOUSE' | 'NOSQL' | 'STREAMING' | 'STORAGE';
  categoryLabel: string;
  icon: string;
}

export interface CatalogCategoryTab {
  id: 'ALL' | 'RELATIONAL' | 'WAREHOUSE' | 'NOSQL' | 'STREAMING' | 'STORAGE';
  label: string;
  count: number;
}

export interface TargetStageState {
  index: number;
  name: string;
  description: string;
  chipLabel: string;
  status: 'PENDING' | 'TESTING' | 'PASSED' | 'FAILED' | 'WARNING';
  detail?: string;
}

export interface SavedConnectionItemExtended extends ConnectionItem {
  scope?: 'PROJECT' | 'TEAM' | 'ENTERPRISE';
}

@Component({
  selector: 'app-step3-target',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    CustomSelectComponent,
    SegmentedControlComponent,
    AccordionComponent
  ],
  template: `
    <div class="max-w-5xl mx-auto w-full space-y-6 select-none animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- ========================================================================= -->
      <!-- 0. PAGE INTRODUCTION & MODE CONTROLS                                      -->
      <!-- ========================================================================= -->
      @if (ms.wizardDraft().targetConnectionMode) {
        <div class="flex flex-col gap-3 border-b border-slate-200/60 pb-3">
          <div class="flex items-center justify-between flex-wrap gap-2">
            <div class="flex flex-col gap-0.5">
              <h1 class="text-base font-bold text-slate-900 tracking-tight">Target Connection</h1>
              <p class="text-xs text-slate-500 font-normal">Choose how AKAAL should connect to the target destination system.</p>
            </div>

            <!-- Compact Segmented Control (Top-Right) -->
            <app-segmented-control
              [options]="modeControlOptions"
              [value]="ms.wizardDraft().targetConnectionMode"
              (valueChange)="setConnectionMode($event)">
            </app-segmented-control>
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- ENTRY STATE: TWO HERO CHOICE CARDS (CENTERED, DEEP, NO EMPTY VOID)        -->
      <!-- ========================================================================= -->
      @if (!ms.wizardDraft().targetConnectionMode) {
        <section class="pt-8 pb-12 flex flex-col items-center justify-center animate-in fade-in duration-150">
          
          <div class="flex flex-col items-center text-center gap-1.5 pb-6">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight">Target Connection</h1>
            <p class="text-sm text-slate-500 max-w-md font-normal">
              Choose how AKAAL should connect to your destination database system.
            </p>
          </div>

          <div class="max-w-3xl mx-auto grid grid-cols-1 sm:grid-cols-2 gap-6 w-full">
            
            <!-- Card 1: Saved Connection -->
            <button
              type="button"
              (click)="setConnectionMode('SAVED')"
              class="p-7 border-2 border-slate-200 hover:border-blue-500 hover:bg-slate-50/60 rounded-2xl cursor-pointer bg-white transition-all text-left flex flex-col justify-between gap-5 group shadow-xs">
              <div class="flex items-center justify-between">
                <div class="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 group-hover:scale-105 transition-transform">
                  <app-lucide-icon name="database" [size]="22"></app-lucide-icon>
                </div>
                <span class="px-2.5 py-1 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                  Enterprise Vault
                </span>
              </div>
              <div class="flex flex-col gap-2">
                <span class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  Saved Connection
                </span>
                <p class="text-xs text-slate-500 font-normal leading-relaxed">
                  Use an existing verified target connection from the Workspace Vault.
                </p>
                <div class="pt-2.5 border-t border-slate-100 flex items-center gap-2 text-[11px] text-slate-600 font-medium">
                  <app-lucide-icon name="check" [size]="13" class="text-emerald-600"></app-lucide-icon>
                  <span>Pre-configured write credentials &amp; IAM policies</span>
                </div>
              </div>
            </button>

            <!-- Card 2: New Connection -->
            <button
              type="button"
              (click)="setConnectionMode('NEW')"
              class="p-7 border-2 border-slate-200 hover:border-blue-500 hover:bg-slate-50/60 rounded-2xl cursor-pointer bg-white transition-all text-left flex flex-col justify-between gap-5 group shadow-xs">
              <div class="flex items-center justify-between">
                <div class="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 group-hover:scale-105 transition-transform">
                  <app-lucide-icon name="plug" [size]="22"></app-lucide-icon>
                </div>
                <span class="px-2.5 py-1 text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded-full">
                  Target Endpoint
                </span>
              </div>
              <div class="flex flex-col gap-2">
                <span class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  New Connection
                </span>
                <p class="text-xs text-slate-500 font-normal leading-relaxed">
                  Configure and verify a new destination database endpoint from the catalog.
                </p>
                <div class="pt-2.5 border-t border-slate-100 flex items-center gap-2 text-[11px] text-slate-600 font-medium">
                  <app-lucide-icon name="check" [size]="13" class="text-blue-600"></app-lucide-icon>
                  <span>Supports native high-speed bulk ingestion APIs</span>
                </div>
              </div>
            </button>

          </div>
        </section>
      }

      <!-- ========================================================================= -->
      <!-- BRANCH 1: SAVED TARGET CONNECTION INTERACTIVE GRID                        -->
      <!-- ========================================================================= -->
      @if (ms.wizardDraft().targetConnectionMode === 'SAVED') {
        <section class="space-y-4 animate-in fade-in duration-150">
          
          <!-- Search & Filter Bar -->
          <div class="relative flex items-center gap-2.5">
            <div class="relative flex-1">
              <input
                type="text"
                [(ngModel)]="savedSearchQuery"
                placeholder="Search saved target connections by name, host, or engine..."
                class="w-full h-10 pl-11 pr-4 bg-white border border-slate-200 focus:border-blue-600 rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors shadow-2xs" />
              <app-lucide-icon name="search" [size]="15" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
              @if (savedSearchQuery()) {
                <button
                  type="button"
                  (click)="savedSearchQuery.set('')"
                  class="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer">
                  <app-lucide-icon name="x-circle" [size]="14"></app-lucide-icon>
                </button>
              }
            </div>

            <!-- Filter Popover Trigger Button -->
            <button
              type="button"
              (click)="isFilterPopoverOpen.set(!isFilterPopoverOpen())"
              class="h-10 px-3.5 bg-white border rounded-xl text-xs font-medium text-slate-700 flex items-center gap-2 cursor-pointer shadow-2xs transition-colors shrink-0"
              [class]="(isFilterPopoverOpen() || activeFilterCount() > 0)
                ? 'border-blue-500 bg-blue-50/20'
                : 'border-slate-200 hover:border-slate-300'">
              <app-lucide-icon name="filter" [size]="14" class="text-slate-500"></app-lucide-icon>
              <span>Filter</span>
              @if (activeFilterCount() > 0) {
                <span class="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                  {{ activeFilterCount() }}
                </span>
              }
              <app-lucide-icon [name]="isFilterPopoverOpen() ? 'chevron-up' : 'chevron-down'" [size]="13" class="text-slate-400"></app-lucide-icon>
            </button>

            <!-- 6-Filter Popover Modal -->
            @if (isFilterPopoverOpen()) {
              <div class="absolute right-0 top-11 z-50 w-88 p-4 bg-white border border-slate-200 rounded-2xl shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-100">
                <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span class="text-xs font-bold text-slate-900">Filter Saved Targets</span>
                  <button type="button" (click)="isFilterPopoverOpen.set(false)" class="text-slate-400 hover:text-slate-600 cursor-pointer">
                    <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
                  </button>
                </div>

                <!-- 1. Mode Compatibility -->
                <div class="flex flex-col gap-1.5">
                  <label class="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      [ngModel]="filterModeCompatible()"
                      (ngModelChange)="filterModeCompatible.set($event)"
                      class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                    <span class="text-xs font-semibold text-slate-800">
                      Show only targets compatible with Step 1 Mode
                    </span>
                  </label>
                  <span class="text-[10px] text-slate-400 pl-6">Auto-evaluates against {{ getModeLabel() }}</span>
                </div>

                <!-- 2. Environment -->
                <div class="flex flex-col gap-1.5 pt-1 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Environment</span>
                  <div class="flex items-center gap-1.5">
                    @for (env of ['ALL', 'Production', 'Non-Production']; track env) {
                      <button
                        type="button"
                        (click)="filterEnvironment.set(env)"
                        class="px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer transition-colors"
                        [class]="filterEnvironment() === env ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200'">
                        {{ env }}
                      </button>
                    }
                  </div>
                </div>

                <!-- 3. Category -->
                <div class="flex flex-col gap-1.5 pt-1 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Category</span>
                  <div class="flex items-center gap-1.5 flex-wrap">
                    @for (cat of ['ALL', 'RELATIONAL', 'WAREHOUSE', 'NOSQL', 'STREAMING', 'STORAGE']; track cat) {
                      <button
                        type="button"
                        (click)="filterCategory.set(cat)"
                        class="px-2 py-0.5 rounded text-[10px] font-medium border cursor-pointer transition-colors"
                        [class]="filterCategory() === cat ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200'">
                        {{ getCategoryFilterLabel(cat) }}
                      </button>
                    }
                  </div>
                </div>

                <!-- 4. Route -->
                <div class="flex flex-col gap-1.5 pt-1 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Network Route</span>
                  <div class="grid grid-cols-2 gap-1.5">
                    @for (route of routeFiltersList; track route.value) {
                      <label class="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          [checked]="filterRoutes().includes(route.value)"
                          (change)="toggleRouteFilter(route.value)"
                          class="w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                        <span>{{ route.label }}</span>
                      </label>
                    }
                  </div>
                </div>

                <!-- Popover Footer -->
                <div class="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <button type="button" (click)="clearAllFilters()" class="text-[11px] font-medium text-slate-500 hover:text-slate-800 cursor-pointer">Clear All</button>
                  <button type="button" (click)="isFilterPopoverOpen.set(false)" class="h-7 px-3 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md cursor-pointer">
                    Apply Filters ({{ filteredSavedConnections().length }} matching)
                  </button>
                </div>
              </div>
            }
          </div>

          <!-- Active Filter Chips -->
          @if (activeFilterChips().length > 0) {
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="text-[11px] text-slate-400 font-medium">Active filters:</span>
              @for (chip of activeFilterChips(); track chip.id) {
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  <span>{{ chip.label }}</span>
                  <button type="button" (click)="removeFilterChip(chip.id)" class="hover:text-rose-600 cursor-pointer">
                    <app-lucide-icon name="x" [size]="10"></app-lucide-icon>
                  </button>
                </span>
              }
              <button type="button" (click)="clearAllFilters()" class="text-[11px] text-blue-600 hover:underline cursor-pointer pl-1">Clear All</button>
            </div>
          }

          <!-- Saved Endpoints Grid -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 max-h-[440px] overflow-y-auto p-1">
            @for (conn of filteredSavedConnections(); track conn.id) {
              @let evalRes = evaluateSavedConnection(conn);
              @let isSelected = ms.wizardDraft().targetConnectionId === conn.id;

              <div
                (click)="selectSavedEndpoint(conn)"
                class="p-3.5 border rounded-xl cursor-pointer transition-all flex flex-col justify-between gap-3 shadow-2xs group"
                [class]="isSelected
                  ? 'border-blue-600 ring-2 ring-blue-600/30 bg-blue-50/15'
                  : 'border-slate-200 hover:border-blue-400 hover:bg-slate-50/50 bg-white'">
                
                <div class="flex items-start justify-between gap-2">
                  <div class="flex items-center gap-2.5 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-700 shrink-0 group-hover:border-blue-300 transition-colors">
                      <app-lucide-icon [name]="getProviderIcon(conn.provider)" [size]="16"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col min-w-0">
                      <span class="text-xs font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors">{{ conn.name }}</span>
                      <span class="text-[10px] text-slate-400 font-mono">{{ conn.provider }}</span>
                    </div>
                  </div>

                  @switch (conn.status) {
                    @case ('CONNECTED') {
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        Verified
                      </span>
                    }
                    @default {
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
                        Needs Re-test
                      </span>
                    }
                  }
                </div>

                <div class="flex flex-col gap-1 py-1 border-y border-slate-100 text-[11px]">
                  <div class="flex items-center justify-between text-slate-500">
                    <span>Endpoint</span>
                    <span class="font-mono text-slate-700 truncate max-w-[170px]">{{ conn.host }}:{{ conn.port }}</span>
                  </div>
                  <div class="flex items-center justify-between text-slate-500">
                    <span>Route</span>
                    <span class="font-medium text-slate-700">{{ conn.networkRoute }}</span>
                  </div>
                </div>

                <div class="flex items-center justify-between text-[11px]">
                  @if (evalRes.isEligible) {
                    <span class="inline-flex items-center gap-1 text-emerald-700 font-semibold">
                      <app-lucide-icon name="check" [size]="12" class="text-emerald-600"></app-lucide-icon>
                      <span>Step 1 Compatible</span>
                    </span>
                  } @else {
                    <span class="inline-flex items-center gap-1 text-amber-700 font-semibold truncate" [title]="evalRes.reason || ''">
                      <app-lucide-icon name="alert-triangle" [size]="12" class="text-amber-600 shrink-0"></app-lucide-icon>
                      <span class="truncate">Incompatible Target</span>
                    </span>
                  }
                  @if (isSelected) {
                    <span class="text-xs font-bold text-blue-600">Active ✓</span>
                  }
                </div>
              </div>
            }
          </div>

          <!-- Instant Lookup Banner -->
          @if (selectedSavedConnection(); as conn) {
            <div class="p-3 bg-emerald-50/40 border border-emerald-200 rounded-xl flex items-center justify-between gap-3 text-xs animate-in fade-in duration-100">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="check-circle-2" [size]="16" class="text-emerald-600 shrink-0"></app-lucide-icon>
                <span class="font-semibold text-emerald-900">
                  Selected Target: <strong class="font-bold text-slate-900">{{ conn.name }}</strong> ({{ conn.provider }}) · 0ms instant cached verification
                </span>
              </div>
              <span class="text-[11px] font-mono text-emerald-700 font-medium">✓ Ready for Scope</span>
            </div>
          }
        </section>
      }

      <!-- ========================================================================= -->
      <!-- BRANCH 2: NEW TARGET CONNECTION BRANCH                                     -->
      <!-- ========================================================================= -->
      @if (ms.wizardDraft().targetConnectionMode === 'NEW') {
        <section class="space-y-6 animate-in fade-in duration-150">
          
          <!-- PHASE A: 28-PROVIDER TARGET CATALOG GRID -->
          @if (!ms.wizardDraft().targetProvider) {
            <div class="flex flex-col gap-4 animate-in fade-in duration-150">
              
              <!-- Search Bar -->
              <div class="relative w-full">
                <input
                  type="text"
                  [(ngModel)]="searchQuery"
                  placeholder="Search target providers (e.g. PostgreSQL, Snowflake, BigQuery, Kafka)..."
                  class="w-full h-10 pl-11 pr-4 bg-white border border-slate-200 focus:border-blue-600 rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors shadow-2xs" />
                <app-lucide-icon name="search" [size]="15" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
                @if (searchQuery()) {
                  <button type="button" (click)="searchQuery.set('')" class="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer">
                    <app-lucide-icon name="x-circle" [size]="14"></app-lucide-icon>
                  </button>
                }
              </div>

              <!-- Category Tabs -->
              <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
                @for (tab of catalogTabs; track tab.id) {
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
                      [class]="selectedCategoryTab() === tab.id ? 'bg-blue-700 text-white' : 'bg-slate-100 text-slate-500'">
                      {{ tab.count }}
                    </span>
                  </button>
                }
              </div>

              <!-- Catalog Grid -->
              <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3.5 mt-2">
                @for (engine of filteredCatalogEngines(); track engine.id) {
                  @let compat = checkTargetCompatibility(engine.id);
                  <button
                    type="button"
                    (click)="selectTargetEngine(engine.id)"
                    [disabled]="!compat.compatible"
                    [class]="compat.compatible 
                      ? 'p-3.5 border border-slate-200 rounded-lg hover:border-blue-500 hover:bg-blue-50/10 cursor-pointer bg-white transition-all text-left flex items-center justify-between gap-3 group shadow-2xs'
                      : 'p-3.5 border border-slate-200/60 rounded-lg bg-slate-50/60 opacity-60 cursor-not-allowed transition-all text-left flex items-center justify-between gap-3 shadow-2xs'"
                    [title]="compat.compatible ? '' : (compat.reason || '')">
                    <div class="flex items-center gap-3 min-w-0">
                      <div [class]="compat.compatible
                        ? 'w-9 h-9 rounded-lg border border-slate-200 bg-slate-50 flex items-center justify-center text-slate-600 group-hover:text-blue-600 group-hover:bg-blue-50 group-hover:border-blue-200 transition-colors shrink-0'
                        : 'w-9 h-9 rounded-lg border border-slate-200 bg-slate-100 flex items-center justify-center text-slate-400 shrink-0'">
                        <app-lucide-icon [name]="engine.icon" [size]="18"></app-lucide-icon>
                      </div>
                      <div class="flex flex-col min-w-0">
                        <span class="text-xs font-semibold truncate transition-colors" [class]="compat.compatible ? 'text-slate-900 group-hover:text-blue-600' : 'text-slate-500'">
                          {{ engine.name }}
                        </span>
                        <span class="text-[10px] text-slate-400 font-medium uppercase tracking-wider truncate">
                          {{ engine.categoryLabel }}
                        </span>
                      </div>
                    </div>
                    @if (!compat.compatible) {
                      <span class="px-1.5 py-0.5 text-[9px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 rounded shrink-0">
                        Incompatible
                      </span>
                    }
                  </button>
                }
              </div>
            </div>
          }

          <!-- PHASE B: TARGET ENGINE SELECTED -->
          @if (selectedProviderSchema(); as schema) {
            <div class="space-y-5 animate-in fade-in duration-150">
              
              <!-- 1. Active Context Bar with [ Change Target Engine ] -->
              <div class="p-3.5 bg-blue-50/40 border border-blue-200 rounded-xl flex items-center justify-between flex-wrap gap-2">
                <div class="flex items-center gap-3 min-w-0">
                  <div class="w-9 h-9 rounded-lg bg-white border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 shadow-2xs">
                    <app-lucide-icon [name]="schema.icon" [size]="18"></app-lucide-icon>
                  </div>
                  <div class="flex flex-col min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-bold text-slate-900 truncate">{{ schema.name }}</span>
                      <span class="px-1.5 py-0.2 text-[9px] font-mono font-bold bg-blue-100 text-blue-800 rounded">
                        TARGET
                      </span>
                    </div>
                    <span class="text-[11px] text-slate-500 capitalize">
                      {{ schema.category.toLowerCase().replace('_', ' ') }}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  (click)="changeTargetEngine()"
                  class="h-7 px-3 text-xs font-semibold text-blue-700 bg-white border border-blue-300 hover:bg-blue-50 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs">
                  <app-lucide-icon name="arrow-left" [size]="12"></app-lucide-icon>
                  <span>Change Target Engine</span>
                </button>
              </div>

              <!-- 2. NET-NEW STEP 3: CROSS-ENGINE PAIR COMPATIBILITY BADGE -->
              @if (pairCompatibilityInfo(); as pair) {
                <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
                  <div class="flex items-center gap-2.5">
                    <div class="px-2 py-1 bg-white border border-slate-200 rounded-md text-slate-800 font-bold text-xs flex items-center gap-1.5">
                      <app-lucide-icon [name]="getProviderIcon(pair.sourceProvider)" [size]="14" class="text-blue-600"></app-lucide-icon>
                      <span>{{ pair.sourceProvider }}</span>
                    </div>
                    <app-lucide-icon name="arrow-right" [size]="14" class="text-slate-400 shrink-0"></app-lucide-icon>
                    <div class="px-2 py-1 bg-white border border-slate-200 rounded-md text-slate-800 font-bold text-xs flex items-center gap-1.5">
                      <app-lucide-icon [name]="getProviderIcon(pair.targetProvider)" [size]="14" class="text-emerald-600"></app-lucide-icon>
                      <span>{{ pair.targetProvider }}</span>
                    </div>
                  </div>

                  <div class="flex items-center gap-2 text-[11px]">
                    <span
                      class="px-2 py-0.5 rounded-full font-semibold border text-[10px]"
                      [class]="pair.isHomogeneous 
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                        : 'bg-blue-50 text-blue-700 border-blue-200'">
                      {{ pair.isHomogeneous ? 'Homogeneous Pair' : 'Heterogeneous Pair' }}
                    </span>
                    <span class="text-slate-600 font-medium">{{ pair.transpilerStatus }}</span>
                  </div>
                </div>
              }

              <!-- 3. NET-NEW STEP 3: SELF-TARGETING GUARD WARNING -->
              @if (isSelfTargetingBlocked()) {
                <div class="p-3 bg-amber-50 border border-amber-300 rounded-xl flex items-center gap-3 text-amber-900 text-xs animate-in fade-in duration-100">
                  <app-lucide-icon name="alert-triangle" [size]="18" class="text-amber-600 shrink-0"></app-lucide-icon>
                  <div>
                    <span class="font-bold">Self-Targeting Guardrail Active:</span>
                    <span> Source and Target point to the exact same host and database (<code>{{ ms.wizardDraft().sourceHost }}:{{ ms.wizardDraft().sourceDatabase }}</code>). To prevent circular corruption or accidental destruction, specify a different Target Schema / Namespace below.</span>
                  </div>
                </div>
              }

              <!-- 4. DYNAMIC TARGET ENDPOINT & AUTH PARAMETERS -->
              <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
                <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
                  <span class="text-xs font-bold text-slate-900">Target Endpoint &amp; Authentication Parameters</span>
                  <span class="text-[11px] text-slate-400 font-normal">Generated dynamically from provider schema</span>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  @for (field of schema.fields; track field.id) {
                    @if (isFieldVisible(field, schema)) {
                      <div [class]="(field.type === 'textarea' || field.type === 'file_path') ? 'flex flex-col gap-1.5 md:col-span-2' : 'flex flex-col gap-1.5'">
                        
                        <label [for]="'target-field-' + field.id" class="text-xs font-semibold text-slate-700 flex items-center justify-between">
                          <span>{{ cleanLabel(field.label) }} @if (field.required) { <span class="text-rose-500">*</span> }</span>
                        </label>

                        @if (field.type === 'text' || field.type === 'file_path') {
                          <input
                            [id]="'target-field-' + field.id"
                            type="text"
                            [placeholder]="field.placeholder || ''"
                            [ngModel]="getTargetFieldValue(field.id)"
                            (ngModelChange)="onTargetFieldChange(field.id, $event)"
                            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 transition-colors" />
                        }

                        @if (field.type === 'number') {
                          <input
                            [id]="'target-field-' + field.id"
                            type="number"
                            [placeholder]="field.placeholder || (field.id === 'port' ? (schema.defaultPort ? '' + schema.defaultPort : '') : '')"
                            [ngModel]="getTargetFieldValue(field.id)"
                            (ngModelChange)="onTargetFieldChange(field.id, $event)"
                            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 transition-colors" />
                        }

                        @if (field.type === 'password' || field.type === 'secret_ref') {
                          <div class="relative">
                            <input
                              [id]="'target-field-' + field.id"
                              [type]="isSecretVisible(field.id) ? 'text' : 'password'"
                              [placeholder]="field.placeholder || (isProductionEnv() ? 'vault://secret/... (Enforced in Prod)' : 'Password or vault://secret/...')"
                              [ngModel]="getTargetFieldValue(field.id)"
                              (ngModelChange)="onTargetFieldChange(field.id, $event)"
                              class="w-full h-9 px-3 pr-10 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 transition-colors" />
                            <button
                              type="button"
                              (click)="toggleSecretVisibility(field.id)"
                              class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer p-0.5"
                              [title]="isSecretVisible(field.id) ? 'Hide value' : 'Show value'">
                              <app-lucide-icon [name]="isSecretVisible(field.id) ? 'eye-off' : (field.type === 'secret_ref' ? 'key' : 'eye')" [size]="13"></app-lucide-icon>
                            </button>
                          </div>
                        }

                        @if (field.type === 'textarea') {
                          <textarea
                            [id]="'target-field-' + field.id"
                            rows="3"
                            [placeholder]="field.placeholder || ''"
                            [ngModel]="getTargetFieldValue(field.id)"
                            (ngModelChange)="onTargetFieldChange(field.id, $event)"
                            class="w-full p-2.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 font-mono transition-colors"></textarea>
                        }

                        @if (field.type === 'select') {
                          <app-custom-select
                            [options]="field.options || []"
                            [value]="getTargetFieldValue(field.id)"
                            (valueChange)="onTargetFieldChange(field.id, $event)"
                            placeholder="Select an option...">
                          </app-custom-select>
                        }

                        @if (field.type === 'boolean') {
                          <label class="flex items-center gap-2 cursor-pointer select-none pt-1">
                            <input
                              type="checkbox"
                              [ngModel]="getTargetFieldValue(field.id)"
                              (ngModelChange)="onTargetFieldChange(field.id, $event)"
                              class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                            <span class="text-xs font-medium text-slate-700">{{ cleanLabel(field.label) }}</span>
                          </label>
                        }

                        @if (field.helpText) {
                          <span class="text-[11px] text-slate-400 font-normal">{{ field.helpText }}</span>
                        }
                      </div>
                    }
                  }
                </div>
              </div>

              <!-- 5. NET-NEW STEP 3: TARGET SCHEMA & PROVISIONING + HIGH-SPEED INGESTION ENGINE -->
              <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
                <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
                  <span class="text-xs font-bold text-slate-900">Target Namespace &amp; Ingestion Architecture</span>
                  <span class="text-[11px] text-slate-400 font-normal">Configure target schema, load APIs, and collision handling</span>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  
                  <!-- Target Schema Name -->
                  <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-semibold text-slate-700 block">
                      Target Schema / Namespace <span class="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. finance or public"
                      [ngModel]="ms.wizardDraft().targetSchema"
                      (ngModelChange)="onTargetSchemaChange($event)"
                      class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    
                    <label class="flex items-center gap-2 cursor-pointer select-none pt-1">
                      <input
                        type="checkbox"
                        [ngModel]="ms.wizardDraft().targetAutoCreateSchema"
                        (ngModelChange)="ms.updateDraft({ targetAutoCreateSchema: $event })"
                        class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                      <span class="text-[11px] font-medium text-slate-700">Automatically create target schema/database if it doesn't exist</span>
                    </label>
                  </div>

                  <!-- High-Throughput Ingestion Engine Selector -->
                  <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-semibold text-slate-700 block">
                      High-Throughput Ingestion Engine <span class="text-rose-500">*</span>
                    </label>
                    <app-custom-select
                      [options]="targetIngestionEngineOptions()"
                      [value]="ms.wizardDraft().targetIngestionEngine || defaultIngestionEngine()"
                      (valueChange)="onIngestionEngineChange($event)"
                      placeholder="Select native bulk load method...">
                    </app-custom-select>
                    <span class="text-[10px] text-slate-400">
                      High-speed kernel API for {{ schema.name }}
                    </span>
                  </div>

                  <!-- Collision Policy Selector (Full Width or 2-col) -->
                  <div class="md:col-span-2 flex flex-col gap-1.5 pt-2 border-t border-slate-100">
                    <label class="text-xs font-semibold text-slate-700 block">
                      Target Object Collision Policy <span class="text-rose-500">*</span>
                    </label>
                    <app-custom-select
                      [options]="collisionPolicyOptions()"
                      [value]="ms.wizardDraft().collisionPolicy || 'FAIL_ON_COLLISION'"
                      (valueChange)="onCollisionPolicyChange($event)"
                      placeholder="Select behavior on existing tables...">
                    </app-custom-select>
                    <span class="text-[10px] text-slate-400">
                      Defines behavior if source tables already exist in the target schema
                    </span>
                  </div>

                </div>
              </div>

              <!-- 6. COLLAPSIBLE ACCORDIONS: NETWORK ROUTE & TLS SECURITY -->
              <div class="space-y-3">
                <app-accordion
                  title="Network Route"
                  subtitle="Direct, SSH Bastion, PrivateLink, Proxy"
                  icon="network"
                  [(isOpen)]="isRouteAccordionOpen">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700 block">Route Type</label>
                      <app-custom-select
                        [options]="networkRouteOptions"
                        [value]="ms.wizardDraft().targetNetworkRoute || 'DIRECT'"
                        (valueChange)="onRouteTypeChange($event)"
                        placeholder="Select network route...">
                      </app-custom-select>
                    </div>

                    @if (ms.wizardDraft().targetNetworkRoute === 'DIRECT' || !ms.wizardDraft().targetNetworkRoute) {
                      <div class="flex flex-col justify-center gap-1 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 text-[11px]">
                        <span class="font-medium text-slate-800">Direct TCP Connection</span>
                        <span>Direct routed IP connectivity over VPC peering or corporate network.</span>
                      </div>
                    }

                    @if (ms.wizardDraft().targetNetworkRoute === 'SSH_BASTION') {
                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">SSH Bastion Host <span class="text-rose-500">*</span></label>
                        <input
                          type="text"
                          placeholder="bastion.prod.aws.company.com"
                          [ngModel]="ms.wizardDraft().targetBastionHost"
                          (ngModelChange)="ms.updateDraft({ targetBastionHost: $event, targetVerified: false })"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>
                    }

                    @if (ms.wizardDraft().targetNetworkRoute === 'PRIVATE_ENDPOINT') {
                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">Private Endpoint ID <span class="text-rose-500">*</span></label>
                        <input
                          type="text"
                          placeholder="vpce-0a1b2c3d4e5f6g7h8"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>
                    }
                  </div>
                </app-accordion>

                <app-accordion
                  title="TLS & Transport Encryption"
                  subtitle="Encryption mode, CA certificate binding, mTLS"
                  icon="lock"
                  [(isOpen)]="isTlsAccordionOpen">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700 block">TLS Enforcement Mode</label>
                      <app-custom-select
                        [options]="tlsModeOptions()"
                        [value]="selectedTlsMode()"
                        (valueChange)="onTlsModeChange($event)"
                        placeholder="Select TLS encryption mode...">
                      </app-custom-select>
                    </div>

                    @if (isProductionEnv() && selectedTlsMode() === 'DISABLE') {
                      <div class="md:col-span-2 p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-2 text-rose-800 text-xs font-medium">
                        <app-lucide-icon name="alert-circle" [size]="16" class="text-rose-600 shrink-0"></app-lucide-icon>
                        <span>Plain unencrypted TCP is strictly blocked in Production. TLS 1.2+ is mandatory.</span>
                      </div>
                    }
                  </div>
                </app-accordion>
              </div>

              <!-- 7. BACKEND VERIFICATION ENGINE: 6-STAGE TARGET ATTESTATION PROBE -->
              <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
                <div class="flex items-center justify-between flex-wrap gap-2">
                  <div class="flex flex-col gap-0.5">
                    <span class="text-xs font-bold text-slate-900">Target Connection Attestation</span>
                    <p class="text-[11px] text-slate-500 font-normal">
                      Executes the 6-stage target attestation: Transport, Identity/Charset, DDL Write Canary, Fast-Path Ingestion, Disk Headroom, and Collision Audit.
                    </p>
                  </div>

                  <button
                    type="button"
                    (click)="runTargetAttestationProbe()"
                    [disabled]="isVerifying()"
                    class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50 flex items-center gap-2 cursor-pointer transition-colors shadow-2xs">
                    @if (isVerifying()) {
                      <app-lucide-icon name="refresh-cw" [size]="13" class="animate-spin text-white"></app-lucide-icon>
                      <span>Testing Stage ({{ activeStageIndex() }}/6)...</span>
                    } @else {
                      <app-lucide-icon name="shield-check" [size]="14"></app-lucide-icon>
                      <span>Verify Target Connection</span>
                    }
                  </button>
                </div>

                <!-- Live Progress Display -->
                @if (isVerifying()) {
                  <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5 animate-in fade-in duration-100">
                    <div class="flex items-center justify-between text-xs">
                      <span class="font-bold text-slate-800">
                        Running Stage {{ activeStageIndex() }}: {{ activeStageName() }}
                      </span>
                      <span class="text-slate-500 font-mono text-[11px]">
                        {{ Math.round((activeStageIndex() / 6) * 100) }}% complete
                      </span>
                    </div>
                    <div class="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-blue-600 transition-all duration-150 rounded-full"
                        [style.width.%]="(activeStageIndex() / 6) * 100"></div>
                    </div>
                  </div>
                }

                <!-- Post-Attestation Diagnostic Card -->
                @if (probeExecuted()) {
                  @if (ms.wizardDraft().targetVerified) {
                    <div class="p-3.5 bg-emerald-50/50 border border-emerald-200 rounded-xl flex flex-col gap-2.5 animate-in fade-in duration-150">
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                          <span class="text-xs font-bold text-emerald-900">
                            Target Attested Successfully · All 6 Stages Passed (1.8s)
                          </span>
                        </div>
                        <span class="text-[11px] font-mono text-emerald-700 font-medium">Ready for Step 4</span>
                      </div>

                      <div class="flex items-center gap-1.5 flex-wrap">
                        @for (stage of targetStages; track stage.index) {
                          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-white text-emerald-800 border border-emerald-200 shadow-2xs">
                            <app-lucide-icon name="check" [size]="11" class="text-emerald-600"></app-lucide-icon>
                            <span>{{ stage.chipLabel }}</span>
                          </span>
                        }
                      </div>
                    </div>
                  }
                  @if (verificationError(); as err) {
                    <div class="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex flex-col gap-2 animate-in fade-in duration-150">
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                          <span class="w-2 h-2 rounded-full bg-rose-500"></span>
                          <span class="text-xs font-bold text-rose-900">Target Verification Blocked ({{ err.stage }})</span>
                        </div>
                        <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-rose-100 text-rose-800 rounded">
                          {{ err.category }}
                        </span>
                      </div>
                      <p class="text-xs text-rose-800 font-normal leading-relaxed">
                        {{ err.message }}
                      </p>
                    </div>
                  }
                }
              </div>

              <!-- 8. POST-SUCCESS: SAVE TARGET TO VAULT -->
              @if (ms.wizardDraft().targetVerified) {
                <div class="p-4 bg-slate-50/70 border border-slate-200 rounded-xl space-y-3 animate-in fade-in duration-150">
                  <label class="flex items-center gap-2.5 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      [ngModel]="ms.wizardDraft().targetSaveToVault"
                      (ngModelChange)="onSaveToVaultChange($event)"
                      class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                    <span class="text-xs font-semibold text-slate-800">
                      Save this target connection to Enterprise Vault for future migrations
                    </span>
                  </label>

                  @if (ms.wizardDraft().targetSaveToVault) {
                    <div class="flex flex-col gap-1.5 pl-6 animate-in fade-in duration-100 max-w-xl">
                      <label class="text-xs font-semibold text-slate-700 block">
                        Connection Name <span class="text-rose-500">*</span>
                      </label>
                      <div class="flex items-center gap-2.5">
                        <input
                          type="text"
                          [ngModel]="vaultTargetConnectionName()"
                          (ngModelChange)="onVaultTargetNameChange($event)"
                          placeholder="e.g. Aurora PostgreSQL 16 Target"
                          class="flex-1 h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 focus:outline-none transition-colors" />
                        
                        <button
                          type="button"
                          (click)="saveTargetToVault()"
                          [disabled]="!vaultTargetConnectionName().trim() || isTargetVaultSaved()"
                          class="h-9 px-4 text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer transition-all shrink-0 shadow-2xs"
                          [class]="isTargetVaultSaved()
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed'">
                          <app-lucide-icon [name]="isTargetVaultSaved() ? 'check' : 'bookmark'" [size]="13"></app-lucide-icon>
                          <span>{{ isTargetVaultSaved() ? 'Saved to Vault' : 'Save Connection' }}</span>
                        </button>
                      </div>
                      <span class="text-[10px] text-slate-400">
                        Will be saved to Connection Hub and accessible in "Saved Connection" branch.
                      </span>
                    </div>
                  }
                </div>
              }

            </div>
          }

        </section>
      }

    </div>
  `
})
export class Step3TargetComponent implements OnInit {
  public ms = inject(MigrationUiService);
  public Math = Math;

  public modeControlOptions: SegmentedControlOption[] = [
    { label: 'Saved Connection', value: 'SAVED', icon: 'database' },
    { label: 'New Connection', value: 'NEW', icon: 'plug' }
  ];

  public isRouteAccordionOpen = false;
  public isTlsAccordionOpen = false;

  // Catalog & Search Signals
  public searchQuery = signal<string>('');
  public selectedCategoryTab = signal<'ALL' | 'RELATIONAL' | 'WAREHOUSE' | 'NOSQL' | 'STREAMING' | 'STORAGE'>('ALL');

  // Saved Grid Signals
  public savedSearchQuery = signal<string>('');
  public isFilterPopoverOpen = signal<boolean>(false);
  public filterModeCompatible = signal<boolean>(true);
  public filterEnvironment = signal<string>('Production');
  public filterCategory = signal<string>('ALL');
  public filterRoutes = signal<NetworkRouteType[]>([]);

  // Secret Visibility Map
  public secretVisibilityMap = signal<Record<string, boolean>>({});

  // Target Vault Save Signals
  public vaultTargetConnectionName = signal<string>('');
  public isTargetVaultSaved = signal<boolean>(false);

  // Target Attestation Signals
  public isVerifying = signal<boolean>(false);
  public probeExecuted = signal<boolean>(false);
  public selectedTlsMode = signal<string>('VERIFY_FULL');
  public verificationError = signal<{ stage: string; category: string; message: string } | null>(null);
  public activeStageIndex = signal<number>(1);
  public activeStageName = signal<string>('Transport & Network Route Ping');

  // 6-Stage Target Attestation Lifecycle
  public targetStages: TargetStageState[] = [
    { index: 1, name: 'Stage 1: Transport & Network Route Ping', description: 'Resolves DNS, TCP latency, and negotiates TLS 1.2/1.3', chipLabel: 'Transport & TLS', status: 'PENDING' },
    { index: 2, name: 'Stage 2: Target Identity & Charset Check', description: 'Validates target engine edition, version, and character encoding', chipLabel: 'Identity & Charset', status: 'PENDING' },
    { index: 3, name: 'Stage 3: Live DDL & Write Canary Probe', description: 'Executes ephemeral sandboxed CREATE, INSERT, and DROP canary test', chipLabel: 'Write & DDL Canary', status: 'PENDING' },
    { index: 4, name: 'Stage 4: High-Throughput Ingestion Fast-Path', description: 'Probes native bulk load APIs (COPY, Direct-Path, Snowpipe)', chipLabel: 'Fast-Path Verified', status: 'PENDING' },
    { index: 5, name: 'Stage 5: Storage Headroom & Tablespace Capacity', description: 'Verifies free disk space and quota threshold (>10% free)', chipLabel: 'Storage Headroom', status: 'PENDING' },
    { index: 6, name: 'Stage 6: Pre-Existing Object Collision Audit', description: 'Audits target schema for colliding table names against collision policy', chipLabel: 'Collision Audit', status: 'PENDING' }
  ];

  // The 28 Canonical Engines
  public catalogEngines: CatalogEngineItem[] = [
    { id: 'Oracle', name: 'Oracle Database', category: 'RELATIONAL', categoryLabel: 'Relational', icon: 'database' },
    { id: 'PostgreSQL', name: 'PostgreSQL', category: 'RELATIONAL', categoryLabel: 'Relational', icon: 'database' },
    { id: 'MySQL', name: 'MySQL', category: 'RELATIONAL', categoryLabel: 'Relational', icon: 'database' },
    { id: 'Microsoft SQL Server', name: 'SQL Server (MSSQL)', category: 'RELATIONAL', categoryLabel: 'Relational', icon: 'database' },
    { id: 'MariaDB', name: 'MariaDB', category: 'RELATIONAL', categoryLabel: 'Relational', icon: 'database' },
    { id: 'SQLite', name: 'SQLite', category: 'RELATIONAL', categoryLabel: 'Relational', icon: 'database' },
    { id: 'IBM Db2', name: 'IBM Db2 LUW', category: 'RELATIONAL', categoryLabel: 'Relational', icon: 'database' },

    { id: 'Snowflake', name: 'Snowflake', category: 'WAREHOUSE', categoryLabel: 'Warehouse', icon: 'layers' },
    { id: 'Google BigQuery', name: 'Google BigQuery', category: 'WAREHOUSE', categoryLabel: 'Warehouse', icon: 'layers' },
    { id: 'Amazon Redshift', name: 'Amazon Redshift', category: 'WAREHOUSE', categoryLabel: 'Warehouse', icon: 'layers' },
    { id: 'Databricks', name: 'Databricks Delta', category: 'WAREHOUSE', categoryLabel: 'Warehouse', icon: 'layers' },

    { id: 'MongoDB', name: 'MongoDB', category: 'NOSQL', categoryLabel: 'NoSQL / Doc', icon: 'boxes' },
    { id: 'Apache Cassandra', name: 'Apache Cassandra', category: 'NOSQL', categoryLabel: 'NoSQL / Wide', icon: 'boxes' },
    { id: 'ScyllaDB', name: 'ScyllaDB', category: 'NOSQL', categoryLabel: 'NoSQL / Wide', icon: 'boxes' },
    { id: 'Neo4j', name: 'Neo4j Graph', category: 'NOSQL', categoryLabel: 'Graph DB', icon: 'boxes' },
    { id: 'Redis', name: 'Redis', category: 'NOSQL', categoryLabel: 'In-Memory KV', icon: 'boxes' },
    { id: 'KeyDB', name: 'KeyDB', category: 'NOSQL', categoryLabel: 'In-Memory KV', icon: 'boxes' },
    { id: 'Elasticsearch', name: 'Elasticsearch', category: 'NOSQL', categoryLabel: 'Search Index', icon: 'boxes' },
    { id: 'OpenSearch', name: 'OpenSearch', category: 'NOSQL', categoryLabel: 'Search Index', icon: 'boxes' },

    { id: 'Apache Kafka', name: 'Apache Kafka', category: 'STREAMING', categoryLabel: 'Streaming', icon: 'radio' },
    { id: 'Amazon Kinesis', name: 'Amazon Kinesis', category: 'STREAMING', categoryLabel: 'Streaming', icon: 'radio' },
    { id: 'Azure Event Hubs', name: 'Azure Event Hubs', category: 'STREAMING', categoryLabel: 'Streaming', icon: 'radio' },
    { id: 'Google Cloud Pub/Sub', name: 'Google Cloud Pub/Sub', category: 'STREAMING', categoryLabel: 'Streaming', icon: 'radio' },

    { id: 'Amazon S3', name: 'Amazon S3', category: 'STORAGE', categoryLabel: 'Cloud Storage', icon: 'hard-drive' },
    { id: 'Google Cloud Storage', name: 'Google Cloud Storage', category: 'STORAGE', categoryLabel: 'Cloud Storage', icon: 'hard-drive' },
    { id: 'Azure Blob Storage', name: 'Azure Blob Storage', category: 'STORAGE', categoryLabel: 'Cloud Storage', icon: 'hard-drive' },
    { id: 'MinIO', name: 'MinIO Object Store', category: 'STORAGE', categoryLabel: 'Cloud Storage', icon: 'hard-drive' },
    { id: 'Apache HDFS', name: 'Apache HDFS', category: 'STORAGE', categoryLabel: 'Filesystem', icon: 'hard-drive' }
  ];

  public catalogTabs: CatalogCategoryTab[] = [
    { id: 'ALL', label: 'All', count: 28 },
    { id: 'RELATIONAL', label: 'Relational', count: 7 },
    { id: 'WAREHOUSE', label: 'Warehouse', count: 4 },
    { id: 'NOSQL', label: 'NoSQL', count: 8 },
    { id: 'STREAMING', label: 'Streaming', count: 4 },
    { id: 'STORAGE', label: 'Storage', count: 5 }
  ];

  public routeFiltersList: { label: string; value: NetworkRouteType }[] = [
    { label: 'Direct TCP', value: 'DIRECT' },
    { label: 'SSH Bastion Tunnel', value: 'SSH_BASTION' },
    { label: 'AWS PrivateLink', value: 'PRIVATE_ENDPOINT' },
    { label: 'Corporate Proxy', value: 'HTTP_PROXY' }
  ];

  public networkRouteOptions: CustomSelectOption[] = [
    { label: 'Direct TCP Network Connection (Default)', value: 'DIRECT', desc: 'Standard routed IP connectivity over VPC peering or LAN' },
    { label: 'SSH Bastion Jump Tunnel', value: 'SSH_BASTION', desc: 'Encrypted SSH bastion jump host traversal' },
    { label: 'Private Endpoint / AWS PrivateLink', value: 'PRIVATE_ENDPOINT', desc: 'VPC endpoint or cloud private link interface' },
    { label: 'Corporate HTTP Proxy', value: 'HTTP_PROXY', desc: 'Standard corporate HTTP forward proxy' },
    { label: 'SOCKS5 Proxy Tunnel', value: 'SOCKS5_PROXY', desc: 'Binary stream SOCKS5 proxy traversal' }
  ];

  public enterpriseSavedTargets: SavedConnectionItemExtended[] = [
    {
      id: 'target-01',
      name: 'Aurora PostgreSQL 16 Target Cluster',
      provider: 'PostgreSQL',
      category: 'RELATIONAL',
      environment: 'Production',
      host: 'aurora-pg-target.prod.internal',
      port: 5432,
      databaseName: 'finance_dw',
      username: 'akaal_applier',
      secretRef: 'vault://secret/prod/pg_target',
      tlsEnabled: true,
      networkRoute: 'PRIVATE_ENDPOINT',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 2 min ago',
      latencyMs: 1.8,
      capabilities: ['BINARY_COPY', 'DDL_WRITE'],
      assignedMigrationCount: 2,
      assignedProjectCount: 1,
      createdAt: '2026-08-01T10:00:00Z',
      updatedAt: '2026-08-28T09:00:00Z',
      scope: 'PROJECT'
    },
    {
      id: 'target-02',
      name: 'Snowflake Enterprise Analytical Lake',
      provider: 'Snowflake',
      category: 'WAREHOUSE',
      environment: 'Production',
      host: 'org-dw12345.snowflakecomputing.com',
      port: 443,
      databaseName: 'ANALYTICS_TARGET',
      username: 'akaal_loader',
      secretRef: 'vault://secret/prod/snowflake_loader',
      tlsEnabled: true,
      networkRoute: 'DIRECT',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 10 min ago',
      latencyMs: 16.2,
      capabilities: ['SNOWPIPE_STREAMING', 'STAGE_COPY'],
      assignedMigrationCount: 3,
      assignedProjectCount: 2,
      createdAt: '2026-08-10T14:00:00Z',
      updatedAt: '2026-08-28T08:00:00Z',
      scope: 'TEAM'
    },
    {
      id: 'target-03',
      name: 'Kafka Target Bus (CDC Events)',
      provider: 'Apache Kafka',
      category: 'STREAMING',
      environment: 'Production',
      host: 'kafka-target-01.prod.internal',
      port: 9092,
      username: 'akaal_producer',
      secretRef: 'vault://secret/prod/kafka_prod',
      tlsEnabled: true,
      networkRoute: 'PRIVATE_ENDPOINT',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 25 min ago',
      latencyMs: 3.1,
      capabilities: ['PRODUCER_BATCHING'],
      assignedMigrationCount: 1,
      assignedProjectCount: 1,
      createdAt: '2026-08-15T09:00:00Z',
      updatedAt: '2026-08-28T07:00:00Z',
      scope: 'ENTERPRISE'
    }
  ];

  public filteredCatalogEngines = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const tab = this.selectedCategoryTab();
    let list = this.catalogEngines;

    if (tab !== 'ALL') {
      list = list.filter(e => e.category === tab);
    }
    if (q) {
      list = list.filter(e =>
        e.name.toLowerCase().includes(q) ||
        e.categoryLabel.toLowerCase().includes(q) ||
        e.id.toLowerCase().includes(q)
      );
    }
    return list;
  });

  public filteredSavedConnections = computed(() => {
    const q = this.savedSearchQuery().trim().toLowerCase();
    const onlyCompat = this.filterModeCompatible();
    const env = this.filterEnvironment();
    const cat = this.filterCategory();
    const routes = this.filterRoutes();

    let list = this.enterpriseSavedTargets;

    if (q) {
      list = list.filter(c =>
        c.name.toLowerCase().includes(q) ||
        c.provider.toLowerCase().includes(q) ||
        c.host.toLowerCase().includes(q)
      );
    }
    if (onlyCompat) {
      list = list.filter(c => this.evaluateSavedConnection(c).isEligible);
    }
    if (env !== 'ALL') {
      list = list.filter(c => c.environment === env);
    }
    if (cat !== 'ALL') {
      list = list.filter(c => c.category === cat);
    }
    if (routes.length > 0) {
      list = list.filter(c => routes.includes(c.networkRoute));
    }
    return list;
  });

  public activeFilterCount = computed(() => {
    let count = 0;
    if (this.filterModeCompatible()) count++;
    if (this.filterEnvironment() !== 'ALL') count++;
    if (this.filterCategory() !== 'ALL') count++;
    count += this.filterRoutes().length;
    return count;
  });

  public activeFilterChips = computed(() => {
    const chips: { id: string; label: string }[] = [];
    if (this.filterModeCompatible()) {
      chips.push({ id: 'mode', label: `Step 1 Compatible (${this.getModeLabel()})` });
    }
    if (this.filterEnvironment() !== 'ALL') {
      chips.push({ id: 'env', label: `Env: ${this.filterEnvironment()}` });
    }
    if (this.filterCategory() !== 'ALL') {
      chips.push({ id: 'cat', label: `Cat: ${this.getCategoryFilterLabel(this.filterCategory())}` });
    }
    for (const r of this.filterRoutes()) {
      chips.push({ id: `route-${r}`, label: `Route: ${r}` });
    }
    return chips;
  });

  public selectedSavedConnection = computed<SavedConnectionItemExtended | undefined>(() => {
    const id = this.ms.wizardDraft().targetConnectionId;
    if (!id) return undefined;
    return this.enterpriseSavedTargets.find(c => c.id === id);
  });

  public selectedProviderSchema = computed<ProviderFormSchema | undefined>(() => {
    const pid = this.ms.wizardDraft().targetProvider;
    if (!pid) return undefined;
    return ALL_28_PROVIDER_SCHEMAS[pid];
  });

  // Cross-Engine Pair Compatibility Badge Evaluation
  public pairCompatibilityInfo = computed(() => {
    const srcProvider = this.ms.wizardDraft().sourceProvider;
    const tgtProvider = this.ms.wizardDraft().targetProvider;
    if (!srcProvider || !tgtProvider) return null;

    const isHomogeneous = srcProvider === tgtProvider;
    let transpilerStatus = '';

    if (isHomogeneous) {
      transpilerStatus = 'Native 1:1 Dialect & Data Types · Fast-Path Direct Transfer';
    } else {
      const srcSchema = ALL_28_PROVIDER_SCHEMAS[srcProvider];
      const tgtSchema = ALL_28_PROVIDER_SCHEMAS[tgtProvider];
      if (srcSchema?.category === 'RELATIONAL' && tgtSchema?.category === 'WAREHOUSE') {
        transpilerStatus = 'Relational to Lakehouse · Cloud Ingestion Stream Ready';
      } else {
        transpilerStatus = `Dialect Transpiler Active (${srcProvider} → ${tgtProvider}) · Type Conversion Engine Ready`;
      }
    }

    return {
      sourceProvider: srcProvider,
      targetProvider: tgtProvider,
      isHomogeneous,
      transpilerStatus
    };
  });

  // Self-targeting Guard Evaluation
  public isSelfTargetingBlocked = computed(() => {
    const d = this.ms.wizardDraft();
    if (!d.sourceHost || !d.targetHost) return false;
    const sameHost = d.sourceHost.toLowerCase().trim() === d.targetHost.toLowerCase().trim();
    const sameDb = (d.sourceDatabase || '').toLowerCase().trim() === (d.targetDatabase || '').toLowerCase().trim();
    const hasDifferentSchema = !!d.targetSchema && d.targetSchema.trim() !== '' && d.targetSchema.trim() !== (d.sourceDatabase || '').trim();
    return sameHost && sameDb && !hasDifferentSchema;
  });

  // Collision Policy Options (Adapts based on Step 1 Mode)
  public collisionPolicyOptions = computed<CustomSelectOption[]>(() => {
    const mode = this.ms.wizardDraft().mode;
    if (mode === 'M7_DATA_ONLY') {
      return [
        { label: 'Append Existing Tables (Recommended for M7)', value: 'APPEND_EXISTING', desc: 'Inserts incoming records into pre-existing target tables' },
        { label: 'Truncate and Load', value: 'TRUNCATE_AND_LOAD', desc: 'Wipes existing rows, preserves schema and indexes' },
        { label: 'Fail on Collision', value: 'FAIL_ON_COLLISION', desc: 'Abort immediately if target table already contains data' },
        { label: 'Rename and Backup', value: 'RENAME_AND_BACKUP', desc: 'Auto-renames existing tables before loading' }
      ];
    }
    return [
      { label: 'Fail on Collision (Default / Safest)', value: 'FAIL_ON_COLLISION', desc: 'Abort migration immediately if target table already exists' },
      { label: 'Drop and Recreate (Destructive)', value: 'DROP_AND_RECREATE', desc: 'Drops existing target tables and recreates clean DDL schema' },
      { label: 'Truncate and Load', value: 'TRUNCATE_AND_LOAD', desc: 'Wipes existing table rows, preserving existing DDL structure' },
      { label: 'Append to Existing', value: 'APPEND_EXISTING', desc: 'Appends data directly into existing target tables' },
      { label: 'Rename and Backup', value: 'RENAME_AND_BACKUP', desc: 'Renames existing tables to backup before creation' }
    ];
  });

  // Ingestion Engine Options (Schema-driven per target provider)
  public targetIngestionEngineOptions = computed<CustomSelectOption[]>(() => {
    const schema = this.selectedProviderSchema();
    if (!schema?.ingestionEngines || schema.ingestionEngines.length === 0) {
      return [
        { label: 'Standard Batch Insert Stream', value: 'STANDARD_INSERT', desc: 'Default parameterized multi-row insert batching' }
      ];
    }
    return schema.ingestionEngines.map(e => ({
      label: e.label + (e.recommended ? ' (Recommended)' : ''),
      value: e.value,
      desc: e.desc
    }));
  });

  public defaultIngestionEngine = computed<string>(() => {
    const schema = this.selectedProviderSchema();
    if (!schema?.ingestionEngines || schema.ingestionEngines.length === 0) return 'STANDARD_INSERT';
    const rec = schema.ingestionEngines.find(e => e.recommended);
    return rec ? rec.value : schema.ingestionEngines[0].value;
  });

  public tlsModeOptions = computed<CustomSelectOption[]>(() => {
    const isProd = this.isProductionEnv();
    if (isProd) {
      return [
        { label: 'Verify Full (CA & Hostname Match) — Production Default', value: 'VERIFY_FULL', desc: 'Enforces TLS 1.2+, validates CA chain, and checks Hostname SAN' },
        { label: 'Verify CA Certificate', value: 'VERIFY_CA', desc: 'Enforces TLS and validates against enterprise trusted CA' },
        { label: 'Require TLS', value: 'REQUIRE', desc: 'Enforces TLS encryption on wire without CA validation' },
        { label: 'Mutual TLS (mTLS)', value: 'CERTIFICATE_MTLS', desc: 'Two-way cryptographic authentication with client certificate' }
      ];
    } else {
      return [
        { label: 'Prefer TLS (Non-Prod Default)', value: 'PREFER', desc: 'Attempts TLS first, falls back to unencrypted TCP if unsupported' },
        { label: 'Require TLS', value: 'REQUIRE', desc: 'Enforces TLS encryption on wire without CA validation' },
        { label: 'Verify CA Certificate', value: 'VERIFY_CA', desc: 'Enforces TLS and validates against enterprise trusted CA' },
        { label: 'Verify Full (CA & Hostname Match)', value: 'VERIFY_FULL', desc: 'Enforces TLS 1.2+, validates CA chain, and checks Hostname SAN' },
        { label: 'Disable TLS (Unencrypted TCP)', value: 'DISABLE', desc: 'Plain unencrypted TCP (allowed for localhost in Non-Prod)' }
      ];
    }
  });

  public ngOnInit(): void {
    const draftEnv = this.ms.wizardDraft().environment;
    if (draftEnv) {
      this.filterEnvironment.set(draftEnv);
      this.selectedTlsMode.set(draftEnv === 'Production' ? 'VERIFY_FULL' : 'PREFER');
    }
    if (!this.ms.wizardDraft().collisionPolicy) {
      this.ms.updateDraft({ collisionPolicy: 'FAIL_ON_COLLISION' });
    }
  }

  public isProductionEnv(): boolean {
    return this.ms.wizardDraft().environment === 'Production';
  }

  public getModeLabel(): string {
    const m = this.ms.wizardDraft().mode;
    switch (m) {
      case 'M1_BULK': return 'Bulk Migration';
      case 'M2_BULK_CDC': return 'Bulk + CDC';
      case 'M3_CDC': return 'Continuous CDC';
      case 'M4_INCREMENTAL': return 'Incremental Watermark';
      case 'M5_STATE_SYNC': return 'Bi-Directional Sync';
      case 'M6_SCHEMA_ONLY': return 'Schema / DDL Only';
      case 'M7_DATA_ONLY': return 'Data Only';
      default: return 'Bulk Migration';
    }
  }

  public getCategoryFilterLabel(cat: string): string {
    switch (cat) {
      case 'ALL': return 'All';
      case 'RELATIONAL': return 'Relational';
      case 'WAREHOUSE': return 'Warehouse';
      case 'NOSQL': return 'NoSQL';
      case 'STREAMING': return 'Streaming';
      case 'STORAGE': return 'Storage';
      default: return cat;
    }
  }

  public cleanLabel(label: string): string {
    if (!label) return '';
    return label.replace(/\s*\*+\s*$/, '').trim();
  }

  public getProviderIcon(provider: PhysicalProviderId): string {
    const s = ALL_28_PROVIDER_SCHEMAS[provider];
    return s?.icon || 'database';
  }

  public isSecretVisible(fieldId: string): boolean {
    return !!this.secretVisibilityMap()[fieldId];
  }

  public toggleSecretVisibility(fieldId: string): void {
    const current = this.secretVisibilityMap();
    this.secretVisibilityMap.set({ ...current, [fieldId]: !current[fieldId] });
  }

  public setConnectionMode(mode: 'SAVED' | 'NEW'): void {
    if (this.ms.wizardDraft().targetConnectionMode === mode) return;

    this.ms.updateDraft({
      targetConnectionMode: mode,
      targetConnectionId: undefined,
      targetProvider: undefined as any,
      targetHost: '',
      targetPort: 0,
      targetDatabase: '',
      targetUsername: '',
      targetSecretRef: '',
      targetParams: {},
      targetVerified: false,
      targetVerificationResult: undefined,
      targetSaveToVault: false,
      targetSchema: '',
      targetAutoCreateSchema: true,
      targetIngestionEngine: ''
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public toggleRouteFilter(route: NetworkRouteType): void {
    const current = this.filterRoutes();
    if (current.includes(route)) {
      this.filterRoutes.set(current.filter(r => r !== route));
    } else {
      this.filterRoutes.set([...current, route]);
    }
  }

  public removeFilterChip(chipId: string): void {
    if (chipId === 'mode') this.filterModeCompatible.set(false);
    else if (chipId === 'env') this.filterEnvironment.set('ALL');
    else if (chipId === 'cat') this.filterCategory.set('ALL');
    else if (chipId.startsWith('route-')) {
      const r = chipId.replace('route-', '') as NetworkRouteType;
      this.toggleRouteFilter(r);
    }
  }

  public clearAllFilters(): void {
    this.filterModeCompatible.set(false);
    this.filterEnvironment.set('ALL');
    this.filterCategory.set('ALL');
    this.filterRoutes.set([]);
    this.savedSearchQuery.set('');
  }

  public selectTargetEngine(engineId: PhysicalProviderId): void {
    const schema = ALL_28_PROVIDER_SCHEMAS[engineId];
    if (!schema) return;

    const defIngest = schema.ingestionEngines?.find(e => e.recommended)?.value ||
      schema.ingestionEngines?.[0]?.value || 'STANDARD_INSERT';

    this.ms.updateDraft({
      targetProvider: engineId,
      targetHost: '',
      targetPort: schema.defaultPort || 0,
      targetDatabase: '',
      targetUsername: '',
      targetSecretRef: '',
      targetParams: {},
      targetVerified: false,
      targetVerificationResult: undefined,
      targetSaveToVault: false,
      targetSchema: '',
      targetAutoCreateSchema: true,
      targetIngestionEngine: defIngest
    });

    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public changeTargetEngine(): void {
    this.ms.updateDraft({
      targetProvider: undefined as any,
      targetHost: '',
      targetPort: 0,
      targetDatabase: '',
      targetUsername: '',
      targetSecretRef: '',
      targetParams: {},
      targetVerified: false,
      targetVerificationResult: undefined,
      targetSaveToVault: false,
      targetSchema: '',
      targetIngestionEngine: ''
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  // Step 3 Target Compatibility Check (Mode Rules)
  public checkTargetCompatibility(engineId: PhysicalProviderId): { compatible: boolean; reason?: string } {
    const mode = this.ms.wizardDraft().mode || 'M1_BULK';

    // M1 & M7: All 28 Providers available
    if (mode === 'M1_BULK' || mode === 'M7_DATA_ONLY') {
      return { compatible: true };
    }

    // M6: Schema Only -> Target MUST be a schema-bearing SQL database
    if (mode === 'M6_SCHEMA_ONLY') {
      const nonSqlTargets: PhysicalProviderId[] = [
        'Apache Kafka', 'Amazon Kinesis', 'Azure Event Hubs', 'Google Cloud Pub/Sub',
        'Amazon S3', 'Google Cloud Storage', 'Azure Blob Storage', 'MinIO', 'Apache HDFS',
        'Redis', 'KeyDB'
      ];
      if (nonSqlTargets.includes(engineId)) {
        return {
          compatible: false,
          reason: `${engineId} is a streaming/object store without a relational DDL catalog required for ${this.getModeLabel()}.`
        };
      }
      return { compatible: true };
    }

    // M2 / M3: Continuous CDC -> Target must support continuous upsert / stream writes
    if (mode === 'M2_BULK_CDC' || mode === 'M3_CDC') {
      const rawStorageTargets: PhysicalProviderId[] = [
        'Amazon S3', 'Google Cloud Storage', 'Azure Blob Storage', 'MinIO', 'Apache HDFS', 'SQLite'
      ];
      if (rawStorageTargets.includes(engineId)) {
        return {
          compatible: false,
          reason: `Raw storage without transactional table format does not support idempotent continuous CDC upserts required for ${this.getModeLabel()}.`
        };
      }
      return { compatible: true };
    }

    return { compatible: true };
  }

  public isFieldVisible(field: ProviderFormField, schema: ProviderFormSchema): boolean {
    const fid = field.id;

    if (schema.name.includes('Oracle') || schema.providerId === 'Oracle') {
      const connType = this.getTargetFieldValue('connection_type') || 'SERVICE_NAME';
      if (connType === 'SERVICE_NAME' && ['sid', 'tns_descriptor', 'wallet_path', 'wallet_password', 'tns_alias'].includes(fid)) return false;
      if (connType === 'SID' && ['service_name', 'tns_descriptor', 'wallet_path', 'wallet_password', 'tns_alias'].includes(fid)) return false;
      if (connType === 'TNS_DESCRIPTOR' && ['host', 'port', 'service_name', 'sid', 'wallet_path', 'wallet_password', 'tns_alias'].includes(fid)) return false;
      if (connType === 'WALLET' && ['host', 'port', 'service_name', 'sid', 'tns_descriptor'].includes(fid)) return false;
    }

    if (schema.name.includes('SQL Server') || schema.providerId === 'Microsoft SQL Server') {
      const authType = this.getTargetFieldValue('auth_type') || 'SQL_AUTH';
      if (authType === 'WINDOWS_SSPI' && ['username', 'secret_ref'].includes(fid)) return false;
    }

    if (schema.name.includes('MongoDB') || schema.providerId === 'MongoDB') {
      const connMode = this.getTargetFieldValue('connection_mode') || 'STANDALONE';
      if (connMode === 'STANDALONE' && ['replica_endpoints', 'replica_set_name'].includes(fid)) return false;
      if (connMode === 'CLUSTER' && ['host', 'port'].includes(fid)) return false;
    }

    if (schema.name.includes('Snowflake') || schema.providerId === 'Snowflake') {
      const authType = this.getTargetFieldValue('auth_type') || 'PASSWORD';
      if (authType === 'PASSWORD' && ['private_key_path', 'passphrase', 'oauth_token'].includes(fid)) return false;
      if (authType === 'KEY_PAIR' && ['secret_ref', 'oauth_token'].includes(fid)) return false;
      if (authType === 'OAUTH' && ['username', 'secret_ref', 'private_key_path', 'passphrase'].includes(fid)) return false;
      if (authType === 'SSO' && ['secret_ref', 'private_key_path', 'passphrase', 'oauth_token'].includes(fid)) return false;
    }

    if (schema.name.includes('BigQuery') || schema.providerId === 'Google BigQuery') {
      const authType = this.getTargetFieldValue('auth_type') || 'SERVICE_ACCOUNT_KEY';
      if (authType === 'ADC' && fid === 'service_account_json') return false;
    }

    if (schema.name.includes('Elasticsearch') || schema.providerId === 'Elasticsearch') {
      const authType = this.getTargetFieldValue('auth_type') || 'BASIC';
      if (authType === 'API_KEY' && ['username', 'secret_ref'].includes(fid)) return false;
      if (authType === 'BASIC' && fid === 'api_key') return false;
    }

    if (schema.name.includes('Kafka') || schema.providerId === 'Apache Kafka') {
      const secProt = this.getTargetFieldValue('security_protocol') || 'PLAINTEXT';
      if ((secProt === 'PLAINTEXT' || secProt === 'SSL') && ['sasl_mechanism', 'sasl_username', 'secret_ref'].includes(fid)) return false;
    }

    if (schema.name.includes('Kinesis') || schema.name.includes('S3') || schema.providerId === 'Amazon S3' || schema.providerId === 'Amazon Kinesis') {
      const authType = this.getTargetFieldValue('auth_type') || 'ACCESS_KEYS';
      if (authType === 'IAM_ROLE' && ['aws_access_key_id', 'secret_ref'].includes(fid)) return false;
    }

    if (schema.name.includes('Blob') || schema.providerId === 'Azure Blob Storage') {
      const authType = this.getTargetFieldValue('auth_type') || 'CONN_STRING';
      if (authType === 'CONN_STRING' && ['storage_account_name', 'account_key', 'sas_token'].includes(fid)) return false;
      if (authType === 'ACCOUNT_KEY' && ['secret_ref', 'sas_token'].includes(fid)) return false;
      if (authType === 'SAS_TOKEN' && ['secret_ref', 'storage_account_name', 'account_key'].includes(fid)) return false;
    }

    return true;
  }

  public evaluateSavedConnection(conn: ConnectionItem): { isEligible: boolean; reason?: string } {
    const compat = this.checkTargetCompatibility(conn.provider);
    if (!compat.compatible) {
      return { isEligible: false, reason: compat.reason };
    }
    return { isEligible: true };
  }

  public selectSavedEndpoint(conn: SavedConnectionItemExtended): void {
    const evalRes = this.evaluateSavedConnection(conn);

    if (evalRes.isEligible) {
      this.ms.updateDraft({
        targetConnectionId: conn.id,
        targetProvider: conn.provider,
        targetHost: conn.host,
        targetPort: conn.port,
        targetDatabase: conn.databaseName,
        targetUsername: conn.username,
        targetSecretRef: conn.secretRef || '',
        targetTls: conn.tlsEnabled,
        targetNetworkRoute: conn.networkRoute as any,
        targetVerified: true,
        targetSchema: conn.databaseName || 'public',
        targetAutoCreateSchema: true,
        targetVerificationResult: {
          fingerprint: `fp-target-${conn.id}-${Date.now()}`,
          isVerified: true,
          hasBlockingIssues: false,
          latencyMs: conn.latencyMs || 1.8,
          physicalConnection: { status: 'PASSED', latencyMs: conn.latencyMs || 1.8, detail: `${conn.networkRoute} active` },
          identityAttestation: { status: 'PASSED', systemVersion: `${conn.provider} Target Engine 2026.1` },
          writeAuthority: { status: 'PASSED', permissions: ['CREATE', 'INSERT', 'ALTER', 'DROP'] },
          ingestionCapability: { status: 'PASSED', preferredStrategy: 'NATIVE_FAST_PATH', fallbackStrategy: 'BATCH_INSERT', directPathAvailable: true, privilegesVerified: true },
          sandboxCapability: { status: 'PASSED', supported: true, detail: 'Canary probe passed' },
          storageHeadroom: { status: 'SUFFICIENT', displayStatus: '420 GB free space available' },
          compatibility: {
            sourceProvider: this.ms.wizardDraft().sourceProvider || 'Oracle',
            sourceVersion: '19.3',
            targetProvider: conn.provider,
            targetVersion: '16.2',
            topology: this.ms.wizardDraft().sourceProvider === conn.provider ? 'Homogeneous' : 'Heterogeneous',
            schemaConversion: 'Supported',
            dataTypeMapping: { status: 'Direct map', reviewCount: 0, detail: '100% verified' },
            proceduralConversion: { status: 'Supported', analyzedCount: 0, automaticCount: 0, reviewCount: 0 },
            isBlocked: false
          },
          targetContents: { existingObjectsDetected: false, tableCount: 0, viewCount: 0, indexCount: 0, conflictingObjectsCount: 0 }
        }
      });
    } else {
      this.ms.updateDraft({
        targetConnectionId: conn.id,
        targetProvider: conn.provider,
        targetVerified: false
      });
    }
  }

  public getTargetFieldValue(fieldId: string): any {
    const d = this.ms.wizardDraft();
    switch (fieldId) {
      case 'host': return d.targetHost;
      case 'port': return d.targetPort ? d.targetPort : '';
      case 'database':
      case 'database_name':
      case 'database_path':
      case 'service_name': return d.targetDatabase;
      case 'username': return d.targetUsername;
      case 'secret_ref':
      case 'password': return d.targetSecretRef;
      default: return d.targetParams?.[fieldId] ?? '';
    }
  }

  public onTargetFieldChange(fieldId: string, value: any): void {
    const d = this.ms.wizardDraft();
    const partial: any = { targetVerified: false, targetVerificationResult: undefined };

    switch (fieldId) {
      case 'host': partial.targetHost = value; break;
      case 'port': partial.targetPort = Number(value) || 0; break;
      case 'database':
      case 'database_name':
      case 'database_path':
      case 'service_name': partial.targetDatabase = value; break;
      case 'username': partial.targetUsername = value; break;
      case 'secret_ref':
      case 'password': partial.targetSecretRef = value; break;
      default: partial.targetParams = { ...(d.targetParams || {}), [fieldId]: value }; break;
    }

    this.ms.updateDraft(partial);
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public onTargetSchemaChange(val: string): void {
    this.ms.updateDraft({
      targetSchema: val,
      targetVerified: false,
      targetVerificationResult: undefined
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public onIngestionEngineChange(val: any): void {
    this.ms.updateDraft({ targetIngestionEngine: val });
  }

  public onCollisionPolicyChange(val: any): void {
    if (val === 'DROP_AND_RECREATE' && this.isProductionEnv()) {
      this.ms.openDestructiveModal();
      return;
    }
    this.ms.updateDraft({ collisionPolicy: val as CollisionPolicyType, productionCollisionAcknowledged: false });
  }

  public onVaultTargetNameChange(name: string): void {
    this.vaultTargetConnectionName.set(name);
    this.isTargetVaultSaved.set(false);
  }

  public saveTargetToVault(): void {
    if (!this.vaultTargetConnectionName().trim()) return;
    const d = this.ms.wizardDraft();
    const schema = this.selectedProviderSchema();
    const newTarget: SavedConnectionItemExtended = {
      id: `conn-target-${Date.now()}`,
      name: this.vaultTargetConnectionName().trim(),
      provider: d.targetProvider,
      category: (schema?.category as any) || 'RELATIONAL',
      environment: (d.environment as any) || 'Production',
      host: d.targetHost || 'localhost',
      port: d.targetPort || 5432,
      databaseName: d.targetDatabase || 'defaultdb',
      username: d.targetUsername || 'admin',
      tlsEnabled: !!d.targetTls,
      networkRoute: (d.targetNetworkRoute as any) || 'DIRECT',
      status: 'CONNECTED',
      verificationFreshness: 'Just now',
      latencyMs: 1.8,
      secretRef: d.targetSecretRef || '',
      capabilities: ['BULK_WRITE', 'DDL_CANARY'],
      assignedMigrationCount: 0,
      assignedProjectCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      scope: 'PROJECT'
    };
    this.enterpriseSavedTargets = [newTarget, ...this.enterpriseSavedTargets];
    this.ms.connections.update(list => [newTarget, ...list]);
    this.isTargetVaultSaved.set(true);
    this.ms.updateDraft({ targetSaveToVault: true });
  }

  public onRouteTypeChange(route: any): void {
    this.ms.updateDraft({
      targetNetworkRoute: route,
      targetVerified: false,
      targetVerificationResult: undefined
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public onTlsModeChange(mode: string): void {
    this.selectedTlsMode.set(mode);
    this.ms.updateDraft({
      targetTls: mode !== 'DISABLE',
      targetVerified: false,
      targetVerificationResult: undefined
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public onSaveToVaultChange(checked: boolean): void {
    this.ms.updateDraft({ targetSaveToVault: checked });
    if (!checked) {
      this.isTargetVaultSaved.set(false);
    } else if (!this.vaultTargetConnectionName()) {
      const schema = this.selectedProviderSchema();
      this.vaultTargetConnectionName.set(`${schema?.name || this.ms.wizardDraft().targetProvider || 'Target'} ${this.isProductionEnv() ? 'Production' : 'Target'}`);
    }
  }

  // ===========================================================================
  // 6-STAGE TARGET ATTESTATION PROBE (Write Canary, Headroom, Collisions)
  // ===========================================================================
  public runTargetAttestationProbe(): void {
    const d = this.ms.wizardDraft();
    const schema = this.selectedProviderSchema();
    if (!schema) return;

    // Guard: Required target schema
    if (!d.targetSchema || d.targetSchema.trim() === '') {
      this.verificationError.set({
        stage: 'Parameter Validation',
        category: 'MISSING_TARGET_SCHEMA',
        message: 'Target Schema / Namespace is required before attestation.'
      });
      this.probeExecuted.set(true);
      return;
    }

    // Guard: Self-targeting
    if (this.isSelfTargetingBlocked()) {
      this.verificationError.set({
        stage: 'Stage 1: Transport & Routing',
        category: 'CIRCULAR_SELF_TARGETING',
        message: 'Self-targeting detected: Source and Target instances are identical. A distinct target schema is required.'
      });
      this.probeExecuted.set(true);
      return;
    }

    this.isVerifying.set(true);
    this.probeExecuted.set(false);
    this.verificationError.set(null);

    this.targetStages.forEach(s => {
      s.status = 'PENDING';
      s.detail = undefined;
    });

    const runStage = (stageIdx: number) => {
      if (stageIdx > 6) {
        this.isVerifying.set(false);
        this.probeExecuted.set(true);

        const targetResult: TargetVerificationResult = {
          fingerprint: `fp-target-${Date.now()}`,
          isVerified: true,
          hasBlockingIssues: false,
          latencyMs: 1.8,
          physicalConnection: { status: 'PASSED', latencyMs: 1.8, detail: 'Direct TCP negotiated' },
          identityAttestation: { status: 'PASSED', systemVersion: `${schema.name} 2026.1 Enterprise · Charset: UTF8` },
          writeAuthority: { status: 'PASSED', permissions: ['CREATE', 'INSERT', 'ALTER', 'TRUNCATE', 'DROP'], detail: 'Canary passed' },
          ingestionCapability: {
            status: 'PASSED',
            preferredStrategy: d.targetIngestionEngine || 'NATIVE_FAST_PATH',
            fallbackStrategy: 'BATCH_INSERT',
            directPathAvailable: true,
            privilegesVerified: true
          },
          sandboxCapability: { status: 'PASSED', supported: true, detail: '__akaal_canary_probe clean' },
          storageHeadroom: { status: 'SUFFICIENT', displayStatus: '420 GB free space available on tablespace' },
          compatibility: {
            sourceProvider: d.sourceProvider || 'Oracle',
            sourceVersion: '19.3',
            targetProvider: schema.providerId,
            targetVersion: '16.2',
            topology: d.sourceProvider === schema.providerId ? 'Homogeneous' : 'Heterogeneous',
            schemaConversion: 'Supported',
            dataTypeMapping: { status: 'Direct map', reviewCount: 0, detail: '100% data types mapped' },
            proceduralConversion: { status: 'Supported', analyzedCount: 0, automaticCount: 0, reviewCount: 0 },
            isBlocked: false
          },
          targetContents: { existingObjectsDetected: false, tableCount: 0, viewCount: 0, indexCount: 0, conflictingObjectsCount: 0 }
        };

        this.ms.updateDraft({
          targetVerified: true,
          targetVerificationResult: targetResult
        });
        if (!this.vaultTargetConnectionName()) {
          this.vaultTargetConnectionName.set(`${schema.name} ${this.isProductionEnv() ? 'Production' : 'Target'}`);
        }
        return;
      }

      this.activeStageIndex.set(stageIdx);
      const stage = this.targetStages[stageIdx - 1];
      this.activeStageName.set(stage.name);
      stage.status = 'TESTING';

      setTimeout(() => {
        if (stageIdx === 1) {
          // Stage 1: Transport & Routing Ping
          const route = d.targetNetworkRoute || 'DIRECT';
          if (route === 'SSH_BASTION' && !d.targetBastionHost) {
            stage.status = 'FAILED';
            this.verificationError.set({
              stage: 'Stage 1: Transport & Routing',
              category: 'UNRESOLVED_BASTION_HOST',
              message: 'SSH Bastion Host is required when using Bastion Tunnel on Target'
            });
            this.isVerifying.set(false);
            this.probeExecuted.set(true);
            return;
          }
          stage.status = 'PASSED';
          runStage(stageIdx + 1);
        } else if (stageIdx === 2) {
          // Stage 2: Target Identity & Charset Check
          stage.status = 'PASSED';
          runStage(stageIdx + 1);
        } else if (stageIdx === 3) {
          // Stage 3: Live DDL & Write Canary Probe
          stage.status = 'PASSED';
          runStage(stageIdx + 1);
        } else if (stageIdx === 4) {
          // Stage 4: High-Throughput Ingestion Fast-Path
          stage.status = 'PASSED';
          runStage(stageIdx + 1);
        } else if (stageIdx === 5) {
          // Stage 5: Storage Headroom & Tablespace Capacity
          stage.status = 'PASSED';
          runStage(stageIdx + 1);
        } else if (stageIdx === 6) {
          // Stage 6: Pre-Existing Object Collision Audit
          stage.status = 'PASSED';
          runStage(stageIdx + 1);
        }
      }, 200);
    };

    runStage(1);
  }
}
