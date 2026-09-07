import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-cockpit-current-activity',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      <!-- Section Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="activity" [size]="18" class="text-blue-600" />
          <h3 class="text-base font-bold text-slate-900 tracking-tight font-heading">Active Physical Execution</h3>
        </div>
        
        <div class="flex items-center gap-2">
          @if (store.currentActivity().isStalled) {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200">
              <span class="w-2 h-2 rounded-sm bg-rose-500 animate-pulse"></span>
              <span>I/O Stalled</span>
            </span>
          } @else {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200">
              <span class="w-2 h-2 rounded-sm bg-blue-500 animate-pulse"></span>
              <span>Active Physical Stream</span>
            </span>
          }
        </div>
      </div>

      <!-- Execution Parameters Grid with Generous Spacing -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        
        <!-- Target Entity & Stage -->
        <div class="bg-white hover:border-blue-200 border border-slate-200 rounded-xl p-5 flex flex-col justify-between min-h-[115px] transition-colors shadow-xs">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Target Entity</span>
            <app-lucide-icon name="database" [size]="15" class="text-slate-400" />
          </div>
          <div class="my-1">
            <span class="font-mono text-sm font-bold text-slate-900 tracking-tight block truncate" [title]="store.currentActivity().activeEntityName">
              {{ cleanText(store.currentActivity().activeEntityName) }}
            </span>
            <div class="text-[11px] text-slate-500 mt-1.5">
              {{ cleanText(store.currentActivity().entityType) }} &middot; {{ cleanText(store.currentActivity().activeStageName) }}
            </div>
          </div>
        </div>

        <!-- Partition / Chunk Index -->
        <div class="bg-white hover:border-blue-200 border border-slate-200 rounded-xl p-5 flex flex-col justify-between min-h-[115px] transition-colors shadow-xs">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Partition / Chunk</span>
            <app-lucide-icon name="git-branch" [size]="15" class="text-slate-400" />
          </div>
          <div class="my-1">
            <span class="font-mono text-xs font-bold text-slate-900 block truncate" [title]="store.currentActivity().partitionChunkInfo">
              {{ cleanText(store.currentActivity().partitionChunkInfo) }}
            </span>
            <div class="text-[11px] text-slate-500 mt-1.5">Parallel boundary split</div>
          </div>
        </div>

        <!-- Worker Concurrency Ratio -->
        <div class="bg-white hover:border-blue-200 border border-slate-200 rounded-xl p-5 flex flex-col justify-between min-h-[115px] transition-colors shadow-xs">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Concurrency Ratio</span>
            <app-lucide-icon name="cpu" [size]="15" class="text-slate-400" />
          </div>
          <div class="my-1">
            <div class="flex items-baseline gap-1.5">
              <span class="font-mono text-base font-bold text-slate-900">
                {{ store.currentActivity().activeWorkerCount }} / {{ store.currentActivity().totalWorkerCount }}
              </span>
              <span class="text-xs text-slate-600 font-medium">threads active</span>
            </div>
            <div class="text-[11px] text-slate-400 mt-1.5">Pool saturation: 100%</div>
          </div>
        </div>

        <!-- Checkpoint Boundary Context -->
        <div class="bg-white hover:border-blue-200 border border-slate-200 rounded-xl p-5 flex flex-col justify-between min-h-[115px] transition-colors shadow-xs">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Checkpoint State</span>
            <app-lucide-icon name="hard-drive" [size]="15" class="text-slate-400" />
          </div>
          <div class="my-1">
            <span class="font-mono text-xs font-bold text-slate-900 truncate block" [title]="store.currentActivity().checkpointContext">
              {{ cleanText(store.currentActivity().checkpointContext) }}
            </span>
            <div class="text-[11px] text-emerald-700 font-semibold mt-1.5 flex items-center gap-1">
              <app-lucide-icon name="shield-check" [size]="12" />
              <span>Durable on target WAL</span>
            </div>
          </div>
        </div>

      </div>
    </section>
  `
})
export class CockpitCurrentActivityComponent {
  public store = inject(CockpitStoreService);

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }
}
