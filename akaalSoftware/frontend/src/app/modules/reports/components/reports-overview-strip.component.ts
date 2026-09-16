import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ReportsService } from '../services/reports.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-reports-overview-strip',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 select-none">
      
      <!-- Card 1: Total Reports -->
      <div 
        (click)="navigate('/reports/library')"
        class="p-5 rounded-2xl border transition-all duration-200 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs bg-white dark:bg-[#1a1b1e] border-slate-200 dark:border-[#26272b] hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-[#202226] hover:-translate-y-0.5 active:scale-[0.98]">
        
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-heading group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-colors">
            TOTAL REPORTS
          </span>
          <app-lucide-icon name="circle-dot" [size]="10" class="text-blue-500"></app-lucide-icon>
        </div>

        <div class="flex items-baseline justify-between gap-3">
          <span class="text-3xl font-bold font-mono text-slate-900 dark:text-slate-100 tracking-tight tabular-nums">
            {{ rs.summary().total_reports_count }}
          </span>
        </div>

      </div>

      <!-- Card 2: Certification Attention -->
      <div 
        (click)="navigate('/reports/certification')"
        class="p-5 rounded-2xl border transition-all duration-200 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs bg-white dark:bg-[#1a1b1e] border-slate-200 dark:border-[#26272b] hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-[#202226] hover:-translate-y-0.5 active:scale-[0.98]">
        
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-heading group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-colors">
            CERTIFICATION ATTENTION
          </span>
          @if (rs.summary().certification_attention_count > 0) {
            <app-lucide-icon name="circle-dot" [size]="10" class="text-amber-500 animate-pulse"></app-lucide-icon>
          } @else {
            <app-lucide-icon name="circle-dot" [size]="10" class="text-emerald-500"></app-lucide-icon>
          }
        </div>

        <div class="flex items-baseline justify-between gap-3">
          <span 
            class="text-3xl font-bold font-mono tracking-tight tabular-nums"
            [ngClass]="rs.summary().certification_attention_count > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-900 dark:text-slate-100'">
            {{ rs.summary().certification_attention_count }}
          </span>
        </div>

      </div>

      <!-- Card 3: Evidence Manifests -->
      <div 
        (click)="navigate('/reports/evidence')"
        class="p-5 rounded-2xl border transition-all duration-200 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs bg-white dark:bg-[#1a1b1e] border-slate-200 dark:border-[#26272b] hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-[#202226] hover:-translate-y-0.5 active:scale-[0.98]">
        
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-heading group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-colors">
            EVIDENCE MANIFESTS
          </span>
          <app-lucide-icon name="circle-dot" [size]="10" class="text-blue-500"></app-lucide-icon>
        </div>

        <div class="flex items-baseline justify-between gap-3">
          <span class="text-3xl font-bold font-mono text-slate-900 dark:text-slate-100 tracking-tight tabular-nums">
            {{ rs.summary().evidence_manifests_count }}
          </span>
        </div>

      </div>

    </div>
  `
})
export class ReportsOverviewStripComponent {
  public rs = inject(ReportsService);
  private router = inject(Router);

  public navigate(route: string): void {
    this.router.navigate([route]);
  }
}

