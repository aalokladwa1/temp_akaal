import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-audit-timeline',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 mb-5 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
            <app-lucide-icon name="list" [size]="16" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">
              Chronological Audit Trail
            </h2>
            <p class="text-xs text-slate-500">
              Verifiable event log recorded during mission lifecycle
            </p>
          </div>
        </div>

        @if (store.auditTimeline().length > 0) {
          <div class="text-xs text-slate-500 font-mono">
            {{ store.auditTimeline().length }} events recorded
          </div>
        }
      </div>

      <!-- Timeline Content -->
      @if (store.auditTimeline().length > 0) {
        
        <div class="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
          @for (event of store.auditTimeline(); track event.id) {
            <div class="relative flex items-start gap-3.5 group">
              
              <!-- Timeline Marker Node -->
              <div class="absolute -left-6 sm:-left-8 mt-1 w-6 h-6 rounded-full bg-white border-2 border-blue-500 flex items-center justify-center text-blue-600 shadow-2xs">
                <span class="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
              </div>

              <!-- Event Details Card -->
              <div class="flex-1 p-4 rounded-xl bg-slate-50/80 border border-slate-200/80 flex flex-col gap-1.5 shadow-2xs">
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <div class="flex items-center gap-2">
                    <span
                      [ngClass]="{
                        'bg-blue-50 text-blue-700 border-blue-200': event.category === 'VALIDATION',
                        'bg-purple-50 text-purple-700 border-purple-200': event.category === 'REMEDIATION',
                        'bg-emerald-50 text-emerald-700 border-emerald-200': event.category === 'EVIDENCE',
                        'bg-slate-100 text-slate-700 border-slate-200': event.category === 'SYSTEM'
                      }"
                      class="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded border">
                      {{ event.category }}
                    </span>
                    <span class="text-xs font-bold text-slate-900 font-heading">
                      {{ event.title }}
                    </span>
                  </div>

                  <span class="text-[11px] text-slate-500 font-sans">
                    {{ event.timestamp | date:'medium' }}
                  </span>
                </div>

                <p class="text-xs text-slate-600 leading-relaxed">
                  {{ event.description }}
                </p>

                @if (event.actor) {
                  <div class="flex items-center gap-1.5 text-[11px] text-slate-500 pt-1">
                    <app-lucide-icon name="user" [size]="11" class="text-slate-400" />
                    <span>Actor: <strong class="font-mono text-slate-700">{{ event.actor }}</strong></span>
                  </div>
                }
              </div>

            </div>
          }
        </div>

      } @else {
        
        <!-- Empty / Standby Timeline -->
        <div class="p-5 rounded-xl bg-slate-50/60 border border-slate-200/80 text-center flex flex-col items-center justify-center gap-2 text-slate-500 py-8">
          <app-lucide-icon name="list" [size]="24" class="text-slate-400" />
          <span class="text-xs font-medium text-slate-700">Audit event history is not currently available</span>
          <p class="text-[11px] text-slate-500 max-w-md">
            Chronological audit events are emitted during active validation execution and remediation cycles.
          </p>
        </div>

      }

    </section>
  `
})
export class ResultsAuditTimelineComponent {
  readonly store = inject(ValidationResultsService);
}
