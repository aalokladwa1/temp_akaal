import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import { MigrationDevFixturesAdapter } from '../../../../core/fixtures/migration-dev-fixtures.adapter';
import {
  PhysicalProviderId,
  ConnectionItem,
  SourceVerificationResult,
  NetworkRouteType
} from '../../../../core/models/migration-view.models';
import {
  ALL_48_PROVIDER_SCHEMAS,
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
  category: 'RELATIONAL' | 'DISTRIBUTED_SQL' | 'WAREHOUSE' | 'NOSQL' | 'STREAMING' | 'STORAGE' | 'SAAS';
  categoryLabel: string;
  icon: string;
}

export interface CatalogCategoryTab {
  id: 'ALL' | 'RELATIONAL' | 'DISTRIBUTED_SQL' | 'WAREHOUSE' | 'NOSQL' | 'STREAMING' | 'STORAGE' | 'SAAS';
  label: string;
  count: number;
}

export interface VerificationPhaseState {
  index: number;
  name: string;
  description: string;
  chipLabel: string;
  status: 'PENDING' | 'TESTING' | 'PASSED' | 'FAILED';
  detail?: string;
  latencyMs?: number;
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
      @if (vs.newValidationDraft().targetConnectionMode) {
        <div class="flex flex-col gap-3 border-b border-slate-200/60 pb-3">
          <div class="flex items-center justify-between flex-wrap gap-2">
            <div class="flex flex-col gap-0.5">
              <h1 class="text-base font-bold text-slate-900 tracking-tight">Target Connection</h1>
              <p class="text-xs text-slate-500 font-normal">Choose how AKAAL Validation Studio should connect to the target database system.</p>
            </div>

            <!-- Compact Segmented Control (Top-Right) -->
            <app-segmented-control
              [options]="modeControlOptions"
              [value]="vs.newValidationDraft().targetConnectionMode"
              (valueChange)="setConnectionMode($event)">
            </app-segmented-control>
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- SAME-ENDPOINT GUARD ALERT (Calm, non-alarming contextual indicator)       -->
      <!-- ========================================================================= -->
      @if (isSameEndpoint()) {
        <div class="p-3.5 bg-amber-50/70 border border-amber-200/80 rounded-xl flex items-start gap-3 text-xs text-amber-900 animate-in fade-in duration-150">
          <app-lucide-icon name="info" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-0.5">
            <span class="font-semibold text-amber-950">Same Endpoint Detected</span>
            <p class="text-xs text-amber-800 font-normal leading-relaxed">
              Source and Target appear to reference the same endpoint. Confirm this is intentional. Comparable objects are selected in Step 4.
            </p>
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- PROJECT-LINKED TARGET CANDIDATE CONTEXT (Subtle helper)                   -->
      <!-- ========================================================================= -->
      @if (projectTargetCandidate(); as candidate) {
        <div class="p-3 bg-blue-50/40 border border-blue-200/80 rounded-xl flex items-center justify-between gap-3 text-xs animate-in fade-in duration-150">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="link" [size]="15" class="text-blue-600 shrink-0"></app-lucide-icon>
            <span class="text-slate-700">
              Linked project candidate: <strong class="font-semibold text-slate-900">{{ candidate.engine }}</strong> ({{ candidate.instance }})
            </span>
          </div>
          <button
            type="button"
            (click)="applyCandidateTarget(candidate)"
            class="px-2.5 py-1 text-xs font-semibold text-blue-700 bg-white hover:bg-blue-50 border border-blue-200 rounded-md transition-colors cursor-pointer shrink-0">
            Prefill Target Details
          </button>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- ENTRY STATE: TWO HERO CHOICE CARDS (CENTERED, DEEP, NO EMPTY VOID)        -->
      <!-- ========================================================================= -->
      @if (!vs.newValidationDraft().targetConnectionMode) {
        <section class="pt-8 pb-12 flex flex-col items-center justify-center animate-in fade-in duration-150">
          
          <div class="flex flex-col items-center text-center gap-1.5 pb-6">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight">Target Connection</h1>
            <p class="text-sm text-slate-500 max-w-md font-normal">
              Choose how AKAAL Validation Studio should connect to your target database system.
            </p>
          </div>

          <!-- 2 Selection Cards Wrapper: max-w-3xl mx-auto mt-2 grid grid-cols-2 gap-6 -->
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
                <span class="px-2.5 py-1 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md">
                  Enterprise Vault
                </span>
              </div>
              <div class="flex flex-col gap-2">
                <span class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  Saved Connection
                </span>
                <p class="text-xs text-slate-500 font-normal leading-relaxed">
                  Use an existing enterprise connection already verified in the Workspace Vault.
                </p>
                <div class="pt-2.5 border-t border-slate-100 flex items-center gap-2 text-[11px] text-slate-600 font-medium">
                  <app-lucide-icon name="check" [size]="13" class="text-emerald-600"></app-lucide-icon>
                  <span>Instant attach with existing IAM &amp; VPC routes</span>
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
                <span class="px-2.5 py-1 text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
                  Target Endpoint
                </span>
              </div>
              <div class="flex flex-col gap-2">
                <span class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  New Connection
                </span>
                <p class="text-xs text-slate-500 font-normal leading-relaxed">
                  Configure and verify a new target database endpoint from the catalog.
                </p>
                <div class="pt-2.5 border-t border-slate-100 flex items-center gap-2 text-[11px] text-slate-600 font-medium">
                  <app-lucide-icon name="check" [size]="13" class="text-blue-600"></app-lucide-icon>
                  <span>Read-only attestation with configurable TLS &amp; Bastion routes</span>
                </div>
              </div>
            </button>

          </div>
        </section>
      }

      <!-- ========================================================================= -->
      <!-- BRANCH 1: SAVED CONNECTION INTERACTIVE ENDPOINT GRID & 6-FILTER POPOVER   -->
      <!-- ========================================================================= -->
      @if (vs.newValidationDraft().targetConnectionMode === 'SAVED') {
        <section class="space-y-4 animate-in fade-in duration-150">
          
          <!-- Top Search & Filter Bar with Popover Anchor -->
          <div class="relative flex items-center gap-2.5">
            
            <div class="relative flex-1">
              <input
                type="text"
                [(ngModel)]="savedSearchQuery"
                placeholder="Search saved target connections by name, host, or engine..."
                class="w-full h-10 pl-11 pr-4 bg-white border border-slate-200 focus:border-blue-600 rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors shadow-2xs" />
              <app-lucide-icon name="search" [size]="15" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none flex items-center justify-center"></app-lucide-icon>
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
                <span class="w-5 h-5 rounded-md bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
                  {{ activeFilterCount() }}
                </span>
              }
              <app-lucide-icon [name]="isFilterPopoverOpen() ? 'chevron-up' : 'chevron-down'" [size]="13" class="text-slate-400"></app-lucide-icon>
            </button>

            <!-- 6-FILTER POPOVER MODAL -->
            @if (isFilterPopoverOpen()) {
              <div
                class="absolute right-0 top-11 z-50 w-88 p-4 bg-white border border-slate-200 rounded-2xl shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-100">
                
                <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span class="text-xs font-bold text-slate-900">Filter Saved Targets</span>
                  <button
                    type="button"
                    (click)="isFilterPopoverOpen.set(false)"
                    class="text-slate-400 hover:text-slate-600 cursor-pointer">
                    <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
                  </button>
                </div>

                <!-- 1. Environment Predicate -->
                <div class="flex flex-col gap-1.5">
                  <span class="text-[11px] font-semibold text-slate-700">Environment</span>
                  <div class="flex items-center gap-1.5">
                    @for (env of ['ALL', 'Production', 'Non-Production']; track env) {
                      <button
                        type="button"
                        (click)="filterEnvironment.set(env)"
                        class="px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer transition-colors"
                        [class]="filterEnvironment() === env
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-slate-600 border-slate-200'">
                        {{ env }}
                      </button>
                    }
                  </div>
                </div>

                <!-- 2. Category Filter -->
                <div class="flex flex-col gap-1.5 pt-2 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Category</span>
                  <div class="flex items-center gap-1.5 flex-wrap">
                    @for (cat of ['ALL', 'RELATIONAL', 'DISTRIBUTED_SQL', 'WAREHOUSE', 'NOSQL', 'STREAMING', 'STORAGE', 'SAAS']; track cat) {
                      <button
                        type="button"
                        (click)="filterCategory.set(cat)"
                        class="px-2 py-0.5 rounded text-[10px] font-medium border cursor-pointer transition-colors"
                        [class]="filterCategory() === cat
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-slate-600 border-slate-200'">
                        {{ getCategoryFilterLabel(cat) }}
                      </button>
                    }
                  </div>
                </div>

                <!-- 3. Network Route Filter -->
                <div class="flex flex-col gap-1.5 pt-2 border-t border-slate-100">
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

                <!-- 4. Health Status Filter -->
                <div class="flex flex-col gap-1.5 pt-2 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Target Readiness Status</span>
                  <div class="flex flex-col gap-1">
                    @for (status of healthFiltersList; track status.value) {
                      <label class="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          [checked]="filterHealthStatuses().includes(status.value)"
                          (change)="toggleHealthFilter(status.value)"
                          class="w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                        <span>{{ status.label }}</span>
                      </label>
                    }
                  </div>
                </div>

                <!-- 5. Scope Filter -->
                <div class="flex flex-col gap-1.5 pt-2 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Connection Vault Scope</span>
                  <div class="flex flex-col gap-1">
                    @for (scopeOpt of scopeFiltersList; track scopeOpt.value) {
                      <label class="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer select-none">
                        <input
                          type="radio"
                          name="targetScopeFilter"
                          [checked]="filterScope() === scopeOpt.value"
                          (change)="filterScope.set(scopeOpt.value)"
                          class="w-3.5 h-3.5 border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                        <span>{{ scopeOpt.label }}</span>
                      </label>
                    }
                  </div>
                </div>

                <!-- Popover Footer -->
                <div class="pt-2.5 border-t border-slate-100 flex items-center justify-between">
                  <button
                    type="button"
                    (click)="clearAllFilters()"
                    class="text-[11px] font-medium text-slate-500 hover:text-slate-800 cursor-pointer">
                    Clear All
                  </button>
                  <button
                    type="button"
                    (click)="isFilterPopoverOpen.set(false)"
                    class="h-7 px-3 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md cursor-pointer">
                    Apply ({{ filteredSavedConnections().length }} results)
                  </button>
                </div>

              </div>
            }

          </div>

          <!-- Active Filter Chips Row -->
          @if (activeFilterChips().length > 0) {
            <div class="flex items-center gap-1.5 flex-wrap animate-in fade-in duration-100">
              <span class="text-[11px] text-slate-400 font-medium">Active filters:</span>
              @for (chip of activeFilterChips(); track chip.id) {
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  <span>{{ chip.label }}</span>
                  <button
                    type="button"
                    (click)="removeFilterChip(chip.id)"
                    class="hover:text-rose-600 cursor-pointer">
                    <app-lucide-icon name="x" [size]="10"></app-lucide-icon>
                  </button>
                </span>
              }
              <button
                type="button"
                (click)="clearAllFilters()"
                class="text-[11px] text-blue-600 hover:underline cursor-pointer pl-1">
                Clear All
              </button>
            </div>
          }

          <!-- The Saved Connections Interactive Grid: grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            @for (conn of filteredSavedConnections(); track conn.id) {
              @let isSelected = vs.newValidationDraft().targetConnectionId === conn.id;
              <div
                (click)="selectSavedEndpoint(conn)"
                class="p-4 rounded-xl border transition-all text-left flex flex-col justify-between gap-3 bg-white shadow-2xs relative cursor-pointer group"
                [class]="isSelected
                  ? 'border-blue-600 ring-2 ring-blue-500/20 bg-blue-50/10'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/40'">
                
                <!-- Card Header -->
                <div class="flex items-start justify-between gap-2">
                  <div class="flex items-center gap-2.5 min-w-0">
                    <div
                      class="w-8 h-8 rounded-lg border flex items-center justify-center transition-colors shrink-0"
                      [class]="isSelected ? 'bg-blue-600 text-white border-blue-600' : 'bg-slate-50 border-slate-200 text-slate-600 group-hover:border-slate-300'">
                      <app-lucide-icon [name]="getProviderIcon(conn.provider)" [size]="16"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col min-w-0">
                      <span class="text-xs font-bold text-slate-900 truncate leading-tight group-hover:text-blue-600 transition-colors">
                        {{ conn.name }}
                      </span>
                      <span class="text-[10px] text-slate-400 font-medium truncate">
                        {{ conn.provider }} &middot; {{ conn.category }}
                      </span>
                    </div>
                  </div>

                  <!-- Status Dot Pill -->
                  <div class="flex items-center gap-1.5 shrink-0">
                    <span
                      class="w-2 h-2 rounded-xs shrink-0"
                      [class]="conn.status === 'CONNECTED' ? 'bg-emerald-500' : 'bg-amber-500'">
                    </span>
                    <span class="text-[10px] font-mono font-medium text-slate-500">
                      {{ conn.status === 'CONNECTED' ? 'Healthy' : 'Needs Test' }}
                    </span>
                  </div>
                </div>

                <!-- Card Details -->
                <div class="space-y-1.5 py-1 text-[11px] text-slate-600 border-t border-slate-100 font-medium">
                  <div class="flex items-center justify-between">
                    <span class="text-slate-400">Endpoint</span>
                    <span class="font-mono text-slate-800 truncate max-w-[180px]" [title]="conn.host + ':' + conn.port">
                      {{ conn.host }}:{{ conn.port }}
                    </span>
                  </div>
                  @if (conn.databaseName) {
                    <div class="flex items-center justify-between">
                      <span class="text-slate-400">Database</span>
                      <span class="font-mono text-slate-800 truncate max-w-[180px]">{{ conn.databaseName }}</span>
                    </div>
                  }
                  <div class="flex items-center justify-between">
                    <span class="text-slate-400">Network Route</span>
                    <span class="text-slate-700 capitalize">{{ conn.networkRoute.toLowerCase().replace('_', ' ') }}</span>
                  </div>
                </div>

                <!-- Card Footer Badges -->
                <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
                  <span>{{ conn.verificationFreshness || 'Verified recently' }}</span>
                  @if (isSelected) {
                    <span class="inline-flex items-center gap-1 font-semibold text-blue-600">
                      <span>Selected</span>
                      <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                    </span>
                  }
                </div>

              </div>
            }

            @if (filteredSavedConnections().length === 0) {
              <div class="col-span-full py-12 text-center text-slate-400 text-xs bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                No saved target connections match your active search and filter criteria.
              </div>
            }
          </div>

          <!-- Active Selected Connection Banner Strip -->
          @if (selectedSavedConnection(); as conn) {
            <div class="p-3 bg-emerald-50/40 border border-emerald-200 rounded-xl flex items-center justify-between gap-3 text-xs animate-in fade-in duration-100">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="check-circle-2" [size]="16" class="text-emerald-600 shrink-0"></app-lucide-icon>
                <span class="font-semibold text-emerald-900">
                  Selected <strong class="font-bold text-slate-900">{{ conn.name }}</strong> ({{ conn.provider }}) &middot; Read verified in Enterprise Vault &middot; Ready for Step 4
                </span>
              </div>
              <span class="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-700 font-medium">
                <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                <span>Target Attached</span>
              </span>
            </div>
          }

        </section>
      }

      <!-- ========================================================================= -->
      <!-- BRANCH 2: NEW CONNECTION BRANCH                                           -->
      <!-- ========================================================================= -->
      @if (vs.newValidationDraft().targetConnectionMode === 'NEW') {
        <section class="space-y-6 animate-in fade-in duration-150">
          
          <!-- PHASE A: EXPANSIVE PROVIDER CATALOG GRID -->
          @if (!vs.newValidationDraft().targetProvider) {
            <div class="flex flex-col gap-4 animate-in fade-in duration-150">
              
              <!-- Full-Width Search Bar -->
              <div class="relative w-full">
                <input
                  type="text"
                  [(ngModel)]="searchQuery"
                  placeholder="Search target providers (e.g. PostgreSQL, Oracle, Snowflake, Kafka)..."
                  class="w-full h-10 pl-11 pr-4 bg-white border border-slate-200 focus:border-blue-600 rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors shadow-2xs" />
                <app-lucide-icon name="search" [size]="15" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
                @if (searchQuery()) {
                  <button
                    type="button"
                    (click)="searchQuery.set('')"
                    class="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer">
                    <app-lucide-icon name="x-circle" [size]="14"></app-lucide-icon>
                  </button>
                }
              </div>

              <!-- Category Filter Pill Tabs -->
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
                      [class]="selectedCategoryTab() === tab.id
                        ? 'bg-blue-700 text-white'
                        : 'bg-slate-100 text-slate-500'">
                      {{ tab.count }}
                    </span>
                  </button>
                }
              </div>

              <!-- The 48 Engine Grid: grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3.5 -->
              <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3.5 mt-2">
                @for (engine of filteredCatalogEngines(); track engine.id) {
                  <button
                    type="button"
                    (click)="selectEngine(engine.id)"
                    class="p-3.5 border border-slate-200 rounded-lg hover:border-blue-500 hover:bg-blue-50/10 cursor-pointer bg-white transition-all text-left flex items-center justify-between gap-3 group shadow-2xs">
                    <div class="flex items-center gap-3 min-w-0">
                      <div class="w-9 h-9 rounded-lg border border-slate-200 bg-slate-50 flex items-center justify-center text-slate-600 group-hover:text-blue-600 group-hover:bg-blue-50 group-hover:border-blue-200 transition-colors shrink-0">
                        <app-lucide-icon [name]="engine.icon" [size]="18"></app-lucide-icon>
                      </div>
                      <div class="flex flex-col min-w-0">
                        <span class="text-xs font-semibold truncate transition-colors text-slate-900 group-hover:text-blue-600">
                          {{ engine.name }}
                        </span>
                        <span class="text-[10px] text-slate-400 font-medium uppercase tracking-wider truncate">
                          {{ engine.categoryLabel }}
                        </span>
                      </div>
                    </div>
                  </button>
                }
                @if (filteredCatalogEngines().length === 0) {
                  <div class="col-span-full py-12 text-center text-slate-400 text-xs">
                    No database engines match your search query.
                  </div>
                }
              </div>

            </div>
          }

          <!-- PHASE B: DYNAMIC TARGET CONFIGURATION FORM -->
          @if (vs.newValidationDraft().targetProvider && selectedProviderSchema(); as schema) {
            <div class="space-y-6 animate-in fade-in duration-150">
              
              <!-- Sticky Engine Summary Banner -->
              <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-blue-600 shadow-2xs shrink-0">
                    <app-lucide-icon [name]="schema.icon" [size]="20"></app-lucide-icon>
                  </div>
                  <div class="flex flex-col">
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-bold text-slate-900">{{ schema.name }}</span>
                      <span class="px-2 py-0.5 text-[10px] font-semibold bg-slate-200/70 text-slate-700 rounded-md">
                        {{ schema.category }}
                      </span>
                    </div>
                    <span class="text-[11px] text-slate-500 font-medium">Target Read-Side Endpoint for M8 Validation</span>
                  </div>
                </div>

                <button
                  type="button"
                  (click)="changeEngine()"
                  class="px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:border-slate-300 rounded-md cursor-pointer transition-colors">
                  Change Target Engine
                </button>
              </div>

              <!-- Group 1: Essential Endpoint & Network Settings -->
              <div class="p-5 bg-white border border-slate-200 rounded-2xl space-y-4 shadow-2xs">
                <div class="border-b border-slate-100 pb-2.5">
                  <h3 class="text-xs font-bold text-slate-900 tracking-tight">Endpoint &amp; Resource Identity</h3>
                  <p class="text-[11px] text-slate-500 font-normal">Physical network identity and connection descriptors for the target system.</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  @for (field of schema.fields; track field.id) {
                    @if (field.group === 'ENDPOINT' && isFieldVisible(field, schema)) {
                      <div class="flex flex-col gap-1" [class.md:col-span-2]="field.type === 'textarea'">
                        <label class="text-xs font-semibold text-slate-700 flex items-center justify-between">
                          <span>
                            {{ cleanLabel(field.label) }}
                            @if (field.required) {
                              <span class="text-rose-500">*</span>
                            }
                          </span>
                        </label>

                        @if (field.type === 'text') {
                          <input
                            type="text"
                            [value]="getFieldValue(field.id)"
                            (input)="onFieldChange(field.id, $any($event.target).value)"
                            [placeholder]="field.placeholder || ''"
                            class="h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors" />
                        }

                        @if (field.type === 'number') {
                          <input
                            type="number"
                            [value]="getFieldValue(field.id)"
                            (input)="onFieldChange(field.id, +$any($event.target).value)"
                            [placeholder]="field.placeholder || ''"
                            class="h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors" />
                        }

                        @if (field.type === 'select') {
                          <app-custom-select
                            [options]="field.options || []"
                            [value]="getFieldValue(field.id)"
                            (valueChange)="onFieldChange(field.id, $event)">
                          </app-custom-select>
                        }

                        @if (field.type === 'textarea') {
                          <textarea
                            rows="3"
                            [value]="getFieldValue(field.id)"
                            (input)="onFieldChange(field.id, $any($event.target).value)"
                            [placeholder]="field.placeholder || ''"
                            class="p-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors font-mono"></textarea>
                        }

                        @if (field.helpText) {
                          <span class="text-[10px] text-slate-400">{{ field.helpText }}</span>
                        }
                      </div>
                    }
                  }
                </div>
              </div>

              <!-- Group 2: Authentication & Read Credentials -->
              <div class="p-5 bg-white border border-slate-200 rounded-2xl space-y-4 shadow-2xs">
                <div class="border-b border-slate-100 pb-2.5">
                  <h3 class="text-xs font-bold text-slate-900 tracking-tight">Authentication &amp; Credentials</h3>
                  <p class="text-[11px] text-slate-500 font-normal">Secure read credentials or Enterprise Vault secret reference for target access.</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  @for (field of schema.fields; track field.id) {
                    @if (field.group === 'AUTH' && isFieldVisible(field, schema)) {
                      <div class="flex flex-col gap-1" [class.md:col-span-2]="field.type === 'textarea'">
                        <label class="text-xs font-semibold text-slate-700 flex items-center justify-between">
                          <span>
                            {{ cleanLabel(field.label) }}
                            @if (field.required) {
                              <span class="text-rose-500">*</span>
                            }
                          </span>
                        </label>

                        @if (field.type === 'password' || field.type === 'secret_ref') {
                          <div class="relative">
                            <input
                              [type]="isSecretVisible(field.id) ? 'text' : 'password'"
                              [value]="getFieldValue(field.id)"
                              (input)="onFieldChange(field.id, $any($event.target).value)"
                              [placeholder]="field.placeholder || 'e.g. vault://secret/target/creds or password'"
                              class="w-full h-9 pl-3 pr-9 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors font-mono" />
                            <button
                              type="button"
                              (click)="toggleSecretVisibility(field.id)"
                              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer">
                              <app-lucide-icon [name]="isSecretVisible(field.id) ? 'eye-off' : 'eye'" [size]="14"></app-lucide-icon>
                            </button>
                          </div>
                        }

                        @if (field.type === 'text') {
                          <input
                            type="text"
                            [value]="getFieldValue(field.id)"
                            (input)="onFieldChange(field.id, $any($event.target).value)"
                            [placeholder]="field.placeholder || ''"
                            class="h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors" />
                        }

                        @if (field.type === 'select') {
                          <app-custom-select
                            [options]="field.options || []"
                            [value]="getFieldValue(field.id)"
                            (valueChange)="onFieldChange(field.id, $event)">
                          </app-custom-select>
                        }

                        @if (field.helpText) {
                          <span class="text-[10px] text-slate-400">{{ field.helpText }}</span>
                        }
                      </div>
                    }
                  }
                </div>
              </div>

              <!-- ================================================================= -->
              <!-- PROGRESSIVE DISCLOSURE ACCORDIONS (Network Route & TLS)           -->
              <!-- ================================================================= -->
              <div class="space-y-3">
                
                <!-- Accordion 1: Network Route -->
                <app-accordion title="Network Route & Bastion Configuration">
                  <div class="space-y-4 pt-1">
                    <p class="text-xs text-slate-500 font-normal">Select how AKAAL Validation Studio reaches this target endpoint.</p>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                      @for (route of routeOptions; track route.value) {
                        @let isRouteActive = (vs.newValidationDraft().targetNetworkRoute || 'DIRECT') === route.value;
                        <button
                          type="button"
                          (click)="onRouteTypeChange(route.value)"
                          class="p-3 rounded-xl border text-left flex items-start gap-3 transition-all cursor-pointer"
                          [class]="isRouteActive
                            ? 'border-blue-600 bg-blue-50/20 shadow-2xs'
                            : 'border-slate-200 bg-white hover:border-slate-300'">
                          <div
                            class="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border"
                            [class]="isRouteActive ? 'bg-blue-600 text-white border-blue-600' : 'bg-slate-50 text-slate-600 border-slate-200'">
                            <app-lucide-icon [name]="route.icon" [size]="14"></app-lucide-icon>
                          </div>
                          <div class="flex flex-col">
                            <span class="text-xs font-semibold text-slate-900">{{ route.label }}</span>
                            <span class="text-[11px] text-slate-500 leading-tight">{{ route.desc }}</span>
                          </div>
                        </button>
                      }
                    </div>

                    @if (vs.newValidationDraft().targetNetworkRoute === 'SSH_BASTION') {
                      <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2 animate-in fade-in duration-100">
                        <label class="text-xs font-semibold text-slate-700 block">
                          SSH Bastion Jump Host <span class="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          [value]="vs.newValidationDraft().targetBastionHost || ''"
                          (input)="vs.updateDraft({ targetBastionHost: $any($event.target).value })"
                          placeholder="bastion.target.corp.internal:22"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 focus:outline-none font-mono" />
                        <span class="text-[10px] text-slate-400">AKAAL will establish an encrypted SSH tunnel to access this private target subnet.</span>
                      </div>
                    }
                  </div>
                </app-accordion>

                <!-- Accordion 2: Security & TLS Settings -->
                <app-accordion title="Transport Layer Security (TLS) & Certificates">
                  <div class="space-y-4 pt-1">
                    <p class="text-xs text-slate-500 font-normal">Configure cryptographic handshake and certificate verification for target connection.</p>
                    
                    <div class="max-w-md">
                      <label class="text-xs font-semibold text-slate-700 block mb-1.5">TLS Enforcement Mode</label>
                      <app-custom-select
                        [options]="tlsModeOptions"
                        [value]="selectedTlsMode()"
                        (valueChange)="onTlsModeChange($event)">
                      </app-custom-select>
                    </div>

                    @if (selectedTlsMode() === 'VERIFY_CA' || selectedTlsMode() === 'VERIFY_FULL') {
                      <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-3 animate-in fade-in duration-100">
                        <div class="flex flex-col gap-1">
                          <label class="text-xs font-semibold text-slate-700 block">
                            Custom CA Certificate Path (PEM)
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. /etc/ssl/certs/enterprise-target-ca.pem"
                            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 focus:outline-none font-mono" />
                          <span class="text-[10px] text-slate-400">Required for internal PKI or self-signed enterprise certificates.</span>
                        </div>
                      </div>
                    }
                  </div>
                </app-accordion>

                <!-- Accordion 3: Advanced Options -->
                <app-accordion title="Advanced Target Connection Settings">
                  <div class="space-y-4 pt-1">
                    <p class="text-xs text-slate-500 font-normal">Tune read session timeouts, socket keepalives, and pool sizes for validation workers.</p>
                    
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div class="flex flex-col gap-1">
                        <label class="text-xs font-semibold text-slate-700 block">Connection Timeout (s)</label>
                        <input
                          type="number"
                          value="30"
                          class="h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 focus:outline-none font-mono" />
                      </div>
                      <div class="flex flex-col gap-1">
                        <label class="text-xs font-semibold text-slate-700 block">Read Socket Timeout (s)</label>
                        <input
                          type="number"
                          value="60"
                          class="h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 focus:outline-none font-mono" />
                      </div>
                      <div class="flex flex-col gap-1">
                        <label class="text-xs font-semibold text-slate-700 block">Read Worker Pool Size</label>
                        <input
                          type="number"
                          value="8"
                          class="h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 focus:outline-none font-mono" />
                      </div>
                    </div>
                  </div>
                </app-accordion>

              </div>

              <!-- ================================================================= -->
              <!-- TARGET TEST CONNECTION & 6-PHASE READ ATTESTATION PROBE           -->
              <!-- ================================================================= -->
              <div class="p-5 bg-white border border-slate-200 rounded-2xl space-y-4 shadow-2xs">
                <div class="flex items-center justify-between flex-wrap gap-2 border-b border-slate-100 pb-3">
                  <div class="flex flex-col gap-0.5">
                    <h3 class="text-xs font-bold text-slate-900 tracking-tight">Target Read Connection Attestation</h3>
                    <p class="text-[11px] text-slate-500 font-normal">Executes non-mutating live read probes to verify network, auth, catalog, and data read access.</p>
                  </div>

                  <button
                    type="button"
                    (click)="runTargetReadProbe()"
                    [disabled]="isVerifying()"
                    class="h-9 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 cursor-pointer transition-colors shadow-2xs">
                    @if (isVerifying()) {
                      <app-lucide-icon name="loader-2" [size]="14" class="animate-spin"></app-lucide-icon>
                      <span>Probing Target Read Access...</span>
                    } @else {
                      <app-lucide-icon name="play" [size]="13"></app-lucide-icon>
                      <span>Run Target Read Probe</span>
                    }
                  </button>
                </div>

                <!-- Active In-Flight Verification Progress Strip -->
                @if (isVerifying()) {
                  <div class="p-3.5 bg-blue-50/50 border border-blue-200 rounded-xl space-y-2 animate-in fade-in duration-100">
                    <div class="flex items-center justify-between text-xs">
                      <span class="font-semibold text-blue-900">Executing Read Probe (Phase {{ activeExecutingPhaseIndex() }} of 6)</span>
                      <span class="text-[11px] font-mono text-blue-700">{{ activePhaseName() }}</span>
                    </div>
                    <div class="w-full h-1.5 bg-blue-200/50 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-blue-600 transition-all duration-200"
                        [style.width.%]="(activeExecutingPhaseIndex() / 6) * 100">
                      </div>
                    </div>
                  </div>
                }

                <!-- Probe Results View -->
                @if (probeExecuted()) {
                  @if (vs.newValidationDraft().targetVerified) {
                    <!-- Compact Parameter Validation Notice -->
                    <div class="p-3.5 bg-blue-50/40 border border-blue-200 rounded-lg flex flex-col gap-2.5 animate-in fade-in duration-150">
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                          <app-lucide-icon name="check-circle-2" [size]="15" class="text-blue-600 shrink-0"></app-lucide-icon>
                          <span class="text-xs font-bold text-slate-900">
                            Connection parameters validated. Live connection verification has not been performed.
                          </span>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-blue-100 text-blue-800 border border-blue-200">
                          Parameters Validated
                        </span>
                      </div>

                      <p class="text-[11.5px] text-slate-600 leading-relaxed font-normal m-0">
                        Local target endpoint specification and read credentials configuration are complete. Live transport handshake, authentication, and read-permission verification require an active backend engine.
                      </p>
                    </div>
                  }

                  @if (verificationError(); as err) {
                    <!-- Compact Failure Card -->
                    <div class="p-3.5 bg-rose-50 border border-rose-200 rounded-lg flex flex-col gap-2 animate-in fade-in duration-150">
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                          <span class="w-2 h-2 rounded-xs bg-rose-500"></span>
                          <span class="text-xs font-bold text-rose-900">Parameter Validation Incomplete ({{ err.phase }})</span>
                        </div>
                        <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-rose-100 text-rose-800 rounded">
                          {{ err.category }}
                        </span>
                      </div>
                      <p class="text-xs text-rose-800 font-normal leading-relaxed m-0">
                        {{ err.message }}
                      </p>
                    </div>
                  }
                }

              </div>

              <!-- ================================================================= -->
              <!-- OPERATOR INTENT: "SAVE CONNECTION FOR REUSE"                      -->
              <!-- ================================================================= -->
              @if (vs.newValidationDraft().targetVerified) {
                <div class="p-4 bg-slate-50/70 border border-slate-200 rounded-xl space-y-3 animate-in fade-in duration-150">
                  <label class="flex items-center gap-2.5 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      [ngModel]="vs.newValidationDraft().targetSaveToVault"
                      (ngModelChange)="onSaveToVaultChange($event)"
                      class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                    <span class="text-xs font-semibold text-slate-800">
                      Save connection for reuse
                    </span>
                  </label>

                  @if (vs.newValidationDraft().targetSaveToVault) {
                    <div class="flex flex-col gap-1.5 pl-6 animate-in fade-in duration-100 max-w-xl">
                      <label class="text-xs font-semibold text-slate-700 block">
                        Connection Label
                      </label>
                      <div class="flex items-center gap-2.5">
                        <input
                          type="text"
                          [ngModel]="vaultConnectionName()"
                          (ngModelChange)="onVaultConnectionNameChange($event)"
                          placeholder="e.g. Finance Postgres Target"
                          class="flex-1 h-9 px-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 focus:outline-none transition-colors" />
                      </div>
                      <span class="text-[10.5px] text-slate-500 font-normal">
                        Connection intent recorded. Persistence service is not currently connected.
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
  public vs: ValidationUiService;
  private fixtures: MigrationDevFixturesAdapter = new MigrationDevFixturesAdapter();
  public Math = Math;

  constructor(vs?: ValidationUiService, fixtures?: MigrationDevFixturesAdapter) {
    this.vs = vs || inject(ValidationUiService);
    if (fixtures) this.fixtures = fixtures;
  }

  // Top-Right Segmented Control Options
  public readonly modeControlOptions: SegmentedControlOption[] = [
    { label: 'Saved Connection', value: 'SAVED', icon: 'database' },
    { label: 'New Connection', value: 'NEW', icon: 'plug' }
  ];

  // Saved Connections Search & 6-Filter States
  public savedSearchQuery = signal<string>('');
  public isFilterPopoverOpen = signal<boolean>(false);
  public filterEnvironment = signal<string>('ALL');
  public filterCategory = signal<string>('ALL');
  public filterRoutes = signal<NetworkRouteType[]>([]);
  public filterHealthStatuses = signal<string[]>([]);
  public filterScope = signal<'PROJECT' | 'TEAM' | 'ENTERPRISE'>('PROJECT');

  // New Connection Catalog Search & Tabs
  public searchQuery = signal<string>('');
  public selectedCategoryTab = signal<CatalogCategoryTab['id']>('ALL');

  // Dynamic Secret Obfuscation Map
  public secretVisibilityMap = signal<Record<string, boolean>>({});

  // Target Read Verification State
  public isVerifying = signal<boolean>(false);
  public probeExecuted = signal<boolean>(false);
  public selectedTlsMode = signal<string>('VERIFY_FULL');
  public vaultConnectionName = signal<string>('');
  public isTargetVaultSaved = signal<boolean>(false);
  public verificationError = signal<{ phase: string; category: string; message: string } | null>(null);
  public activeExecutingPhaseIndex = signal<number>(1);
  public activePhaseName = signal<string>('DNS & Network Resolution');

  // Full 6-Phase Non-Mutating Read Attestation Schema for Target
  public executionPhases: VerificationPhaseState[] = [
    { index: 1, name: 'Phase 1: DNS & Network Resolution', description: 'Resolves target host, VPC subnet, or Bastion jump route', chipLabel: 'DNS & Network', status: 'PENDING' },
    { index: 2, name: 'Phase 2: TCP Handshake & TLS Negotiation', description: 'Enforces TLS 1.2+, negotiates cipher, and validates CA', chipLabel: 'TCP & TLS 1.3', status: 'PENDING' },
    { index: 3, name: 'Phase 3: Vault Decryption & Credential Auth', description: 'Authenticates target credentials and session initialization', chipLabel: 'Auth Verified', status: 'PENDING' },
    { index: 4, name: 'Phase 4: Physical Engine & Version Attestation', description: 'Attests target engine edition, version, build, and charset', chipLabel: 'Engine Attested', status: 'PENDING' },
    { index: 5, name: 'Phase 5: Metadata & Catalog Read Probe', description: 'Audits read access to information schema, system catalogs, and namespaces', chipLabel: 'Catalog Read', status: 'PENDING' },
    { index: 6, name: 'Phase 6: Data Read & Partition Sampling Probe', description: 'Executes non-mutating query probe to verify record and block access', chipLabel: 'Data Read Verified', status: 'PENDING' }
  ];

  // The 48 Canonical Engines for the Expansive Catalog Grid
  public catalogEngines: CatalogEngineItem[] = [
    // 1. Relational (10)
    { id: 'SQLite', name: 'SQLite', category: 'RELATIONAL', categoryLabel: 'Embedded Relational', icon: 'database' },
    { id: 'PostgreSQL', name: 'PostgreSQL', category: 'RELATIONAL', categoryLabel: 'Relational DB', icon: 'database' },
    { id: 'MySQL', name: 'MySQL', category: 'RELATIONAL', categoryLabel: 'Relational DB', icon: 'database' },
    { id: 'MariaDB', name: 'MariaDB', category: 'RELATIONAL', categoryLabel: 'Relational DB', icon: 'database' },
    { id: 'Oracle', name: 'Oracle Database', category: 'RELATIONAL', categoryLabel: 'Enterprise RDBMS', icon: 'database' },
    { id: 'Microsoft SQL Server', name: 'SQL Server (MSSQL)', category: 'RELATIONAL', categoryLabel: 'Enterprise RDBMS', icon: 'database' },
    { id: 'IBM Db2', name: 'IBM Db2 LUW', category: 'RELATIONAL', categoryLabel: 'Enterprise RDBMS', icon: 'database' },
    { id: 'SAP HANA', name: 'SAP HANA', category: 'RELATIONAL', categoryLabel: 'In-Memory RDBMS', icon: 'database' },
    { id: 'SAP ASE', name: 'SAP ASE (Sybase)', category: 'RELATIONAL', categoryLabel: 'Enterprise RDBMS', icon: 'database' },
    { id: 'IBM Informix', name: 'IBM Informix', category: 'RELATIONAL', categoryLabel: 'OLTP & Timeseries', icon: 'database' },

    // 2. Distributed SQL (5)
    { id: 'CockroachDB', name: 'CockroachDB', category: 'DISTRIBUTED_SQL', categoryLabel: 'Distributed SQL', icon: 'network' },
    { id: 'YugabyteDB', name: 'YugabyteDB', category: 'DISTRIBUTED_SQL', categoryLabel: 'Distributed SQL', icon: 'network' },
    { id: 'TiDB', name: 'TiDB (PingCAP)', category: 'DISTRIBUTED_SQL', categoryLabel: 'HTAP Distributed SQL', icon: 'network' },
    { id: 'SingleStore', name: 'SingleStore (MemSQL)', category: 'DISTRIBUTED_SQL', categoryLabel: 'Real-Time Distributed', icon: 'network' },
    { id: 'Google Cloud Spanner', name: 'Google Cloud Spanner', category: 'DISTRIBUTED_SQL', categoryLabel: 'Global Distributed SQL', icon: 'network' },

    // 3. Warehouse (7)
    { id: 'Snowflake', name: 'Snowflake Data Cloud', category: 'WAREHOUSE', categoryLabel: 'Cloud Data Warehouse', icon: 'layers' },
    { id: 'Google BigQuery', name: 'Google BigQuery', category: 'WAREHOUSE', categoryLabel: 'Serverless Warehouse', icon: 'layers' },
    { id: 'Amazon Redshift', name: 'Amazon Redshift', category: 'WAREHOUSE', categoryLabel: 'Cloud Data Warehouse', icon: 'layers' },
    { id: 'Databricks', name: 'Databricks Delta Lake', category: 'WAREHOUSE', categoryLabel: 'Lakehouse & Delta', icon: 'layers' },
    { id: 'ClickHouse', name: 'ClickHouse', category: 'WAREHOUSE', categoryLabel: 'Columnar Analytics', icon: 'layers' },
    { id: 'Teradata', name: 'Teradata Vantage', category: 'WAREHOUSE', categoryLabel: 'Enterprise Warehouse', icon: 'layers' },
    { id: 'OpenText Vertica', name: 'OpenText Vertica', category: 'WAREHOUSE', categoryLabel: 'Columnar Analytics', icon: 'layers' },

    // 4. NoSQL (12)
    { id: 'MongoDB', name: 'MongoDB', category: 'NOSQL', categoryLabel: 'Document Store', icon: 'boxes' },
    { id: 'Apache Cassandra', name: 'Apache Cassandra', category: 'NOSQL', categoryLabel: 'Wide-Column Store', icon: 'boxes' },
    { id: 'ScyllaDB', name: 'ScyllaDB', category: 'NOSQL', categoryLabel: 'Real-Time NoSQL', icon: 'boxes' },
    { id: 'Neo4j', name: 'Neo4j Graph Database', category: 'NOSQL', categoryLabel: 'Native Graph DB', icon: 'boxes' },
    { id: 'Redis', name: 'Redis', category: 'NOSQL', categoryLabel: 'In-Memory Cache & KV', icon: 'boxes' },
    { id: 'KeyDB', name: 'KeyDB', category: 'NOSQL', categoryLabel: 'Multithreaded In-Memory', icon: 'boxes' },
    { id: 'Elasticsearch', name: 'Elasticsearch', category: 'NOSQL', categoryLabel: 'Search & Analytics', icon: 'boxes' },
    { id: 'OpenSearch', name: 'OpenSearch', category: 'NOSQL', categoryLabel: 'Search & Analytics', icon: 'boxes' },
    { id: 'Apache Couchbase', name: 'Apache Couchbase', category: 'NOSQL', categoryLabel: 'Document & KV DB', icon: 'boxes' },
    { id: 'Amazon DynamoDB', name: 'Amazon DynamoDB', category: 'NOSQL', categoryLabel: 'Serverless Key-Value', icon: 'boxes' },
    { id: 'Azure Cosmos DB', name: 'Azure Cosmos DB', category: 'NOSQL', categoryLabel: 'Multi-Model Distributed', icon: 'boxes' },
    { id: 'InfluxDB', name: 'InfluxDB', category: 'NOSQL', categoryLabel: 'Time-Series Engine', icon: 'boxes' },

    // 5. Streaming (6)
    { id: 'Apache Kafka', name: 'Apache Kafka', category: 'STREAMING', categoryLabel: 'Event Streaming', icon: 'radio' },
    { id: 'Amazon Kinesis', name: 'Amazon Kinesis Data Streams', category: 'STREAMING', categoryLabel: 'Cloud Event Streaming', icon: 'radio' },
    { id: 'Azure Event Hubs', name: 'Azure Event Hubs', category: 'STREAMING', categoryLabel: 'Cloud Event Ingestion', icon: 'radio' },
    { id: 'Google Cloud Pub/Sub', name: 'Google Cloud Pub/Sub', category: 'STREAMING', categoryLabel: 'Enterprise Messaging', icon: 'radio' },
    { id: 'Apache Pulsar', name: 'Apache Pulsar', category: 'STREAMING', categoryLabel: 'Distributed Pub/Sub', icon: 'radio' },
    { id: 'RabbitMQ', name: 'RabbitMQ', category: 'STREAMING', categoryLabel: 'Message Broker', icon: 'radio' },

    // 6. Storage (5)
    { id: 'Amazon S3', name: 'Amazon S3', category: 'STORAGE', categoryLabel: 'Object Storage', icon: 'hard-drive' },
    { id: 'Google Cloud Storage', name: 'Google Cloud Storage (GCS)', category: 'STORAGE', categoryLabel: 'Object Storage', icon: 'hard-drive' },
    { id: 'Azure Blob Storage', name: 'Azure Blob Storage', category: 'STORAGE', categoryLabel: 'Cloud Blob Storage', icon: 'hard-drive' },
    { id: 'MinIO', name: 'MinIO Object Storage', category: 'STORAGE', categoryLabel: 'S3-Compatible Storage', icon: 'hard-drive' },
    { id: 'Apache HDFS', name: 'Apache HDFS', category: 'STORAGE', categoryLabel: 'Hadoop Distributed FS', icon: 'hard-drive' },

    // 7. SaaS & Apps (3)
    { id: 'Salesforce', name: 'Salesforce', category: 'SAAS', categoryLabel: 'CRM & Cloud Platform', icon: 'cloud' },
    { id: 'ServiceNow', name: 'ServiceNow', category: 'SAAS', categoryLabel: 'Enterprise ITSM / Tables', icon: 'cloud' },
    { id: 'SAP Application Ecosystem', name: 'SAP Application Ecosystem', category: 'SAAS', categoryLabel: 'SAP NetWeaver / RFC', icon: 'cloud' }
  ];

  // Category Pill Tabs with Exact Counts
  public catalogTabs: CatalogCategoryTab[] = [
    { id: 'ALL', label: 'All', count: 48 },
    { id: 'RELATIONAL', label: 'Relational', count: 10 },
    { id: 'DISTRIBUTED_SQL', label: 'Distributed SQL', count: 5 },
    { id: 'WAREHOUSE', label: 'Warehouse', count: 7 },
    { id: 'NOSQL', label: 'NoSQL', count: 12 },
    { id: 'STREAMING', label: 'Streaming', count: 6 },
    { id: 'STORAGE', label: 'Storage', count: 5 },
    { id: 'SAAS', label: 'SaaS & Apps', count: 3 }
  ];

  // Filter Popover Option Lists
  public routeFiltersList: { label: string; value: NetworkRouteType }[] = [
    { label: 'Direct TCP', value: 'DIRECT' },
    { label: 'SSH Bastion Tunnel', value: 'SSH_BASTION' },
    { label: 'AWS PrivateLink', value: 'PRIVATE_ENDPOINT' },
    { label: 'Corporate Proxy', value: 'HTTP_PROXY' }
  ];

  public healthFiltersList: { label: string; value: string }[] = [
    { label: 'Healthy (Verified)', value: 'CONNECTED' },
    { label: 'Stale / Needs Re-test', value: 'ATTENTION' },
    { label: 'Expired Secret', value: 'DISCONNECTED' }
  ];

  public scopeFiltersList: { label: string; value: 'PROJECT' | 'TEAM' | 'ENTERPRISE' }[] = [
    { label: 'Current Project Only', value: 'PROJECT' },
    { label: "My Team's Vault", value: 'TEAM' },
    { label: 'All Enterprise Connections', value: 'ENTERPRISE' }
  ];

  // Rich Enterprise Dataset for Saved Connections
  public enterpriseSavedConnections: SavedConnectionItemExtended[] = [
    {
      id: 'conn-01',
      name: 'Oracle 19c Enterprise RAC',
      provider: 'Oracle',
      category: 'RELATIONAL',
      environment: 'Production',
      host: 'ora-rac-cluster.prod.internal',
      port: 1521,
      databaseName: 'ORCLPDB',
      username: 'akaal_val_user',
      secretRef: 'vault://secret/prod/oracle/akaal_val',
      tlsEnabled: true,
      networkRoute: 'SSH_BASTION',
      bastionHost: 'bastion-ap-south.corp.internal',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 4 min ago',
      latencyMs: 2.1,
      capabilities: ['HASH_SCAN', 'TABLE_PARTITIONING', 'DIRECT_READ'],
      assignedMigrationCount: 3,
      assignedProjectCount: 2,
      createdAt: '2026-08-01T10:00:00Z',
      updatedAt: '2026-08-28T09:00:00Z',
      scope: 'PROJECT'
    },
    {
      id: 'conn-02',
      name: 'AWS Aurora PostgreSQL Cluster',
      provider: 'PostgreSQL',
      category: 'RELATIONAL',
      environment: 'Production',
      host: 'aurora-pg-cluster.aws.internal',
      port: 5432,
      databaseName: 'banking_ledger',
      username: 'akaal_verifier',
      secretRef: 'vault://secret/prod/postgres/verifier',
      tlsEnabled: true,
      networkRoute: 'PRIVATE_ENDPOINT',
      privateEndpointId: 'vpce-0a1b2c3d4e5f6g7h8',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 8 min ago',
      latencyMs: 1.4,
      capabilities: ['PARALLEL_SCAN', 'ROW_LEVEL_HASHING'],
      assignedMigrationCount: 4,
      assignedProjectCount: 2,
      createdAt: '2026-08-01T11:00:00Z',
      updatedAt: '2026-08-28T09:00:00Z',
      scope: 'PROJECT'
    },
    {
      id: 'conn-03',
      name: 'Snowflake Enterprise Data Lake',
      provider: 'Snowflake',
      category: 'WAREHOUSE',
      environment: 'Production',
      host: 'org-xy12345.snowflakecomputing.com',
      port: 443,
      databaseName: 'ANALYTICS_PROD',
      username: 'akaal_val_reader',
      secretRef: 'vault://secret/prod/snowflake/reader',
      tlsEnabled: true,
      networkRoute: 'DIRECT',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 15 min ago',
      latencyMs: 18.5,
      capabilities: ['STAGE_BULK_READ', 'METRIC_SAMPLING'],
      assignedMigrationCount: 2,
      assignedProjectCount: 1,
      createdAt: '2026-08-10T14:00:00Z',
      updatedAt: '2026-08-28T08:00:00Z',
      scope: 'TEAM'
    },
    {
      id: 'conn-04',
      name: 'Kafka Event Bus (Core Stream)',
      provider: 'Apache Kafka',
      category: 'STREAMING',
      environment: 'Production',
      host: 'kafka-broker-01.prod.internal',
      port: 9092,
      username: 'akaal_consumer',
      secretRef: 'vault://secret/prod/kafka/consumer',
      tlsEnabled: true,
      networkRoute: 'PRIVATE_ENDPOINT',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 30 min ago',
      latencyMs: 3.2,
      capabilities: ['WATERMARK_OFFSET_AUDIT', 'SCHEMA_REGISTRY_AVRO'],
      assignedMigrationCount: 1,
      assignedProjectCount: 1,
      createdAt: '2026-08-15T09:00:00Z',
      updatedAt: '2026-08-28T07:00:00Z',
      scope: 'ENTERPRISE'
    },
    {
      id: 'conn-05',
      name: 'Staging MongoDB Atlas Cluster',
      provider: 'MongoDB',
      category: 'NOSQL',
      environment: 'Non-Production',
      host: 'cluster0.mongodb.net',
      port: 27017,
      databaseName: 'customers_stage',
      username: 'val_tester',
      secretRef: 'vault://secret/stage/mongo',
      tlsEnabled: true,
      networkRoute: 'DIRECT',
      status: 'ATTENTION',
      verificationFreshness: 'Stale (4 days ago)',
      latencyMs: 42.0,
      capabilities: ['DOCUMENT_PROBE', 'SHARD_CURSOR'],
      assignedMigrationCount: 1,
      assignedProjectCount: 1,
      createdAt: '2026-08-18T16:00:00Z',
      updatedAt: '2026-08-24T12:00:00Z',
      scope: 'PROJECT'
    },
    {
      id: 'conn-06',
      name: 'Dev MySQL Local Replica',
      provider: 'MySQL',
      category: 'RELATIONAL',
      environment: 'Non-Production',
      host: '127.0.0.1',
      port: 3306,
      databaseName: 'app_dev',
      username: 'root',
      secretRef: 'vault://secret/dev/mysql',
      tlsEnabled: false,
      networkRoute: 'DIRECT',
      status: 'DISCONNECTED',
      verificationFreshness: 'Secret Expired',
      latencyMs: 0.0,
      capabilities: ['BINLOG_ROW_CAPTURE'],
      assignedMigrationCount: 0,
      assignedProjectCount: 1,
      createdAt: '2026-08-20T08:00:00Z',
      updatedAt: '2026-08-27T11:00:00Z',
      scope: 'PROJECT'
    }
  ];

  // Route & TLS Configuration Options
  public readonly routeOptions: { label: string; value: NetworkRouteType; desc: string; icon: string }[] = [
    { label: 'Direct TCP / Cloud Listener', value: 'DIRECT', desc: 'Direct network connectivity via standard internet or cloud egress', icon: 'globe' },
    { label: 'SSH Bastion Jump Tunnel', value: 'SSH_BASTION', desc: 'Encrypted SSH hop tunnel into isolated private VPC or on-prem DMZ', icon: 'shield' },
    { label: 'AWS PrivateLink / Azure Endpoint', value: 'PRIVATE_ENDPOINT', desc: 'Direct VPC peering or private cloud service interface endpoint', icon: 'network' },
    { label: 'Corporate Forward Proxy', value: 'HTTP_PROXY', desc: 'Routes all TLS validation traffic through enterprise proxy inspection', icon: 'server' }
  ];

  public readonly tlsModeOptions: CustomSelectOption[] = [
    { label: 'Verify Full (Enforce TLS 1.3 & Match SAN/CA) [Recommended]', value: 'VERIFY_FULL', desc: 'Full certificate chain verification and hostname SAN matching' },
    { label: 'Verify CA (Validate CA Chain, Skip Hostname SAN)', value: 'VERIFY_CA', desc: 'Validates issuer CA trust chain without matching exact hostname' },
    { label: 'Require Encryption (Skip Certificate Authority Validation)', value: 'REQUIRED', desc: 'Encrypts TCP stream but ignores certificate validation errors' },
    { label: 'Prefer TLS (Opportunistic STARTTLS Upgrade)', value: 'PREFER', desc: 'Attempts TLS upgrade, falls back to cleartext if unsupported' },
    { label: 'Disable TLS (Unencrypted TCP)', value: 'DISABLE', desc: 'Plain unencrypted TCP (allowed only in Non-Production)' }
  ];

  // Same-Endpoint Guard Detection
  public isSameEndpoint = computed<boolean>(() => {
    const d = this.vs.newValidationDraft();
    if (d.sourceConnectionMode === 'SAVED' && d.targetConnectionMode === 'SAVED') {
      return !!d.sourceConnectionId && !!d.targetConnectionId && d.sourceConnectionId === d.targetConnectionId;
    }
    const srcHost = (d.sourceHost || '').trim().toLowerCase();
    const tgtHost = (d.targetHost || '').trim().toLowerCase();
    if (!srcHost || !tgtHost) return false;
    if (srcHost !== tgtHost) return false;

    const srcPort = d.sourcePort || 0;
    const tgtPort = d.targetPort || 0;
    if (srcPort && tgtPort && srcPort !== tgtPort) return false;

    const srcDb = (d.sourceDatabase || '').trim().toLowerCase();
    const tgtDb = (d.targetDatabase || '').trim().toLowerCase();
    if (srcDb && tgtDb && srcDb === tgtDb) return true;

    return srcHost === tgtHost;
  });

  // Project Target Candidate Context
  public projectTargetCandidate = computed<{ engine: PhysicalProviderId; instance: string; host: string; port: number; database: string } | null>(() => {
    const d = this.vs.newValidationDraft();
    if (d.validationContext !== 'EXISTING_PROJECT' || !d.projectId) {
      return null;
    }
    const migrations = this.fixtures.getPortfolioMigrations();
    const projectMig = migrations.find(m => m.projectId === d.projectId);
    if (projectMig && projectMig.targetEngine) {
      const parts = projectMig.targetInstance ? projectMig.targetInstance.split(':') : [];
      const host = parts[0] || '';
      const port = parts[1] ? parseInt(parts[1], 10) : 5432;
      return {
        engine: projectMig.targetEngine as PhysicalProviderId,
        instance: projectMig.targetInstance,
        host,
        port,
        database: 'target_db'
      };
    }
    return null;
  });

  // Filtered Catalog Engines for New Connection
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

  // Filtered Saved Connections for Saved Grid
  public filteredSavedConnections = computed(() => {
    const q = this.savedSearchQuery().trim().toLowerCase();
    const env = this.filterEnvironment();
    const cat = this.filterCategory();
    const routes = this.filterRoutes();
    const statuses = this.filterHealthStatuses();
    const scope = this.filterScope();

    let list = this.enterpriseSavedConnections;

    if (q) {
      list = list.filter(c =>
        c.name.toLowerCase().includes(q) ||
        c.provider.toLowerCase().includes(q) ||
        c.host.toLowerCase().includes(q)
      );
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

    if (statuses.length > 0) {
      list = list.filter(c => statuses.includes(c.status));
    }

    if (scope === 'PROJECT') {
      list = list.filter(c => c.scope === 'PROJECT');
    } else if (scope === 'TEAM') {
      list = list.filter(c => c.scope === 'PROJECT' || c.scope === 'TEAM');
    }

    return list;
  });

  public activeFilterCount = computed(() => {
    let count = 0;
    if (this.filterEnvironment() !== 'ALL') count++;
    if (this.filterCategory() !== 'ALL') count++;
    count += this.filterRoutes().length;
    count += this.filterHealthStatuses().length;
    if (this.filterScope() !== 'PROJECT') count++;
    return count;
  });

  public activeFilterChips = computed(() => {
    const chips: { id: string; label: string }[] = [];
    if (this.filterEnvironment() !== 'ALL') {
      chips.push({ id: 'env', label: `Env: ${this.filterEnvironment()}` });
    }
    if (this.filterCategory() !== 'ALL') {
      chips.push({ id: 'cat', label: `Cat: ${this.getCategoryFilterLabel(this.filterCategory())}` });
    }
    for (const r of this.filterRoutes()) {
      chips.push({ id: `route-${r}`, label: `Route: ${r}` });
    }
    for (const s of this.filterHealthStatuses()) {
      chips.push({ id: `status-${s}`, label: `Status: ${s}` });
    }
    if (this.filterScope() !== 'PROJECT') {
      chips.push({ id: 'scope', label: `Scope: ${this.filterScope()}` });
    }
    return chips;
  });

  public selectedSavedConnection = computed<SavedConnectionItemExtended | undefined>(() => {
    const id = this.vs.newValidationDraft().targetConnectionId;
    if (!id) return undefined;
    return this.enterpriseSavedConnections.find(c => c.id === id);
  });

  public selectedProviderSchema = computed<ProviderFormSchema | undefined>(() => {
    const pid = this.vs.newValidationDraft().targetProvider;
    if (!pid) return undefined;
    return ALL_48_PROVIDER_SCHEMAS[pid];
  });

  public ngOnInit(): void {
    const draftEnv = this.vs.newValidationDraft().environment;
    if (draftEnv) {
      this.filterEnvironment.set(draftEnv);
      this.selectedTlsMode.set(draftEnv === 'Production' ? 'VERIFY_FULL' : 'PREFER');
    }
  }

  public getCategoryFilterLabel(cat: string): string {
    switch (cat) {
      case 'ALL': return 'All';
      case 'RELATIONAL': return 'Relational';
      case 'DISTRIBUTED_SQL': return 'Distributed SQL';
      case 'WAREHOUSE': return 'Warehouse';
      case 'NOSQL': return 'NoSQL';
      case 'STREAMING': return 'Streaming';
      case 'STORAGE': return 'Storage';
      case 'SAAS': return 'SaaS & Apps';
      default: return cat;
    }
  }

  public cleanLabel(label: string): string {
    if (!label) return '';
    return label.replace(/\s*\*+\s*$/, '').trim();
  }

  public getProviderIcon(provider: PhysicalProviderId): string {
    const s = ALL_48_PROVIDER_SCHEMAS[provider];
    return s?.icon || 'database';
  }

  public isSecretVisible(fieldId: string): boolean {
    return !!this.secretVisibilityMap()[fieldId];
  }

  public toggleSecretVisibility(fieldId: string): void {
    const current = this.secretVisibilityMap();
    this.secretVisibilityMap.set({
      ...current,
      [fieldId]: !current[fieldId]
    });
  }

  public setConnectionMode(mode: 'SAVED' | 'NEW'): void {
    if (this.vs.newValidationDraft().targetConnectionMode === mode) return;

    this.vs.updateDraft({
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
      targetSaveToVault: false
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

  public toggleHealthFilter(status: string): void {
    const current = this.filterHealthStatuses();
    if (current.includes(status)) {
      this.filterHealthStatuses.set(current.filter(s => s !== status));
    } else {
      this.filterHealthStatuses.set([...current, status]);
    }
  }

  public removeFilterChip(chipId: string): void {
    if (chipId === 'env') this.filterEnvironment.set('ALL');
    else if (chipId === 'cat') this.filterCategory.set('ALL');
    else if (chipId === 'scope') this.filterScope.set('PROJECT');
    else if (chipId.startsWith('route-')) {
      const r = chipId.replace('route-', '') as NetworkRouteType;
      this.toggleRouteFilter(r);
    } else if (chipId.startsWith('status-')) {
      const s = chipId.replace('status-', '');
      this.toggleHealthFilter(s);
    }
  }

  public clearAllFilters(): void {
    this.filterEnvironment.set('ALL');
    this.filterCategory.set('ALL');
    this.filterRoutes.set([]);
    this.filterHealthStatuses.set([]);
    this.filterScope.set('PROJECT');
    this.savedSearchQuery.set('');
  }

  public selectSavedEndpoint(conn: SavedConnectionItemExtended): void {
    const isHealthy = conn.status === 'CONNECTED';
    this.vs.updateDraft({
      targetConnectionId: conn.id,
      targetProvider: conn.provider,
      targetHost: conn.host,
      targetPort: conn.port,
      targetDatabase: conn.databaseName,
      targetUsername: conn.username,
      targetSecretRef: conn.secretRef,
      targetTls: conn.tlsEnabled,
      targetNetworkRoute: conn.networkRoute,
      targetVerified: isHealthy,
      targetVerificationResult: isHealthy ? {
        fingerprint: `fp-tgt-${conn.id}`,
        isVerified: true,
        hasBlockingIssues: false,
        overallLatencyMs: conn.latencyMs || 2.5,
        latencyMs: conn.latencyMs || 2.5,
        parameterValidation: { status: 'PASSED', detail: 'Parameters valid' },
        routeResolution: { status: 'PASSED', detail: `Route resolved via ${conn.networkRoute}` },
        transportHandshake: { status: 'PASSED', cipher: conn.tlsEnabled ? 'TLS 1.3 (TLS_AES_256_GCM_SHA384)' : 'Plain TCP', protocol: conn.tlsEnabled ? 'TLS 1.3' : 'TCP' },
        authentication: { status: 'PASSED', detail: `Authenticated as ${conn.username}` },
        identityAttestation: { status: 'PASSED', serverVersion: 'Enterprise Production Core', engineType: conn.provider }
      } : undefined
    });
    this.probeExecuted.set(false);
  }

  public selectEngine(engineId: PhysicalProviderId): void {
    const schema = ALL_48_PROVIDER_SCHEMAS[engineId];
    if (!schema) return;

    this.vs.updateDraft({
      targetProvider: engineId,
      targetHost: '',
      targetPort: schema.defaultPort || 0,
      targetDatabase: '',
      targetUsername: '',
      targetSecretRef: '',
      targetParams: {},
      targetVerified: false,
      targetVerificationResult: undefined,
      targetSaveToVault: false
    });

    this.probeExecuted.set(false);
    this.verificationError.set(null);
    this.vaultConnectionName.set(`${schema.name} Target Production`);
  }

  public changeEngine(): void {
    this.vs.updateDraft({
      targetProvider: undefined as any,
      targetHost: '',
      targetPort: 0,
      targetDatabase: '',
      targetUsername: '',
      targetSecretRef: '',
      targetParams: {},
      targetVerified: false,
      targetVerificationResult: undefined,
      targetSaveToVault: false
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public applyCandidateTarget(candidate: { engine: PhysicalProviderId; instance: string; host: string; port: number; database: string }): void {
    this.setConnectionMode('NEW');
    this.selectEngine(candidate.engine);
    this.onFieldChange('host', candidate.host);
    this.onFieldChange('port', candidate.port);
    this.onFieldChange('database', candidate.database);
  }

  public isFieldVisible(field: ProviderFormField, schema: ProviderFormSchema): boolean {
    const fid = field.id;

    if (schema.name.includes('Oracle') || schema.providerId === 'Oracle') {
      const connType = this.getFieldValue('connection_type') || 'SERVICE_NAME';
      if (connType === 'SERVICE_NAME') {
        if (fid === 'sid' || fid === 'tns_descriptor' || fid === 'wallet_path' || fid === 'wallet_password' || fid === 'tns_alias') return false;
      } else if (connType === 'SID') {
        if (fid === 'service_name' || fid === 'tns_descriptor' || fid === 'wallet_path' || fid === 'wallet_password' || fid === 'tns_alias') return false;
      } else if (connType === 'TNS_DESCRIPTOR') {
        if (fid === 'host' || fid === 'port' || fid === 'service_name' || fid === 'sid' || fid === 'wallet_path' || fid === 'wallet_password' || fid === 'tns_alias') return false;
      } else if (connType === 'WALLET') {
        if (fid === 'host' || fid === 'port' || fid === 'service_name' || fid === 'sid' || fid === 'tns_descriptor') return false;
      }
    }

    if (schema.name.includes('SQL Server') || schema.providerId === 'Microsoft SQL Server') {
      const authType = this.getFieldValue('auth_type') || 'SQL_AUTH';
      if (authType === 'WINDOWS_SSPI' && (fid === 'username' || fid === 'secret_ref' || fid === 'password')) return false;
    }

    if (schema.name.includes('MongoDB') || schema.providerId === 'MongoDB') {
      const connMode = this.getFieldValue('connection_mode') || 'STANDALONE';
      if (connMode === 'STANDALONE' && (fid === 'replica_endpoints' || fid === 'replica_set_name')) return false;
      if (connMode === 'CLUSTER' && (fid === 'host' || fid === 'port')) return false;
    }

    if (schema.name.includes('Snowflake') || schema.providerId === 'Snowflake') {
      const authType = this.getFieldValue('auth_type') || 'PASSWORD';
      if (authType === 'PASSWORD' && (fid === 'private_key_path' || fid === 'passphrase' || fid === 'oauth_token')) return false;
      if (authType === 'KEY_PAIR' && (fid === 'secret_ref' || fid === 'password' || fid === 'oauth_token')) return false;
      if (authType === 'OAUTH' && (fid === 'username' || fid === 'secret_ref' || fid === 'password' || fid === 'private_key_path' || fid === 'passphrase')) return false;
      if (authType === 'SSO' && (fid === 'secret_ref' || fid === 'password' || fid === 'private_key_path' || fid === 'passphrase' || fid === 'oauth_token')) return false;
    }

    if (schema.name.includes('BigQuery') || schema.providerId === 'Google BigQuery') {
      const authType = this.getFieldValue('auth_type') || 'SERVICE_ACCOUNT_KEY';
      if (authType === 'ADC' && fid === 'service_account_json') return false;
    }

    if (schema.name.includes('Elasticsearch') || schema.providerId === 'Elasticsearch') {
      const authType = this.getFieldValue('auth_type') || 'BASIC';
      if (authType === 'API_KEY' && (fid === 'username' || fid === 'secret_ref' || fid === 'password')) return false;
      if (authType === 'BASIC' && fid === 'api_key') return false;
    }

    if (field.dependsOn) {
      const parentVal = this.getFieldValue(field.dependsOn);
      if (field.conditionValue !== undefined) {
        return parentVal === field.conditionValue;
      }
      return !!parentVal;
    }

    return true;
  }

  public onFieldChange(fieldId: string, value: any): void {
    const draft = this.vs.newValidationDraft();
    const params = { ...(draft.targetParams || {}) };
    params[fieldId] = value;

    const patch: any = { targetParams: params };

    if (fieldId === 'host') patch.targetHost = value;
    if (fieldId === 'port') patch.targetPort = Number(value) || 0;
    if (fieldId === 'database' || fieldId === 'database_name' || fieldId === 'service_name') patch.targetDatabase = value;
    if (fieldId === 'username') patch.targetUsername = value;
    if (fieldId === 'secret_ref' || fieldId === 'password') patch.targetSecretRef = value;

    if (draft.targetVerified) {
      patch.targetVerified = false;
      patch.targetVerificationResult = undefined;
      this.probeExecuted.set(false);
    }

    this.vs.updateDraft(patch);
  }

  public getFieldValue(fieldId: string): any {
    const draft = this.vs.newValidationDraft();
    if (fieldId === 'host') return draft.targetHost || '';
    if (fieldId === 'port') return draft.targetPort || '';
    if (fieldId === 'database' || fieldId === 'database_name' || fieldId === 'service_name') return draft.targetDatabase || '';
    if (fieldId === 'username') return draft.targetUsername || '';
    if (fieldId === 'secret_ref' || fieldId === 'password') return draft.targetSecretRef || '';

    const params = draft.targetParams || {};
    if (params[fieldId] !== undefined) return params[fieldId];

    const schema = this.selectedProviderSchema();
    const field = schema?.fields.find(f => f.id === fieldId);
    return field?.defaultValue ?? '';
  }

  public onRouteTypeChange(route: NetworkRouteType): void {
    this.vs.updateDraft({
      targetNetworkRoute: route,
      targetVerified: false,
      targetVerificationResult: undefined
    });
    this.probeExecuted.set(false);
  }

  public onTlsModeChange(mode: string): void {
    this.selectedTlsMode.set(mode);
    this.vs.updateDraft({
      targetTls: mode !== 'DISABLE',
      targetTlsMode: mode,
      targetVerified: false,
      targetVerificationResult: undefined
    });
    this.probeExecuted.set(false);
  }

  public runTargetReadProbe(): void {
    const draft = this.vs.newValidationDraft();
    const schema = this.selectedProviderSchema();

    this.isVerifying.set(true);
    this.probeExecuted.set(false);
    this.verificationError.set(null);
    this.activeExecutingPhaseIndex.set(1);
    this.activePhaseName.set(this.executionPhases[0].name);

    this.executionPhases.forEach(p => {
      p.status = 'PENDING';
      p.latencyMs = undefined;
    });

    const isNonNetwork = schema?.providerId === 'SQLite';
    if (!isNonNetwork) {
      const isMissingHost = !draft.targetHost || draft.targetHost.trim() === '';
      const isMissingPort = !draft.targetPort && schema?.category !== 'STORAGE' && schema?.category !== 'SAAS';
      const isMissingUser = !draft.targetUsername && schema?.category !== 'STORAGE';
      const isMissingAuth = !draft.targetSecretRef && schema?.category !== 'STORAGE';

      if (isMissingHost || isMissingPort || isMissingUser || isMissingAuth) {
        this.isVerifying.set(false);
        this.probeExecuted.set(true);
        this.executionPhases[0].status = 'FAILED';
        this.verificationError.set({
          phase: 'Phase 1: Parameter Validation',
          category: 'MISSING_REQUIRED_PARAMETERS',
          message: 'Target host, port, username, and authentication secret are required before running live read attestation.'
        });
        this.vs.updateDraft({
          targetVerified: false,
          targetVerificationResult: undefined
        });
        return;
      }
    }

    // Parameters validated successfully
    this.isVerifying.set(false);
    this.probeExecuted.set(true);
    this.verificationError.set(null);
    this.executionPhases.forEach(p => p.status = 'PASSED');

    const res: SourceVerificationResult = {
      fingerprint: 'NOT_EVALUATED',
      isVerified: true,
      hasBlockingIssues: false,
      parameterValidation: { status: 'PASSED', detail: 'Connection parameters validated' },
      routeResolution: { status: 'PASSED', detail: `Route configured via ${draft.targetNetworkRoute || 'DIRECT'}` },
      transportHandshake: { status: 'NOT_EVALUATED' as any, protocol: this.selectedTlsMode() },
      authentication: { status: 'NOT_EVALUATED' as any, detail: 'Authentication not evaluated in client draft' },
      permissionAudit: { status: 'NOT_EVALUATED' as any, detail: 'Read permissions not evaluated in client draft', permissions: [] },
      physicalConnection: { status: 'NOT_EVALUATED' as any, detail: 'Live connection verification has not been performed' }
    };

    this.vs.updateDraft({
      targetVerified: true,
      targetVerificationResult: res
    });
  }

  public getTotalProbeLatency(): number {
    return this.executionPhases.reduce((acc, p) => acc + (p.latencyMs || 2), 0);
  }

  public onSaveToVaultChange(val: boolean): void {
    this.vs.updateDraft({ targetSaveToVault: val });
  }

  public onVaultConnectionNameChange(name: string): void {
    this.vaultConnectionName.set(name);
  }

  public saveTargetToVault(): void {
    const name = this.vaultConnectionName().trim();
    if (!name) return;

    const draft = this.vs.newValidationDraft();
    const schema = this.selectedProviderSchema();

    const newSaved: SavedConnectionItemExtended = {
      id: `conn-custom-${Date.now()}`,
      name,
      provider: draft.targetProvider || 'PostgreSQL',
      category: schema?.category || 'RELATIONAL',
      environment: draft.environment,
      host: draft.targetHost || 'localhost',
      port: draft.targetPort || 5432,
      databaseName: draft.targetDatabase,
      username: draft.targetUsername || '',
      secretRef: draft.targetSecretRef || '',
      tlsEnabled: !!draft.targetTls,
      networkRoute: draft.targetNetworkRoute || 'DIRECT',
      status: 'CONNECTED',
      verificationFreshness: 'Saved just now',
      latencyMs: 2.4,
      capabilities: ['CATALOG_READ', 'DATA_READ'],
      assignedMigrationCount: 0,
      assignedProjectCount: 1,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      scope: 'PROJECT'
    };

    this.enterpriseSavedConnections.unshift(newSaved);
    this.isTargetVaultSaved.set(true);
  }
}
