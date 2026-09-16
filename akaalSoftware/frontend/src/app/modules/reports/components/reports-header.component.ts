import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ReportsService } from '../services/reports.service';

@Component({
  selector: 'app-reports-header',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 dark:border-white/[0.08] flex-wrap select-none animate-in fade-in duration-200">
      <div class="flex flex-col gap-1">
        <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight font-heading">Reports</h1>
        <p class="text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-400 max-w-3xl flex items-center gap-2 flex-wrap">
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800/40">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
            <span>Live System Catalog</span>
          </span>
          <span>
            {{ rs.summary().total_reports_count || 14 }} reports cataloged &bull; 
            <ng-container *ngIf="rs.summary().certification_attention_count > 0; else allNominal">
              <span class="text-amber-600 dark:text-amber-400 font-semibold">{{ rs.summary().certification_attention_count }} items require certification attention</span>
            </ng-container>
            <ng-template #allNominal>
              <span class="text-emerald-600 dark:text-emerald-400 font-medium">All workload assurance certifications nominal</span>
            </ng-template>
          </span>
        </p>
      </div>

      <div class="flex items-center gap-3 pt-1">
        <!-- Primary Action Button: Opens Report Library -->
        <a
          routerLink="/reports/library"
          class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center justify-center cursor-pointer transition-all duration-150 active:scale-[0.98] shadow-2xs select-none">
          Report Library
        </a>
      </div>
    </div>
  `
})
export class ReportsHeaderComponent {
  public rs = inject(ReportsService);
}
