import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationDiscrepanciesService } from '../validation-discrepancies.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-discrepancies-summary-band',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 lg:p-7 shadow-2xs flex flex-col gap-5">
      <div class="flex items-center justify-between flex-wrap gap-6">
        
        <!-- Left: Primary Investigation Metric & Scope -->
        <div class="flex items-center gap-5 flex-wrap">
          <div class="w-12 h-12 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 shrink-0">
            <app-lucide-icon name="alert-triangle" [size]="22"></app-lucide-icon>
          </div>

          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-3 flex-wrap">
              <h2 class="text-lg font-bold text-slate-900 font-heading tracking-tight">
                Discrepancy Findings &amp; Localization
              </h2>
              
              <!-- Historical Mission Tag if applicable -->
              @if (store.isHistorical()) {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  <app-lucide-icon name="history" [size]="13"></app-lucide-icon>
                  <span>Historical Read-Only Mission</span>
                </span>
              }
            </div>

            <p class="text-xs text-slate-600 leading-relaxed">
              @if (store.summary().totalDiscrepancies !== null && store.summary().totalDiscrepancies! > 0) {
                <span class="font-bold text-slate-900 font-mono text-sm">{{ store.summary().totalDiscrepanciesFormatted }}</span>
                findings across
                <span class="font-bold text-slate-900 font-mono text-sm">{{ store.summary().affectedObjectsCount }}</span>
                affected objects require investigation
                <span class="text-slate-400 mx-1">·</span>
                Evaluated scope: <span class="font-mono font-semibold text-slate-800">{{ store.summary().evaluatedScopeCount }} objects</span>
              } @else if (store.summary().totalDiscrepancies === 0) {
                <span>Zero discrepancies established across evaluated scope (<span class="font-mono font-semibold text-slate-800">{{ store.summary().evaluatedScopeCount }} objects</span>).</span>
              } @else {
                <span>Awaiting canonical discrepancy stream from validation engine daemon.</span>
              }
            </p>
          </div>
        </div>

        <!-- Right: Canonical Status Indicators (Truthful, No Fake Confidence) -->
        <div class="flex items-center gap-3 flex-wrap">
          
          <!-- Localization Status Badge -->
          <div class="flex items-center gap-2 px-3.5 py-2 rounded-lg border text-xs"
               [ngClass]="getLocalizationClasses(store.summary().localizationStatus)">
            <app-lucide-icon [name]="getLocalizationIcon(store.summary().localizationStatus)" [size]="14"></app-lucide-icon>
            <span class="font-semibold uppercase tracking-wider text-[11px]">Localization:</span>
            <span class="font-bold">{{ formatLocalization(store.summary().localizationStatus) }}</span>
          </div>

          <!-- Baseline Status Badge -->
          <div class="flex items-center gap-2 px-3.5 py-2 rounded-lg border text-xs"
               [ngClass]="getBaselineClasses(store.summary().baselineStatus)">
            <app-lucide-icon [name]="getBaselineIcon(store.summary().baselineStatus)" [size]="14"></app-lucide-icon>
            <span class="font-semibold uppercase tracking-wider text-[11px]">Baseline:</span>
            <span class="font-bold">{{ formatBaseline(store.summary().baselineStatus) }}</span>
          </div>

          <!-- Unresolved Findings Counter Badge -->
          @if (store.summary().unresolvedCount !== null && store.summary().unresolvedCount! > 0) {
            <div class="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold">
              <app-lucide-icon name="alert-circle" [size]="14" class="text-rose-600"></app-lucide-icon>
              <span>{{ store.summary().unresolvedCount | number }} Unresolved</span>
            </div>
          }

          <!-- Explained Findings Counter Badge -->
          @if (store.summary().explainedCount !== null && store.summary().explainedCount! > 0) {
            <div class="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
              <app-lucide-icon name="check-circle-2" [size]="14" class="text-emerald-600"></app-lucide-icon>
              <span>{{ store.summary().explainedCount | number }} Explained</span>
            </div>
          }

        </div>

      </div>
    </section>
  `
})
export class DiscrepanciesSummaryBandComponent {
  readonly store = inject(ValidationDiscrepanciesService);

  getLocalizationClasses(status: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE'): string {
    switch (status) {
      case 'AVAILABLE': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'LIMITED': return 'bg-amber-50 border-amber-200 text-amber-800';
      case 'UNAVAILABLE': return 'bg-slate-50 border-slate-200 text-slate-600';
    }
  }

  getLocalizationIcon(status: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE'): string {
    switch (status) {
      case 'AVAILABLE': return 'check-circle-2';
      case 'LIMITED': return 'alert-circle';
      case 'UNAVAILABLE': return 'minus-circle';
    }
  }

  formatLocalization(status: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE'): string {
    switch (status) {
      case 'AVAILABLE': return 'Available';
      case 'LIMITED': return 'Limited (Tier 3 Only)';
      case 'UNAVAILABLE': return 'Unavailable';
    }
  }

  getBaselineClasses(status: 'VALID' | 'STALE' | 'NOT_AVAILABLE'): string {
    switch (status) {
      case 'VALID': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'STALE': return 'bg-amber-50 border-amber-200 text-amber-800';
      case 'NOT_AVAILABLE': return 'bg-slate-50 border-slate-200 text-slate-600';
    }
  }

  getBaselineIcon(status: 'VALID' | 'STALE' | 'NOT_AVAILABLE'): string {
    switch (status) {
      case 'VALID': return 'shield-check';
      case 'STALE': return 'alert-triangle';
      case 'NOT_AVAILABLE': return 'shield-off';
    }
  }

  formatBaseline(status: 'VALID' | 'STALE' | 'NOT_AVAILABLE'): string {
    switch (status) {
      case 'VALID': return 'Valid';
      case 'STALE': return 'Drift Detected';
      case 'NOT_AVAILABLE': return 'Not Bound';
    }
  }
}
