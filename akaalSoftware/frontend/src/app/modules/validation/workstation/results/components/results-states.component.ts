import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResultsViewStatus } from '../validation-results.models';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-states',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="bg-white border border-slate-200 rounded-xl p-8 sm:p-12 shadow-2xs flex flex-col items-center justify-center text-center max-w-3xl mx-auto my-8 gap-6 animate-in fade-in duration-150">
      
      @switch (status) {
        
        <!-- NOT_EVALUATED -->
        @case ('NOT_EVALUATED') {
          <div class="w-14 h-14 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 shadow-2xs">
            <app-lucide-icon name="clock" [size]="28" />
          </div>
          <div class="flex flex-col gap-2 max-w-lg">
            <h2 class="text-base sm:text-lg font-bold text-slate-900 font-heading">
              Validation Mission Not Yet Evaluated
            </h2>
            <p class="text-xs text-slate-600 leading-relaxed">
              This validation mission is configured and ready in standby. Comprehensive results, 4-tier assurance proof, and content integrity digests are recorded once execution completes.
            </p>
          </div>
          <div class="p-4 rounded-lg bg-slate-50 border border-slate-200 text-left w-full text-xs flex flex-col gap-2 text-slate-700">
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-sans">Mission ID:</span>
              <span class="font-mono font-bold text-slate-900">{{ store.validationId() }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-sans">Execution Status:</span>
              <span class="font-semibold text-slate-700 font-mono">{{ store.executionState() }}</span>
            </div>
          </div>
        }

        <!-- WITHHELD -->
        @case ('WITHHELD') {
          <div class="w-14 h-14 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shadow-2xs">
            <app-lucide-icon name="shield-off" [size]="28" />
          </div>
          <div class="flex flex-col gap-2 max-w-lg">
            <h2 class="text-base sm:text-lg font-bold text-slate-900 font-heading">
              Validation Proof Withheld
            </h2>
            <p class="text-xs text-slate-600 leading-relaxed">
              Validation #11 authority withheld final verdict due to read-boundary lease expiration or concurrent mutation drift on active source. Proof cannot be certified in this state.
            </p>
          </div>
          <div class="p-4 rounded-lg bg-amber-50/50 border border-amber-200 text-left w-full text-xs flex flex-col gap-2 text-amber-900">
            <div class="flex items-center justify-between">
              <span class="text-amber-700 font-sans">Withheld Reason:</span>
              <span class="font-medium">Read Consistency Window Lease Exceeded</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-amber-700 font-sans">Recommended Action:</span>
              <span>Re-run validation under isolated or quiet transaction window</span>
            </div>
          </div>
        }

        <!-- UNAVAILABLE -->
        @case ('UNAVAILABLE') {
          <div class="w-14 h-14 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 shadow-2xs">
            <app-lucide-icon name="file-x" [size]="28" />
          </div>
          <div class="flex flex-col gap-2 max-w-lg">
            <h2 class="text-base sm:text-lg font-bold text-slate-900 font-heading">
              Results &amp; Evidence Unavailable
            </h2>
            <p class="text-xs text-slate-600 leading-relaxed">
              Validation results data is not available for the requested mission identifier.
            </p>
          </div>
        }

        <!-- LOADING -->
        @case ('LOADING') {
          <div class="w-14 h-14 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 animate-spin shadow-2xs">
            <app-lucide-icon name="refresh-cw" [size]="28" />
          </div>
          <div class="flex flex-col gap-2 max-w-lg">
            <h2 class="text-base sm:text-lg font-bold text-slate-900 font-heading">
              Loading Validation Results...
            </h2>
            <p class="text-xs text-slate-600 leading-relaxed">
              Retrieving execution summaries, 4-tier assurance proof records, and content integrity data.
            </p>
          </div>
        }

        <!-- ERROR -->
        @case ('ERROR') {
          <div class="w-14 h-14 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 shadow-2xs">
            <app-lucide-icon name="alert-triangle" [size]="28" />
          </div>
          <div class="flex flex-col gap-2 max-w-lg">
            <h2 class="text-base sm:text-lg font-bold text-slate-900 font-heading">
              Failed to Retrieve Results
            </h2>
            <p class="text-xs text-slate-600 leading-relaxed">
              {{ errorMessage || 'An unexpected error occurred while loading validation results.' }}
            </p>
          </div>
        }

        @default {
          <div class="w-14 h-14 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500">
            <app-lucide-icon name="help-circle" [size]="28" />
          </div>
          <p class="text-xs text-slate-600">Standby</p>
        }

      }

    </div>
  `
})
export class ResultsStatesComponent {
  readonly store = inject(ValidationResultsService);
  @Input() status: ResultsViewStatus = 'NOT_EVALUATED';
  @Input() errorMessage?: string;
}
