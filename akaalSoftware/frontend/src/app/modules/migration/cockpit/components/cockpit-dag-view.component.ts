import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { RuntimeDagNode, RuntimeDagNodeState } from '../cockpit.models';

@Component({
  selector: 'app-cockpit-dag-view',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      <!-- Section Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="git-branch" [size]="18" class="text-blue-600" />
          <h3 class="text-base font-bold text-slate-900 tracking-tight font-heading">Execution Plan Topology (Runtime DAG)</h3>
          <span class="text-xs text-slate-400 font-medium">&middot; Active Neighborhood</span>
        </div>

        <div class="flex items-center gap-2.5">
          @if (store.selectedNode()) {
            <button
              (click)="store.selectDagNode(null)"
              class="text-xs text-slate-600 hover:text-blue-700 font-semibold px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-blue-50 border border-transparent hover:border-blue-200 transition-colors cursor-pointer">
              Clear Selection
            </button>
          }
          <button
            (click)="store.toggleFullDagModal(true)"
            class="h-8 px-3 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50 text-slate-700 hover:text-blue-700 transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs">
            <app-lucide-icon name="maximize-2" [size]="13" />
            <span>View Full Plan DAG</span>
          </button>
        </div>
      </div>

      <!-- Neighborhood DAG Nodes Ribbon (Distinct Enterprise Semantic Color Coding) -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        @for (node of store.activeNeighborhood().nodes; track node.id) {
          <div
            (click)="store.selectDagNode(node.id)"
            [ngClass]="[
              getNodeCardClasses(node.runtimeState),
              store.selectedDagNodeId() === node.id ? 'ring-2 ring-blue-600 shadow-md' : 'shadow-xs'
            ]"
            class="relative rounded-xl border p-5 transition-all cursor-pointer flex flex-col justify-between min-h-[155px] group">
            
            <!-- Top: Order & State Badge (Rectangular with curved corners) -->
            <div class="flex items-center justify-between gap-3 mb-3">
              <span class="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                Step {{ node.order }}
              </span>
              <span [ngClass]="getNodeStateBadgeClasses(node.runtimeState)"
                    class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border inline-flex items-center gap-1.5 shadow-xs">
                <app-lucide-icon [name]="getNodeStateIcon(node.runtimeState)" [size]="11" />
                <span>{{ cleanText(formatStateLabel(node.runtimeState)) }}</span>
              </span>
            </div>

            <!-- Middle: Stage Name & Subtitle with proper line spacing -->
            <div class="flex flex-col gap-1.5 my-1">
              <h4 class="text-xs font-bold leading-snug line-clamp-2" [ngClass]="getNodeTitleColor(node.runtimeState)">
                {{ cleanText(node.label) }}
              </h4>
              <p class="text-[11px] leading-relaxed line-clamp-2" [ngClass]="getNodeSubtitleColor(node.runtimeState)">
                {{ cleanText(node.subtitle) }}
              </p>
            </div>

            <!-- Bottom: Metrics & Workers with generous padding -->
            <div class="mt-3 pt-3 border-t flex items-center justify-between text-[11px]" [ngClass]="getNodeDividerColor(node.runtimeState)">
              @if (node.progressPercent !== undefined) {
                <span class="font-mono font-bold text-slate-800">
                  {{ node.progressPercent }}%
                </span>
              } @else if (node.throughputFormatted) {
                <span class="font-mono font-bold text-slate-800">
                  {{ cleanText(node.throughputFormatted) }}
                </span>
              } @else {
                <span class="text-slate-400 font-mono text-[10px]">&mdash;</span>
              }

              @if (node.workerAllocation) {
                <span class="text-slate-600 font-medium">
                  {{ node.workerAllocation }} workers
                </span>
              } @else if (node.isBarrier) {
                <span class="text-purple-700 font-bold inline-flex items-center gap-1 bg-purple-100/80 px-2 py-0.5 rounded-md border border-purple-200">
                  <app-lucide-icon name="shield-check" [size]="11" />
                  <span>Gate</span>
                </span>
              } @else {
                <span class="font-mono text-[10px] uppercase text-slate-400">{{ cleanText(node.stageType) }}</span>
              }
            </div>

            <!-- Flow Connector Icon (for sequential flow) -->
            <div class="hidden lg:block absolute -right-3.5 top-1/2 -translate-y-1/2 z-10">
              <div class="w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-400 shadow-xs group-hover:border-blue-300 group-hover:text-blue-600 transition-colors">
                <app-lucide-icon name="chevron-right" [size]="12" />
              </div>
            </div>
          </div>
        }
      </div>

      <!-- Selected Node Detail Drawer (When clicked) -->
      @if (store.selectedNode(); as sel) {
        <div class="bg-blue-50/40 border border-blue-200 rounded-xl p-5 mt-2 flex flex-col gap-3.5 animate-in fade-in duration-100">
          <div class="flex items-center justify-between pb-3 border-b border-blue-200/80">
            <div class="flex items-center gap-2.5">
              <app-lucide-icon name="info" [size]="15" class="text-blue-600" />
              <span class="text-xs font-bold text-slate-900 font-heading">Node Properties: {{ cleanText(sel.label) }}</span>
              <span class="text-slate-300">&middot;</span>
              <span class="font-mono text-xs text-slate-600">ID: {{ cleanText(sel.id) }}</span>
            </div>
            <button
              (click)="store.selectDagNode(null)"
              class="w-7 h-7 flex items-center justify-center text-slate-400 hover:text-slate-700 rounded-md hover:bg-slate-100 cursor-pointer">
              <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
            </button>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div class="flex flex-col gap-1">
              <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Stage Type</div>
              <div class="font-bold text-slate-900">{{ cleanText(sel.stageType) }}</div>
            </div>
            <div class="flex flex-col gap-1">
              <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Runtime State</div>
              <div class="font-bold" [ngClass]="getNodeStateTextClasses(sel.runtimeState)">{{ cleanText(sel.runtimeState) }}</div>
            </div>
            <div class="flex flex-col gap-1">
              <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Worker Allocation</div>
              <div class="font-mono font-bold text-slate-900">{{ sel.workerAllocation || 0 }} threads</div>
            </div>
            <div class="flex flex-col gap-1">
              <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Dependencies</div>
              <div class="text-slate-700 font-mono text-[11px]">{{ sel.incomingNodeIds.length ? cleanText(sel.incomingNodeIds.join(', ')) : 'None (Root)' }}</div>
            </div>
          </div>

          @if (sel.failureMessage) {
            <div class="bg-rose-50 border border-rose-200 rounded-lg p-3.5 text-xs text-rose-800 flex items-start gap-2">
              <app-lucide-icon name="alert-circle" [size]="15" class="text-rose-600 shrink-0 mt-0.5" />
              <div><span class="font-bold">Error Condition:</span> {{ cleanText(sel.failureMessage) }}</div>
            </div>
          }
        </div>
      }
    </section>

    <!-- Full Plan DAG Topology Modal -->
    @if (store.isFullDagModalOpen()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-6 animate-in fade-in duration-150 backdrop-blur-xs">
        <div class="bg-white rounded-2xl border border-slate-200 max-w-5xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
          
          <!-- Modal Header -->
          <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-xs">
                <app-lucide-icon name="git-branch" [size]="18" />
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 font-heading">Complete Execution Plan DAG Topology</h3>
                <p class="text-xs text-slate-500">Ordered execution flow for {{ cleanText(store.identity().modeTitle) }}</p>
              </div>
            </div>

            <button
              (click)="store.toggleFullDagModal(false)"
              class="w-8 h-8 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 flex items-center justify-center text-slate-500 transition-colors cursor-pointer">
              <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
            </button>
          </div>

          <!-- Modal Body: Full Graph Node Sequence -->
          <div class="p-6 overflow-y-auto flex flex-col gap-4">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              @for (node of store.runtimeDag().nodes; track node.id) {
                <div
                  (click)="store.selectDagNode(node.id); store.toggleFullDagModal(false)"
                  [ngClass]="getNodeCardClasses(node.runtimeState)"
                  class="rounded-xl border p-5 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between min-h-[150px]">
                  
                  <div class="flex items-center justify-between gap-2 mb-2.5">
                    <span class="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                      Step {{ node.order }}
                    </span>
                    <span [ngClass]="getNodeStateBadgeClasses(node.runtimeState)"
                          class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border inline-flex items-center gap-1">
                      <app-lucide-icon [name]="getNodeStateIcon(node.runtimeState)" [size]="11" />
                      <span>{{ cleanText(formatStateLabel(node.runtimeState)) }}</span>
                    </span>
                  </div>

                  <div class="flex flex-col gap-1.5 my-1">
                    <h4 class="text-xs font-bold text-slate-900">{{ cleanText(node.label) }}</h4>
                    <p class="text-[11px] text-slate-500 leading-relaxed">{{ cleanText(node.subtitle) }}</p>
                  </div>

                  <div class="mt-3 pt-3 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
                    <span class="font-mono text-slate-600">{{ cleanText(node.stageType) }}</span>
                    @if (node.workerAllocation) {
                      <span class="text-slate-600 font-semibold">{{ node.workerAllocation }} workers</span>
                    }
                  </div>
                </div>
              }
            </div>
          </div>

          <!-- Modal Footer (Blue Enterprise Button) -->
          <div class="px-6 py-4 border-t border-slate-200 bg-slate-50/80 flex items-center justify-between">
            <span class="text-xs text-slate-600 font-medium">
              Total Stages: <strong class="text-slate-900 font-bold">{{ store.runtimeDag().nodes.length }}</strong>
            </span>
            <button
              (click)="store.toggleFullDagModal(false)"
              class="h-9 px-4 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white transition-colors cursor-pointer shadow-xs">
              Close Topology View
            </button>
          </div>
        </div>
      </div>
    }
  `
})
export class CockpitDagViewComponent {
  public store = inject(CockpitStoreService);

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }

  public formatStateLabel(state: RuntimeDagNodeState): string {
    switch (state) {
      case 'COMPLETED': return 'Completed';
      case 'ACTIVE': return 'Active';
      case 'RUNNING_PARALLEL': return 'In Progress';
      case 'WAITING': return 'Waiting';
      case 'APPROVAL_BARRIER': return 'Approval Gate';
      case 'FAILED': return 'Failed';
      case 'RECOVERING': return 'Recovering';
      case 'SKIPPED': return 'Skipped';
      case 'UPCOMING': return 'Upcoming';
      default: return state;
    }
  }

  public getNodeStateIcon(state: RuntimeDagNodeState): string {
    switch (state) {
      case 'COMPLETED': return 'check';
      case 'ACTIVE':
      case 'RUNNING_PARALLEL': return 'zap';
      case 'WAITING': return 'clock';
      case 'APPROVAL_BARRIER': return 'shield-alert';
      case 'FAILED': return 'alert-triangle';
      case 'RECOVERING': return 'rotate-ccw';
      default: return 'circle';
    }
  }

  public getNodeCardClasses(state: RuntimeDagNodeState): string {
    switch (state) {
      case 'ACTIVE':
      case 'RUNNING_PARALLEL':
        return 'border-blue-400 bg-blue-50/40 hover:bg-blue-50/70 hover:border-blue-500';
      case 'COMPLETED':
        return 'border-emerald-200 bg-emerald-50/30 hover:bg-emerald-50/60 hover:border-emerald-300';
      case 'WAITING':
        return 'border-amber-200 bg-amber-50/30 hover:bg-amber-50/60 hover:border-amber-300';
      case 'APPROVAL_BARRIER':
        return 'border-purple-300 bg-purple-50/40 hover:bg-purple-50/70 hover:border-purple-400';
      case 'FAILED':
        return 'border-rose-300 bg-rose-50/40 hover:bg-rose-50/70 hover:border-rose-400';
      case 'RECOVERING':
        return 'border-sky-300 bg-sky-50/40 hover:bg-sky-50/70 hover:border-sky-400';
      default:
        return 'border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300';
    }
  }

  public getNodeStateBadgeClasses(state: RuntimeDagNodeState): string {
    switch (state) {
      case 'ACTIVE':
      case 'RUNNING_PARALLEL':
        return 'bg-blue-600 text-white border-blue-600 font-bold';
      case 'COMPLETED':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200 font-bold';
      case 'WAITING':
        return 'bg-amber-100 text-amber-800 border-amber-200 font-bold';
      case 'APPROVAL_BARRIER':
        return 'bg-purple-100 text-purple-800 border-purple-200 font-bold';
      case 'FAILED':
        return 'bg-rose-100 text-rose-800 border-rose-200 font-bold';
      case 'RECOVERING':
        return 'bg-sky-100 text-sky-800 border-sky-200 font-bold';
      default:
        return 'bg-slate-100 text-slate-500 border-slate-200 font-medium';
    }
  }

  public getNodeTitleColor(state: RuntimeDagNodeState): string {
    switch (state) {
      case 'ACTIVE':
      case 'RUNNING_PARALLEL': return 'text-blue-950 font-heading';
      case 'COMPLETED': return 'text-slate-900 font-heading';
      case 'APPROVAL_BARRIER': return 'text-purple-950 font-heading';
      case 'FAILED': return 'text-rose-950 font-heading';
      default: return 'text-slate-800 font-heading';
    }
  }

  public getNodeSubtitleColor(state: RuntimeDagNodeState): string {
    switch (state) {
      case 'ACTIVE':
      case 'RUNNING_PARALLEL': return 'text-blue-800/80';
      case 'COMPLETED': return 'text-emerald-800/80';
      case 'APPROVAL_BARRIER': return 'text-purple-800/80';
      case 'FAILED': return 'text-rose-800/80';
      default: return 'text-slate-500';
    }
  }

  public getNodeDividerColor(state: RuntimeDagNodeState): string {
    switch (state) {
      case 'ACTIVE':
      case 'RUNNING_PARALLEL': return 'border-blue-200/80';
      case 'COMPLETED': return 'border-emerald-200/80';
      case 'APPROVAL_BARRIER': return 'border-purple-200/80';
      case 'FAILED': return 'border-rose-200/80';
      default: return 'border-slate-200/60';
    }
  }

  public getNodeStateTextClasses(state: RuntimeDagNodeState): string {
    switch (state) {
      case 'ACTIVE':
      case 'RUNNING_PARALLEL': return 'text-blue-700';
      case 'COMPLETED': return 'text-emerald-700';
      case 'APPROVAL_BARRIER': return 'text-purple-700';
      case 'FAILED': return 'text-rose-700';
      default: return 'text-slate-600';
    }
  }
}
