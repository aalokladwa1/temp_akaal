import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-verdict-banner',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        
        <!-- Left: Verdict, Authority & Contextual Summary -->
        <div class="flex items-start gap-4 sm:gap-5 flex-1 min-w-0">
          
          <!-- Semantic Verdict Icon Container (Formal, restrained, NOT theatrical) -->
          <div
            [ngClass]="{
              'bg-emerald-50 text-emerald-700 border-emerald-200': store.verdict() === 'PASSED',
              'bg-rose-50 text-rose-700 border-rose-200': store.verdict() === 'FAILED',
              'bg-amber-50 text-amber-700 border-amber-200': store.verdict() === 'WITHHELD',
              'bg-slate-50 text-slate-600 border-slate-200': store.verdict() === 'NOT_EVALUATED'
            }"
            class="w-13 h-13 rounded-xl border flex items-center justify-center shrink-0 shadow-2xs">
            @switch (store.verdict()) {
              @case ('PASSED') {
                <app-lucide-icon name="badge-check" [size]="26" />
              }
              @case ('FAILED') {
                <app-lucide-icon name="alert-triangle" [size]="26" />
              }
              @case ('WITHHELD') {
                <app-lucide-icon name="shield-off" [size]="26" />
              }
              @default {
                <app-lucide-icon name="help-circle" [size]="26" />
              }
            }
          </div>

          <!-- Verdict Text & Metadata -->
          <div class="flex flex-col gap-1.5 min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2.5">
              <span class="text-[11px] font-mono uppercase tracking-wider text-slate-700 font-semibold">
                Validation #11 Authority
              </span>
              <span class="text-slate-300">•</span>
              
              <!-- Verdict Badge -->
              <span
                [ngClass]="{
                  'bg-emerald-50 text-emerald-700 border-emerald-200': store.verdict() === 'PASSED',
                  'bg-rose-50 text-rose-700 border-rose-200': store.verdict() === 'FAILED',
                  'bg-amber-50 text-amber-700 border-amber-200': store.verdict() === 'WITHHELD',
                  'bg-slate-100 text-slate-700 border-slate-200': store.verdict() === 'NOT_EVALUATED'
                }"
                class="px-2.5 py-0.5 text-xs font-bold rounded-md border tracking-wide">
                {{ store.verdict() }}
              </span>

              @if (store.completedAt()) {
                <span class="text-slate-300">•</span>
                <span class="text-xs text-slate-500 font-sans">
                  Completed {{ store.completedAt() | date:'medium' }}
                </span>
              }
            </div>

            <!-- Verdict Title & Description -->
            <h1 class="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight font-heading break-words">
              {{ store.validationName() }}
            </h1>

            <p class="text-xs sm:text-sm text-slate-600 leading-relaxed max-w-3xl">
              {{ store.verdictSummaryNote() || 'Validation execution completed under governed authority.' }}
            </p>

            <!-- Execution Meta Details -->
            <div class="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
              @if (store.durationFormatted()) {
                <div class="flex items-center gap-1.5">
                  <app-lucide-icon name="clock" [size]="13" class="text-slate-700" />
                  <span>Runtime: <strong class="text-slate-700">{{ store.durationFormatted() }}</strong></span>
                </div>
              }
              @if (store.operator()) {
                <div class="flex items-center gap-1.5 min-w-0 max-w-full">
                  <app-lucide-icon name="user" [size]="13" class="text-slate-700 shrink-0" />
                  <span class="truncate">Operator: <strong class="text-slate-700 font-mono text-[11px] break-all">{{ store.operator() }}</strong></span>
                </div>
              }
              <div class="flex items-center gap-1.5 min-w-0">
                <app-lucide-icon name="fingerprint" [size]="13" class="text-slate-700 shrink-0" />
                <span class="shrink-0">Mission ID:</span>
                <button
                  type="button"
                  (click)="store.copyValidationId()"
                  class="font-mono text-[11px] text-blue-600 hover:text-blue-800 hover:underline cursor-pointer flex items-center gap-1 min-w-0 truncate">
                  <span class="truncate max-w-[220px] sm:max-w-none">{{ store.validationId() }}</span>
                  <app-lucide-icon [name]="store.copiedId() ? 'check' : 'copy'" [size]="11" class="shrink-0" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Primary Dimensional Chips & Technical Drawer Trigger -->
        <div class="flex flex-col sm:flex-row lg:flex-col items-stretch sm:items-center lg:items-end justify-between gap-3 border-t lg:border-t-0 pt-4 lg:pt-0 border-slate-100 shrink-0">
          
          <!-- Dimensions Container -->
          <div class="flex flex-wrap items-center gap-2">
            
            <!-- Relationship Mode Chip (Decoupled from Verdict!) -->
            <div
              [title]="'Canonical comparison mode: ' + store.comparisonMode()"
              class="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 text-xs flex items-center gap-1.5">
              <app-lucide-icon name="refresh-cw" [size]="12" class="text-slate-700" />
              <span class="text-slate-700">Mode:</span>
              <strong class="font-bold text-slate-900">{{ store.comparisonMode() }}</strong>
            </div>

            <!-- Temporal Model Chip -->
            <div
              [title]="'Temporal validation model: ' + store.temporalModel()"
              class="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 text-xs flex items-center gap-1.5">
              <app-lucide-icon name="layers" [size]="12" class="text-slate-700" />
              <span class="text-slate-700">Model:</span>
              <strong class="font-bold text-slate-900 font-sans">
                {{ store.temporalModel() === 'CONSISTENT_STATE' ? 'Consistent-State' : store.temporalModel() === 'CONTINUOUS' ? 'Continuous' : 'Unspecified' }}
              </strong>
            </div>

            <!-- Baseline State Chip -->
            <div
              class="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 text-xs flex items-center gap-1.5">
              <app-lucide-icon name="shield" [size]="12" class="text-slate-700" />
              <span class="text-slate-700">Baseline:</span>
              <strong
                [ngClass]="{
                  'text-emerald-700': store.baselineState() === 'VALID',
                  'text-amber-700': store.baselineState() === 'STALE',
                  'text-slate-600': store.baselineState() === 'NOT_AVAILABLE'
                }"
                class="font-semibold">
                {{ store.baselineState() }}
              </strong>
            </div>

          </div>

          <!-- Drawer Action Button -->
          <button
            type="button"
            (click)="store.toggleTechnicalDrawer(true)"
            class="h-9 px-3.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-2xs">
            <app-lucide-icon name="info" [size]="13" class="text-slate-500" />
            <span>Inspect Technical Provenance</span>
          </button>

        </div>

      </div>

      <!-- Action Toast Notice -->
      @if (store.actionNotice(); as notice) {
        <div class="mt-4 p-3 rounded-lg bg-blue-50 border border-blue-200 text-xs text-blue-800 flex items-center gap-2 animate-in fade-in duration-150">
          <app-lucide-icon name="info" [size]="14" class="text-blue-600 shrink-0" />
          <span>{{ notice }}</span>
        </div>
      }
    </section>
  `
})
export class ResultsVerdictBannerComponent {
  readonly store = inject(ValidationResultsService);
}
