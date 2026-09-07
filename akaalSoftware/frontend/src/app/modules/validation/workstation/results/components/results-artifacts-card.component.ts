import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-artifacts-card',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 mb-5 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
            <app-lucide-icon name="download" [size]="16" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">
              Artifacts &amp; Export Packages
            </h2>
            <p class="text-xs text-slate-500">
              Canonical validation summaries and evidence package exports
            </p>
          </div>
        </div>

        <div class="text-xs text-slate-500 font-sans">
          Governed Exports
        </div>
      </div>

      <!-- Artifacts List -->
      @if (store.artifacts().generationAvailable && store.artifacts().artifacts.length > 0) {
        
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          @for (art of store.artifacts().artifacts; track art.id) {
            <div class="p-4 rounded-xl bg-slate-50/80 border border-slate-200/90 flex flex-col justify-between gap-3 shadow-2xs">
              <div class="flex flex-col gap-1.5">
                <div class="flex items-center justify-between">
                  <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-slate-200 text-slate-800">
                    {{ art.format }}
                  </span>
                  @if (art.ready) {
                    <span class="text-[10px] font-semibold text-emerald-700 flex items-center gap-1">
                      <app-lucide-icon name="check-circle" [size]="11" />
                      <span>Ready</span>
                    </span>
                  }
                </div>

                <span class="text-xs font-bold text-slate-900 font-heading pt-1">
                  {{ art.name }}
                </span>
                <p class="text-[11px] text-slate-600 leading-relaxed">
                  {{ art.description }}
                </p>
              </div>

              <button
                type="button"
                (click)="store.triggerArtifactAction(art.name)"
                class="w-full h-8 px-3 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                <app-lucide-icon name="download" [size]="12" class="text-slate-500" />
                <span>Export {{ art.format }}</span>
              </button>
            </div>
          }
        </div>

      } @else {
        
        <!-- Truthful Unavailable State (Directive #12) -->
        <div class="p-5 rounded-xl bg-slate-50/60 border border-slate-200/80 text-center flex flex-col items-center justify-center gap-2 text-slate-500 py-8">
          <app-lucide-icon name="download" [size]="24" class="text-slate-400" />
          <span class="text-xs font-medium text-slate-700">Artifact generation is not currently available</span>
          <p class="text-[11px] text-slate-500 max-w-md">
            {{ store.artifacts().availabilityNotice || 'Authoritative export packages and PDF summary generation will become active upon export backend integration.' }}
          </p>
        </div>

      }

    </section>
  `
})
export class ResultsArtifactsCardComponent {
  readonly store = inject(ValidationResultsService);
}
