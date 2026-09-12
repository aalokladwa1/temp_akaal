import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { ReportsService } from '../services/reports.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-reports-recent-table',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-3 select-none">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            RECENT REPORTS
          </span>
          <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">
            {{ rs.filteredReports().length }}
          </span>
        </div>

        <div class="flex items-center gap-3">
          <!-- Search input -->
          <div class="relative w-60">
            <app-lucide-icon name="search" [size]="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
            <input
              type="text"
              [value]="rs.reportSearchQuery()"
              (input)="onSearchInput($event)"
              placeholder="Search reports..."
              class="w-full pl-8 pr-3 py-1.5 text-xs font-medium bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 transition-all shadow-2xs"
            />
          </div>

          <!-- View All Link to Specialist Workspace -->
          <a
            routerLink="/reports/library"
            class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer shrink-0">
            <span>View all</span>
            <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
          </a>
        </div>
      </div>

      <!-- State: LOADING -->
      @if (rs.reportsState() === 'LOADING') {
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-3 shadow-2xs animate-pulse">
          @for (i of [1,2,3,4]; track i) {
            <div class="h-10 bg-slate-100 rounded"></div>
          }
        </div>
      } @else if (rs.reportsState() === 'UNAVAILABLE' || rs.reportsState() === 'ERROR') {
        <!-- State: UNAVAILABLE / ERROR -->
        <div class="p-6 rounded-xl bg-slate-50 border border-slate-200 text-center flex flex-col items-center justify-center gap-2">
          <app-lucide-icon name="alert-triangle" [size]="24" class="text-amber-500"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-800">Report catalog is currently unavailable</span>
          <p class="text-xs text-slate-500 max-w-sm">Unable to connect to the reporting storage subsystem.</p>
        </div>
      } @else if (rs.filteredReports().length === 0) {
        <!-- State: AVAILABLE_EMPTY -->
        <div class="p-8 rounded-xl bg-white border border-slate-200 text-center flex flex-col items-center justify-center gap-2 shadow-2xs">
          <app-lucide-icon name="file-text" [size]="28" class="text-slate-400"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-800">No reports generated yet</span>
          <p class="text-xs text-slate-500 max-w-sm">Technical reports will appear here automatically as validations and migrations complete.</p>
        </div>
      } @else {
        <!-- State: AVAILABLE_WITH_DATA (Clean Standard AKAAL Table) -->
        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Report</th>
                <th class="py-3 px-4">Subject</th>
                <th class="py-3 px-4 hidden md:table-cell">Generated</th>
                <th class="py-3 px-4">Outcome</th>
                <th class="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (report of rs.filteredReports(); track report.id) {
                <tr class="hover:bg-slate-50/80 transition-colors group cursor-pointer" (click)="openReport(report.id)">
                  
                  <!-- Report Title & Category -->
                  <td class="py-3.5 px-4">
                    <div class="flex flex-col gap-0.5">
                      <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                        {{ report.title }}
                      </span>
                      <span class="text-[11px] text-slate-500 font-medium">
                        {{ report.category_label }}
                      </span>
                    </div>
                  </td>

                  <!-- Subject -->
                  <td class="py-3.5 px-4 text-slate-700 font-medium">
                    {{ report.subject_name }}
                  </td>

                  <!-- Generated Timestamp -->
                  <td class="py-3.5 px-4 text-slate-500 hidden md:table-cell font-mono text-[11px]">
                    {{ report.generated_at | date:'yyyy-MM-dd HH:mm' }}
                  </td>

                  <!-- Outcome Badge -->
                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2.5 py-1 rounded-md text-[11px] font-bold inline-block"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': report.outcome === 'SATISFIED' || report.outcome === 'CONVERGED' || report.outcome === 'RECONCILED',
                        'bg-rose-50 text-rose-700 border border-rose-200': report.outcome === 'DEFECTS_FOUND' || report.outcome === 'BLOCKED',
                        'bg-blue-50 text-blue-700 border border-blue-200': report.outcome === 'IN_PROGRESS',
                        'bg-slate-50 text-slate-700 border border-slate-200': report.outcome === 'NOT_APPLICABLE' || report.outcome === 'UNKNOWN'
                      }">
                      {{ rs.formatText(report.outcome) }}
                    </span>
                  </td>

                  <!-- Action -->
                  <td class="py-3.5 px-4 text-right">
                    <button
                      type="button"
                      (click)="openReport(report.id); $event.stopPropagation()"
                      class="px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs border border-slate-200 transition-colors cursor-pointer">
                      Inspect
                    </button>
                  </td>

                </tr>
              }
            </tbody>
          </table>
        </div>
      }

    </div>
  `
})
export class ReportsRecentTableComponent {
  public rs = inject(ReportsService);
  private router = inject(Router);

  public onSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.rs.reportSearchQuery.set(target.value);
  }

  public openReport(reportId: string): void {
    this.router.navigate(['/reports/library'], { queryParams: { reportId } });
  }
}
