import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DiscrepancyViewStatus } from '../validation-discrepancies.models';
import { ValidationDiscrepanciesService } from '../validation-discrepancies.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-discrepancies-states',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @switch (status) {
      
      <!-- State 1: EMPTY (Canonical Pass / Zero Discrepancies Established) -->
      @case ('EMPTY') {
        <section class="bg-white border border-slate-200/80 rounded-xl p-14 lg:p-16 shadow-2xs flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-10 gap-5">
          <div class="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shadow-2xs">
            <app-lucide-icon name="check-circle-2" [size]="32"></app-lucide-icon>
          </div>

          <div class="flex flex-col gap-2 max-w-md">
            <h3 class="text-base font-bold text-slate-900 font-heading">
              No Discrepancies Established
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              No row-level differences, cardinality mismatches, or schema divergences were detected across the evaluated validation scope.
            </p>
          </div>

          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-600 w-full max-w-sm">
            Validation Proof Gate: All Executed Tiers Matched
          </div>
        </section>
      }

      <!-- State 2: NOT_EVALUATED (Standby / Prior to Run) -->
      @case ('NOT_EVALUATED') {
        <section class="bg-white border border-slate-200/80 rounded-xl p-14 lg:p-16 shadow-2xs flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-10 gap-5">
          <div class="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 shadow-2xs">
            <app-lucide-icon name="clock" [size]="32"></app-lucide-icon>
          </div>

          <div class="flex flex-col gap-2 max-w-md">
            <h3 class="text-base font-bold text-slate-900 font-heading">
              Validation Not Evaluated
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              Validation execution has not been evaluated for this mission yet. Discrepancy findings and mismatch localization will generate upon mission execution.
            </p>
          </div>
        </section>
      }

      <!-- State 3: UNAVAILABLE (Engine Disconnected / Production Default) -->
      @case ('UNAVAILABLE') {
        <section class="bg-white border border-slate-200/80 rounded-xl p-14 lg:p-16 shadow-2xs flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-10 gap-5">
          <div class="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 shadow-2xs">
            <app-lucide-icon name="network" [size]="32"></app-lucide-icon>
          </div>

          <div class="flex flex-col gap-2 max-w-md">
            <h3 class="text-base font-bold text-slate-900 font-heading">
              Discrepancy Results Unavailable
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              Canonical discrepancy stream is not currently linked to the validation daemon. The workspace interface structure is ready for backend streaming upon daemon connection.
            </p>
          </div>

          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-500 w-full max-w-sm">
            Status: Truthful Standby Mode (Zero Inferred Data)
          </div>
        </section>
      }

      <!-- State 4: LOADING (Calm Skeleton) -->
      @case ('LOADING') {
        <div class="flex flex-col gap-5 animate-pulse">
          <div class="h-24 bg-slate-200/60 rounded-xl w-full"></div>
          <div class="h-14 bg-slate-200/60 rounded-xl w-full"></div>
          <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div class="h-96 bg-slate-200/60 rounded-xl col-span-1"></div>
            <div class="h-96 bg-slate-200/60 rounded-xl col-span-3"></div>
          </div>
        </div>
      }

      <!-- State 5: ERROR -->
      @case ('ERROR') {
        <section class="bg-white border border-rose-200 rounded-xl p-14 lg:p-16 shadow-2xs flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-10 gap-5">
          <div class="w-16 h-16 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 shadow-2xs">
            <app-lucide-icon name="alert-octagon" [size]="32"></app-lucide-icon>
          </div>

          <div class="flex flex-col gap-2 max-w-md">
            <h3 class="text-base font-bold text-slate-900 font-heading">
              Failed to Retrieve Discrepancy Stream
            </h3>
            <p class="text-xs text-rose-700 leading-relaxed">
              {{ errorMessage || 'An unexpected error occurred while communicating with the validation stream authority.' }}
            </p>
          </div>

          <button
            type="button"
            (click)="retry()"
            class="px-4 py-2.5 rounded-lg bg-rose-600 text-white hover:bg-rose-700 text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer shadow-2xs">
            <app-lucide-icon name="refresh-cw" [size]="14"></app-lucide-icon>
            <span>Retry Connection</span>
          </button>
        </section>
      }

    }
  `
})
export class DiscrepanciesStatesComponent {
  @Input({ required: true }) status!: DiscrepancyViewStatus;
  @Input() errorMessage?: string;

  private readonly store = inject(ValidationDiscrepanciesService);

  retry(): void {
    this.store.setViewStatus('LOADING');
    setTimeout(() => {
      this.store.setFixture('NORMAL_19_FINDINGS');
    }, 1000);
  }
}
