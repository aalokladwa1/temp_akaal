import { Component, inject, signal, computed, HostListener, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { DiscoveryScopeService } from '../../../../core/services/discovery-scope.service';
import { DiscoveryDepthTier } from '../../../../core/models/migration-view.models';
import {
  DiscoveredResourceNode,
  DiscoveryDepthCardOption,
  FlattenedTreeNode,
  HierarchyFilterLabels,
  ScopeSummaryMetrics
} from './step4-scope.models';

@Component({
  selector: 'app-step4-scope',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  host: {
    class: 'flex flex-1 flex-col w-full h-full min-h-0'
  },
  template: `
    <div class="w-full h-full flex flex-col font-sans select-none text-xs min-h-0">
      
      <!-- ========================================================================= -->
      <!-- STATE 1: DEPTH_SELECTION (Discovery Depth Decision Owns the Workspace)    -->
      <!-- ========================================================================= -->
      @if (svc.lifecycleState() === 'DEPTH_SELECTION') {
        <div class="flex-1 flex flex-col items-center justify-center p-6 max-w-5xl mx-auto w-full">
          
          <!-- Header Area -->
          <div class="flex flex-col items-center text-center gap-1.5 pb-8">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight">Discover Source</h1>
            <p class="text-xs text-slate-500 max-w-lg font-normal">
              Choose how deeply AKAAL should inspect the source system before defining migration scope.
            </p>
          </div>

          <!-- 4 Depth Tier Cards (Responsive Grid, Zero-Shadow, No Fake Timings) -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
            @for (card of depthCards; track card.depth) {
              <div
                (click)="selectedDepthTier.set(card.depth)"
                class="flex flex-col justify-between p-4 rounded-lg border text-left cursor-pointer transition-colors bg-white relative"
                [class.border-blue-600]="selectedDepthTier() === card.depth"
                [class.border-2]="selectedDepthTier() === card.depth"
                [class.border-slate-200]="selectedDepthTier() !== card.depth"
                [class.hover:border-slate-300]="selectedDepthTier() !== card.depth">
                
                <div class="flex flex-col gap-2">
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-sm font-bold text-slate-900">{{ card.title }}</span>
                    @if (card.badge) {
                      <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                        {{ card.badge }}
                      </span>
                    }
                  </div>
                  
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    {{ card.tag }}
                  </span>

                  <p class="text-xs text-slate-600 leading-relaxed font-normal pt-1">
                    {{ card.description }}
                  </p>
                </div>

                <div class="pt-4 flex items-center justify-between border-t border-slate-100 mt-4">
                  <div class="flex items-center gap-2">
                    <span
                      class="w-4 h-4 rounded-full border flex items-center justify-center transition-colors"
                      [class.border-blue-600]="selectedDepthTier() === card.depth"
                      [class.bg-blue-600]="selectedDepthTier() === card.depth"
                      [class.border-slate-300]="selectedDepthTier() !== card.depth">
                      @if (selectedDepthTier() === card.depth) {
                        <span class="w-1.5 h-1.5 rounded-full bg-white"></span>
                      }
                    </span>
                    <span class="text-[11px] font-medium" [class.text-blue-700]="selectedDepthTier() === card.depth" [class.text-slate-500]="selectedDepthTier() !== card.depth">
                      {{ selectedDepthTier() === card.depth ? 'Selected' : 'Select' }}
                    </span>
                  </div>
                </div>

              </div>
            }
          </div>

          <!-- Bottom Action Button: Run Discovery -->
          <div class="w-full flex items-center justify-end pt-8">
            <button
              type="button"
              (click)="onRunDiscovery()"
              class="h-9 px-5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md flex items-center gap-2 cursor-pointer transition-colors">
              <span>Run Discovery</span>
              <app-lucide-icon name="arrow-right" [size]="14"></app-lucide-icon>
            </button>
          </div>

        </div>
      }

      <!-- ========================================================================= -->
      <!-- STATE 2: DISCOVERING (Discovery Process Owns the Workspace)               -->
      <!-- ========================================================================= -->
      @if (svc.lifecycleState() === 'DISCOVERING') {
        <div class="flex-1 flex flex-col items-center justify-center p-6 max-w-2xl mx-auto w-full text-center">
          
          <div class="flex flex-col items-center gap-2 pb-6">
            <h1 class="text-lg font-bold text-slate-900 tracking-tight">Discovering Source</h1>
            <p class="text-xs text-slate-500 font-medium">
              {{ currentDepthTitle() }} discovery &middot; {{ ms.wizardDraft().sourceProvider }} ({{ sourceHostInfo() }})
            </p>
          </div>

          <!-- Operational Spinner -->
          <div class="py-4">
            <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>

          <!-- Stage-Aware Progression List -->
          <div class="w-full max-w-md bg-white border border-slate-200 rounded-lg p-4 flex flex-col gap-2.5 text-left my-4">
            @for (stage of svc.discoveryStages(); track stage.id) {
              <div class="flex items-center justify-between text-xs">
                <div class="flex items-center gap-2.5">
                  @if (stage.status === 'COMPLETED') {
                    <span class="text-emerald-600 font-bold">&check;</span>
                    <span class="text-slate-800 font-medium">{{ stage.label }}</span>
                  } @else if (stage.status === 'RUNNING') {
                    <span class="text-blue-600 animate-spin font-bold">&circlearrowright;</span>
                    <span class="text-blue-700 font-semibold">{{ stage.label }}</span>
                  } @else {
                    <span class="text-slate-300">&bull;</span>
                    <span class="text-slate-400">{{ stage.label }}</span>
                  }
                </div>

                <div class="text-[11px] font-mono text-slate-500">
                  @if (stage.detail) {
                    <span>{{ stage.detail }}</span>
                  } @else if (stage.durationMs) {
                    <span>{{ stage.durationMs }}ms</span>
                  }
                </div>
              </div>
            }
          </div>

          <!-- Real Elapsed Time Indicator -->
          <div class="text-xs font-mono text-slate-500 pb-6">
            Elapsed: {{ svc.elapsedSeconds() }}s
          </div>

          <!-- Cancel Discovery Button -->
          <div>
            <button
              type="button"
              (click)="svc.cancelDiscovery()"
              [disabled]="svc.isCancelling()"
              class="h-8 px-4 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer transition-colors disabled:opacity-50">
              <span>{{ svc.isCancelling() ? 'Cancelling...' : 'Cancel Discovery' }}</span>
            </button>
          </div>

        </div>
      }

      <!-- ========================================================================= -->
      <!-- STATE 3A: FAILURE (Dedicated Truthful Failure Screen)                     -->
      <!-- ========================================================================= -->
      @if (svc.lifecycleState() === 'FAILURE') {
        <div class="flex-1 flex flex-col items-center justify-center p-6 max-w-xl mx-auto w-full text-center">
          
          <div class="w-12 h-12 rounded-full bg-rose-50 border border-rose-200 text-rose-600 flex items-center justify-center mb-3">
            <app-lucide-icon name="alert-triangle" [size]="24"></app-lucide-icon>
          </div>

          <h1 class="text-lg font-bold text-slate-900 pb-1">Discovery Failed</h1>
          <p class="text-xs text-slate-500 font-medium pb-4">
            {{ ms.wizardDraft().sourceProvider }} &middot; {{ currentDepthTitle() }} discovery
          </p>

          <p class="text-xs text-slate-600 max-w-md pb-4 font-normal">
            AKAAL could not complete source discovery due to a physical introspection failure.
          </p>

          <!-- Sanitized Error Reason Box -->
          <div class="w-full bg-rose-50 border border-rose-200 rounded-lg p-3 text-left mb-6">
            <div class="text-[11px] font-bold text-rose-800 uppercase tracking-wider mb-1">Reason</div>
            <div class="text-xs text-rose-700 font-mono leading-relaxed">
              {{ svc.errorMessage() || 'Insufficient privileges to inspect required source metadata catalog.' }}
            </div>
          </div>

          <!-- Failed Stage Report -->
          <div class="w-full bg-white border border-slate-200 rounded-lg p-3 text-left mb-6 flex flex-col gap-2">
            <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-0.5">Stages Executed</div>
            <div class="flex items-center gap-2 text-xs text-emerald-700">
              <span>&check;</span>
              <span>Source identity verified</span>
            </div>
            <div class="flex items-center gap-2 text-xs text-emerald-700">
              <span>&check;</span>
              <span>Namespace discovery complete</span>
            </div>
            <div class="flex items-center gap-2 text-xs text-rose-600 font-semibold">
              <span>&cross;</span>
              <span>Structural metadata catalog query rejected</span>
            </div>
          </div>

          <!-- Actions: Change Depth / Retry Discovery -->
          <div class="flex items-center justify-center gap-3">
            <button
              type="button"
              (click)="svc.returnToDepthSelection()"
              class="h-8 px-4 text-xs font-medium text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer transition-colors">
              Change Depth
            </button>
            <button
              type="button"
              (click)="svc.retryDiscovery()"
              class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md cursor-pointer transition-colors">
              Retry Discovery
            </button>
          </div>

        </div>
      }

      <!-- ========================================================================= -->
      <!-- STATE 3B & 4: SCOPE_WORKBENCH & SCOPE_READY (Primary Dense DBA Studio)   -->
      <!-- ========================================================================= -->
      @if (svc.lifecycleState() === 'SCOPE_WORKBENCH') {
        <div class="flex-1 flex flex-col min-h-0 gap-2">
          <h1 class="sr-only">Scope Workbench</h1>
          
          <!-- 1. Collapsed Discovery Depth Line (Top Header Strip) -->
          <div class="h-9 px-3 bg-white border border-slate-200 rounded-md flex items-center justify-between shrink-0">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-blue-600 shrink-0"></span>
              <span class="text-xs text-slate-600">
                Discovery depth: <strong class="text-slate-900">{{ currentDepthTitle() }}</strong> &middot; {{ currentDepthSubtitle() }}
              </span>
            </div>

            <button
              type="button"
              (click)="promptChangeDepth()"
              class="text-xs font-semibold text-blue-600 hover:text-blue-800 cursor-pointer transition-colors">
              Change depth
            </button>
          </div>

          <!-- 2. Restrained Summary Strip (Zero Floating Cards, Subtle Dividers, Mode-Aware) -->
          <div class="h-10 px-4 bg-white border border-slate-200 rounded-md flex items-center justify-between shrink-0">
            <div class="flex items-center divide-x divide-slate-200 text-xs w-full">
              
              <!-- Schemas / Namespaces -->
              <div class="pr-6 flex items-baseline gap-1.5">
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{{ hierarchyLabels().level2Label.toUpperCase() }}S</span>
                <span class="font-bold text-slate-900 font-mono">{{ metrics().schemasSelected }}/{{ metrics().schemasTotal }}</span>
                <span class="text-slate-500 text-[11px]">selected</span>
              </div>

              <!-- Objects -->
              <div class="px-6 flex items-baseline gap-1.5">
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">OBJECTS</span>
                <span class="font-bold text-slate-900 font-mono">{{ metrics().objectsSelected }}/{{ metrics().objectsTotal }}</span>
                <span class="text-slate-500 text-[11px]">selected</span>
              </div>

              <!-- Primary Object Count (e.g. Tables / Collections / Topics) -->
              <div class="px-6 flex items-baseline gap-1.5">
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{{ hierarchyLabels().primaryObjectLabel.toUpperCase() }}</span>
                <span class="font-bold text-slate-900 font-mono">{{ metrics().primarySelected }}</span>
                <span class="text-slate-500 text-[11px]">selected</span>
              </div>

              <!-- Volume (Suppressed or Inapplicable for M6_SCHEMA_ONLY) -->
              <div class="pl-6 flex items-baseline gap-1.5">
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">VOLUME</span>
                <span class="font-bold text-slate-900 font-mono">{{ metrics().volumeFormatted }}</span>
                @if (metrics().isVolumeApplicable) {
                  <span class="text-slate-500 text-[11px]">selected</span>
                }
              </div>

            </div>
          </div>

          <!-- 2.5 Metadata Drift Banner (If Drift Detected) -->
          @if (svc.isDriftDetected()) {
            <div class="px-3 py-2 bg-amber-50 border border-amber-300 rounded-md flex items-center justify-between shrink-0">
              <div class="flex items-center gap-2 text-xs text-amber-900 font-medium">
                <app-lucide-icon name="alert-triangle" [size]="14" class="text-amber-600"></app-lucide-icon>
                <span>Source metadata changed after discovery. Refresh discovery before continuing.</span>
              </div>
              <button
                type="button"
                (click)="svc.refreshDiscoveryAfterDrift()"
                class="h-6 px-2.5 text-[11px] font-semibold text-amber-900 bg-amber-200 hover:bg-amber-300 rounded cursor-pointer transition-colors">
                Refresh discovery
              </button>
            </div>
          }

          <!-- 3. Toolbar (Hierarchy Filters, Search, Bulk Actions, Zero Cut-List Extras) -->
          <div class="h-10 px-3 bg-white border border-slate-200 rounded-md flex items-center justify-between shrink-0 gap-3">
            
            <!-- Left Filter Cluster -->
            <div class="flex items-center gap-2 flex-1 min-w-0">
              
              <!-- Level 1 Filter (Instance / Database / Cluster / Endpoint) -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleToolbarDropdown('level1', $event)"
                  class="h-7 px-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded text-xs font-medium text-slate-700 flex items-center gap-1.5 cursor-pointer transition-colors">
                  <span>{{ hierarchyLabels().level1Label }}: {{ svc.selectedLevel1Filter() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
                </button>

                @if (activeToolbarDropdown() === 'level1') {
                  <div class="absolute left-0 top-full mt-1 z-40 w-48 bg-white border border-slate-200 rounded-md p-1 flex flex-col gap-0.5">
                    <button
                      type="button"
                      (click)="setLevel1Filter('ALL')"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer"
                      [class.font-bold]="svc.selectedLevel1Filter() === 'ALL'">
                      All {{ hierarchyLabels().level1Label }}s
                    </button>
                    @for (opt of svc.getLevel1FilterOptions(); track opt) {
                      <button
                        type="button"
                        (click)="setLevel1Filter(opt)"
                        class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer truncate"
                        [class.font-bold]="svc.selectedLevel1Filter() === opt">
                        {{ opt }}
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Level 2 Filter (Schema / Database / Topic / Bucket) -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleToolbarDropdown('level2', $event)"
                  class="h-7 px-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded text-xs font-medium text-slate-700 flex items-center gap-1.5 cursor-pointer transition-colors">
                  <span>{{ hierarchyLabels().level2Label }}: {{ svc.selectedLevel2Filter() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
                </button>

                @if (activeToolbarDropdown() === 'level2') {
                  <div class="absolute left-0 top-full mt-1 z-40 w-48 bg-white border border-slate-200 rounded-md p-1 flex flex-col gap-0.5">
                    <button
                      type="button"
                      (click)="setLevel2Filter('ALL')"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer"
                      [class.font-bold]="svc.selectedLevel2Filter() === 'ALL'">
                      All {{ hierarchyLabels().level2Label }}s
                    </button>
                    @for (opt of svc.getLevel2FilterOptions(); track opt) {
                      <button
                        type="button"
                        (click)="setLevel2Filter(opt)"
                        class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer truncate"
                        [class.font-bold]="svc.selectedLevel2Filter() === opt">
                        {{ opt }}
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Type Filter -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleToolbarDropdown('type', $event)"
                  class="h-7 px-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded text-xs font-medium text-slate-700 flex items-center gap-1.5 cursor-pointer transition-colors">
                  <span>Type: {{ svc.selectedTypeFilter() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
                </button>

                @if (activeToolbarDropdown() === 'type') {
                  <div class="absolute left-0 top-full mt-1 z-40 w-40 bg-white border border-slate-200 rounded-md p-1 flex flex-col gap-0.5">
                    <button
                      type="button"
                      (click)="setTypeFilter('ALL')"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer"
                      [class.font-bold]="svc.selectedTypeFilter() === 'ALL'">
                      All Types
                    </button>
                    @for (t of svc.getAvailableTypesInCurrentEstate(); track t) {
                      <button
                        type="button"
                        (click)="setTypeFilter(t)"
                        class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer"
                        [class.font-bold]="svc.selectedTypeFilter() === t">
                        {{ t }}
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Search Input (Exact Placeholder: Search object name) -->
              <div class="relative w-56">
                <input
                  type="text"
                  [ngModel]="svc.searchQuery()"
                  (ngModelChange)="svc.searchQuery.set($event)"
                  placeholder="Search object name"
                  class="w-full h-7 pl-9 pr-2.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
                <app-lucide-icon name="search" [size]="12" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none flex items-center justify-center"></app-lucide-icon>
              </div>

            </div>

            <!-- Right Action Cluster (Select ▾ & Expand ▾) -->
            <div class="flex items-center gap-2 shrink-0">
              
              <!-- Select ▾ Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleToolbarDropdown('select', $event)"
                  class="h-7 px-2.5 bg-white hover:bg-slate-50 border border-slate-200 rounded text-xs font-medium text-slate-700 flex items-center gap-1.5 cursor-pointer transition-colors">
                  <span>Select</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
                </button>

                @if (activeToolbarDropdown() === 'select') {
                  <div class="absolute right-0 top-full mt-1 z-40 w-52 bg-white border border-slate-200 rounded-md p-1 flex flex-col gap-0.5">
                    <button
                      type="button"
                      (click)="onSelectVisible()"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Select visible
                    </button>
                    <button
                      type="button"
                      (click)="onSelectFiltered()"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Select filtered results
                    </button>
                    <button
                      type="button"
                      (click)="onSelectCurrentNamespace()"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Select current namespace
                    </button>
                    <button
                      type="button"
                      (click)="svc.selectAll(); activeToolbarDropdown.set(null)"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Select all discovered resources
                    </button>

                    <span class="h-[1px] bg-slate-100 my-0.5"></span>

                    <button
                      type="button"
                      (click)="onDeselectVisible()"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Deselect visible
                    </button>
                    <button
                      type="button"
                      (click)="onDeselectFiltered()"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Deselect filtered results
                    </button>
                    <button
                      type="button"
                      (click)="svc.deselectAll(); activeToolbarDropdown.set(null)"
                      class="w-full text-left px-2 py-1 text-xs text-rose-600 hover:bg-rose-50 rounded cursor-pointer">
                      Deselect all
                    </button>
                  </div>
                }
              </div>

              <!-- Expand ▾ Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleToolbarDropdown('expand', $event)"
                  class="h-7 px-2.5 bg-white hover:bg-slate-50 border border-slate-200 rounded text-xs font-medium text-slate-700 flex items-center gap-1.5 cursor-pointer transition-colors">
                  <span>Expand</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
                </button>

                @if (activeToolbarDropdown() === 'expand') {
                  <div class="absolute right-0 top-full mt-1 z-40 w-48 bg-white border border-slate-200 rounded-md p-1 flex flex-col gap-0.5">
                    <button
                      type="button"
                      (click)="onExpandVisible()"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Expand visible
                    </button>
                    <button
                      type="button"
                      (click)="svc.expandAll(); activeToolbarDropdown.set(null)"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Expand all loaded
                    </button>
                    <button
                      type="button"
                      (click)="svc.collapseAll(); activeToolbarDropdown.set(null)"
                      class="w-full text-left px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 rounded cursor-pointer">
                      Collapse all loaded
                    </button>
                  </div>
                }
              </div>

            </div>

          </div>

          <!-- 4. Provider-Aware Tree Table (Virtual/Flat Rendering, Dense DBA Columns) -->
          <div class="flex-1 bg-white border border-slate-200 rounded-md flex flex-col min-h-0 overflow-hidden">
            
            <!-- Table Header -->
            <div class="h-8 bg-slate-100 border-b border-slate-200 flex items-center text-[10px] font-bold uppercase tracking-wider text-slate-600 shrink-0 select-none">
              <div class="flex items-center gap-2 flex-1 min-w-0 px-3 h-full">
                <input
                  type="checkbox"
                  [checked]="isMasterChecked()"
                  [indeterminate]="isMasterIndeterminate()"
                  [disabled]="isLocked()"
                  (change)="toggleMasterCheckbox()"
                  aria-label="Select or deselect all resources"
                  class="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                <span>{{ hierarchyLabels().level1Label }} &amp; {{ hierarchyLabels().level2Label }} Hierarchy</span>
              </div>
              <div class="w-28 px-3 border-l border-slate-200 h-full flex items-center shrink-0">Type</div>
              <div class="w-28 px-3 text-right border-l border-slate-200 h-full flex items-center justify-end shrink-0">Rows</div>
              <div class="w-28 px-3 text-right border-l border-slate-200 h-full flex items-center justify-end shrink-0">Size</div>
              <div class="w-36 px-3 text-left border-l border-slate-200 h-full flex items-center shrink-0">Status</div>
            </div>

            <!-- Table Rows Scroll Container -->
            <div class="flex-1 overflow-y-auto divide-y divide-slate-100 min-h-0">
              @for (item of flattenedVisibleRows(); track item.node.id) {
                <div
                  class="h-8 flex items-center text-xs hover:bg-slate-50 transition-colors"
                  [class.bg-slate-50]="item.level === 0">
                  
                  <!-- Hierarchy Column with Indentation & Node Toggle -->
                  <div class="flex items-center gap-1.5 flex-1 min-w-0 px-3 h-full" [style.padding-left.px]="12 + item.level * 16">
                    
                    <!-- Chevron Expand/Collapse Toggle -->
                    @if (item.hasChildren) {
                      <button
                        type="button"
                        (click)="svc.toggleNodeExpansion(item.node.id)"
                        class="w-4 h-4 flex items-center justify-center text-slate-400 hover:text-slate-700 cursor-pointer"
                        [attr.aria-expanded]="item.isExpanded"
                        [attr.aria-label]="(item.isExpanded ? 'Collapse ' : 'Expand ') + item.node.name">
                        <app-lucide-icon [name]="item.isExpanded ? 'chevron-down' : 'chevron-right'" [size]="13"></app-lucide-icon>
                      </button>
                    } @else {
                      <span class="w-4"></span>
                    }

                    <!-- Tri-State Checkbox -->
                    <input
                      type="checkbox"
                      [checked]="item.node.isSelected"
                      [indeterminate]="item.isIndeterminate"
                      [disabled]="isLocked()"
                      (change)="svc.toggleNodeSelection(item.node.id)"
                      [attr.aria-checked]="item.isIndeterminate ? 'mixed' : item.node.isSelected"
                      [attr.aria-label]="'Select ' + item.node.name"
                      class="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer shrink-0" />

                    <!-- Node Icon -->
                    <app-lucide-icon [name]="getNodeIcon(item.node.type)" [size]="13" class="text-slate-500 shrink-0"></app-lucide-icon>

                    <!-- Node Name Label -->
                    <span class="font-medium text-slate-800 truncate" [class.font-semibold]="item.level <= 1">
                      {{ item.node.name }}
                    </span>

                    <!-- Secondary Traits Chips (Restrained, Max ~2) -->
                    @if (item.node.secondaryTraits && item.node.secondaryTraits.length > 0) {
                      <div class="flex items-center gap-1 shrink-0 ml-1">
                        @for (trait of item.node.secondaryTraits.slice(0, 2); track trait) {
                          <span class="px-1.5 py-0.2 rounded text-[10px] font-mono bg-slate-100 text-slate-600 border border-slate-200">
                            {{ trait }}
                          </span>
                        }
                      </div>
                    }

                  </div>

                  <!-- Type Column -->
                  <div class="w-28 px-3 text-slate-500 text-[11px] truncate border-l border-slate-100 h-full flex items-center shrink-0">
                    {{ item.node.typeLabel }}
                  </div>

                  <!-- Rows Column -->
                  <div
                    class="w-28 px-3 text-right font-mono text-slate-700 text-[11px] tabular-nums border-l border-slate-100 h-full flex items-center justify-end shrink-0"
                    [title]="svc.getRowCountDisplay(item.node).tooltip">
                    {{ svc.getRowCountDisplay(item.node).text }}
                  </div>

                  <!-- Size Column -->
                  <div class="w-28 px-3 text-right font-mono text-slate-700 text-[11px] tabular-nums border-l border-slate-100 h-full flex items-center justify-end shrink-0">
                    {{ (ms.wizardDraft().mode === 'M6_SCHEMA_ONLY' || !item.node.estimatedSizeBytes) ? '—' : svc.formatBytes(item.node.estimatedSizeBytes) }}
                  </div>

                  <!-- Status Column (Separating Selection from Canonical Eligibility) -->
                  <div class="w-36 px-3 flex items-center justify-between gap-1 text-[11px] border-l border-slate-100 h-full shrink-0">
                    @if (item.node.isSelected) {
                      @if (item.node.status === 'READY') {
                        <span class="text-emerald-700 font-medium flex items-center gap-1">
                          <span>&check;</span>
                          <span>Ready</span>
                        </span>
                      } @else if (item.node.status === 'ADVISORY') {
                        <span class="text-amber-700 font-medium flex items-center gap-1" [title]="item.node.statusReason || 'Advisory notice'">
                          <app-lucide-icon name="alert-triangle" [size]="12"></app-lucide-icon>
                          <span>Advisory</span>
                        </span>
                      } @else if (item.node.status === 'BLOCKED') {
                        <div class="flex items-center justify-between w-full">
                          <span class="text-rose-700 font-semibold flex items-center gap-1 truncate" [title]="item.node.statusReason || 'Blocked resource'">
                            <span>&bull;</span>
                            <span class="truncate">Blocked</span>
                          </span>
                          @if (!isLocked()) {
                            <button
                              type="button"
                              (click)="svc.skipBlockedResource(item.node.id)"
                              class="px-1.5 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded text-[10px] cursor-pointer transition-colors shrink-0"
                              title="Exclude this resource from migration scope">
                              Skip
                            </button>
                          }
                        </div>
                      }
                    } @else {
                      <div class="flex items-center justify-between w-full text-slate-400">
                        <span>Excluded</span>
                        @if (item.node.isDependencyReference && !isLocked()) {
                          <button
                            type="button"
                            (click)="svc.includeDependencyResource(item.node.id)"
                            class="px-1.5 py-0.5 bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold rounded text-[10px] cursor-pointer transition-colors shrink-0"
                            title="Include referenced dependency in scope">
                            + Include
                          </button>
                        }
                      </div>
                    }
                  </div>

                </div>
              }

              @if (flattenedVisibleRows().length === 0) {
                <div class="p-8 text-center text-slate-400 text-xs">
                  No resources match the selected filter criteria.
                </div>
              }
            </div>

          </div>

          <!-- 5. Scope Findings Line (Immediately Above Footer) -->
          <div class="h-8 px-3 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between shrink-0 text-xs select-none">
            <div class="flex items-center gap-2 min-w-0 flex-1">
              @if (isLocked()) {
                <span class="text-slate-700 font-medium flex items-center gap-1.5 min-w-0">
                  <app-lucide-icon name="lock" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span>Scope Locked &middot; {{ metrics().objectsSelected }} resources &middot; Selection frozen</span>
                  <button
                    type="button"
                    (click)="ms.unlockScope()"
                    class="ml-2 px-2 py-0.5 text-[11px] font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 rounded cursor-pointer transition-colors flex items-center gap-1"
                    title="Unlock scope to modify selections">
                    <app-lucide-icon name="unlock" [size]="11"></app-lucide-icon>
                    <span>Unlock Scope</span>
                  </button>
                </span>
              } @else if (metrics().objectsSelected === 0) {
                <span class="text-rose-600 font-medium truncate">
                  0 resources selected &mdash; select at least one migratable resource to continue.
                </span>
              } @else if (metrics().selectedBlockersCount > 0) {
                <span class="text-rose-700 font-medium flex items-center gap-1.5 min-w-0">
                  <app-lucide-icon name="alert-triangle" [size]="13" class="text-rose-600 shrink-0"></app-lucide-icon>
                  <span class="truncate">
                    {{ metrics().selectedBlockersCount }} blocked &middot;
                    {{ metrics().selectedAdvisoriesCount }} advisories &middot;
                    Exclude blocked items to continue
                  </span>
                </span>
              } @else {
                <span class="text-emerald-700 font-medium flex items-center gap-1.5 min-w-0">
                  <span class="font-bold shrink-0">&check;</span>
                  <span class="truncate">
                    {{ metrics().objectsSelected }} resources selected &middot; Scope ready
                    @if (metrics().excludedReferencedCount > 0) {
                      &middot; {{ metrics().excludedReferencedCount }} excluded dependency referenced
                    }
                  </span>
                </span>
              }
            </div>

            <div class="text-[11px] text-slate-500 font-medium shrink-0 ml-4">
              Mode: {{ getModeLabel() }}
            </div>
          </div>

        </div>
      }

      <!-- ========================================================================= -->
      <!-- OVERLAYS: CHANGE DEPTH CONFIRMATION MODAL                                 -->
      <!-- ========================================================================= -->
      @if (showChangeDepthModal()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
          (click)="showChangeDepthModal.set(false)">
          <div
            class="w-full max-w-md rounded-xl bg-white border border-slate-200 p-6 flex flex-col gap-4"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="alert-triangle" [size]="18"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900">Change discovery depth?</h3>
                <span class="text-xs text-slate-500 font-medium">Scope selection re-evaluation</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed font-normal">
              Running discovery again may change discovered resources and invalidate the current scope selection.
            </p>

            <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-200">
              <button
                type="button"
                (click)="showChangeDepthModal.set(false)"
                class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 cursor-pointer transition-colors">
                Cancel
              </button>

              <button
                type="button"
                (click)="confirmChangeDepth()"
                class="h-8 px-3.5 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-700 text-white cursor-pointer transition-colors">
                Change &amp; Rediscover
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class Step4ScopeComponent implements OnInit {
  public ms = inject(MigrationUiService);
  public svc = inject(DiscoveryScopeService);

  public ngOnInit(): void {
    if (typeof window !== 'undefined') {
      (window as any).__step4Svc = this.svc;
    }
  }

  public selectedDepthTier = signal<DiscoveryDepthTier>('STANDARD');
  public activeToolbarDropdown = signal<'level1' | 'level2' | 'type' | 'select' | 'expand' | null>(null);
  public showChangeDepthModal = signal<boolean>(false);

  // Depth card configurations
  public readonly depthCards: DiscoveryDepthCardOption[] = [
    {
      depth: 'QUICK',
      title: 'Quick',
      tag: 'Essential structure',
      description: 'Basic endpoint identity, version, and catalog/schema namespace listing.'
    },
    {
      depth: 'STANDARD',
      title: 'Standard',
      badge: 'Recommended',
      tag: 'Migration-ready detail',
      description: 'Full schema inventory, tables, views, primary keys, foreign keys, and catalog estimates.'
    },
    {
      depth: 'DEEP',
      title: 'Deep',
      tag: 'Extended metadata',
      description: 'Programmables, procedures, triggers, partitioning, LOB stats, and CDC prerequisites.'
    },
    {
      depth: 'COMPLIANCE',
      title: 'Compliance',
      tag: 'Extended inspection',
      description: 'Full deep discovery plus exact user grants, security audits, and permission analysis.'
    }
  ];

  public isLocked = computed(() => !!this.ms.wizardDraft().isScopeLocked);
  public metrics = computed<ScopeSummaryMetrics>(() => this.svc.computeSummaryMetrics());
  public hierarchyLabels = computed<HierarchyFilterLabels>(() => this.svc.getHierarchyFilterLabels());

  public currentDepthTitle = computed(() => {
    const d = this.svc.currentDepth();
    const card = this.depthCards.find(c => c.depth === d);
    return card ? card.title : 'Standard';
  });

  public currentDepthSubtitle = computed(() => {
    const d = this.svc.currentDepth();
    const card = this.depthCards.find(c => c.depth === d);
    return card ? card.tag : 'Migration-ready detail';
  });

  public sourceHostInfo = computed(() => {
    const d = this.ms.wizardDraft();
    return `${d.sourceHost || 'source-db.internal'}:${d.sourcePort || 1521}`;
  });

  public getModeLabel(): string {
    const m = this.ms.wizardDraft().mode;
    switch (m) {
      case 'M1_BULK': return 'Bulk Migration';
      case 'M2_BULK_CDC': return 'Bulk + CDC';
      case 'M3_CDC': return 'CDC Replication';
      case 'M4_INCREMENTAL': return 'Incremental Polling';
      case 'M5_STATE_SYNC': return 'State Synchronization';
      case 'M6_SCHEMA_ONLY': return 'Schema Only';
      case 'M7_DATA_ONLY': return 'Data Only';
      default: return m || 'Bulk Migration';
    }
  }

  // Flattened visible rows for table rendering
  public flattenedVisibleRows = computed<FlattenedTreeNode[]>(() => {
    const roots = this.svc.rootNodes();
    const expanded = this.svc.expandedNodeIds();
    const q = this.svc.searchQuery().trim().toLowerCase();
    const l1 = this.svc.selectedLevel1Filter();
    const l2 = this.svc.selectedLevel2Filter();
    const typeF = this.svc.selectedTypeFilter();

    const result: FlattenedTreeNode[] = [];

    const traverse = (node: DiscoveredResourceNode, level: number, isParentExpanded: boolean) => {
      // Check filters
      const matchesSearch = !q || node.name.toLowerCase().includes(q) || (node.typeLabel && node.typeLabel.toLowerCase().includes(q));
      const matchesL1 = l1 === 'ALL' || !node.database || node.database === l1 || node.name === l1;
      const matchesL2 = l2 === 'ALL' || !node.namespace || node.namespace === l2 || node.name === l2;
      const matchesType = typeF === 'ALL' || node.typeLabel === typeF || (node.children && node.children.length > 0);

      const isVisible = matchesSearch && matchesL1 && matchesL2 && matchesType;
      const hasChildren = !!(node.children && node.children.length > 0);
      const isExpanded = expanded.has(node.id);
      const isIndeterminate = this.svc.isNodeIndeterminate(node);

      if (isParentExpanded && isVisible) {
        result.push({
          node,
          level,
          isExpanded,
          isVisible: true,
          hasChildren,
          isIndeterminate
        });
      }

      if (hasChildren && node.children) {
        node.children.forEach(c => traverse(c, level + 1, isParentExpanded && isExpanded));
      }
    };

    roots.forEach(r => traverse(r, 0, true));
    return result;
  });

  public isMasterChecked = computed(() => {
    const leaves = this.svc.getMigratableLeafNodes();
    if (leaves.length === 0) return false;
    return leaves.every(l => l.isSelected);
  });

  public isMasterIndeterminate = computed(() => {
    const leaves = this.svc.getMigratableLeafNodes();
    if (leaves.length === 0) return false;
    const selected = leaves.filter(l => l.isSelected).length;
    return selected > 0 && selected < leaves.length;
  });

  @HostListener('document:click', ['$event'])
  public onDocClick(): void {
    this.activeToolbarDropdown.set(null);
  }

  public toggleToolbarDropdown(name: 'level1' | 'level2' | 'type' | 'select' | 'expand', event: MouseEvent): void {
    event.stopPropagation();
    this.activeToolbarDropdown.update(curr => (curr === name ? null : name));
  }

  public onRunDiscovery(): void {
    this.svc.startDiscovery(this.selectedDepthTier());
  }

  public promptChangeDepth(): void {
    this.showChangeDepthModal.set(true);
  }

  public confirmChangeDepth(): void {
    this.showChangeDepthModal.set(false);
    this.svc.returnToDepthSelection();
  }

  public setLevel1Filter(val: string): void {
    this.svc.selectedLevel1Filter.set(val);
    this.activeToolbarDropdown.set(null);
  }

  public setLevel2Filter(val: string): void {
    this.svc.selectedLevel2Filter.set(val);
    this.activeToolbarDropdown.set(null);
  }

  public setTypeFilter(val: string): void {
    this.svc.selectedTypeFilter.set(val);
    this.activeToolbarDropdown.set(null);
  }

  public toggleMasterCheckbox(): void {
    if (this.isLocked()) return;
    if (this.isMasterChecked()) {
      this.svc.deselectAll();
    } else {
      this.svc.selectAll();
    }
  }

  public onSelectVisible(): void {
    const ids = this.flattenedVisibleRows().map(r => r.node.id);
    this.svc.selectVisible(ids);
    this.activeToolbarDropdown.set(null);
  }

  public onDeselectVisible(): void {
    const ids = this.flattenedVisibleRows().map(r => r.node.id);
    this.svc.deselectVisible(ids);
    this.activeToolbarDropdown.set(null);
  }

  public onSelectFiltered(): void {
    const ids = this.flattenedVisibleRows().map(r => r.node.id);
    this.svc.selectVisible(ids);
    this.activeToolbarDropdown.set(null);
  }

  public onDeselectFiltered(): void {
    const ids = this.flattenedVisibleRows().map(r => r.node.id);
    this.svc.deselectVisible(ids);
    this.activeToolbarDropdown.set(null);
  }

  public onSelectCurrentNamespace(): void {
    const l2 = this.svc.selectedLevel2Filter();
    if (l2 !== 'ALL') {
      this.svc.selectNamespace(l2);
    } else {
      this.onSelectVisible();
    }
    this.activeToolbarDropdown.set(null);
  }

  public onExpandVisible(): void {
    const ids = this.flattenedVisibleRows().map(r => r.node.id);
    this.svc.expandVisible(ids);
    this.activeToolbarDropdown.set(null);
  }

  public getNodeIcon(type: string): string {
    switch (type) {
      case 'INSTANCE':
        return 'server';
      case 'DATABASE':
        return 'database';
      case 'SCHEMA':
        return 'folder';
      case 'OBJECT_GROUP':
        return 'layers';
      case 'TABLE':
        return 'table';
      case 'VIEW':
        return 'eye';
      case 'PROCEDURE':
      case 'FUNCTION':
      case 'PACKAGE':
        return 'code';
      case 'COLLECTION':
        return 'file-text';
      case 'TOPIC':
        return 'radio';
      case 'PARTITION':
        return 'split';
      case 'BUCKET':
        return 'archive';
      case 'PREFIX':
        return 'folder-tree';
      case 'OBJECT':
        return 'file';
      default:
        return 'box';
    }
  }
}
