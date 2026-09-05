import { Component, inject, signal, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MigrationHomeService } from '../../../core/services/migration-home.service';
import { MigrationHomeRow, ProjectHomeRow } from '../../../core/models/migration-home.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { StatusBadgeComponent } from '../components/status-badge.component';

interface CompactFunctionItem {
  title: string;
  icon: string;
  route: string;
}

interface StatusOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-migration-portfolio',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    LucideIconComponent,
    StatusBadgeComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-2 select-none animate-in fade-in duration-150" (click)="closeAllPopovers()">
      
      <!-- =============================================================== -->
      <!-- 1. MIGRATION HEADER & DYNAMIC OPERATIONAL SUBTEXT               -->
      <!-- =============================================================== -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">OPERATIONS</span>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Migration Operations</h1>
          <p class="text-sm font-medium text-slate-600">
            {{ mhs.dynamicHeadline() }}
          </p>
        </div>

        <div class="flex items-center gap-3 pt-1">
          <a
            routerLink="/migration/create"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/40">
            <app-lucide-icon name="plus" [size]="15"></app-lucide-icon>
            <span>Create Migration</span>
          </a>
        </div>
      </div>

      <!-- Database / State Unavailable Notice -->
      @if (mhs.isUnavailable()) {
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold">{{ mhs.errorMessage() }}</span>
          </div>
          <button
            type="button"
            (click)="mhs.loadState()"
            class="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs cursor-pointer">
            Retry Connection
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 2. STANDARDIZED INTERACTIVE CLICK-TO-FILTER KPI STRIP (4 CARDS)  -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        
        <!-- 1. Active KPI Card -->
        <div 
          (click)="toggleKpiFilter('ACTIVE', $event)"
          class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs"
          [class.border-blue-600]="selectedState() === 'ACTIVE'"
          [class.ring-1]="selectedState() === 'ACTIVE'"
          [class.ring-blue-500]="selectedState() === 'ACTIVE'"
          [class.bg-blue-50]="selectedState() === 'ACTIVE'"
          [class.bg-white]="selectedState() !== 'ACTIVE'"
          [class.border-slate-200]="selectedState() !== 'ACTIVE'"
          [class.hover:border-slate-300]="selectedState() !== 'ACTIVE'"
          [class.hover:bg-slate-50]="selectedState() !== 'ACTIVE'">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
              Active
            </span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
              {{ mhs.computedCounters().active }}
            </span>
            <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
              {{ mhs.computedCounters().active }} progressing
            </span>
          </div>
        </div>

        <!-- 2. Attention KPI Card -->
        <div 
          (click)="toggleKpiFilter('ATTENTION', $event)"
          class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs"
          [class.border-blue-600]="selectedState() === 'ATTENTION'"
          [class.ring-1]="selectedState() === 'ATTENTION'"
          [class.ring-blue-500]="selectedState() === 'ATTENTION'"
          [class.bg-blue-50]="selectedState() === 'ATTENTION'"
          [class.bg-white]="selectedState() !== 'ATTENTION'"
          [class.border-slate-200]="selectedState() !== 'ATTENTION'"
          [class.hover:border-slate-300]="selectedState() !== 'ATTENTION'"
          [class.hover:bg-slate-50]="selectedState() !== 'ATTENTION'">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
              Attention
            </span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
              {{ mhs.computedCounters().attention }}
            </span>
            <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
              {{ mhs.computedCounters().attention > 0 ? 'Actionable items' : 'All clear' }}
            </span>
          </div>
        </div>

        <!-- 3. Scheduled KPI Card -->
        <div 
          (click)="toggleKpiFilter('SCHEDULED', $event)"
          class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs"
          [class.border-blue-600]="selectedState() === 'SCHEDULED'"
          [class.ring-1]="selectedState() === 'SCHEDULED'"
          [class.ring-blue-500]="selectedState() === 'SCHEDULED'"
          [class.bg-blue-50]="selectedState() === 'SCHEDULED'"
          [class.bg-white]="selectedState() !== 'SCHEDULED'"
          [class.border-slate-200]="selectedState() !== 'SCHEDULED'"
          [class.hover:border-slate-300]="selectedState() !== 'SCHEDULED'"
          [class.hover:bg-slate-50]="selectedState() !== 'SCHEDULED'">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
              Scheduled
            </span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
              {{ mhs.computedCounters().scheduled }}
            </span>
            <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
              Maintenance window
            </span>
          </div>
        </div>

        <!-- 4. Completed KPI Card -->
        <div 
          (click)="toggleKpiFilter('COMPLETED', $event)"
          class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs"
          [class.border-blue-600]="selectedState() === 'COMPLETED'"
          [class.ring-1]="selectedState() === 'COMPLETED'"
          [class.ring-blue-500]="selectedState() === 'COMPLETED'"
          [class.bg-blue-50]="selectedState() === 'COMPLETED'"
          [class.bg-white]="selectedState() !== 'COMPLETED'"
          [class.border-slate-200]="selectedState() !== 'COMPLETED'"
          [class.hover:border-slate-300]="selectedState() !== 'COMPLETED'"
          [class.hover:bg-slate-50]="selectedState() !== 'COMPLETED'">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
              Completed
            </span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
              {{ mhs.computedCounters().completed }}
            </span>
            <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
              100% verified
            </span>
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 3. COMPACT FUNCTION STRIP (5 HORIZONTAL UTILITY TILES)          -->
      <!-- =============================================================== -->
      <div class="flex flex-col gap-2.5">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">CORE MIGRATION FUNCTIONS</span>

        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          @for (func of compactFunctions; track func.title) {
            <div
              (click)="navigateTo(func.route)"
              class="h-14 flex items-center justify-between px-3.5 bg-white border border-slate-200 rounded-lg hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group shadow-2xs">
              
              <div class="flex items-center gap-2.5 min-w-0">
                <app-lucide-icon [name]="func.icon" [size]="16" class="text-slate-600 group-hover:text-blue-600 transition-colors shrink-0"></app-lucide-icon>
                <span class="text-xs font-semibold text-slate-800 group-hover:text-blue-600 transition-colors truncate">
                  {{ func.title }}
                </span>
              </div>

              <app-lucide-icon name="arrow-right" [size]="14" class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all shrink-0"></app-lucide-icon>
            </div>
          }
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- 4. FLEET TABLE & TELEMETRY (INDEPENDENT MIGRATIONS)             -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        
        <!-- Complete Operational Toolbar (Header, Search, GDS Filter Dropdown, View All) -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-3">
          
          <!-- Left: Title & Count Badge -->
          <div class="flex items-center gap-2.5">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Independent Migrations</span>
            <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              {{ filteredMigrations().length }}
            </span>
          </div>

          <!-- Right: Search Input + GDS Filter Dropdown + Secondary View All Link -->
          <div class="flex items-center gap-2.5 flex-wrap">
            
            <!-- Search Input with Pure Inline Style Overlay -->
            <div class="search-box-wrapper" style="position: relative; display: flex; align-items: center; width: 256px;">
              <!-- Icon absolutely positioned with z-index, never inline in text flow -->
              <app-lucide-icon 
                name="search" 
                [size]="14"
                style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: #94a3b8; pointer-events: none; z-index: 2;"
              ></app-lucide-icon>
              
              <!-- Input with explicit padding-left: 36px !important -->
              <input
                type="text"
                [ngModel]="searchQuery()"
                (ngModelChange)="searchQuery.set($event)"
                placeholder="Search migrations..."
                style="width: 100%; height: 32px; padding-left: 36px !important; padding-right: 28px; font-size: 12px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; outline: none; color: #0f172a;"
              />
              @if (searchQuery()) {
                <button 
                  type="button" 
                  (click)="searchQuery.set('')" 
                  style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: #94a3b8; font-size: 14px; font-weight: bold; cursor: pointer; z-index: 2;">
                  &times;
                </button>
              }
            </div>

            <!-- GDS Option A "All States" Dropdown Popover -->
            <div class="relative" (click)="$event.stopPropagation()">
              <button
                type="button"
                (click)="toggleStatusDropdown($event)"
                class="h-8 px-2.5 text-xs text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 flex items-center justify-between gap-2 cursor-pointer select-none transition-colors"
                [class.bg-blue-50]="isStatusDropdownOpen()"
                [class.border-blue-300]="isStatusDropdownOpen()">
                <span>{{ selectedStatusFilterLabel() }}</span>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0"></app-lucide-icon>
              </button>

              @if (isStatusDropdownOpen()) {
                <div 
                  class="absolute right-0 mt-1.5 origin-top-right w-44 rounded-xl bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                  @for (opt of statusOptions; track opt.value) {
                    <button
                      type="button"
                      (click)="selectStatusFilter(opt.value)"
                      class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                      [class.bg-blue-50]="selectedState() === opt.value"
                      [class.text-blue-700]="selectedState() === opt.value">
                      <span>{{ opt.label }}</span>
                      @if (selectedState() === opt.value) {
                        <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                      }
                    </button>
                  }
                </div>
              }
            </div>

            <!-- Secondary View All Link -->
            <a routerLink="/migration/projects" class="h-8 px-3 rounded-md bg-white hover:bg-slate-50 text-slate-700 hover:text-blue-700 border border-slate-200 text-xs font-semibold transition-all inline-flex items-center gap-1.5 group/btn cursor-pointer">
              <span>View all</span>
              <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
            </a>

          </div>

        </div>

        <!-- Active Filter Indicator Banner if State or Search Active -->
        @if (selectedState() !== 'ALL') {
          <div class="flex items-center justify-between p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-xs text-blue-800">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="filter" [size]="13" class="text-blue-600"></app-lucide-icon>
              <span>Filtering by: <strong>{{ selectedStatusFilterLabel() }}</strong> ({{ filteredMigrations().length }} matches)</span>
            </div>
            <button 
              type="button" 
              (click)="selectedState.set('ALL'); $event.stopPropagation()"
              class="text-blue-700 hover:text-blue-900 font-bold px-2 py-0.5 rounded hover:bg-blue-100 cursor-pointer">
              &times; Clear Filter
            </button>
          </div>
        }

        @if (filteredMigrations().length === 0) {
          <div class="py-12 flex flex-col items-center justify-center text-center gap-2">
            <app-lucide-icon name="database" [size]="28" class="text-slate-300"></app-lucide-icon>
            <span class="text-xs font-semibold text-slate-700">No migrations match your search or filter</span>
            <p class="text-xs text-slate-500 font-normal">
              {{ (selectedState() !== 'ALL' || searchQuery()) ? 'Try adjusting your search keywords or resetting the state filter.' : 'Create an independent migration to run outside project groups.' }}
            </p>
            @if (selectedState() !== 'ALL' || searchQuery()) {
              <button 
                type="button" 
                (click)="clearAllFilters()" 
                class="mt-2 h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer shadow-2xs">
                Reset All Filters
              </button>
            }
          </div>
        } @else {
          <!-- High-Precision Data Table with Zebra Rows -->
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse table-fixed">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-2.5 px-4 w-[28%]">Migration</th>
                  <th class="py-2.5 px-4 w-[20%]">Route</th>
                  <th class="py-2.5 px-4 w-[16%]">Mode</th>
                  <th class="py-2.5 px-4 w-[18%]">Current Phase</th>
                  <th class="py-2.5 px-4 w-[14%]">State</th>
                  <th class="py-2.5 px-3 w-[4%] text-right"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-200 text-xs">
                @for (m of filteredMigrations(); track m.id; let i = $index) {
                  <tr 
                    (click)="navigateToMigration(m.id)"
                    class="hover:bg-blue-50 even:bg-slate-50 transition-colors cursor-pointer group h-14 select-none">
                    
                    <!-- 1. Migration Name & Stage Milestone Subtitle -->
                    <td class="py-2.5 px-4 min-w-0">
                      <div class="flex flex-col min-w-0">
                        <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors truncate text-xs">
                          {{ m.name }}
                        </span>
                        <span class="text-[11px] text-slate-500 font-normal truncate mt-0.5">
                          {{ m.current_stage || 'Ready' }}
                        </span>
                      </div>
                    </td>

                    <!-- 2. Route (Source -> Target) -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <div class="flex items-center gap-1.5 text-xs text-slate-700 font-medium">
                        <span class="font-semibold text-slate-800 truncate">{{ m.source_provider }}</span>
                        <span class="text-slate-400 font-normal shrink-0">&rarr;</span>
                        <span class="font-semibold text-slate-800 truncate">{{ m.target_provider }}</span>
                      </div>
                    </td>

                    <!-- 3. Canonical Mode Identifier -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <app-status-badge [mode]="m.mode"></app-status-badge>
                    </td>

                    <!-- 4. Current Phase (Coarse Milestone text) -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <span class="text-xs text-slate-600 font-medium truncate block">
                        {{ m.current_stage || 'Initialization' }}
                      </span>
                    </td>

                    <!-- 5. State (Title Case with dot) -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <app-status-badge [lifecycle]="m.lifecycle_state"></app-status-badge>
                    </td>

                    <!-- 6. Actions (··· Context Menu with dynamic upward flip) -->
                    <td class="py-2.5 px-3 text-right whitespace-nowrap" (click)="$event.stopPropagation()">
                      <div class="relative inline-block">
                        <button
                          type="button"
                          (click)="toggleActionMenu(m.id, $event)"
                          class="w-7 h-7 flex items-center justify-center rounded border border-transparent text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer focus:outline-none focus-visible:outline-none focus:ring-0"
                          [class.bg-slate-100]="activeActionMenuId() === m.id"
                          [class.text-slate-700]="activeActionMenuId() === m.id"
                          [class.border-slate-200]="activeActionMenuId() === m.id"
                          title="More actions">
                          <app-lucide-icon name="more-horizontal" [size]="15"></app-lucide-icon>
                        </button>

                        <!-- Context Menu Dropdown Popover (Dynamic upward flip on bottom 2 rows) -->
                        @if (activeActionMenuId() === m.id) {
                          <div 
                            (click)="$event.stopPropagation()"
                            class="absolute right-0 w-52 rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-0.5 z-50 text-left animate-in fade-in zoom-in-95 duration-100"
                            [ngClass]="(i >= filteredMigrations().length - 2 && filteredMigrations().length > 2)
                              ? 'bottom-full mb-1 origin-bottom-right' 
                              : 'top-full mt-1 origin-top-right'">
                            
                            <button
                              type="button"
                              (click)="launchMissionControl(m.id)"
                              class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer">
                              <app-lucide-icon name="play" [size]="13" class="text-blue-600"></app-lucide-icon>
                              <span>Launch Cockpit</span>
                            </button>

                            @if ((m.lifecycle_state || '').toUpperCase() === 'ACTIVE' || (m.lifecycle_state || '').toUpperCase() === 'RUNNING') {
                              <button
                                type="button"
                                (click)="promptPauseMigration(m)"
                                class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-amber-700 hover:bg-amber-50 transition-colors flex items-center gap-2 cursor-pointer">
                                <app-lucide-icon name="pause" [size]="13" class="text-amber-600"></app-lucide-icon>
                                <span>Pause Migration</span>
                              </button>
                            } @else if ((m.lifecycle_state || '').toUpperCase() === 'PAUSED') {
                              <button
                                type="button"
                                (click)="resumeMigration(m)"
                                class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-emerald-700 hover:bg-emerald-50 transition-colors flex items-center gap-2 cursor-pointer">
                                <app-lucide-icon name="play" [size]="13" class="text-emerald-600"></app-lucide-icon>
                                <span>Resume Migration</span>
                              </button>
                            }

                            <button
                              type="button"
                              (click)="cloneConfiguration(m)"
                              class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer">
                              <app-lucide-icon name="copy" [size]="13" class="text-slate-500"></app-lucide-icon>
                              <span>Clone Configuration</span>
                            </button>

                            <button
                              type="button"
                              (click)="openAssignProjectDialog(m)"
                              class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer">
                              <app-lucide-icon name="folder-plus" [size]="13" class="text-slate-500"></app-lucide-icon>
                              <span>Assign to Project</span>
                            </button>

                            <div class="border-t border-slate-200 my-0.5 mx-1"></div>

                            <button
                              type="button"
                              (click)="exportDossier(m)"
                              class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer">
                              <app-lucide-icon name="file-down" [size]="13" class="text-slate-500"></app-lucide-icon>
                              <span>Export Evidence Dossier</span>
                            </button>
                          </div>
                        }
                      </div>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>
        }

      </div>

      <!-- =============================================================== -->
      <!-- 5. PROJECTS & INITIATIVES (SYMMETRICAL EQUAL HEIGHT CARDS)      -->
      <!-- =============================================================== -->
      <div class="flex flex-col gap-3.5">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <span class="text-xs font-bold text-slate-600 uppercase tracking-wider">PROJECTS &amp; INITIATIVES</span>
          <a routerLink="/migration/projects" class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-200 text-xs font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 group/btn cursor-pointer">
            <span>View all</span>
            <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
          </a>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
          @for (proj of mhs.projects(); track proj.id) {
            <div 
              (click)="navigateTo('/migration/projects/' + proj.id)"
              class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between h-full cursor-pointer hover:border-slate-300 transition-all select-none group">
              
              <!-- Top Section: Header + Uniform Title + Counts -->
              <div class="flex flex-col gap-3">
                
                <!-- Environment Tag & Canonical Dot Badge -->
                <div class="flex items-center justify-between">
                  <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">{{ proj.environment }}</span>
                  
                  @if (proj.health === 'HEALTHY') {
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 select-none">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                      <span>Healthy</span>
                    </span>
                  } @else {
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 select-none">
                      <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                      <span>Attention</span>
                    </span>
                  }
                </div>

                <!-- Uniform Typography for all titles -->
                <h3 class="text-sm font-semibold text-slate-900 group-hover:text-blue-600 transition-colors leading-snug cursor-pointer">
                  {{ proj.name }}
                </h3>

                <!-- Subtext Counts -->
                <div class="flex items-center gap-2 text-xs text-slate-600 font-medium">
                  <span>{{ proj.migration_count }} migrations</span>
                  <span>&bull;</span>
                  <span>
                    {{ proj.active_count }} active
                    {{ proj.attention_count > 0 ? ('· ' + proj.attention_count + ' attention') : '· All clear' }}
                  </span>
                </div>

              </div>

              <!-- Bottom Section: Progress Bar + Target Date + Anchored Warning Notice -->
              <div class="flex flex-col gap-3 mt-4">
                
                <!-- Sleek Delivery Progress Bar -->
                <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    class="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                    [style.width.%]="proj.delivery_percent">
                  </div>
                </div>

                <!-- Dynamic Remaining Time in Monospace -->
                <div class="flex items-center justify-between text-xs font-mono">
                  <span class="font-bold text-slate-900 tabular-nums">
                    {{ mhs.formatProjectRemainingTime(proj.target_date).primary }}
                  </span>
                  <span class="text-slate-500 font-medium tabular-nums">
                    {{ mhs.formatProjectRemainingTime(proj.target_date).secondary }}
                  </span>
                </div>

                <!-- Bottom Warning Container with guaranteed min-height for strict baseline alignment across all cards -->
                <div class="min-h-[34px] flex items-center">
                  @if (proj.attention_count > 0) {
                    <div class="w-full p-2 rounded-lg bg-amber-50 text-amber-800 text-xs font-semibold flex items-center gap-1.5 border border-amber-200">
                      <app-lucide-icon name="alert-circle" [size]="13" class="text-amber-600 shrink-0"></app-lucide-icon>
                      <span>{{ proj.attention_count }} item{{ proj.attention_count === 1 ? '' : 's' }} need attention</span>
                    </div>
                  }
                </div>

              </div>

            </div>
          }
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- 6. RECENT ACTIVITY — DEDICATED AUDIT TRAIL CARD                 -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="activity" [size]="16" class="text-blue-600"></app-lucide-icon>
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Recent Activity</span>
          </div>
          <a routerLink="/migration/history" class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-200 text-xs font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 group/btn cursor-pointer">
            <span>View all history</span>
            <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
          </a>
        </div>

        @if (mhs.activities().length === 0) {
          <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
            <span class="text-xs font-medium">No migration activity recorded yet.</span>
          </div>
        } @else {
          <div class="flex flex-col divide-y divide-slate-200 font-normal">
            @for (act of mhs.activities(); track act.id) {
              <div class="py-3.5 first:pt-0 last:pb-0 flex items-center justify-between gap-4 text-xs">
                
                <div class="flex items-center gap-3.5 min-w-0">
                  <!-- Severity Indicator Dot -->
                  <div
                    class="w-2 h-2 rounded-full shrink-0"
                    [class.bg-emerald-500]="act.severity === 'SUCCESS'"
                    [class.bg-amber-500]="act.severity === 'WARNING'"
                    [class.bg-blue-500]="act.severity === 'INFO'"
                    [class.bg-rose-500]="act.severity === 'ERROR'">
                  </div>

                  <!-- Relative and Exact Time in Tabular Monospace -->
                  <div class="flex flex-col shrink-0 w-24">
                    <span class="font-bold text-slate-900 text-xs">
                      {{ mhs.formatRelativeTime(act.occurred_at).relative }}
                    </span>
                    <span class="text-[11px] text-slate-500 font-mono font-medium tabular-nums">
                      {{ mhs.formatRelativeTime(act.occurred_at).exactTime }}
                    </span>
                  </div>

                  <!-- Activity Title & Subject Name -->
                  <div class="flex flex-col min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="font-bold text-slate-900">{{ act.title }}</span>
                      <span class="text-slate-300">&bull;</span>
                      <span class="font-semibold text-blue-700 truncate">{{ act.subject_name }}</span>
                    </div>
                    <span class="text-xs text-slate-600 truncate font-normal">{{ act.status_text }}</span>
                  </div>
                </div>

                <!-- Action Button -->
                <div class="shrink-0">
                  <a
                    [routerLink]="getActivityRoute(act)"
                    class="h-7 px-3 rounded-lg border text-xs font-semibold transition-all inline-flex items-center gap-1.5 shadow-2xs group/btn cursor-pointer"
                    [ngClass]="act.action_type === 'REVIEW' 
                      ? 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100 hover:border-amber-300' 
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200'">
                    <span>{{ act.action_type === 'REVIEW' ? 'Review' : 'View' }}</span>
                    <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
                  </a>
                </div>

              </div>
            }
          </div>
        }

      </div>

      <!-- =============================================================== -->
      <!-- 7. CONFIRMATION GUARDRAIL MODAL (FOR DISRUPTIVE ACTIONS ONLY)   -->
      <!-- =============================================================== -->
      @if (confirmModal(); as modal) {
        <div 
          (click)="confirmModal.set(null)"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div 
            (click)="$event.stopPropagation()"
            class="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-2xl p-6 flex flex-col gap-4">
            
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="alert-triangle" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-base font-bold text-slate-900 font-heading">{{ modal.title }}</h3>
                <span class="text-xs text-slate-500 font-medium">Operation Guardrail</span>
              </div>
            </div>

            <p class="text-xs text-slate-700 font-medium leading-relaxed">
              {{ modal.message }}
            </p>

            <div class="pt-3 border-t border-slate-200 flex justify-end gap-2.5">
              <button
                type="button"
                (click)="confirmModal.set(null)"
                class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="modal.onConfirm(); confirmModal.set(null)"
                class="h-8 px-3.5 text-xs font-semibold rounded-md bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white shadow-2xs transition-colors cursor-pointer">
                {{ modal.actionLabel }}
              </button>
            </div>

          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 8. ASSIGN TO PROJECT DIALOG                                     -->
      <!-- =============================================================== -->
      @if (assignProjectModal(); as modal) {
        <div 
          (click)="assignProjectModal.set(null)"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div 
            (click)="$event.stopPropagation()"
            class="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-2xl p-6 flex flex-col gap-4">
            
            <div class="flex items-center justify-between pb-3 border-b border-slate-200">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon name="folder-plus" [size]="18" class="text-blue-600"></app-lucide-icon>
                <h3 class="text-base font-bold text-slate-900 font-heading">Assign to Initiative</h3>
              </div>
              <button type="button" (click)="assignProjectModal.set(null)" class="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 cursor-pointer">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <p class="text-xs text-slate-600 font-medium">
              Select an active project initiative to attach <strong>{{ modal.migration?.name }}</strong>:
            </p>

            <div class="flex flex-col gap-1 max-h-56 overflow-y-auto">
              @for (proj of mhs.projects(); track proj.id) {
                <button
                  type="button"
                  (click)="assignToProject(modal.migration, proj)"
                  class="w-full text-left px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-700 hover:text-blue-700 hover:bg-blue-50 border border-slate-200 transition-colors flex items-center justify-between cursor-pointer">
                  <div class="flex flex-col">
                    <span>{{ proj.name }}</span>
                    <span class="text-[11px] text-slate-500 font-normal">{{ proj.environment }} &bull; {{ proj.migration_count }} migrations</span>
                  </div>
                  <app-lucide-icon name="arrow-right" [size]="14" class="text-slate-400"></app-lucide-icon>
                </button>
              }
            </div>

            <div class="pt-2 border-t border-slate-200 flex justify-end">
              <button
                type="button"
                (click)="assignProjectModal.set(null)"
                class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer">
                Cancel
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class MigrationPortfolioComponent {
  public mhs = inject(MigrationHomeService);
  private router = inject(Router);

  // Unified State Signals for Search & Filter
  public searchQuery = signal<string>('');
  public selectedState = signal<string>('ALL');
  public isStatusDropdownOpen = signal<boolean>(false);

  // Status Filter Options for GDS Dropdown
  public statusOptions: StatusOption[] = [
    { label: 'All States', value: 'ALL' },
    { label: 'Active / Running', value: 'ACTIVE' },
    { label: 'Attention Required', value: 'ATTENTION' },
    { label: 'Scheduled', value: 'SCHEDULED' },
    { label: 'Completed', value: 'COMPLETED' },
    { label: 'Paused', value: 'PAUSED' }
  ];

  // Context menu popover state
  public activeActionMenuId = signal<string | null>(null);

  // Guardrail Modals
  public confirmModal = signal<{
    isOpen: boolean;
    title: string;
    message: string;
    actionLabel: string;
    onConfirm: () => void;
  } | null>(null);

  public assignProjectModal = signal<{
    isOpen: boolean;
    migration: MigrationHomeRow | null;
  } | null>(null);

  // Compact 5 Function Tiles with explicit registered icons
  public compactFunctions: CompactFunctionItem[] = [
    { title: 'Projects & Initiatives', icon: 'folder-kanban', route: '/migration/projects' },
    { title: 'Active Connections', icon: 'database', route: '/migration/connections' },
    { title: 'Validation Studio', icon: 'shield-check', route: '/migration/validation' },
    { title: 'Template Catalog', icon: 'file-code-2', route: '/migration/templates' },
    { title: 'History & Evidence', icon: 'history', route: '/migration/history' }
  ];

  // Fully Functional Unified Filtered Migrations computed signal
  public filteredMigrations = computed(() => {
    const list = this.mhs.migrations().filter(m => !m.project_id);
    const query = this.searchQuery().trim().toLowerCase();
    const state = this.selectedState();

    return list.filter(item => {
      const matchesSearch = !query || 
        (item.name || '').toLowerCase().includes(query) || 
        (item.source_provider || '').toLowerCase().includes(query) ||
        (item.target_provider || '').toLowerCase().includes(query) ||
        (`${item.source_provider} -> ${item.target_provider}`).toLowerCase().includes(query) ||
        (`${item.source_provider} → ${item.target_provider}`).toLowerCase().includes(query) ||
        (item.current_stage || '').toLowerCase().includes(query) ||
        (item.mode || '').toLowerCase().includes(query);

      let matchesState = true;
      if (state === 'ACTIVE') {
        matchesState = item.lifecycle_state === 'ACTIVE' || item.lifecycle_state === 'RUNNING';
      } else if (state === 'ATTENTION') {
        matchesState = item.lifecycle_state === 'ATTENTION' || !!item.attention_level;
      } else if (state === 'SCHEDULED') {
        matchesState = item.lifecycle_state === 'SCHEDULED' || item.lifecycle_state === 'INITIALIZED';
      } else if (state === 'COMPLETED') {
        matchesState = item.lifecycle_state === 'COMPLETED';
      } else if (state === 'PAUSED') {
        matchesState = item.lifecycle_state === 'PAUSED';
      }

      return matchesSearch && matchesState;
    });
  });

  public selectedStatusFilterLabel(): string {
    const opt = this.statusOptions.find(o => o.value === this.selectedState());
    return opt ? opt.label : 'All States';
  }

  @HostListener('document:click', ['$event'])
  public handleDocumentClick(): void {
    this.closeAllPopovers();
  }

  @HostListener('window:keydown', ['$event'])
  public handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.closeAllPopovers();
      this.confirmModal.set(null);
      this.assignProjectModal.set(null);
    }
  }

  public closeAllPopovers(): void {
    this.activeActionMenuId.set(null);
    this.isStatusDropdownOpen.set(false);
  }

  public toggleStatusDropdown(event?: MouseEvent): void {
    event?.stopPropagation();
    this.isStatusDropdownOpen.update(v => !v);
  }

  public selectStatusFilter(val: string): void {
    this.selectedState.set(val);
    this.isStatusDropdownOpen.set(false);
  }

  public clearAllFilters(): void {
    this.searchQuery.set('');
    this.selectedState.set('ALL');
  }

  public toggleKpiFilter(filter: 'ACTIVE' | 'ATTENTION' | 'SCHEDULED' | 'COMPLETED', event?: MouseEvent): void {
    event?.stopPropagation();
    if (this.selectedState() === filter) {
      this.selectedState.set('ALL');
    } else {
      this.selectedState.set(filter);
    }
  }

  public toggleActionMenu(id: string, event?: MouseEvent): void {
    event?.stopPropagation();
    if (this.activeActionMenuId() === id) {
      this.activeActionMenuId.set(null);
    } else {
      this.activeActionMenuId.set(id);
    }
  }

  public navigateTo(route: string): void {
    this.router.navigate([route]);
  }

  public navigateToMigration(id: string): void {
    this.router.navigate(['/migration', id]);
  }

  public launchMissionControl(id: string): void {
    this.activeActionMenuId.set(null);
    this.navigateToMigration(id);
  }

  public promptPauseMigration(m: MigrationHomeRow): void {
    this.activeActionMenuId.set(null);
    this.confirmModal.set({
      isOpen: true,
      title: 'Pause Migration Execution?',
      message: `Pausing "${m.name}" will safely checkpoint replication streams and pause engine workers. CDC replication can be resumed at any time without data loss.`,
      actionLabel: 'Pause Migration',
      onConfirm: () => {
        m.lifecycle_state = 'PAUSED';
        m.current_stage = 'Paused by Operator';
      }
    });
  }

  public resumeMigration(m: MigrationHomeRow): void {
    this.activeActionMenuId.set(null);
    m.lifecycle_state = 'ACTIVE';
    m.current_stage = 'Resuming Replication...';
  }

  public cloneConfiguration(m: MigrationHomeRow): void {
    this.activeActionMenuId.set(null);
    this.router.navigate(['/migration/create'], { queryParams: { cloneFrom: m.id } });
  }

  public openAssignProjectDialog(m: MigrationHomeRow): void {
    this.activeActionMenuId.set(null);
    this.assignProjectModal.set({
      isOpen: true,
      migration: m
    });
  }

  public assignToProject(m: MigrationHomeRow | null, project: ProjectHomeRow): void {
    if (m) {
      m.project_id = project.id;
      project.migration_count += 1;
    }
    this.assignProjectModal.set(null);
  }

  public exportDossier(m: MigrationHomeRow): void {
    this.activeActionMenuId.set(null);
    const payload = JSON.stringify(m, null, 2);
    const blob = new Blob([payload], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `migration-evidence-${m.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  public getActivityRoute(act: any): string[] {
    if (act.subject_type === 'migration') {
      return ['/migration', act.subject_id];
    }
    if (act.subject_type === 'validation') {
      return ['/migration/validation', act.subject_id];
    }
    if (act.subject_type === 'project') {
      return ['/migration/projects', act.subject_id];
    }
    return ['/migration/history'];
  }
}
