import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ReportsService } from '../services/reports.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-reports-certification-attention',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-3 select-none">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="alert-triangle" [size]="15" class="text-amber-600"></app-lucide-icon>
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            CERTIFICATION ATTENTION
          </span>
          @if (rs.hasCertificationAttention()) {
            <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-amber-100 text-amber-800">
              {{ rs.certificationAttention().length }}
            </span>
          }
        </div>

        <a
          routerLink="/reports/certification"
          class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer">
          <span>View Trust &amp; Certification</span>
          <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
        </a>
      </div>

      <!-- State: LOADING -->
      @if (rs.certificationState() === 'LOADING') {
        <div class="p-5 bg-white border border-slate-200 rounded-xl animate-pulse h-24"></div>
      } @else if (rs.certificationState() === 'UNAVAILABLE' || rs.certificationState() === 'ERROR') {
        <!-- State: UNAVAILABLE / ERROR -->
        <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 text-xs flex items-center justify-between">
          <span>Certification state is currently unavailable from the reporting engine.</span>
          <a routerLink="/reports/certification" class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs inline-flex items-center gap-1">Open Certification</a>
        </div>
      } @else if (!rs.hasCertificationAttention()) {
        <!-- State: AVAILABLE_EMPTY -->
        <div class="p-4 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs flex items-center gap-3">
          <div class="w-6 h-6 rounded-md bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <app-lucide-icon name="check-circle" [size]="14"></app-lucide-icon>
          </div>
          <div>
            <span class="font-semibold text-slate-800">All workloads are currently in good certification standing.</span>
            <p class="text-[11px] text-slate-500 mt-0.5">No unresolved discrepancies or criteria gaps require operator sign-off.</p>
          </div>
        </div>
      } @else {
        <!-- State: AVAILABLE_WITH_DATA (Clean Cards matching AKAAL Needs Attention pattern) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          @for (item of rs.certificationAttention(); track item.id) {
            <div class="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col justify-between gap-3 hover:border-slate-300 transition-colors">
              <div class="flex flex-col gap-1.5">
                <div class="flex items-center justify-between gap-2">
                  <span class="text-xs font-bold text-slate-900 leading-snug">
                    {{ item.headline }}
                  </span>
                  <span 
                    class="px-2 py-0.5 rounded text-[10px] font-bold shrink-0"
                    [ngClass]="{
                      'bg-rose-50 text-rose-700 border border-rose-200': item.severity === 'HIGH',
                      'bg-amber-50 text-amber-800 border border-amber-200': item.severity === 'MEDIUM',
                      'bg-slate-100 text-slate-700': item.severity === 'LOW' || item.severity === 'INFO'
                    }">
                    {{ item.severity }}
                  </span>
                </div>

                <span class="text-[11px] font-medium text-slate-500">
                  Subject: <strong class="text-slate-700">{{ item.subject_name }}</strong>
                </span>

                <p class="text-xs text-slate-600 leading-relaxed mt-0.5">
                  {{ item.detail }}
                </p>
              </div>

              <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                @if (item.related_report_id) {
                  <span class="text-[11px] text-slate-400">
                    Ref: <strong class="text-slate-600">{{ item.related_report_id }}</strong>
                  </span>
                } @else {
                  <span></span>
                }

                <a
                  routerLink="/reports/certification"
                  class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer">
                  <span>Review Discrepancy</span>
                  <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                </a>
              </div>
            </div>
          }
        </div>
      }

    </div>
  `
})
export class ReportsCertificationAttentionComponent {
  public rs = inject(ReportsService);
}
