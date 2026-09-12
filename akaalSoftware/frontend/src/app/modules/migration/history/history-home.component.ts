import { Component, inject, Optional, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryHomeService } from './history-home.service';
import { HistoryHeaderComponent } from './components/history-header.component';
import { HistoryToolbarComponent } from './components/history-toolbar.component';
import { HistoryTableComponent } from './components/history-table.component';
import { HistoryStatesComponent } from './components/history-states.component';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-history-home',
  standalone: true,
  imports: [
    CommonModule,
    HistoryHeaderComponent,
    HistoryToolbarComponent,
    HistoryTableComponent,
    HistoryStatesComponent,
    LucideIconComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- 1. Header Hierarchy -->
      <app-history-header></app-history-header>

      <!-- Database / State Unavailable Notice -->
      @if (hs.availabilityState() === 'UNAVAILABLE' || hs.availabilityState() === 'ERROR') {
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold">{{ hs.errorMessage() || 'The migration history repository or forensic audit ledger is currently unreachable.' }}</span>
          </div>
          <button
            type="button"
            (click)="hs.reload()"
            class="h-8 px-3.5 rounded-md bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs cursor-pointer focus:outline-none focus:ring-2 focus:ring-amber-500">
            Retry
          </button>
        </div>
      }

      <!-- 2. Main History Ledger Card -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5 select-none">
        
        <!-- Integrated Toolbar -->
        <app-history-toolbar></app-history-toolbar>

        <!-- Table or Empty/Error States -->
        <div class="relative">
          @if (showTable()) {
            <app-history-table></app-history-table>
          } @else {
            <app-history-states></app-history-states>
          }
        </div>

      </div>

    </div>
  `
})
export class HistoryHomeComponent implements OnInit {
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

  ngOnInit(): void {
    if (this.hs.availabilityState() === 'LOADING') {
      setTimeout(() => {
        this.hs.availabilityState.set('READY');
      }, 100);
    }
  }

  showTable(): boolean {
    return (
      this.hs.availabilityState() === 'READY' &&
      this.hs.filteredHistoryItems().length > 0
    );
  }
}
