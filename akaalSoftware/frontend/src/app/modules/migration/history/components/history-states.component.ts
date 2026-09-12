import { Component, inject, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryHomeService } from '../history-home.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-history-states',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col items-center justify-center p-12 text-center rounded-2xl bg-white border border-slate-200">
      
      <!-- 1. LOADING SKELETON STATE -->
      @if (hs.availabilityState() === 'LOADING') {
        <div class="w-full flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100 animate-pulse">
            <div class="h-4 bg-slate-200 rounded w-48"></div>
            <div class="h-8 bg-slate-200 rounded w-64"></div>
          </div>
          <div class="flex flex-col gap-3">
            @for (i of [1, 2, 3, 4, 5]; track i) {
              <div class="h-12 bg-slate-100 rounded-lg w-full animate-pulse"></div>
            }
          </div>
        </div>
      }

      <!-- 2. NO FILTER MATCH RESULTS -->
      @else if (hs.availabilityState() === 'READY' && hs.isFiltered() && hs.filteredHistoryItems().length === 0) {
        <div class="flex flex-col items-center gap-3 max-w-md py-6">
          <div class="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500">
            <app-lucide-icon name="search" [size]="22"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900 font-heading">No matching historical migrations</h3>
            <p class="text-xs text-slate-500">
              No executions in the historical ledger match your current search queries or filter selections.
            </p>
          </div>
          <button
            type="button"
            (click)="hs.clearFilters()"
            class="mt-2 h-8 px-4 rounded-md bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-800 text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-400">
            Clear filters
          </button>
        </div>
      }

      <!-- 3. EMPTY HISTORY LEDGER -->
      @else if (hs.availabilityState() === 'EMPTY' || (hs.availabilityState() === 'READY' && hs.historyItems().length === 0)) {
        <div class="flex flex-col items-center gap-3 max-w-md py-8">
          <div class="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <app-lucide-icon name="history" [size]="22"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900 font-heading">No migration history recorded</h3>
            <p class="text-xs text-slate-500">
              No historical migration executions or validation audits have been completed yet in this environment.
            </p>
          </div>
        </div>
      }

      <!-- 4. ERROR / UNAVAILABLE -->
      @else if (hs.availabilityState() === 'UNAVAILABLE' || hs.availabilityState() === 'ERROR') {
        <div class="flex flex-col items-center gap-3 max-w-md py-6">
          <div class="w-12 h-12 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
            <app-lucide-icon name="alert-triangle" [size]="22"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900 font-heading">History Ledger Unavailable</h3>
            <p class="text-xs text-slate-500">
              {{ hs.errorMessage() || 'The forensic audit repository or historical execution ledger is currently unreachable.' }}
            </p>
          </div>
          <button
            type="button"
            (click)="hs.reload()"
            class="mt-2 h-8 px-4 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500">
            Retry
          </button>
        </div>
      }

      <!-- 5. UNAUTHORIZED -->
      @else if (hs.availabilityState() === 'UNAUTHORIZED') {
        <div class="flex flex-col items-center gap-3 max-w-md py-6">
          <div class="w-12 h-12 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
            <app-lucide-icon name="shield-alert" [size]="22"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900 font-heading">Audit Access Restricted</h3>
            <p class="text-xs text-slate-500">
              You do not possess the required RBAC permissions to inspect the historical migration ledger or sealed cryptographic evidence.
            </p>
          </div>
        </div>
      }

    </div>
  `
})
export class HistoryStatesComponent {
  public hs: HistoryHomeService;

  constructor(@Optional() hs?: HistoryHomeService) {
    if (hs) {
      this.hs = hs;
    } else {
      try {
        this.hs = inject(HistoryHomeService);
      } catch {
        this.hs = new HistoryHomeService();
      }
    }
  }
}
