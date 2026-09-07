import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-cockpit-execution-context',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      <div class="flex items-center gap-2.5 pb-4 border-b border-slate-100">
        <app-lucide-icon name="git-merge" [size]="18" class="text-blue-600" />
        <h3 class="text-base font-bold text-slate-900 tracking-tight font-heading">Execution Context &amp; Sequence Flow</h3>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-5 relative">
        
        <!-- PREVIOUS STAGE -->
        <div class="rounded-xl border border-slate-200 bg-slate-50/60 p-5 flex flex-col justify-between min-h-[135px] shadow-2xs">
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Previous Completed</span>
            <span class="px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-200 inline-flex items-center gap-1">
              <app-lucide-icon name="check" [size]="11" class="text-slate-600" />
              <span>Finished</span>
            </span>
          </div>

          <div class="flex flex-col gap-1.5 my-1">
            <h4 class="text-xs font-bold text-slate-900 font-heading line-clamp-1">
              {{ cleanText(store.executionContext().previousCompleted.stageName) }}
            </h4>
            <p class="text-[11px] text-slate-500 leading-relaxed line-clamp-2">
              {{ cleanText(store.executionContext().previousCompleted.summary) }}
            </p>
          </div>

          <div class="mt-3 pt-2.5 border-t border-slate-200/60 text-[10px] font-mono text-slate-400">
            Completed: {{ store.executionContext().previousCompleted.completedAt }}
          </div>
        </div>

        <!-- NOW ACTIVE STAGE (Blue Enterprise Accent) -->
        <div class="rounded-xl border border-blue-400 bg-blue-50/30 p-5 flex flex-col justify-between min-h-[135px] shadow-xs ring-1 ring-blue-500/20">
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="text-[10px] font-bold uppercase tracking-wider text-blue-800">Now Executing</span>
            <span class="px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-blue-600 text-white border border-blue-600 inline-flex items-center gap-1 shadow-3xs">
              <span class="w-1.5 h-1.5 rounded-sm bg-white animate-pulse"></span>
              <span>Active</span>
            </span>
          </div>

          <div class="flex flex-col gap-1.5 my-1">
            <h4 class="text-xs font-bold text-slate-900 font-heading line-clamp-1">
              {{ cleanText(store.executionContext().currentNow.stageName) }}
            </h4>
            <p class="text-[11px] text-slate-600 leading-relaxed line-clamp-2">
              {{ cleanText(store.executionContext().currentNow.summary) }}
            </p>
          </div>

          <div class="mt-3 pt-2.5 border-t border-blue-200/60 text-[10px] font-mono text-blue-700 font-medium">
            Active since: {{ store.executionContext().currentNow.activeSince }}
          </div>
        </div>

        <!-- NEXT PLANNED STAGE -->
        <div class="rounded-xl border border-slate-200 bg-slate-50/60 p-5 flex flex-col justify-between min-h-[135px] shadow-2xs">
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Next Planned</span>
            <span [ngClass]="store.executionContext().nextPlanned.isBlocked ? 'bg-amber-100 text-amber-800 border-amber-200' : 'bg-slate-100 text-slate-600 border-slate-200'"
                  class="px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border inline-flex items-center gap-1 shadow-3xs">
              @if (store.executionContext().nextPlanned.isBlocked) {
                <app-lucide-icon name="shield-alert" [size]="11" class="text-amber-700" />
                <span>Barrier Gate</span>
              } @else {
                <span>Queued</span>
              }
            </span>
          </div>

          <div class="flex flex-col gap-1.5 my-1">
            <h4 class="text-xs font-bold text-slate-800 font-heading line-clamp-1">
              {{ cleanText(store.executionContext().nextPlanned.stageName) }}
            </h4>
            <p class="text-[11px] text-slate-500 leading-relaxed line-clamp-2">
              {{ cleanText(store.executionContext().nextPlanned.summary) }}
            </p>
          </div>

          <div class="mt-3 pt-2.5 border-t border-slate-200/60 text-[10px] text-slate-500">
            @if (store.executionContext().nextPlanned.dependencyNotice) {
              <span class="font-semibold text-amber-700">{{ cleanText(store.executionContext().nextPlanned.dependencyNotice) }}</span>
            } @else {
              <span class="text-slate-400">Auto-proceeds on completion</span>
            }
          </div>
        </div>

      </div>
    </section>
  `
})
export class CockpitExecutionContextComponent {
  public store = inject(CockpitStoreService);

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }
}
