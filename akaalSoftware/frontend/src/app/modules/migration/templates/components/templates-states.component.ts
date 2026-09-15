import { Component, inject, Optional, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TemplatesService } from '../templates.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-templates-states',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="w-full">
      
      <!-- =============================================================== -->
      <!-- 1. LOADING SKELETON STATE                                       -->
      <!-- =============================================================== -->
      @if (ts.availabilityState() === 'LOADING') {
        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4 animate-pulse">
          <div class="h-8 bg-slate-100 rounded-lg w-1/3 mb-2"></div>
          <div class="space-y-3">
            @for (i of [1, 2, 3, 4, 5]; track i) {
              <div class="h-12 bg-slate-50 border border-slate-100 rounded-xl w-full"></div>
            }
          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 2. FILTERED EMPTY STATE (No Search / Filter Matches)            -->
      <!-- =============================================================== -->
      @if (ts.availabilityState() === 'READY' && ts.filteredTemplates().length === 0 && ts.isFiltered()) {
        <div class="p-12 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col items-center justify-center text-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400">
            <app-lucide-icon name="search-x" [size]="22"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">No templates found</h3>
          <p class="text-xs text-slate-500 max-w-sm">
            No migration templates matched your active search query or filter criteria.
          </p>
          <div class="pt-2">
            <button
              type="button"
              (click)="ts.clearFilters()"
              class="h-8 px-4 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-400">
              Clear filters
            </button>
          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 3. ABSOLUTE EMPTY STATE (Zero Templates In Scope)               -->
      <!-- =============================================================== -->
      @if (ts.availabilityState() === 'EMPTY' || (ts.availabilityState() === 'READY' && ts.templates().length === 0)) {
        <div class="p-12 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col items-center justify-center text-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400">
            <app-lucide-icon name="file-text" [size]="22"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">No migration templates</h3>
          <p class="text-xs text-slate-500 max-w-sm">
            Templates standardize and accelerate recurring migration workflows across all operational modes.
          </p>
          <div class="pt-2">
            <button
              type="button"
              (click)="createNewTemplate.emit()"
              class="h-8 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/40">
              New Template
            </button>
          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 4. UNAUTHORIZED STATE                                           -->
      <!-- =============================================================== -->
      @if (ts.availabilityState() === 'UNAUTHORIZED') {
        <div class="p-12 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col items-center justify-center text-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-500">
            <app-lucide-icon name="shield-alert" [size]="22"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">Access restricted</h3>
          <p class="text-xs text-slate-500 max-w-sm">
            You do not have the required permissions to access template definitions in this operational scope.
          </p>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 5. UNAVAILABLE / ERROR STATE                                    -->
      <!-- =============================================================== -->
      @if (ts.availabilityState() === 'UNAVAILABLE' || ts.availabilityState() === 'ERROR') {
        <div class="p-12 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col items-center justify-center text-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
            <app-lucide-icon name="alert-triangle" [size]="22"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">Templates unavailable</h3>
          <p class="text-xs text-slate-500 max-w-sm">
            {{ ts.errorMessage() || 'The template repository or migration configuration service is currently unreachable.' }}
          </p>
          <div class="pt-2">
            <button
              type="button"
              (click)="ts.reload()"
              class="h-8 px-4 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-amber-500/40">
              Retry
            </button>
          </div>
        </div>
      }

    </div>
  `
})
export class TemplatesStatesComponent {
  public ts: TemplatesService;
  @Output() createNewTemplate = new EventEmitter<void>();

  constructor(@Optional() ts?: TemplatesService) {
    if (ts) {
      this.ts = ts;
    } else {
      try {
        this.ts = inject(TemplatesService);
      } catch {
        this.ts = new TemplatesService();
      }
    }
  }
}
