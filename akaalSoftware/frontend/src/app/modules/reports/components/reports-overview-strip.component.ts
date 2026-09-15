import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ReportsService } from '../services/reports.service';

@Component({
  selector: 'app-reports-overview-strip',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 select-none">
      
      <!-- Card 1: Total Reports -->
      <div 
        (click)="navigate('/reports/library')"
        class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50">
        
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading group-hover:text-slate-800 transition-colors">
            TOTAL REPORTS
          </span>
        </div>

        <div class="flex items-baseline justify-between gap-3">
          <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
            {{ rs.summary().total_reports_count }}
          </span>
        </div>

      </div>

      <!-- Card 2: Certification Attention -->
      <div 
        (click)="navigate('/reports/certification')"
        class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50">
        
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading group-hover:text-slate-800 transition-colors">
            CERTIFICATION ATTENTION
          </span>
          @if (rs.summary().certification_attention_count > 0) {
            <span class="w-2 h-2 rounded-full bg-amber-500 shrink-0"></span>
          } @else {
            <span class="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>
          }
        </div>

        <div class="flex items-baseline justify-between gap-3">
          <span 
            class="text-3xl font-bold font-mono tracking-tight tabular-nums"
            [ngClass]="rs.summary().certification_attention_count > 0 ? 'text-amber-600' : 'text-slate-900'">
            {{ rs.summary().certification_attention_count }}
          </span>
        </div>

      </div>

      <!-- Card 3: Evidence Manifests -->
      <div 
        (click)="navigate('/reports/evidence')"
        class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50">
        
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading group-hover:text-slate-800 transition-colors">
            EVIDENCE MANIFESTS
          </span>
        </div>

        <div class="flex items-baseline justify-between gap-3">
          <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
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

