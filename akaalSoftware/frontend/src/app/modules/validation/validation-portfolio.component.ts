import { Component, inject, signal, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ValidationHomeService } from '../../core/services/validation-home.service';
import { ValidationItemRow, ValidationAttentionItem, ValidationUpcomingRow, ValidationRecentResultRow, ValidationActivityRow } from '../../core/models/validation-home.models';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';
import { StatusBadgeComponent } from '../migration/components/status-badge.component';

interface FilterOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-validation-portfolio',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    LucideIconComponent,
    StatusBadgeComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" (click)="closeAllPopovers()">
      
      <!-- =============================================================== -->
      <!-- 1. HEADER                                                       -->
      <!-- =============================================================== -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">VALIDATION</span>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Validation Studio</h1>
          <p class="text-sm font-medium text-slate-600">
            Verify source and target data, investigate discrepancies, and review validation results.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-1">
          <a
            routerLink="/migration/validation/new"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/40">
            <app-lucide-icon name="plus" [size]="15"></app-lucide-icon>
            <span>Create Validation</span>
          </a>
        </div>
      </div>

      <!-- Database / State Unavailable Notice -->
      @if (vs.isUnavailable()) {
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold">{{ vs.errorMessage() }}</span>
          </div>
          <button
            type="button"
            (click)="vs.loadState()"
            class="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs cursor-pointer">
            Retry Connection
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 2. FOUR KPI QUICK FILTERS                                        -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        
        <!-- 1. Active KPI Card -->
        <div 
          (click)="toggleKpiFilter('ACTIVE', $event)"
          class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs"
          [class.border-blue-600]="vs.kpiFilter() === 'ACTIVE'"
          [class.ring-1]="vs.kpiFilter() === 'ACTIVE'"
          [class.ring-blue-500]="vs.kpiFilter() === 'ACTIVE'"
          [class.bg-blue-50]="vs.kpiFilter() === 'ACTIVE'"
          [class.bg-white]="vs.kpiFilter() !== 'ACTIVE'"
          [class.border-slate-200]="vs.kpiFilter() !== 'ACTIVE'"
          [class.hover:border-slate-300]="vs.kpiFilter() !== 'ACTIVE'"
          [class.hover:bg-slate-50]="vs.kpiFilter() !== 'ACTIVE'">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
              Active
            </span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
              {{ vs.computedCounters().active }}
            </span>
            <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
              {{ vs.computedCounters().active }} progressing
            </span>
          </div>
        </div>

        <!-- 2. Needs Attention KPI Card -->
        <div 
          (click)="toggleKpiFilter('ATTENTION', $event)"
          class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs"
          [class.border-blue-600]="vs.kpiFilter() === 'ATTENTION'"
          [class.ring-1]="vs.kpiFilter() === 'ATTENTION'"
          [class.ring-blue-500]="vs.kpiFilter() === 'ATTENTION'"
          [class.bg-blue-50]="vs.kpiFilter() === 'ATTENTION'"
          [class.bg-white]="vs.kpiFilter() !== 'ATTENTION'"
          [class.border-slate-200]="vs.kpiFilter() !== 'ATTENTION'"
          [class.hover:border-slate-300]="vs.kpiFilter() !== 'ATTENTION'"
          [class.hover:bg-slate-50]="vs.kpiFilter() !== 'ATTENTION'">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
              Needs Attention
            </span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
              {{ vs.computedCounters().attention }}
            </span>
            <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
              {{ vs.computedCounters().attention > 0 ? 'Actionable items' : 'All clear' }}
            </span>
          </div>
        </div>

        <!-- 3. Scheduled KPI Card -->
        <div 
          (click)="toggleKpiFilter('SCHEDULED', $event)"
          class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs"
          [class.border-blue-600]="vs.kpiFilter() === 'SCHEDULED'"
          [class.ring-1]="vs.kpiFilter() === 'SCHEDULED'"
          [class.ring-blue-500]="vs.kpiFilter() === 'SCHEDULED'"
          [class.bg-blue-50]="vs.kpiFilter() === 'SCHEDULED'"
          [class.bg-white]="vs.kpiFilter() !== 'SCHEDULED'"
          [class.border-slate-200]="vs.kpiFilter() !== 'SCHEDULED'"
          [class.hover:border-slate-300]="vs.kpiFilter() !== 'SCHEDULED'"
          [class.hover:bg-slate-50]="vs.kpiFilter() !== 'SCHEDULED'">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
              Scheduled
            </span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
              {{ vs.computedCounters().scheduled }}
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
          [class.border-blue-600]="vs.kpiFilter() === 'COMPLETED'"
          [class.ring-1]="vs.kpiFilter() === 'COMPLETED'"
          [class.ring-blue-500]="vs.kpiFilter() === 'COMPLETED'"
          [class.bg-blue-50]="vs.kpiFilter() === 'COMPLETED'"
          [class.bg-white]="vs.kpiFilter() !== 'COMPLETED'"
          [class.border-slate-200]="vs.kpiFilter() !== 'COMPLETED'"
          [class.hover:border-slate-300]="vs.kpiFilter() !== 'COMPLETED'"
          [class.hover:bg-slate-50]="vs.kpiFilter() !== 'COMPLETED'">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
              Completed
            </span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
              {{ vs.computedCounters().completed }}
            </span>
            <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
              Verified
            </span>
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 3. ACTIVE VALIDATIONS (8fr) + NEEDS ATTENTION (4fr)             -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-12 gap-6 items-stretch">
        
        <!-- Left: Active Validations (8fr) -->
        <div class="col-span-12 lg:col-span-8 flex flex-col">
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4 flex-1">
            <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="activity" [size]="16" class="text-blue-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Active Validations</span>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  {{ vs.activeValidations().length }}
                </span>
              </div>
            </div>

            @if (vs.activeValidations().length === 0) {
              <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
                <app-lucide-icon name="check-circle" [size]="24" class="text-slate-300"></app-lucide-icon>
                <span class="text-xs font-medium">No validations currently running.</span>
              </div>
            } @else {
              <div class="flex flex-col divide-y divide-slate-200">
                @for (item of vs.activeValidations(); track item.id) {
                  <div class="py-4 first:pt-0 last:pb-0 flex flex-col gap-3">
                    <div class="flex items-center justify-between gap-4 flex-wrap">
                      <div class="flex flex-col min-w-0">
                        <a [routerLink]="['/migration/validation', item.id]" class="text-sm font-semibold text-slate-900 hover:text-blue-600 transition-colors cursor-pointer truncate">
                          {{ item.name }}
                        </a>
                        <div class="flex items-center gap-2 text-xs text-slate-600 mt-0.5">
                          <span class="font-medium text-slate-800">{{ item.source_provider }}</span>
                          <span class="text-slate-400">&rarr;</span>
                          <span class="font-medium text-slate-800">{{ item.target_provider }}</span>
                          <span class="text-slate-300">&bull;</span>
                          <app-status-badge [strategy]="item.strategy"></app-status-badge>
                        </div>
                      </div>

                      <div class="flex items-center gap-3">
                        <app-status-badge [lifecycle]="item.state"></app-status-badge>
                        <a
                          [routerLink]="['/migration/validation', item.id]"
                          class="h-8 px-3 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold inline-flex items-center gap-1.5 transition-colors cursor-pointer">
                          <span>Open</span>
                          <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
                        </a>
                      </div>
                    </div>

                    @if (item.progress_percent !== undefined) {
                      <div class="flex flex-col gap-1.5">
                        <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div class="bg-blue-600 h-1.5 rounded-full transition-all duration-300" [style.width.%]="item.progress_percent"></div>
                        </div>
                        <div class="flex items-center justify-between text-[11px] font-mono text-slate-500">
                          <span>{{ item.progress_percent }}% complete</span>
                          @if (item.elapsed_time) {
                            <span>Elapsed: {{ item.elapsed_time }}</span>
                          }
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            }
          </div>
        </div>

        <!-- Right: Needs Attention (4fr) -->
        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4 flex-1">
            <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Needs Attention</span>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                  {{ vs.attentionItems().length }}
                </span>
              </div>
            </div>

            @if (vs.attentionItems().length === 0) {
              <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
                <app-lucide-icon name="shield-check" [size]="24" class="text-emerald-500"></app-lucide-icon>
                <span class="text-xs font-medium text-slate-700">All clear</span>
                <p class="text-[11px] text-slate-500">No actionable validation discrepancies detected.</p>
              </div>
            } @else {
              <div class="flex flex-col divide-y divide-slate-200">
                @for (attn of vs.attentionItems(); track attn.id) {
                  <div class="py-3.5 first:pt-0 last:pb-0 flex flex-col gap-2">
                    <div class="flex items-start justify-between gap-2">
                      <div class="flex flex-col min-w-0">
                        <span class="text-xs font-bold text-slate-900 truncate">{{ attn.title }}</span>
                        <span class="text-[11px] font-medium text-slate-500 truncate">{{ attn.validation_name }}</span>
                      </div>
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 shrink-0">
                        {{ attn.severity }}
                      </span>
                    </div>

                    <p class="text-xs text-slate-600 leading-snug">
                      {{ attn.description }}
                    </p>

                    <div class="pt-1">
                      <a
                        [routerLink]="attn.action_route"
                        class="h-7 px-3 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 text-xs font-semibold inline-flex items-center gap-1.5 transition-colors cursor-pointer">
                        <span>{{ attn.action_label }}</span>
                        <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                      </a>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 4. VALIDATIONS (PRIMARY TABLE)                                  -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        
        <!-- Toolbar -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-3">
          
          <!-- Left: Title & Count Badge -->
          <div class="flex items-center gap-2.5">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Validations</span>
            <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              {{ vs.filteredValidations().length }}
            </span>
          </div>

          <!-- Right: Search + Filters -->
          <div class="flex items-center gap-2.5 flex-wrap">
            
            <!-- Search Input -->
            <div class="search-box-wrapper" style="position: relative; display: flex; align-items: center; width: 240px;">
              <app-lucide-icon 
                name="search" 
                [size]="14"
                style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: #94a3b8; pointer-events: none; z-index: 2;"
              ></app-lucide-icon>
              
              <input
                type="text"
                [ngModel]="vs.searchQuery()"
                (ngModelChange)="vs.searchQuery.set($event)"
                placeholder="Search validations..."
                style="width: 100%; height: 32px; padding-left: 36px !important; padding-right: 28px; font-size: 12px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; outline: none; color: #0f172a;"
              />
              @if (vs.searchQuery()) {
                <button 
                  type="button" 
                  (click)="vs.searchQuery.set('')" 
                  style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: #94a3b8; font-size: 14px; font-weight: bold; cursor: pointer; z-index: 2;">
                  &times;
                </button>
              }
            </div>

            <!-- Status Filter Dropdown -->
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
                      [class.bg-blue-50]="vs.statusFilter() === opt.value"
                      [class.text-blue-700]="vs.statusFilter() === opt.value">
                      <span>{{ opt.label }}</span>
                      @if (vs.statusFilter() === opt.value) {
                        <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                      }
                    </button>
                  }
                </div>
              }
            </div>

            <!-- Strategy Filter Dropdown -->
            <div class="relative" (click)="$event.stopPropagation()">
              <button
                type="button"
                (click)="toggleStrategyDropdown($event)"
                class="h-8 px-2.5 text-xs text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 flex items-center justify-between gap-2 cursor-pointer select-none transition-colors"
                [class.bg-blue-50]="isStrategyDropdownOpen()"
                [class.border-blue-300]="isStrategyDropdownOpen()">
                <span>{{ selectedStrategyFilterLabel() }}</span>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0"></app-lucide-icon>
              </button>

              @if (isStrategyDropdownOpen()) {
                <div 
                  class="absolute right-0 mt-1.5 origin-top-right w-40 rounded-xl bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                  @for (opt of strategyOptions; track opt.value) {
                    <button
                      type="button"
                      (click)="selectStrategyFilter(opt.value)"
                      class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                      [class.bg-blue-50]="vs.strategyFilter() === opt.value"
                      [class.text-blue-700]="vs.strategyFilter() === opt.value">
                      <span>{{ opt.label }}</span>
                      @if (vs.strategyFilter() === opt.value) {
                        <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                      }
                    </button>
                  }
                </div>
              }
            </div>

          </div>

        </div>

        <!-- Active Filter Indicator Banner -->
        @if (vs.kpiFilter() !== 'ALL' || vs.statusFilter() !== 'ALL' || vs.strategyFilter() !== 'ALL' || vs.searchQuery()) {
          <div class="flex items-center justify-between p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-xs text-blue-800">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="filter" [size]="13" class="text-blue-600"></app-lucide-icon>
              <span>Filtered ({{ vs.filteredValidations().length }} matching validations)</span>
            </div>
            <button 
              type="button" 
              (click)="clearAllFilters(); $event.stopPropagation()"
              class="text-blue-700 hover:text-blue-900 font-bold px-2 py-0.5 rounded hover:bg-blue-100 cursor-pointer">
              &times; Clear Filters
            </button>
          </div>
        }

        <!-- Table View -->
        @if (vs.filteredValidations().length === 0) {
          <div class="py-12 flex flex-col items-center justify-center text-center gap-2">
            <app-lucide-icon name="database" [size]="28" class="text-slate-300"></app-lucide-icon>
            <span class="text-xs font-semibold text-slate-700">No validations match your search or filter</span>
            <p class="text-xs text-slate-500 font-normal">
              Try adjusting your search query or clearing active filters.
            </p>
            <button 
              type="button" 
              (click)="clearAllFilters()" 
              class="mt-2 h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer shadow-2xs">
              Reset All Filters
            </button>
          </div>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse table-fixed">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-2.5 px-4 w-[28%]">Validation</th>
                  <th class="py-2.5 px-4 w-[20%]">Source &rarr; Target</th>
                  <th class="py-2.5 px-4 w-[14%]">Strategy</th>
                  <th class="py-2.5 px-4 w-[16%]">Last Run</th>
                  <th class="py-2.5 px-4 w-[14%]">Outcome</th>
                  <th class="py-2.5 px-4 w-[14%]">Next Run</th>
                  <th class="py-2.5 px-3 w-[4%] text-right"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-200 text-xs">
                @for (v of vs.filteredValidations(); track v.id; let i = $index) {
                  <tr 
                    [routerLink]="['/migration/validation', v.id]"
                    class="hover:bg-blue-50 even:bg-slate-50 transition-colors cursor-pointer group h-14 select-none">
                    
                    <!-- 1. Validation Name & Description -->
                    <td class="py-2.5 px-4 min-w-0">
                      <div class="flex flex-col min-w-0">
                        <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors truncate text-xs">
                          {{ v.name }}
                        </span>
                        @if (v.description) {
                          <span class="text-[11px] text-slate-500 font-normal truncate mt-0.5">
                            {{ v.description }}
                          </span>
                        }
                      </div>
                    </td>

                    <!-- 2. Source -> Target -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <div class="flex items-center gap-1.5 text-xs text-slate-700 font-medium">
                        <span class="font-semibold text-slate-800 truncate">{{ v.source_provider }}</span>
                        <span class="text-slate-400 font-normal shrink-0">&rarr;</span>
                        <span class="font-semibold text-slate-800 truncate">{{ v.target_provider }}</span>
                      </div>
                    </td>

                    <!-- 3. Strategy -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <app-status-badge [strategy]="v.strategy"></app-status-badge>
                    </td>

                    <!-- 4. Last Run -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <span class="text-xs text-slate-600 font-mono font-medium truncate block">
                        {{ vs.formatRelativeTime(v.last_run).relative }}
                      </span>
                    </td>

                    <!-- 5. Outcome -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <app-status-badge [verdict]="v.outcome"></app-status-badge>
                    </td>

                    <!-- 6. Next Run -->
                    <td class="py-2.5 px-4 whitespace-nowrap">
                      <span class="text-xs text-slate-600 font-mono font-medium truncate block">
                        {{ v.next_run ? vs.formatRelativeTime(v.next_run).relative : '—' }}
                      </span>
                    </td>

                    <!-- 7. Actions Menu -->
                    <td class="py-2.5 px-3 text-right whitespace-nowrap" (click)="$event.stopPropagation()">
                      <div class="relative inline-block">
                        <button
                          type="button"
                          (click)="toggleActionMenu(v.id, $event)"
                          class="w-7 h-7 flex items-center justify-center rounded border border-transparent text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                          [class.bg-slate-100]="activeActionMenuId() === v.id"
                          [class.text-slate-700]="activeActionMenuId() === v.id"
                          title="Actions">
                          <app-lucide-icon name="more-horizontal" [size]="15"></app-lucide-icon>
                        </button>

                        @if (activeActionMenuId() === v.id) {
                          <div 
                            (click)="$event.stopPropagation()"
                            class="absolute right-0 w-48 rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-0.5 z-50 text-left animate-in fade-in zoom-in-95 duration-100"
                            [ngClass]="(i >= vs.filteredValidations().length - 2 && vs.filteredValidations().length > 2) ? 'bottom-full mb-1 origin-bottom-right' : 'top-full mt-1 origin-top-right'">
                            
                            <a
                              [routerLink]="['/migration/validation', v.id]"
                              class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer">
                              <app-lucide-icon name="play" [size]="13" class="text-blue-600"></app-lucide-icon>
                              <span>Open Workstation</span>
                            </a>

                            <button
                              type="button"
                              (click)="viewHistory(v)"
                              class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer">
                              <app-lucide-icon name="history" [size]="13" class="text-slate-500"></app-lucide-icon>
                              <span>View History</span>
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
      <!-- 5. UPCOMING (6fr) + RECENT RESULTS (6fr)                        -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        
        <!-- Left: Upcoming (6fr) -->
        <div class="flex flex-col">
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4 flex-1">
            <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="calendar" [size]="16" class="text-blue-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Upcoming</span>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ vs.upcomingValidations().length }}
                </span>
              </div>
            </div>

            @if (vs.upcomingValidations().length === 0) {
              <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
                <span class="text-xs font-medium">No validations scheduled.</span>
              </div>
            } @else {
              <div class="flex flex-col divide-y divide-slate-200">
                @for (item of vs.upcomingValidations(); track item.id) {
                  <div class="py-3.5 first:pt-0 last:pb-0 flex items-center justify-between gap-4 text-xs">
                    <div class="flex flex-col min-w-0">
                      <span class="font-semibold text-slate-900 truncate">{{ item.name }}</span>
                      <div class="flex items-center gap-2 text-slate-500 text-[11px] mt-0.5">
                        <span>{{ item.source_provider }} &rarr; {{ item.target_provider }}</span>
                        <span>&bull;</span>
                        <app-status-badge [strategy]="item.strategy"></app-status-badge>
                      </div>
                    </div>

                    <div class="flex items-center gap-3 shrink-0">
                      <span class="font-mono text-xs text-slate-600 font-medium">
                        {{ vs.formatRelativeTime(item.next_run).relative }}
                      </span>
                      <a
                        [routerLink]="['/migration/validation', item.id]"
                        class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 text-xs font-semibold inline-flex items-center gap-1 transition-colors cursor-pointer">
                        <span>View</span>
                        <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                      </a>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        </div>

        <!-- Right: Recent Results (6fr) -->
        <div class="flex flex-col">
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4 flex-1">
            <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="shield-check" [size]="16" class="text-emerald-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Recent Results</span>
                <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ vs.recentResults().length }}
                </span>
              </div>
            </div>

            @if (vs.recentResults().length === 0) {
              <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
                <span class="text-xs font-medium">No recent validation results recorded.</span>
              </div>
            } @else {
              <div class="flex flex-col divide-y divide-slate-200">
                @for (res of vs.recentResults(); track res.id) {
                  <div class="py-3.5 first:pt-0 last:pb-0 flex items-center justify-between gap-4 text-xs">
                    <div class="flex flex-col min-w-0">
                      <span class="font-semibold text-slate-900 truncate">{{ res.name }}</span>
                      <div class="flex items-center gap-2 text-slate-500 text-[11px] mt-0.5">
                        <span>{{ res.source_provider }} &rarr; {{ res.target_provider }}</span>
                        <span>&bull;</span>
                        <span class="font-mono text-slate-500">{{ vs.formatRelativeTime(res.completed_at).relative }}</span>
                      </div>
                    </div>

                    <div class="flex items-center gap-3 shrink-0">
                      <app-status-badge [verdict]="res.outcome"></app-status-badge>
                      <a
                        [routerLink]="['/migration/validation', res.validation_id]"
                        class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 text-xs font-semibold inline-flex items-center gap-1 transition-colors cursor-pointer">
                        <span>View Results</span>
                        <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                      </a>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 6. RECENT ACTIVITY                                              -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="activity" [size]="16" class="text-blue-600"></app-lucide-icon>
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Recent Activity</span>
          </div>
        </div>

        @if (vs.activities().length === 0) {
          <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
            <span class="text-xs font-medium">No validation activity recorded yet.</span>
          </div>
        } @else {
          <div class="flex flex-col divide-y divide-slate-200">
            @for (act of vs.activities(); track act.id) {
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

                  <!-- Relative & Exact Time in Tabular Monospace -->
                  <div class="flex flex-col shrink-0 w-24">
                    <span class="font-bold text-slate-900 text-xs">
                      {{ vs.formatRelativeTime(act.occurred_at).relative }}
                    </span>
                    <span class="text-[11px] text-slate-500 font-mono font-medium tabular-nums">
                      {{ vs.formatRelativeTime(act.occurred_at).exactTime }}
                    </span>
                  </div>

                  <!-- Activity Title & Validation Name -->
                  <div class="flex flex-col min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="font-bold text-slate-900">{{ act.title }}</span>
                      <span class="text-slate-300">&bull;</span>
                      <span class="font-semibold text-blue-700 truncate">{{ act.validation_name }}</span>
                    </div>
                    <span class="text-xs text-slate-600 truncate font-normal">{{ act.status_text }}</span>
                  </div>
                </div>

                <!-- Action Button -->
                <div class="shrink-0">
                  <a
                    [routerLink]="['/migration/validation', act.validation_id]"
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

    </div>
  `
})
export class ValidationPortfolioComponent {
  public vs: ValidationHomeService;
  private router: Router;

  // Dropdown states
  public isStatusDropdownOpen = signal<boolean>(false);
  public isStrategyDropdownOpen = signal<boolean>(false);
  public activeActionMenuId = signal<string | null>(null);

  constructor(vs?: ValidationHomeService, router?: Router) {
    this.vs = vs ?? inject(ValidationHomeService);
    this.router = router ?? inject(Router);
  }

  public statusOptions: FilterOption[] = [
    { label: 'All Statuses', value: 'ALL' },
    { label: 'Validated', value: 'VALIDATED' },
    { label: 'Discrepancies Found', value: 'DISCREPANCIES' },
    { label: 'Running', value: 'RUNNING' },
    { label: 'Scheduled', value: 'SCHEDULED' },
    { label: 'Execution Failed', value: 'FAILED' }
  ];

  public strategyOptions: FilterOption[] = [
    { label: 'All Strategies', value: 'ALL' },
    { label: 'Sync', value: 'Sync' },
    { label: 'Async', value: 'Async' }
  ];

  public selectedStatusFilterLabel = computed(() => {
    const s = this.vs.statusFilter();
    return this.statusOptions.find(o => o.value === s)?.label || 'All Statuses';
  });

  public selectedStrategyFilterLabel = computed(() => {
    const s = this.vs.strategyFilter();
    return this.strategyOptions.find(o => o.value === s)?.label || 'All Strategies';
  });

  public toggleKpiFilter(filter: string, event: Event): void {
    event.stopPropagation();
    if (this.vs.kpiFilter() === filter) {
      this.vs.kpiFilter.set('ALL');
    } else {
      this.vs.kpiFilter.set(filter);
    }
  }

  public toggleStatusDropdown(event: Event): void {
    event.stopPropagation();
    this.isStrategyDropdownOpen.set(false);
    this.activeActionMenuId.set(null);
    this.isStatusDropdownOpen.update(v => !v);
  }

  public selectStatusFilter(val: string): void {
    this.vs.statusFilter.set(val);
    this.isStatusDropdownOpen.set(false);
  }

  public toggleStrategyDropdown(event: Event): void {
    event.stopPropagation();
    this.isStatusDropdownOpen.set(false);
    this.activeActionMenuId.set(null);
    this.isStrategyDropdownOpen.update(v => !v);
  }

  public selectStrategyFilter(val: string): void {
    this.vs.strategyFilter.set(val);
    this.isStrategyDropdownOpen.set(false);
  }

  public toggleActionMenu(id: string, event: Event): void {
    event.stopPropagation();
    this.isStatusDropdownOpen.set(false);
    this.isStrategyDropdownOpen.set(false);
    if (this.activeActionMenuId() === id) {
      this.activeActionMenuId.set(null);
    } else {
      this.activeActionMenuId.set(id);
    }
  }

  public clearAllFilters(): void {
    this.vs.kpiFilter.set('ALL');
    this.vs.statusFilter.set('ALL');
    this.vs.strategyFilter.set('ALL');
    this.vs.searchQuery.set('');
  }

  public viewHistory(item: ValidationItemRow): void {
    this.activeActionMenuId.set(null);
    this.router.navigate(['/migration/validation', item.id]);
  }

  @HostListener('document:click')
  public closeAllPopovers(): void {
    this.isStatusDropdownOpen.set(false);
    this.isStrategyDropdownOpen.set(false);
    this.activeActionMenuId.set(null);
  }
}
