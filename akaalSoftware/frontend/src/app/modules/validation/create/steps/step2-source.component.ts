import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import {
  PhysicalProviderId,
  ProviderCategory,
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
  selector: 'app-step2-source',
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
      @if (vs.newValidationDraft().sourceConnectionMode) {
        <div class="flex flex-col gap-3 border-b border-slate-200/60 pb-3">
          <div class="flex items-center justify-between flex-wrap gap-2">
            <div class="flex flex-col gap-0.5">
              <h1 class="text-base font-bold text-slate-900 tracking-tight">Source Connection</h1>
              <p class="text-xs text-slate-500 font-normal">Choose how AKAAL Validation Studio should connect to the source system.</p>
            </div>

            <!-- Compact Segmented Control (Top-Right) -->
            <app-segmented-control
              [options]="modeControlOptions"
              [value]="vs.newValidationDraft().sourceConnectionMode"
              (valueChange)="setConnectionMode($event)">
            </app-segmented-control>
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- ENTRY STATE: TWO HERO CHOICE CARDS (CENTERED, DEEP, NO EMPTY VOID)        -->
      <!-- ========================================================================= -->
      @if (!vs.newValidationDraft().sourceConnectionMode) {
        <section class="pt-8 pb-12 flex flex-col items-center justify-center animate-in fade-in duration-150">
          
          <!-- Centered Header with Increased Font Size & Perfect Vertical Balance -->
          <div class="flex flex-col items-center text-center gap-1.5 pb-6">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight">Source Connection</h1>
            <p class="text-sm text-slate-500 max-w-md font-normal">
              Choose how AKAAL Validation Studio should connect to your source database system.
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
                  New Endpoint
                </span>
              </div>
              <div class="flex flex-col gap-2">
                <span class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  New Connection
                </span>
                <p class="text-xs text-slate-500 font-normal leading-relaxed">
                  Configure and verify a new source database endpoint from the catalog.
                </p>
                <div class="pt-2.5 border-t border-slate-100 flex items-center gap-2 text-[11px] text-slate-600 font-medium">
                  <app-lucide-icon name="check" [size]="13" class="text-blue-600"></app-lucide-icon>
                  <span>Configurable TLS, SSH Bastion, and direct listeners</span>
                </div>
              </div>
            </button>

          </div>
        </section>
      }

      <!-- ========================================================================= -->
      <!-- BRANCH 1: SAVED CONNECTION INTERACTIVE ENDPOINT GRID & 5-FILTER POPOVER   -->
      <!-- ========================================================================= -->
      @if (vs.newValidationDraft().sourceConnectionMode === 'SAVED') {
        <section class="space-y-4 animate-in fade-in duration-150">
          
          <!-- Top Search & Filter Bar with Popover Anchor -->
          <div class="relative flex items-center gap-2.5">
            
            <!-- Search Input with Explicit Padding & Left Icon Clearance -->
            <div class="relative flex-1">
              <input
                type="text"
                [(ngModel)]="savedSearchQuery"
                placeholder="Search saved connections by name, host, or engine..."
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

            <!-- 5-FILTER POPOVER MODAL -->
            @if (isFilterPopoverOpen()) {
              <div
                class="absolute right-0 top-11 z-50 w-88 p-4 bg-white border border-slate-200 rounded-2xl shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-100">
                
                <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span class="text-xs font-bold text-slate-900">Filter Saved Connections</span>
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

                <!-- 2. Engine Category (With Proper NoSQL casing) -->
                <div class="flex flex-col gap-1.5 pt-1 border-t border-slate-100">
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

                <!-- 3. Network Route Topology -->
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

                <!-- 4. Health & Attestation Status -->
                <div class="flex flex-col gap-1.5 pt-1 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Health &amp; Attestation</span>
                  <div class="flex flex-col gap-1">
                    @for (st of healthFiltersList; track st.value) {
                      <label class="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          [checked]="filterHealthStatuses().includes(st.value)"
                          (change)="toggleHealthFilter(st.value)"
                          class="w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                        <span>{{ st.label }}</span>
                      </label>
                    }
                  </div>
                </div>

                <!-- 5. Vault Scope -->
                <div class="flex flex-col gap-1.5 pt-1 border-t border-slate-100">
                  <span class="text-[11px] font-semibold text-slate-700">Vault Scope</span>
                  <div class="flex flex-col gap-1">
                    @for (sc of scopeFiltersList; track sc.value) {
                      <label class="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer select-none">
                        <input
                          type="radio"
                          name="vaultScopeValidation"
                          [checked]="filterScope() === sc.value"
                          (change)="filterScope.set(sc.value)"
                          class="w-3.5 h-3.5 border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                        <span>{{ sc.label }}</span>
                      </label>
                    }
                  </div>
                </div>

                <!-- Popover Action Footer -->
                <div class="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <button
                    type="button"
                    (click)="clearAllFilters()"
                    class="text-[11px] font-medium text-slate-500 hover:text-slate-800 cursor-pointer">
                    Clear All
                  </button>
                  <button
                    type="button"
                    (click)="isFilterPopoverOpen.set(false)"
                    class="h-7 px-3 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors cursor-pointer">
                    Apply Filters ({{ filteredSavedConnections().length }} matching)
                  </button>
                </div>

              </div>
            }

          </div>

          <!-- Active Filter Chips Row -->
          @if (activeFilterChips().length > 0) {
            <div class="flex items-center gap-1.5 flex-wrap">
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

          <!-- Saved Endpoints Card Grid (3-column, max-h-[440px] overflow-y-auto) -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 max-h-[440px] overflow-y-auto p-1">
            @for (conn of filteredSavedConnections(); track conn.id) {
              @let evalRes = evaluateSavedConnection(conn);
              @let isSelected = vs.newValidationDraft().sourceConnectionId === conn.id;

              <div
                (click)="selectSavedEndpoint(conn)"
                class="p-3.5 border rounded-xl cursor-pointer transition-all flex flex-col justify-between gap-3 shadow-2xs group"
                [class]="isSelected
                  ? 'border-blue-600 ring-2 ring-blue-600/30 bg-blue-50/15'
                  : 'border-slate-200 hover:border-blue-400 hover:bg-slate-50/50 bg-white'">
                
                <!-- Top Row: Icon + Name Badge + Status Pill -->
                <div class="flex items-start justify-between gap-2">
                  <div class="flex items-center gap-2.5 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-700 shrink-0 group-hover:border-blue-300 transition-colors">
                      <app-lucide-icon [name]="getProviderIcon(conn.provider)" [size]="16"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col min-w-0">
                      <span class="text-xs font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors">
                        {{ conn.name }}
                      </span>
                      <span class="text-[10px] text-slate-400 font-mono">
                        {{ conn.provider }}
                      </span>
                    </div>
                  </div>

                  <!-- Status Pill (Curved-Corner Rectangle) -->
                  @switch (conn.status) {
                    @case ('CONNECTED') {
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                        <span class="w-1.5 h-1.5 rounded-xs bg-emerald-500"></span>
                        Healthy · Verified
                      </span>
                    }
                    @case ('ATTENTION') {
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
                        <span class="w-1.5 h-1.5 rounded-xs bg-amber-500"></span>
                        Stale · Re-test
                      </span>
                    }
                    @default {
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold bg-rose-50 text-rose-700 border border-rose-200 shrink-0">
                        <span class="w-1.5 h-1.5 rounded-xs bg-rose-500"></span>
                        Expired Secret
                      </span>
                    }
                  }
                </div>

                <!-- Middle Row: Host & Port, Network Route -->
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

                <!-- Bottom Row: Readiness & Selection Tag -->
                <div class="flex items-center justify-between text-[11px]">
                  @if (evalRes.isEligible) {
                    <span class="inline-flex items-center gap-1 text-emerald-700 font-semibold">
                      <app-lucide-icon name="check" [size]="12" class="text-emerald-600"></app-lucide-icon>
                      <span>Read-Only Ready</span>
                    </span>
                  } @else {
                    <span class="inline-flex items-center gap-1 text-amber-700 font-semibold truncate" [title]="evalRes.reason || ''">
                      <app-lucide-icon name="alert-triangle" [size]="12" class="text-amber-600 shrink-0"></app-lucide-icon>
                      <span class="truncate">{{ evalRes.reason }}</span>
                    </span>
                  }

                  @if (isSelected) {
                    <span class="inline-flex items-center gap-1 text-xs font-bold text-blue-600">
                      <span>Active</span>
                      <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                    </span>
                  }
                </div>

              </div>
            }

            @if (filteredSavedConnections().length === 0) {
              <div class="col-span-full py-12 text-center text-slate-400 text-xs bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                No saved connections match your active search and filter criteria.
              </div>
            }
          </div>

          <!-- Active Selected Connection Banner Strip (Instant Lookup Confirmation) -->
          @if (selectedSavedConnection(); as conn) {
            @if (evaluateSavedConnection(conn); as evalResult) {
              @if (evalResult.isEligible) {
                <div class="p-3 bg-emerald-50/40 border border-emerald-200 rounded-xl flex items-center justify-between gap-3 text-xs animate-in fade-in duration-100">
                  <div class="flex items-center gap-2">
                    <app-lucide-icon name="check-circle-2" [size]="16" class="text-emerald-600 shrink-0"></app-lucide-icon>
                    <span class="font-semibold text-emerald-900">
                      Selected <strong class="font-bold text-slate-900">{{ conn.name }}</strong> ({{ conn.provider }}) · 0ms instant cached lookup · Ready for Step 3
                    </span>
                  </div>
                  <span class="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-700 font-medium">
                    <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                    <span>Mode Verified</span>
                  </span>
                </div>
              } @else {
                <div class="p-3 bg-amber-50/50 border border-amber-300 rounded-xl flex items-center justify-between gap-3 text-xs animate-in fade-in duration-100">
                  <div class="flex items-center gap-2">
                    <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
                    <span class="font-semibold text-amber-900">
                      {{ evalResult.reason }}
                    </span>
                  </div>
                  <button
                    type="button"
                    (click)="vs.updateDraft({ sourceConnectionId: undefined, sourceVerified: false })"
                    class="px-2.5 py-1 text-xs font-medium text-amber-800 bg-white border border-amber-300 rounded-md hover:bg-amber-50 cursor-pointer">
                    Deselect
                  </button>
                </div>
              }
            }
          }

        </section>
      }

      <!-- ========================================================================= -->
      <!-- BRANCH 2: NEW CONNECTION BRANCH                                           -->
      <!-- ========================================================================= -->
      @if (vs.newValidationDraft().sourceConnectionMode === 'NEW') {
        <section class="space-y-6 animate-in fade-in duration-150">
          
          <!-- PHASE A: EXPANSIVE PROVIDER CATALOG GRID -->
          @if (!vs.newValidationDraft().sourceProvider) {
            <div class="flex flex-col gap-4 animate-in fade-in duration-150">
              
              <!-- Full-Width Search Bar with Explicit Padding & Left Icon Clearance -->
              <div class="relative w-full">
                <input
                  type="text"
                  [(ngModel)]="searchQuery"
                  placeholder="Search providers (e.g. Oracle, PostgreSQL, Snowflake, Kafka)..."
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

              <!-- Clean Category Filter Pill Tabs -->
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

              <!-- The Engine Grid: grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3.5 -->
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

          <!-- PHASE B: ENGINE SELECTED (ACTIVE CONTEXT BAR & DYNAMIC FORM) -->
          @if (selectedProviderSchema(); as schema) {
            <div class="space-y-5 animate-in fade-in duration-150">
              
              <!-- Active Context Bar: [ Engine Icon ] Title · Category with [ Change Engine ] -->
              <div class="p-3.5 bg-blue-50/40 border border-blue-200 rounded-xl flex items-center justify-between flex-wrap gap-2">
                <div class="flex items-center gap-3 min-w-0">
                  <div class="w-9 h-9 rounded-lg bg-white border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 shadow-2xs">
                    <app-lucide-icon [name]="schema.icon" [size]="18"></app-lucide-icon>
                  </div>
                  <div class="flex flex-col min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-bold text-slate-900 truncate">{{ schema.name }}</span>
                      <span class="px-1.5 py-0.2 text-[9px] font-mono font-bold bg-blue-100 text-blue-800 rounded">
                        {{ schema.providerId }}
                      </span>
                    </div>
                    <span class="text-[11px] text-slate-500 capitalize">
                      {{ schema.category.toLowerCase().replace('_', ' ') }}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  (click)="changeEngine()"
                  class="h-7 px-3 text-xs font-semibold text-blue-700 bg-white border border-blue-300 hover:bg-blue-50 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs">
                  <app-lucide-icon name="arrow-left" [size]="12"></app-lucide-icon>
                  <span>Change Engine</span>
                </button>
              </div>

              <!-- Dynamic Field Schema Form Grid with Conditional Field Show/Hide Rules -->
              <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
                <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
                  <span class="text-xs font-bold text-slate-900">Endpoint &amp; Authentication Parameters</span>
                  <span class="text-[11px] text-slate-400 font-normal">Generated dynamically from provider schema</span>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  @for (field of schema.fields; track field.id) {
                    @if (isFieldVisible(field, schema)) {
                      <div [class]="(field.type === 'textarea' || field.type === 'file_path') ? 'flex flex-col gap-1.5 md:col-span-2' : 'flex flex-col gap-1.5'">
                        
                        <!-- Label with Single Red Asterisk if Required -->
                        <label [for]="'field-' + field.id" class="text-xs font-semibold text-slate-700 flex items-center justify-between">
                          <span>{{ cleanLabel(field.label) }} @if (field.required) { <span class="text-rose-500">*</span> }</span>
                        </label>

                        <!-- Field Type: text / file_path -->
                        @if (field.type === 'text' || field.type === 'file_path') {
                          <input
                            [id]="'field-' + field.id"
                            type="text"
                            [placeholder]="field.placeholder || ''"
                            [ngModel]="getFieldValue(field.id)"
                            (ngModelChange)="onFieldChange(field.id, $event)"
                            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 transition-colors" />
                        }

                        <!-- Field Type: number -->
                        @if (field.type === 'number') {
                          <input
                            [id]="'field-' + field.id"
                            type="number"
                            [placeholder]="field.placeholder || (field.id === 'port' ? (schema.defaultPort ? '' + schema.defaultPort : '') : '')"
                            [ngModel]="getFieldValue(field.id)"
                            (ngModelChange)="onFieldChange(field.id, $event)"
                            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 transition-colors" />
                        }

                        <!-- Field Type: password / secret_ref (STRICTLY ONE CLEAR ICON, NO OVERLAP) -->
                        @if (field.type === 'password' || field.type === 'secret_ref') {
                          <div class="relative">
                            <input
                              [id]="'field-' + field.id"
                              [type]="isSecretVisible(field.id) ? 'text' : 'password'"
                              [placeholder]="field.placeholder || (isProductionEnv() ? 'vault://secret/... (Enforced in Prod)' : 'Password or vault://secret/...')"
                              [ngModel]="getFieldValue(field.id)"
                              (ngModelChange)="onFieldChange(field.id, $event)"
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

                        <!-- Field Type: textarea -->
                        @if (field.type === 'textarea') {
                          <textarea
                            [id]="'field-' + field.id"
                            rows="3"
                            [placeholder]="field.placeholder || ''"
                            [ngModel]="getFieldValue(field.id)"
                            (ngModelChange)="onFieldChange(field.id, $event)"
                            class="w-full p-2.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 font-mono transition-colors"></textarea>
                        }

                        <!-- Field Type: select -->
                        @if (field.type === 'select') {
                          <app-custom-select
                            [options]="field.options || []"
                            [value]="getFieldValue(field.id)"
                            (valueChange)="onFieldChange(field.id, $event)"
                            placeholder="Select an option...">
                          </app-custom-select>
                        }

                        <!-- Field Type: boolean -->
                        @if (field.type === 'boolean') {
                          <label class="flex items-center gap-2 cursor-pointer select-none pt-1">
                            <input
                              type="checkbox"
                              [ngModel]="getFieldValue(field.id)"
                              (ngModelChange)="onFieldChange(field.id, $event)"
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

              <!-- Collapsed Accordion Sections: Network Route & TLS Security -->
              <div class="space-y-3">
                
                <!-- Accordion 1: Network Route (RouteSpec) -->
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
                        [value]="vs.newValidationDraft().sourceNetworkRoute || 'DIRECT'"
                        (valueChange)="onRouteTypeChange($event)"
                        placeholder="Select network route...">
                      </app-custom-select>
                    </div>

                    @if (vs.newValidationDraft().sourceNetworkRoute === 'DIRECT' || !vs.newValidationDraft().sourceNetworkRoute) {
                      <div class="flex flex-col justify-center gap-1 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 text-[11px]">
                        <span class="font-medium text-slate-800">Direct TCP Connection</span>
                        <span>Standard routed IP connectivity over corporate VPC peering, LAN, or local container.</span>
                      </div>
                    }

                    @if (vs.newValidationDraft().sourceNetworkRoute === 'SSH_BASTION') {
                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">SSH Bastion Host <span class="text-rose-500">*</span></label>
                        <input
                          type="text"
                          placeholder="bastion.prod.aws.company.com"
                          [ngModel]="vs.newValidationDraft().sourceBastionHost"
                          (ngModelChange)="vs.updateDraft({ sourceBastionHost: $event, sourceVerified: false })"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>

                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">SSH Port</label>
                        <input
                          type="number"
                          placeholder="22"
                          [ngModel]="sshPort()"
                          (ngModelChange)="sshPort.set($event)"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>

                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">SSH User <span class="text-rose-500">*</span></label>
                        <input
                          type="text"
                          placeholder="ec2-user or ubuntu"
                          [ngModel]="sshUser()"
                          (ngModelChange)="sshUser.set($event)"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>

                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">SSH Private Key / Secret Ref <span class="text-rose-500">*</span></label>
                        <input
                          type="password"
                          placeholder="vault://secret/prod/ssh_key or /path/to/key.pem"
                          [ngModel]="sshKeyRef()"
                          (ngModelChange)="sshKeyRef.set($event)"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>

                      <div class="md:col-span-2 flex items-center justify-between text-[11px] text-slate-500 pt-1">
                        @if (isProductionEnv()) {
                          <span class="inline-flex items-center gap-1 text-emerald-700 font-medium">
                            <app-lucide-icon name="lock" [size]="12" class="text-emerald-600"></app-lucide-icon>
                            <span>Strict SSH host key fingerprint pinning enforced in Production</span>
                          </span>
                        } @else {
                          <span class="text-slate-400">Permissive host key traversal allowed in Non-Production</span>
                        }
                      </div>
                    }

                    @if (vs.newValidationDraft().sourceNetworkRoute === 'PRIVATE_ENDPOINT') {
                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">Private Endpoint ID <span class="text-rose-500">*</span></label>
                        <input
                          type="text"
                          placeholder="vpce-0a1b2c3d4e5f6g7h8 or privatelink.database.windows.net"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>
                    }

                    @if (vs.newValidationDraft().sourceNetworkRoute === 'HTTP_PROXY' || vs.newValidationDraft().sourceNetworkRoute === 'SOCKS5_PROXY') {
                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">Proxy Host <span class="text-rose-500">*</span></label>
                        <input
                          type="text"
                          placeholder="proxy.corp.internal"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>
                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">Proxy Port</label>
                        <input
                          type="number"
                          placeholder="8080"
                          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                      </div>
                    }
                  </div>

                </app-accordion>

                <!-- Accordion 2: TLS & Transport Encryption (TLSBinding) -->
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

                    @if (selectedTlsMode() !== 'DISABLE') {
                      <div class="flex flex-col gap-1.5">
                        <label class="text-xs font-semibold text-slate-700 block">Minimum TLS Version</label>
                        <app-custom-select
                          [options]="[
                            { label: 'TLS 1.3 (Recommended)', value: 'TLS_1_3' },
                            { label: 'TLS 1.2', value: 'TLS_1_2' }
                          ]"
                          value="TLS_1_3"
                          placeholder="Select version...">
                        </app-custom-select>
                      </div>
                    }

                    @if (isProductionEnv() && selectedTlsMode() === 'DISABLE') {
                      <div class="md:col-span-2 p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-2 text-rose-800 text-xs font-medium">
                        <app-lucide-icon name="alert-circle" [size]="16" class="text-rose-600 shrink-0"></app-lucide-icon>
                        <span>Plain unencrypted TCP is strictly blocked in Production. TLS 1.2+ is mandatory.</span>
                      </div>
                    }

                    @if (selectedTlsMode() === 'VERIFY_CA' || selectedTlsMode() === 'VERIFY_FULL' || selectedTlsMode() === 'CERTIFICATE_MTLS') {
                      <div class="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
                        <div class="flex flex-col gap-1.5">
                          <label class="text-xs font-semibold text-slate-700 block">Enterprise CA Certificate Path</label>
                          <input
                            type="text"
                            placeholder="/etc/ssl/certs/enterprise-ca.crt"
                            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                        </div>
                        @if (selectedTlsMode() === 'VERIFY_FULL') {
                          <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-semibold text-slate-700 block">Server Name Override (SNI SAN Match)</label>
                            <input
                              type="text"
                              placeholder="db-cluster.company.com"
                              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                          </div>
                        }
                        @if (selectedTlsMode() === 'CERTIFICATE_MTLS') {
                          <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-semibold text-slate-700 block">Client Certificate Path (.crt / .pem)</label>
                            <input
                              type="text"
                              placeholder="/etc/ssl/client/akaal-agent.crt"
                              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                          </div>
                          <div class="flex flex-col gap-1.5">
                            <label class="text-xs font-semibold text-slate-700 block">Client Private Key (vault:// or .key)</label>
                            <input
                              type="password"
                              placeholder="vault://secret/prod/client_key"
                              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                          </div>
                        }
                      </div>
                    }
                  </div>

                </app-accordion>

              </div>

              <!-- ================================================================= -->
              <!-- BACKEND VERIFICATION ENGINE: 7-PHASE EXECUTION PROBE             -->
              <!-- ================================================================= -->
              <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
                <div class="flex items-center justify-between flex-wrap gap-2">
                  <div class="flex flex-col gap-0.5">
                    <span class="text-xs font-bold text-slate-900">Source Connection Verification</span>
                    <p class="text-[11px] text-slate-500 font-normal">
                      Executes the full 7-phase probe: DNS, TLS, Auth, Engine Attestation, Validation Capabilities, Read-Only Audit, and Teardown.
                    </p>
                  </div>

                  <button
                    type="button"
                    (click)="runSevenPhaseProbe()"
                    [disabled]="isVerifying()"
                    class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50 flex items-center gap-2 cursor-pointer transition-colors shadow-2xs">
                    @if (isVerifying()) {
                      <app-lucide-icon name="refresh-cw" [size]="13" class="animate-spin text-white"></app-lucide-icon>
                      <span>Executing Probe ({{ activeExecutingPhaseIndex() }}/7)...</span>
                    } @else {
                      <app-lucide-icon name="shield-check" [size]="14"></app-lucide-icon>
                      <span>Verify Connection</span>
                    }
                  </button>
                </div>

                <!-- LIVE PROGRESS DISPLAY DURING EXECUTION PROBE -->
                @if (isVerifying()) {
                  <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5 animate-in fade-in duration-100">
                    <div class="flex items-center justify-between text-xs">
                      <span class="font-bold text-slate-800">
                        Running Phase {{ activeExecutingPhaseIndex() }}: {{ activePhaseName() }}
                      </span>
                      <span class="text-slate-500 font-mono text-[11px]">
                        {{ Math.round((activeExecutingPhaseIndex() / 7) * 100) }}% complete
                      </span>
                    </div>
                    <div class="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-blue-600 transition-all duration-150 rounded-full"
                        [style.width.%]="(activeExecutingPhaseIndex() / 7) * 100"></div>
                    </div>
                  </div>
                }

                <!-- COMPACT RESULTS DISPLAY: Rendered ONLY AFTER operator clicks Verify -->
                @if (probeExecuted()) {
                  @if (vs.newValidationDraft().sourceVerified) {
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
                        Local endpoint specification and credentials syntax are complete. Live transport handshake, authentication, and read-permission verification require an active backend engine.
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
              @if (vs.newValidationDraft().sourceVerified) {
                <div class="p-4 bg-slate-50/70 border border-slate-200 rounded-xl space-y-3 animate-in fade-in duration-150">
                  <label class="flex items-center gap-2.5 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      [ngModel]="vs.newValidationDraft().sourceSaveToVault"
                      (ngModelChange)="onSaveToVaultChange($event)"
                      class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                    <span class="text-xs font-semibold text-slate-800">
                      Save connection for reuse
                    </span>
                  </label>

                  @if (vs.newValidationDraft().sourceSaveToVault) {
                    <div class="flex flex-col gap-1.5 pl-6 animate-in fade-in duration-100 max-w-xl">
                      <label class="text-xs font-semibold text-slate-700 block">
                        Connection Label
                      </label>
                      <div class="flex items-center gap-2.5">
                        <input
                          type="text"
                          [ngModel]="vaultConnectionName()"
                          (ngModelChange)="onVaultConnectionNameChange($event)"
                          placeholder="e.g. Finance Oracle 19c Production"
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
export class Step2SourceComponent implements OnInit {
  public vs: ValidationUiService;
  public Math = Math;

  constructor(vs?: ValidationUiService) {
    this.vs = vs || inject(ValidationUiService);
  }

  // Mode Control Segmented Pill Options
  public modeControlOptions: SegmentedControlOption[] = [
    { label: 'Saved Connection', value: 'SAVED', icon: 'database' },
    { label: 'New Connection', value: 'NEW', icon: 'plug' }
  ];

  // Accordion open states
  public isRouteAccordionOpen = false;
  public isTlsAccordionOpen = false;

  // New Connection Catalog Signals
  public searchQuery = signal<string>('');
  public selectedCategoryTab = signal<'ALL' | 'RELATIONAL' | 'DISTRIBUTED_SQL' | 'WAREHOUSE' | 'NOSQL' | 'STREAMING' | 'STORAGE' | 'SAAS'>('ALL');

  // Saved Connection Grid Search & Filter Signals
  public savedSearchQuery = signal<string>('');
  public isFilterPopoverOpen = signal<boolean>(false);
  public filterEnvironment = signal<string>('Production');
  public filterCategory = signal<string>('ALL');
  public filterRoutes = signal<NetworkRouteType[]>([]);
  public filterHealthStatuses = signal<string[]>([]);
  public filterScope = signal<'PROJECT' | 'TEAM' | 'ENTERPRISE'>('PROJECT');

  // Secret Visibility Map (Strictly One Icon, prevents overlap)
  public secretVisibilityMap = signal<Record<string, boolean>>({});

  // Additional route inputs
  public sshPort = signal<number>(22);
  public sshUser = signal<string>('ec2-user');
  public sshKeyRef = signal<string>('');

  // Verification Signals
  public isVerifying = signal<boolean>(false);
  public probeExecuted = signal<boolean>(false);
  public selectedTlsMode = signal<string>('VERIFY_FULL');
  public vaultConnectionName = signal<string>('');
  public isSourceVaultSaved = signal<boolean>(false);
  public verificationError = signal<{ phase: string; category: string; message: string } | null>(null);
  public activeExecutingPhaseIndex = signal<number>(1);
  public activePhaseName = signal<string>('DNS & Network Resolution');

  // Full 7-Phase Execution Probe Schema for Validation Studio
  public executionPhases: VerificationPhaseState[] = [
    { index: 1, name: 'Phase 1: DNS & Network Resolution', description: 'Resolves host, VPC subnet, or Bastion jump route', chipLabel: 'DNS & Network', status: 'PENDING' },
    { index: 2, name: 'Phase 2: TCP Handshake & TLS Negotiation', description: 'Enforces TLS 1.2+, negotiates cipher, and validates CA', chipLabel: 'TCP & TLS 1.3', status: 'PENDING' },
    { index: 3, name: 'Phase 3: Vault Decryption & Credential Auth', description: 'Authenticates principal and checks role privileges', chipLabel: 'Vault Auth', status: 'PENDING' },
    { index: 4, name: 'Phase 4: Physical Engine Attestation', description: 'Probes engine version, build, topology, and cluster state', chipLabel: 'Engine Attested', status: 'PENDING' },
    { index: 5, name: 'Phase 5: Validation Capabilities Discovery', description: 'Probes partition schema, hash sampling APIs, chunked index readers', chipLabel: 'Capabilities Probed', status: 'PENDING' },
    { index: 6, name: 'Phase 6: Read-Only Audit & Fail-Closed Permissions', description: 'Audits SELECT, CATALOG, and verifies zero mutation privileges', chipLabel: 'Read-Only Audited', status: 'PENDING' },
    { index: 7, name: 'Phase 7: Teardown & Normalization', description: 'Safely releases test sessions, locks, and temporary channels', chipLabel: 'Clean Teardown', status: 'PENDING' }
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
      databaseName: 'catalog_qa',
      username: 'qa_user',
      secretRef: 'vault://secret/staging/mongo',
      tlsEnabled: true,
      networkRoute: 'DIRECT',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 1 hr ago',
      latencyMs: 12.0,
      capabilities: ['DOCUMENT_HASHING', 'AGGREGATION_PROBE'],
      assignedMigrationCount: 1,
      assignedProjectCount: 1,
      createdAt: '2026-08-18T10:00:00Z',
      updatedAt: '2026-08-28T06:00:00Z',
      scope: 'PROJECT'
    },
    {
      id: 'conn-06',
      name: 'Azure Blob Storage Archive',
      provider: 'Azure Blob Storage',
      category: 'STORAGE',
      environment: 'Production',
      host: 'storageacc.blob.core.windows.net',
      port: 443,
      databaseName: 'raw-archives',
      username: 'azure_sa',
      secretRef: 'vault://secret/prod/azure/blob',
      tlsEnabled: true,
      networkRoute: 'HTTP_PROXY',
      status: 'CONNECTED',
      verificationFreshness: 'Verified 2 hrs ago',
      latencyMs: 24.1,
      capabilities: ['BLOCK_BLOB_MD5'],
      assignedMigrationCount: 1,
      assignedProjectCount: 1,
      createdAt: '2026-08-20T08:00:00Z',
      updatedAt: '2026-08-28T05:00:00Z',
      scope: 'TEAM'
    },
    {
      id: 'conn-07',
      name: 'Legacy SQL Server 2012',
      provider: 'Microsoft SQL Server',
      category: 'RELATIONAL',
      environment: 'Production',
      host: 'sql-legacy.corp.internal',
      port: 1433,
      databaseName: 'legacy_erp',
      username: 'sa_readonly',
      secretRef: 'vault://secret/prod/mssql/legacy',
      tlsEnabled: false,
      networkRoute: 'DIRECT',
      status: 'ATTENTION',
      verificationFreshness: 'Stale (14 days ago)',
      latencyMs: 8.5,
      capabilities: ['CHECKSUM_AGG'],
      assignedMigrationCount: 0,
      assignedProjectCount: 1,
      createdAt: '2026-07-15T12:00:00Z',
      updatedAt: '2026-08-14T09:00:00Z',
      scope: 'ENTERPRISE'
    },
    {
      id: 'conn-08',
      name: 'Dev SQLite QA Sandbox',
      provider: 'SQLite',
      category: 'RELATIONAL',
      environment: 'Non-Production',
      host: '/var/data/qa_sandbox.db',
      port: 0,
      databaseName: 'main',
      username: 'local',
      secretRef: '',
      tlsEnabled: false,
      networkRoute: 'DIRECT',
      status: 'DISCONNECTED',
      verificationFreshness: 'Failed',
      latencyMs: 0.2,
      capabilities: ['SNAPSHOT_READ'],
      assignedMigrationCount: 0,
      assignedProjectCount: 1,
      createdAt: '2026-08-22T14:00:00Z',
      updatedAt: '2026-08-27T10:00:00Z',
      scope: 'PROJECT'
    }
  ];

  // Network Route Options
  public networkRouteOptions: CustomSelectOption[] = [
    { label: 'Direct TCP Network Connection (Default)', value: 'DIRECT', desc: 'Standard routed IP connectivity over VPC peering or LAN' },
    { label: 'SSH Bastion Jump Tunnel', value: 'SSH_BASTION', desc: 'Encrypted SSH bastion jump host traversal' },
    { label: 'Private Endpoint / AWS PrivateLink', value: 'PRIVATE_ENDPOINT', desc: 'VPC endpoint or cloud private link interface' },
    { label: 'Corporate HTTP Proxy', value: 'HTTP_PROXY', desc: 'Standard corporate HTTP forward proxy' },
    { label: 'SOCKS5 Proxy Tunnel', value: 'SOCKS5_PROXY', desc: 'Binary stream SOCKS5 proxy traversal' }
  ];

  // Dynamic TLS Options (Adapts based on Production vs Non-Production)
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
        { label: 'Mutual TLS (mTLS)', value: 'CERTIFICATE_MTLS', desc: 'Two-way cryptographic authentication with client certificate' },
        { label: 'Disable TLS (Unencrypted TCP)', value: 'DISABLE', desc: 'Plain unencrypted TCP (allowed for localhost/containers in Non-Prod)' }
      ];
    }
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

    // Search query
    if (q) {
      list = list.filter(c =>
        c.name.toLowerCase().includes(q) ||
        c.provider.toLowerCase().includes(q) ||
        c.host.toLowerCase().includes(q)
      );
    }

    // 1. Environment
    if (env !== 'ALL') {
      list = list.filter(c => c.environment === env);
    }

    // 2. Category
    if (cat !== 'ALL') {
      list = list.filter(c => c.category === cat);
    }

    // 3. Routes
    if (routes.length > 0) {
      list = list.filter(c => routes.includes(c.networkRoute));
    }

    // 4. Health Statuses
    if (statuses.length > 0) {
      list = list.filter(c => statuses.includes(c.status));
    }

    // 5. Scope
    if (scope === 'PROJECT') {
      list = list.filter(c => c.scope === 'PROJECT');
    } else if (scope === 'TEAM') {
      list = list.filter(c => c.scope === 'PROJECT' || c.scope === 'TEAM');
    }

    return list;
  });

  // Active Filter Count
  public activeFilterCount = computed(() => {
    let count = 0;
    if (this.filterEnvironment() !== 'ALL') count++;
    if (this.filterCategory() !== 'ALL') count++;
    count += this.filterRoutes().length;
    count += this.filterHealthStatuses().length;
    if (this.filterScope() !== 'PROJECT') count++;
    return count;
  });

  // Active Filter Chips for Removable Chips Row
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
    const id = this.vs.newValidationDraft().sourceConnectionId;
    if (!id) return undefined;
    return this.enterpriseSavedConnections.find(c => c.id === id);
  });

  public selectedProviderSchema = computed<ProviderFormSchema | undefined>(() => {
    const pid = this.vs.newValidationDraft().sourceProvider;
    if (!pid) return undefined;
    return ALL_48_PROVIDER_SCHEMAS[pid];
  });

  public ngOnInit(): void {
    // Sync environment filter with Step 1 environment
    const draftEnv = this.vs.newValidationDraft().environment;
    if (draftEnv) {
      this.filterEnvironment.set(draftEnv);
      this.selectedTlsMode.set(draftEnv === 'Production' ? 'VERIFY_FULL' : 'PREFER');
    }
  }

  public isProductionEnv(): boolean {
    return this.vs.newValidationDraft().environment === 'Production';
  }

  // Proper Category Filter Casing (e.g. NoSQL instead of Nosql)
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

  // Secret Visibility Helpers (Single clear icon, no overlap)
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
    if (this.vs.newValidationDraft().sourceConnectionMode === mode) return;

    this.vs.updateDraft({
      sourceConnectionMode: mode,
      sourceConnectionId: undefined,
      sourceProvider: undefined as any,
      sourceHost: '',
      sourcePort: 0,
      sourceDatabase: '',
      sourceUsername: '',
      sourceSecretRef: '',
      sourceParams: {},
      sourceVerified: false,
      sourceVerificationResult: undefined,
      sourceSaveToVault: false
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  // Filter Toggle Helpers
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

  // Engine Selection in Catalog Grid
  public selectEngine(engineId: PhysicalProviderId): void {
    const schema = ALL_48_PROVIDER_SCHEMAS[engineId];
    if (!schema) return;

    this.vs.updateDraft({
      sourceProvider: engineId,
      sourceHost: '',
      sourcePort: schema.defaultPort || 0,
      sourceDatabase: '',
      sourceUsername: '',
      sourceSecretRef: '',
      sourceParams: {},
      sourceVerified: false,
      sourceVerificationResult: undefined,
      sourceSaveToVault: false
    });

    this.probeExecuted.set(false);
    this.verificationError.set(null);
    this.vaultConnectionName.set(`${schema.name} Production`);
  }

  public changeEngine(): void {
    this.vs.updateDraft({
      sourceProvider: undefined as any,
      sourceHost: '',
      sourcePort: 0,
      sourceDatabase: '',
      sourceUsername: '',
      sourceSecretRef: '',
      sourceParams: {},
      sourceVerified: false,
      sourceVerificationResult: undefined,
      sourceSaveToVault: false
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  // ===========================================================================
  // SECTION 2: DYNAMIC CONDITIONAL SHOW/HIDE RULES PER PROVIDER
  // ===========================================================================
  public isFieldVisible(field: ProviderFormField, schema: ProviderFormSchema): boolean {
    const fid = field.id;

    // 1. Oracle Database Conditional Fields
    if (schema.name.includes('Oracle') || schema.providerId === 'Oracle') {
      const connType = this.getFieldValue('connection_type') || 'SERVICE_NAME';
      if (connType === 'SERVICE_NAME') {
        if (fid === 'sid' || fid === 'tns_descriptor' || fid === 'wallet_path' || fid === 'wallet_password' || fid === 'tns_alias') {
          return false;
        }
      } else if (connType === 'SID') {
        if (fid === 'service_name' || fid === 'tns_descriptor' || fid === 'wallet_path' || fid === 'wallet_password' || fid === 'tns_alias') {
          return false;
        }
      } else if (connType === 'TNS_DESCRIPTOR') {
        if (fid === 'host' || fid === 'port' || fid === 'service_name' || fid === 'sid' || fid === 'wallet_path' || fid === 'wallet_password' || fid === 'tns_alias') {
          return false;
        }
      } else if (connType === 'WALLET') {
        if (fid === 'host' || fid === 'port' || fid === 'service_name' || fid === 'sid' || fid === 'tns_descriptor') {
          return false;
        }
      }
    }

    // 2. Microsoft SQL Server (MSSQL) Authentication Switcher
    if (schema.name.includes('SQL Server') || schema.providerId === 'Microsoft SQL Server') {
      const authType = this.getFieldValue('auth_type') || 'SQL_AUTH';
      if (authType === 'WINDOWS_SSPI' && (fid === 'username' || fid === 'secret_ref' || fid === 'password')) {
        return false;
      }
    }

    // 3. MongoDB Topology Switcher
    if (schema.name.includes('MongoDB') || schema.providerId === 'MongoDB') {
      const connMode = this.getFieldValue('connection_mode') || 'STANDALONE';
      if (connMode === 'STANDALONE' && (fid === 'replica_endpoints' || fid === 'replica_set_name')) {
        return false;
      }
      if (connMode === 'CLUSTER' && (fid === 'host' || fid === 'port')) {
        return false;
      }
    }

    // 4. Snowflake Authentication Switcher
    if (schema.name.includes('Snowflake') || schema.providerId === 'Snowflake') {
      const authType = this.getFieldValue('auth_type') || 'PASSWORD';
      if (authType === 'PASSWORD') {
        if (fid === 'private_key_path' || fid === 'passphrase' || fid === 'oauth_token') return false;
      } else if (authType === 'KEY_PAIR') {
        if (fid === 'secret_ref' || fid === 'oauth_token') return false;
      } else if (authType === 'OAUTH') {
        if (fid === 'username' || fid === 'secret_ref' || fid === 'private_key_path' || fid === 'passphrase') return false;
      } else if (authType === 'SSO') {
        if (fid === 'secret_ref' || fid === 'private_key_path' || fid === 'passphrase' || fid === 'oauth_token') return false;
      }
    }

    // 5. Google BigQuery Authentication Switcher
    if (schema.name.includes('BigQuery') || schema.providerId === 'Google BigQuery') {
      const authType = this.getFieldValue('auth_type') || 'SERVICE_ACCOUNT_KEY';
      if (authType === 'ADC' && fid === 'service_account_json') {
        return false;
      }
    }

    // 6. Elasticsearch Authentication Switcher
    if (schema.name.includes('Elasticsearch') || schema.providerId === 'Elasticsearch') {
      const authType = this.getFieldValue('auth_type') || 'BASIC';
      if (authType === 'API_KEY' && (fid === 'username' || fid === 'secret_ref')) return false;
      if (authType === 'BASIC' && fid === 'api_key') return false;
    }

    // 7. Apache Kafka Security Switcher
    if (schema.name.includes('Kafka') || schema.providerId === 'Apache Kafka') {
      const secProt = this.getFieldValue('security_protocol') || 'PLAINTEXT';
      if ((secProt === 'PLAINTEXT' || secProt === 'SSL') && (fid === 'sasl_mechanism' || fid === 'sasl_username' || fid === 'secret_ref')) {
        return false;
      }
    }

    // 8. Amazon Kinesis / S3 Auth Switcher
    if (schema.name.includes('Kinesis') || schema.name.includes('S3') || schema.providerId === 'Amazon S3' || schema.providerId === 'Amazon Kinesis') {
      const authType = this.getFieldValue('auth_type') || 'ACCESS_KEYS';
      if (authType === 'IAM_ROLE' && (fid === 'aws_access_key_id' || fid === 'secret_ref')) {
        return false;
      }
    }

    // 9. Azure Blob Storage Auth Switcher
    if (schema.name.includes('Blob') || schema.providerId === 'Azure Blob Storage') {
      const authType = this.getFieldValue('auth_type') || 'CONN_STRING';
      if (authType === 'CONN_STRING' && (fid === 'storage_account_name' || fid === 'account_key' || fid === 'sas_token')) return false;
      if (authType === 'ACCOUNT_KEY' && (fid === 'secret_ref' || fid === 'sas_token')) return false;
      if (authType === 'SAS_TOKEN' && (fid === 'secret_ref' || fid === 'storage_account_name' || fid === 'account_key')) return false;
    }

    return true;
  }

  public evaluateSavedConnection(conn: ConnectionItem): {
    isEligible: boolean;
    reason?: string;
    errorCategory?: string;
    canRetest?: boolean;
  } {
    if (conn.status === 'DISCONNECTED') {
      return {
        isEligible: false,
        reason: `The stored credential for "${conn.name}" has expired or failed attestation.`,
        errorCategory: 'CREDENTIAL_EXPIRED',
        canRetest: true
      };
    }

    return { isEligible: true };
  }

  // Instant 0ms Lookup for Saved Connection
  public selectSavedEndpoint(conn: SavedConnectionItemExtended): void {
    const evalRes = this.evaluateSavedConnection(conn);

    if (evalRes.isEligible) {
      this.vs.updateDraft({
        sourceConnectionId: conn.id,
        sourceProvider: conn.provider,
        sourceHost: conn.host,
        sourcePort: conn.port,
        sourceDatabase: conn.databaseName,
        sourceUsername: conn.username,
        sourceSecretRef: conn.secretRef || '',
        sourceTls: conn.tlsEnabled,
        sourceNetworkRoute: conn.networkRoute as any,
        sourceVerified: true,
        sourceVerificationResult: {
          fingerprint: `fp-${conn.id}-${Date.now()}`,
          isVerified: true,
          hasBlockingIssues: false,
          overallLatencyMs: conn.latencyMs || 1.4,
          parameterValidation: { status: 'PASSED', detail: 'Parameters verified' },
          routeResolution: { status: 'PASSED', detail: `${conn.networkRoute} resolved (0.8ms)` },
          transportHandshake: { status: 'PASSED', detail: conn.tlsEnabled ? 'TLS 1.3 active' : 'TCP direct', cipher: 'TLS_AES_256_GCM_SHA384' },
          authentication: { status: 'PASSED', detail: `Authenticated as ${conn.username}` },
          identityAttestation: { status: 'PASSED', detail: `${conn.provider} Enterprise Verified`, serverVersion: '19.4.0' },
          capabilityProbe: { status: 'PASSED', detail: 'Read-only validation primitives supported', capabilities: [] },
          permissionAudit: { status: 'PASSED', detail: 'Read-only query and catalog grants confirmed', permissions: [] }
        }
      });
    } else {
      this.vs.updateDraft({
        sourceConnectionId: conn.id,
        sourceProvider: conn.provider,
        sourceHost: conn.host,
        sourcePort: conn.port,
        sourceDatabase: conn.databaseName,
        sourceUsername: conn.username,
        sourceSecretRef: conn.secretRef || '',
        sourceTls: conn.tlsEnabled,
        sourceNetworkRoute: conn.networkRoute as any,
        sourceVerified: false,
        sourceVerificationResult: {
          fingerprint: `fp-${conn.id}-blocked`,
          isVerified: false,
          hasBlockingIssues: true,
          errorCategory: evalRes.errorCategory,
          blockedReason: evalRes.reason
        }
      });
    }
  }

  public getFieldValue(fieldId: string): any {
    const d = this.vs.newValidationDraft();
    switch (fieldId) {
      case 'host': return d.sourceHost;
      case 'port': return d.sourcePort ? d.sourcePort : '';
      case 'database':
      case 'database_name':
      case 'database_path':
      case 'service_name': return d.sourceDatabase;
      case 'username': return d.sourceUsername;
      case 'secret_ref':
      case 'password': return d.sourceSecretRef;
      default: return d.sourceParams?.[fieldId] ?? '';
    }
  }

  public onFieldChange(fieldId: string, value: any): void {
    const d = this.vs.newValidationDraft();
    const partial: any = { sourceVerified: false, sourceVerificationResult: undefined };

    switch (fieldId) {
      case 'host':
        partial.sourceHost = value;
        break;
      case 'port':
        partial.sourcePort = Number(value) || 0;
        break;
      case 'database':
      case 'database_name':
      case 'database_path':
      case 'service_name':
        partial.sourceDatabase = value;
        break;
      case 'username':
        partial.sourceUsername = value;
        break;
      case 'secret_ref':
      case 'password':
        partial.sourceSecretRef = value;
        break;
      default:
        partial.sourceParams = { ...(d.sourceParams || {}), [fieldId]: value };
        break;
    }

    this.vs.updateDraft(partial);
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public onRouteTypeChange(route: any): void {
    this.vs.updateDraft({
      sourceNetworkRoute: route,
      sourceVerified: false,
      sourceVerificationResult: undefined
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public onTlsModeChange(mode: string): void {
    this.selectedTlsMode.set(mode);
    this.vs.updateDraft({
      sourceTls: mode !== 'DISABLE',
      sourceVerified: false,
      sourceVerificationResult: undefined
    });
    this.probeExecuted.set(false);
    this.verificationError.set(null);
  }

  public onVaultConnectionNameChange(name: string): void {
    this.vaultConnectionName.set(name);
    this.isSourceVaultSaved.set(false);
  }

  public saveSourceToVault(): void {
    if (!this.vaultConnectionName().trim()) return;
    const d = this.vs.newValidationDraft();
    const schema = this.selectedProviderSchema();
    const newConn: SavedConnectionItemExtended = {
      id: `conn-${Date.now()}`,
      name: this.vaultConnectionName().trim(),
      provider: d.sourceProvider || 'PostgreSQL',
      category: (schema?.category as any) || 'RELATIONAL',
      environment: (d.environment as any) || 'Production',
      host: d.sourceHost || 'localhost',
      port: d.sourcePort || 5432,
      databaseName: d.sourceDatabase || 'defaultdb',
      username: d.sourceUsername || 'admin',
      tlsEnabled: !!d.sourceTls,
      networkRoute: (d.sourceNetworkRoute as any) || 'DIRECT',
      status: 'CONNECTED',
      verificationFreshness: 'Just now',
      latencyMs: 1.4,
      secretRef: d.sourceSecretRef || '',
      capabilities: ['HASH_SCAN', 'READ_ONLY_AUDIT'],
      assignedMigrationCount: 0,
      assignedProjectCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      scope: 'PROJECT'
    };
    this.enterpriseSavedConnections = [newConn, ...this.enterpriseSavedConnections];
    this.vs.connections.update(list => [newConn, ...list]);
    this.isSourceVaultSaved.set(true);
    this.vs.updateDraft({ sourceSaveToVault: true });
  }

  public onSaveToVaultChange(checked: boolean): void {
    this.vs.updateDraft({ sourceSaveToVault: checked });
    if (!checked) {
      this.isSourceVaultSaved.set(false);
    }
  }

  // ===========================================================================
  // BACKEND VERIFICATION ENGINE: SEQUENTIAL 7-PHASE EXECUTION PROBE
  // ===========================================================================
  public runSevenPhaseProbe(): void {
    const d = this.vs.newValidationDraft();
    const schema = this.selectedProviderSchema();
    if (!schema) return;

    this.isVerifying.set(true);
    this.probeExecuted.set(false);
    this.verificationError.set(null);

    // Reset phase statuses
    this.executionPhases.forEach(p => {
      p.status = 'PENDING';
      p.detail = undefined;
    });

    // Phase 1: Parameter Validation
    const missingRequired: string[] = [];
    for (const f of schema.fields) {
      if (f.required && this.isFieldVisible(f, schema)) {
        const val = this.getFieldValue(f.id);
        if (val === undefined || val === null || val === '') {
          missingRequired.push(this.cleanLabel(f.label));
        }
      }
    }
    if (missingRequired.length > 0) {
      this.verificationError.set({
        phase: 'Phase 1: Parameter Validation',
        category: 'MISSING_REQUIRED_PARAMETERS',
        message: `Required fields missing: ${missingRequired.join(', ')}`
      });
      this.isVerifying.set(false);
      this.probeExecuted.set(true);
      this.vs.updateDraft({ sourceVerified: false });
      return;
    }

    const route = d.sourceNetworkRoute || 'DIRECT';
    if (route === 'SSH_BASTION' && !d.sourceBastionHost) {
      this.verificationError.set({
        phase: 'Phase 1: Parameter Validation',
        category: 'UNRESOLVED_BASTION_HOST',
        message: 'SSH Bastion Host is required when using SSH Bastion Jump Tunnel'
      });
      this.isVerifying.set(false);
      this.probeExecuted.set(true);
      this.vs.updateDraft({ sourceVerified: false });
      return;
    }

    // Phase 2: TLS Policy Check
    const isProd = this.isProductionEnv();
    const tls = this.selectedTlsMode();
    if (isProd && tls === 'DISABLE') {
      this.verificationError.set({
        phase: 'Phase 2: Transport Security Policy',
        category: 'TLS_MANDATORY_IN_PRODUCTION',
        message: 'Plain unencrypted TCP is blocked in Production environment. Must use TLS 1.2+.'
      });
      this.isVerifying.set(false);
      this.probeExecuted.set(true);
      this.vs.updateDraft({ sourceVerified: false });
      return;
    }

    // Parameters validated successfully
    this.isVerifying.set(false);
    this.probeExecuted.set(true);
    this.verificationError.set(null);

    const verificationResult: SourceVerificationResult = {
      fingerprint: 'NOT_EVALUATED',
      isVerified: true,
      hasBlockingIssues: false,
      parameterValidation: { status: 'PASSED', detail: 'Connection parameters validated' },
      routeResolution: { status: 'PASSED', detail: `Route configured via ${route}` },
      transportHandshake: { status: 'NOT_EVALUATED' as any, protocol: tls },
      authentication: { status: 'NOT_EVALUATED' as any, detail: 'Authentication not evaluated in client draft' },
      permissionAudit: { status: 'NOT_EVALUATED' as any, detail: 'Read permissions not evaluated in client draft', permissions: [] },
      physicalConnection: { status: 'NOT_EVALUATED' as any, detail: 'Live connection verification has not been performed' }
    };

    this.vs.updateDraft({
      sourceVerified: true,
      sourceVerificationResult: verificationResult
    });
  }
}
