import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';
import { PlanDagNode, PlanWorkObject } from './step7-plan.models';

@Component({
  selector: 'app-step7-stage-drawer',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <!-- BACKDROP -->
    <div
      (click)="store.closeStageDrawer()"
      class="fixed inset-0 bg-slate-900/40 z-40 transition-opacity">
    </div>

    <!-- SLIDE-OVER DRAWER -->
    <aside
      class="fixed inset-y-0 right-0 w-[540px] max-w-full bg-white border-l border-slate-200 z-50 flex flex-col font-sans select-none shadow-none">
      
      <!-- 1. HEADER -->
      <header class="p-4 border-b border-slate-200 flex items-center justify-between gap-3 shrink-0 bg-slate-50/70">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shrink-0">
            <app-lucide-icon [name]="getStageIcon(stage()?.stageType || '')" [size]="16"></app-lucide-icon>
          </div>
          <div class="flex flex-col min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono font-bold text-slate-500">STAGE {{ stage()?.order }}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200">
                {{ stage()?.category }}
              </span>
            </div>
            <h3 class="text-sm font-bold text-slate-900 m-0 truncate">{{ stage()?.label }}</h3>
          </div>
        </div>

        <button
          type="button"
          (click)="store.closeStageDrawer()"
          class="w-7 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-800 flex items-center justify-center cursor-pointer transition-colors"
          title="Close Stage Details">
          <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
        </button>
      </header>

      <!-- 2. SCROLLABLE BODY -->
      <div class="flex-1 overflow-y-auto p-5 flex flex-col gap-6">
        
        <!-- SECTION A: WORK & PROVENANCE METRICS -->
        <section class="flex flex-col gap-2.5">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
            <app-lucide-icon name="bar-chart-2" [size]="13" class="text-slate-500"></app-lucide-icon>
            <span>Work & Provenance Metrics</span>
          </h4>

          <div class="grid grid-cols-2 gap-2.5">
            
            <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-1">
              <div class="flex items-center justify-between text-[11px] text-slate-500">
                <span>Assigned Objects</span>
                <span class="px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[9.5px] font-bold">
                  Exact
                </span>
              </div>
              <span class="text-base font-bold text-slate-900">
                {{ stage()?.workObjects?.length || 0 }} objects
              </span>
            </div>

            <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-1">
              <div class="flex items-center justify-between text-[11px] text-slate-500">
                <span>Estimated Rows</span>
                <span class="px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[9.5px] font-bold">
                  Exact
                </span>
              </div>
              <span class="text-base font-bold text-slate-900">
                {{ formatTotalRows() }}
              </span>
            </div>

            <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-1">
              <div class="flex items-center justify-between text-[11px] text-slate-500">
                <span>Data Volume</span>
                <span class="px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[9.5px] font-bold">
                  Estimated
                </span>
              </div>
              <span class="text-base font-bold text-slate-900">
                {{ formatTotalSize() }}
              </span>
            </div>

            <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-1">
              <div class="flex items-center justify-between text-[11px] text-slate-500">
                <span>Duration</span>
                <span class="px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[9.5px] font-bold">
                  Estimated
                </span>
              </div>
              <span class="text-base font-bold text-slate-900">
                {{ stage()?.estimatedDuration }}
              </span>
            </div>

          </div>
        </section>

        <!-- SECTION B: SEARCHABLE WORK OBJECTS -->
        <section class="flex flex-col gap-2.5">
          <div class="flex items-center justify-between gap-2">
            <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
              <app-lucide-icon name="database" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Assigned Work Objects</span>
            </h4>
            <span class="text-[11px] text-slate-500 font-medium">
              Showing {{ filteredObjects().length }} of {{ stage()?.workObjects?.length || 0 }}
            </span>
          </div>

          <!-- Search Input -->
          <div class="relative flex items-center">
            <app-lucide-icon name="search" [size]="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
            <input
              type="text"
              [(ngModel)]="searchQuery"
              placeholder="Search objects by name or schema..."
              class="w-full h-8 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-blue-500" />
          </div>

          <!-- Objects Table -->
          <div class="border border-slate-200 rounded-lg overflow-hidden bg-white">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-semibold text-slate-600">
                  <th class="py-2 px-3">Object</th>
                  <th class="py-2 px-2">Type</th>
                  <th class="py-2 px-2">Strategy</th>
                  <th class="py-2 px-3 text-right">Rows</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-[11.5px]">
                @for (obj of filteredObjects(); track obj.id) {
                  <tr class="hover:bg-slate-50/50">
                    <td class="py-2 px-3 font-mono font-medium text-slate-800 truncate max-w-[170px]" title="{{ obj.schema }}.{{ obj.name }}">
                      {{ obj.schema }}.{{ obj.name }}
                    </td>
                    <td class="py-2 px-2">
                      <span class="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 text-[10px] font-bold">
                        {{ obj.type }}
                      </span>
                    </td>
                    <td class="py-2 px-2 text-slate-600 truncate max-w-[120px] text-[11px]">
                      {{ obj.strategy }}
                    </td>
                    <td class="py-2 px-3 text-right font-mono text-slate-700 font-semibold">
                      {{ obj.estimatedRows.toLocaleString() }}
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="4" class="py-4 text-center text-xs text-slate-400">
                      No objects match search criteria.
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>

        <!-- SECTION C: RESOLVED RUNTIME CONFIGURATION (READ-ONLY) -->
        <section class="flex flex-col gap-2.5">
          <div class="flex items-center justify-between gap-2">
            <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
              <app-lucide-icon name="settings-2" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Resolved Configuration</span>
            </h4>

            <button
              type="button"
              (click)="store.routeToUpstreamStep(6)"
              class="text-[11px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer transition-colors"
              title="Modify in Step 6: Configuration">
              <span>Review in Configuration (Step 6)</span>
              <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
            </button>
          </div>

          <div class="bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex flex-col gap-2.5 text-xs">
            <div class="grid grid-cols-2 gap-y-2 gap-x-4">
              <div>
                <span class="text-[11px] text-slate-500">Worker Allocation:</span>
                <p class="font-semibold text-slate-900 m-0">{{ stage()?.resolvedConfig?.workerAllocation || 16 }} Concurrency Threads</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Batch / Chunk Buffer:</span>
                <p class="font-semibold text-slate-900 m-0">{{ stage()?.resolvedConfig?.batchSizeMb || 16 }} MB per batch</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Checkpoint Interval:</span>
                <p class="font-semibold text-slate-900 m-0">{{ stage()?.resolvedConfig?.checkpointIntervalSec || 60 }} seconds</p>
              </div>

              <div>
                <span class="text-[11px] text-slate-500">Timeout Limit:</span>
                <p class="font-semibold text-slate-900 m-0">{{ stage()?.resolvedConfig?.timeoutMinutes || 180 }} minutes</p>
              </div>

              <div class="col-span-2">
                <span class="text-[11px] text-slate-500">Recovery Strategy:</span>
                <p class="font-semibold text-slate-900 m-0">{{ stage()?.resolvedConfig?.recoveryStrategy || 'Point-in-Time Checkpoint Recovery (WAL-bound)' }}</p>
              </div>

              <div class="col-span-2">
                <span class="text-[11px] text-slate-500">Retry Policy:</span>
                <p class="font-semibold text-slate-900 m-0">{{ stage()?.resolvedConfig?.retryPolicy || 'Exponential backoff (3 attempts, max 30s jitter)' }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- SECTION D: DEPENDENCY TOPOLOGY -->
        <section class="flex flex-col gap-2.5">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
            <app-lucide-icon name="git-fork" [size]="13" class="text-slate-500"></app-lucide-icon>
            <span>Topology Dependencies</span>
          </h4>

          <div class="grid grid-cols-2 gap-2.5 text-xs">
            <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-1">
              <span class="text-[11px] font-semibold text-slate-500">Prerequisites (Inbound)</span>
              @if (stage()?.incomingDependencyIds?.length) {
                <ul class="list-disc list-inside text-slate-800 m-0 pl-1">
                  @for (dep of stage()?.incomingDependencyIds; track dep) {
                    <li class="truncate text-[11.5px] font-mono">{{ dep }}</li>
                  }
                </ul>
              } @else {
                <span class="text-slate-400 text-[11px]">None (Root Stage)</span>
              }
            </div>

            <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-1">
              <span class="text-[11px] font-semibold text-slate-500">Downstream (Outbound)</span>
              @if (stage()?.outgoingDependencyIds?.length) {
                <ul class="list-disc list-inside text-slate-800 m-0 pl-1">
                  @for (dep of stage()?.outgoingDependencyIds; track dep) {
                    <li class="truncate text-[11.5px] font-mono">{{ dep }}</li>
                  }
                </ul>
              } @else {
                <span class="text-slate-400 text-[11px]">None (Terminal Stage)</span>
              }
            </div>
          </div>
        </section>

      </div>

    </aside>
  `
})
export class Step7StageDrawerComponent {
  public store = inject(Step7PlanStoreService);
  public searchQuery = '';

  public stage = computed(() => this.store.selectedStage());

  public filteredObjects = computed(() => {
    const s = this.stage();
    if (!s || !s.workObjects) return [];
    const q = this.searchQuery.trim().toLowerCase();
    if (!q) return s.workObjects;
    return s.workObjects.filter(o =>
      o.name.toLowerCase().includes(q) || o.schema.toLowerCase().includes(q)
    );
  });

  public getStageIcon(stageType: string): string {
    switch (stageType) {
      case 'PRE_FLIGHT': return 'check-circle-2';
      case 'SCHEMA_DDL': return 'code-2';
      case 'DATA_PREPARATION': return 'wrench';
      case 'BULK_EXTRACT': return 'database';
      case 'BULK_LOAD': return 'upload';
      case 'CDC_CAPTURE': return 'radio';
      case 'CDC_APPLY': return 'zap';
      case 'STATE_COMPARE': return 'git-compare';
      case 'INDEX_REBUILD': return 'file-code-2';
      case 'POST_VALIDATION': return 'shield-check';
      case 'CUTOVER': return 'flag';
      case 'ROLLBACK_GUARD': return 'rotate-ccw';
      default: return 'workflow';
    }
  }

  public formatTotalRows(): string {
    const s = this.stage();
    if (!s || !s.workObjects) return '0';
    const sum = s.workObjects.reduce((acc, o) => acc + (o.estimatedRows || 0), 0);
    return sum.toLocaleString();
  }

  public formatTotalSize(): string {
    const s = this.stage();
    if (!s || !s.workObjects) return '0 MB';
    const sum = s.workObjects.reduce((acc, o) => acc + (o.estimatedSizeBytes || 0), 0);
    if (sum > 1024 * 1024 * 1024) {
      return (sum / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
    }
    return (sum / (1024 * 1024)).toFixed(0) + ' MB';
  }
}
