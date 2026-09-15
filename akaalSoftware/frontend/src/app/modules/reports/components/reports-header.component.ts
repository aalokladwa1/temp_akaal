import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ReportsService } from '../services/reports.service';

@Component({
  selector: 'app-reports-header',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap select-none">
      <div class="flex flex-col gap-1">
        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">REPORTS</span>
        <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Reports</h1>
        <p class="text-sm font-medium text-slate-600 max-w-3xl">
          Unified reporting catalog, workload assurance certifications, and cryptographic audit evidence.
        </p>
      </div>

      <div class="flex items-center gap-3 pt-1">
        <!-- Primary Action Button: Opens Report Library -->
        <a
          routerLink="/reports/library"
          class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs select-none">
          Report Library
        </a>
      </div>
    </div>
  `
})
export class ReportsHeaderComponent {
  public rs = inject(ReportsService);
}
