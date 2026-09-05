import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { MappingStatusBucket, ObjectMappingContract } from './step5-mapping.models';

/**
 * MappingReviewComponent
 *
 * Exception-first decision queue for Step 5 Mapping & Data Controls.
 * Prioritizes operator attention on Blocked items and Needs Review items,
 * while keeping automatic and modified mappings readily inspectable.
 *
 * Strictly adheres to Zero Shadow, Zero Blur, and Roboto typography.
 */
@Component({
  selector: 'app-mapping-review',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex-1 flex flex-col gap-3 min-h-0 select-none font-sans text-xs">
      
      <!-- 1. Restrained Status Summary Strip (Zero Floating Cards, Hairline Dividers) -->
      <div class="h-11 px-4 bg-white border border-slate-200 rounded-md flex items-center justify-between shrink-0">
        <div class="flex items-center divide-x divide-slate-200 text-xs w-full">
          
          <!-- All Objects -->
          <button
            type="button"
            (click)="setStatusFilter('ALL')"
            class="pr-7 flex items-baseline gap-1.5 cursor-pointer hover:bg-slate-50/80 px-2 py-0.5 rounded transition-colors"
            [class.bg-slate-100]="store.statusFilter() === 'ALL'">
            <span class="text-[10px] font-bold text-slate-600 uppercase tracking-wider">TOTAL OBJECTS</span>
            <span class="font-bold text-slate-900 tabular-nums text-sm">{{ store.metrics().totalObjects }}</span>
          </button>

          <!-- Auto-mapped -->
          <button
            type="button"
            (click)="setStatusFilter('AUTO_MAPPED')"
            class="px-7 flex items-baseline gap-1.5 cursor-pointer hover:bg-slate-50/80 py-0.5 rounded transition-colors"
            [class.bg-slate-100]="store.statusFilter() === 'AUTO_MAPPED'">
            <span class="text-[10px] font-bold text-slate-600 uppercase tracking-wider">AUTO-MAPPED</span>
            <span class="font-bold text-slate-900 tabular-nums text-sm">{{ store.metrics().autoMappedCount }}</span>
            <span class="text-slate-600 text-[11px]">quiet</span>
          </button>

          <!-- Modified -->
          <button
            type="button"
            (click)="setStatusFilter('MODIFIED')"
            class="px-7 flex items-baseline gap-1.5 cursor-pointer hover:bg-blue-50/50 py-0.5 rounded transition-colors"
            [class.bg-blue-50]="store.statusFilter() === 'MODIFIED'">
            <span class="text-[10px] font-bold text-blue-800 uppercase tracking-wider">MODIFIED</span>
            <span class="font-bold text-blue-900 tabular-nums text-sm">{{ store.metrics().modifiedCount }}</span>
          </button>

          <!-- Needs Review -->
          <button
            type="button"
            (click)="setStatusFilter('NEEDS_REVIEW')"
            class="px-7 flex items-baseline gap-1.5 cursor-pointer hover:bg-amber-50/50 py-0.5 rounded transition-colors"
            [class.bg-amber-50]="store.statusFilter() === 'NEEDS_REVIEW'">
            <span class="text-[10px] font-bold text-amber-900 uppercase tracking-wider">NEEDS REVIEW</span>
            <span class="font-bold text-amber-950 tabular-nums text-sm">{{ store.metrics().needsReviewCount }}</span>
          </button>

          <!-- Blocked -->
          <button
            type="button"
            (click)="setStatusFilter('BLOCKED')"
            class="pl-7 flex items-baseline gap-1.5 cursor-pointer hover:bg-rose-50/50 py-0.5 rounded transition-colors"
            [class.bg-rose-50]="store.statusFilter() === 'BLOCKED'">
            <span class="text-[10px] font-bold text-rose-800 uppercase tracking-wider">BLOCKED</span>
            <span class="font-bold text-rose-900 tabular-nums text-sm">{{ store.metrics().blockedCount }}</span>
            <span class="text-slate-600 text-[11px]">must resolve</span>
          </button>

        </div>
      </div>

      <!-- 2. Search & Filter Bar -->
      <div class="h-10 px-3.5 bg-white border border-slate-200 rounded-md flex items-center justify-between gap-3 shrink-0">
        
        <!-- Search Input -->
        <div class="flex items-center gap-2 flex-1 max-w-md">
          <app-lucide-icon name="search" [size]="13" class="text-slate-400 shrink-0"></app-lucide-icon>
          <input
            type="text"
            [ngModel]="store.searchQuery()"
            (ngModelChange)="store.searchQuery.set($event)"
            placeholder="Search mappings (table, column, namespace)..."
            aria-label="Search mappings"
            class="w-full text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none border-none bg-transparent" />
          @if (store.searchQuery()) {
            <button
              type="button"
              (click)="store.searchQuery.set('')"
              class="text-slate-400 hover:text-slate-600 cursor-pointer">
              <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
            </button>
          }
        </div>

        <!-- Filter Badges / Presets -->
        <div class="flex items-center gap-1.5">
          <span class="text-[11px] text-slate-500 font-medium mr-1">Filter:</span>
          @for (f of filterOptions; track f.id) {
            <button
              type="button"
              (click)="setStatusFilter(f.id)"
              class="h-6.5 px-2.5 text-[11px] font-medium rounded border transition-colors cursor-pointer"
              [class.bg-blue-50]="store.statusFilter() === f.id"
              [class.border-blue-300]="store.statusFilter() === f.id"
              [class.text-blue-700]="store.statusFilter() === f.id"
              [class.bg-white]="store.statusFilter() !== f.id"
              [class.border-slate-200]="store.statusFilter() !== f.id"
              [class.text-slate-600]="store.statusFilter() !== f.id">
              {{ f.label }}
            </button>
          }
        </div>

      </div>

      <!-- 3. Decision Queue Container (Scrollable, High-Density Enterprise Layout) -->
      <div class="flex-1 overflow-y-auto space-y-4 min-h-0 pr-1">
        
        <!-- Empty State: When Zero Mappings Match Search -->
        @if (store.filteredObjects().length === 0) {
          <div class="p-12 text-center bg-white border border-slate-200 rounded-md flex flex-col items-center justify-center gap-2">
            <app-lucide-icon name="search" [size]="24" class="text-slate-300 mb-1"></app-lucide-icon>
            <h3 class="text-sm font-bold text-slate-700">No mappings match your search</h3>
            <p class="text-xs text-slate-400 max-w-sm">
              Try adjusting your filter or search terms to inspect scoped objects.
            </p>
            <button
              type="button"
              (click)="store.searchQuery.set(''); store.statusFilter.set('ALL')"
              class="mt-2 h-7 px-3 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 rounded cursor-pointer transition-colors flex items-center gap-1.5">
              <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
              Clear filters
            </button>
          </div>
        }

        <!-- Clean State: Zero Exceptions in Scoped Set -->
        @if (store.filteredObjects().length > 0 && store.metrics().blockedCount === 0 && store.metrics().needsReviewCount === 0 && store.statusFilter() === 'ALL') {
          <div class="p-4 bg-emerald-50/70 border border-emerald-200 rounded-md flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <div class="w-6 h-6 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-700 flex items-center justify-center shrink-0">
                <app-lucide-icon name="check" [size]="14"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <span class="text-xs font-bold text-emerald-900">All current mappings are ready for review</span>
                <span class="text-[11px] text-emerald-700">Zero unresolved blockers. You can inspect or manually override any mapping in Map.</span>
              </div>
            </div>
            <button
              type="button"
              (click)="store.setWorkMode('MAP')"
              class="h-7 px-3 text-xs font-medium text-emerald-800 bg-emerald-100 hover:bg-emerald-200 border border-emerald-300 rounded cursor-pointer transition-colors flex items-center gap-1.5">
              <span>Inspect in Map</span>
              <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
            </button>
          </div>
        }

        <!-- ========================================================================= -->
        <!-- QUEUE 1: BLOCKED (Highest Priority - Must Resolve to Proceed)              -->
        <!-- ========================================================================= -->
        @if (store.blockedObjects().length > 0) {
          <div class="space-y-2">
            
            <div class="flex items-center justify-between pb-1 border-b border-slate-200">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-rose-600 shrink-0"></span>
                <h2 class="text-xs font-bold uppercase tracking-wider text-rose-800">
                  BLOCKED &middot; {{ store.blockedObjects().length }}
                </h2>
                <span class="text-[11px] text-slate-500 font-normal">
                  Must resolve before continuing to Configure
                </span>
              </div>
            </div>

            <!-- Blocked Work Items (Restrained, High-Density Decision Queue) -->
            <div class="space-y-2">
              @for (item of store.blockedObjects(); track item.id) {
                <div class="p-3.5 bg-white border border-rose-200 rounded-md flex flex-col gap-2 hover:border-rose-300 transition-colors">
                  
                  <!-- Top Line: Object Identity + Direction + Badges -->
                  <div class="flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2 min-w-0">
                      <app-lucide-icon name="table" [size]="14" class="text-slate-500 shrink-0"></app-lucide-icon>
                      <span class="font-bold text-slate-900 text-xs truncate">{{ item.sourceNamespace }}.{{ item.sourceName }}</span>
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                      <span class="font-bold text-rose-700 text-xs truncate">{{ item.currentTargetNamespace }}.{{ item.currentTargetName }}</span>
                    </div>

                    <div class="flex items-center gap-2 shrink-0">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                        BLOCKED
                      </span>
                    </div>
                  </div>

                  <!-- Issue Details -->
                  @for (iss of item.issues; track iss.id) {
                    <div class="bg-rose-50/60 border border-rose-100 rounded p-2.5 flex flex-col gap-1 text-xs">
                      <div class="font-bold text-rose-900 flex items-center gap-1.5">
                        <app-lucide-icon name="alert-circle" [size]="13" class="text-rose-600 shrink-0"></app-lucide-icon>
                        <span>{{ iss.title }}</span>
                      </div>
                      <p class="text-rose-800 text-[11px] font-normal leading-relaxed pl-5">
                        {{ iss.reason }}
                      </p>
                      @if (iss.recommendation) {
                        <div class="text-[11px] text-slate-600 pl-5 pt-0.5">
                          <strong class="font-semibold text-slate-700">Recommendation:</strong> {{ iss.recommendation }}
                        </div>
                      }
                    </div>
                  }

                  <!-- Action Buttons -->
                  <div class="flex items-center justify-end gap-2 pt-1 border-t border-slate-100">
                    <button
                      type="button"
                      (click)="store.toggleObjectInclusion(item.id)"
                      class="h-7 px-2.5 text-[11px] font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded bg-white hover:bg-slate-50 cursor-pointer transition-colors"
                      title="Exclude this object from current migration draft">
                      {{ item.isIncluded ? 'Exclude from Scope' : 'Re-include Object' }}
                    </button>
                    <button
                      type="button"
                      (click)="store.routeToMapObject(item.id)"
                      class="h-7 px-3 text-[11px] font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded cursor-pointer transition-colors flex items-center gap-1.5">
                      <span>Change Target / Map</span>
                      <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                    </button>
                  </div>

                </div>
              }
            </div>

          </div>
        }

        <!-- ========================================================================= -->
        <!-- QUEUE 2: NEEDS REVIEW (Actionable Guidance)                                -->
        <!-- ========================================================================= -->
        @if (store.needsReviewObjects().length > 0) {
          <div class="space-y-2">
            
            <div class="flex items-center justify-between pb-1 border-b border-slate-200">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-amber-500 shrink-0"></span>
                <h2 class="text-xs font-bold uppercase tracking-wider text-amber-800">
                  NEEDS REVIEW &middot; {{ store.needsReviewObjects().length }}
                </h2>
                <span class="text-[11px] text-slate-500 font-normal">
                  Review proposed type widening, collation, or sequence defaults
                </span>
              </div>
            </div>

            <div class="space-y-2">
              @for (item of store.needsReviewObjects(); track item.id) {
                <div class="p-3.5 bg-white border border-amber-200 rounded-md flex flex-col gap-2 hover:border-amber-300 transition-colors">
                  
                  <div class="flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2 min-w-0">
                      <app-lucide-icon name="table" [size]="14" class="text-slate-500 shrink-0"></app-lucide-icon>
                      <span class="font-bold text-slate-900 text-xs truncate">{{ item.sourceNamespace }}.{{ item.sourceName }}</span>
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                      <span class="font-bold text-slate-800 text-xs truncate">{{ item.currentTargetNamespace }}.{{ item.currentTargetName }}</span>
                    </div>

                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200 shrink-0">
                      NEEDS REVIEW
                    </span>
                  </div>

                  @for (iss of item.issues; track iss.id) {
                    <div class="bg-amber-50/60 border border-amber-100 rounded p-2.5 flex flex-col gap-1 text-xs">
                      <div class="font-bold text-amber-900 flex items-center gap-1.5">
                        <app-lucide-icon name="alert-triangle" [size]="13" class="text-amber-600 shrink-0"></app-lucide-icon>
                        <span>{{ iss.title }}</span>
                      </div>
                      <p class="text-amber-800 text-[11px] font-normal leading-relaxed pl-5">
                        {{ iss.reason }}
                      </p>
                      @if (iss.recommendation) {
                        <div class="text-[11px] text-slate-600 pl-5 pt-0.5">
                          <strong class="font-semibold text-slate-700">Guidance:</strong> {{ iss.recommendation }}
                        </div>
                      }
                    </div>
                  }

                  <div class="flex items-center justify-end gap-2 pt-1 border-t border-slate-100">
                    <button
                      type="button"
                      (click)="store.routeToMapObject(item.id)"
                      class="h-7 px-3 text-[11px] font-medium text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded cursor-pointer transition-colors flex items-center gap-1.5">
                      <span>Review in Map</span>
                      <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                    </button>
                  </div>

                </div>
              }
            </div>

          </div>
        }

        <!-- ========================================================================= -->
        <!-- QUEUE 3: MODIFIED (Operator Customizations in Current Draft)              -->
        <!-- ========================================================================= -->
        @if (store.modifiedObjects().length > 0) {
          <div class="space-y-2">
            
            <div class="flex items-center justify-between pb-1 border-b border-slate-200">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-blue-600 shrink-0"></span>
                <h2 class="text-xs font-bold uppercase tracking-wider text-blue-800">
                  MODIFIED &middot; {{ store.modifiedObjects().length }}
                </h2>
                <span class="text-[11px] text-slate-500 font-normal">
                  Deliberate operator customizations applied in Step 5
                </span>
              </div>
            </div>

            <div class="space-y-2">
              @for (item of store.modifiedObjects(); track item.id) {
                <div class="p-3 bg-white border border-blue-200 rounded-md flex flex-col gap-2">
                  
                  <div class="flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2 min-w-0">
                      <app-lucide-icon name="edit-3" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                      <span class="font-bold text-slate-900 text-xs truncate">{{ item.sourceName }}</span>
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                      <span class="font-bold text-blue-700 text-xs truncate">{{ item.currentTargetNamespace }}.{{ item.currentTargetName }}</span>
                    </div>

                    <div class="flex items-center gap-2 shrink-0">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                        MODIFIED
                      </span>
                    </div>
                  </div>

                  <!-- Change Summary Pill Tags -->
                  <div class="flex items-center gap-1.5 flex-wrap text-[11px]">
                    @if (item.currentTargetName !== item.originalProposal.targetName) {
                      <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded font-medium text-slate-700 inline-flex items-center gap-1">
                        <span>Table: {{ item.originalProposal.targetName }}</span>
                        <app-lucide-icon name="arrow-right" [size]="10" class="text-slate-400"></app-lucide-icon>
                        <span>{{ item.currentTargetName }}</span>
                      </span>
                    }
                    @if (item.rowFilterMode === 'CUSTOM') {
                      <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded font-medium text-slate-700">
                        Row filter: {{ item.rowFilterPredicate || 'Custom' }}
                      </span>
                    }
                    @if (item.deduplication.enabled) {
                      <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded font-medium text-slate-700">
                        Deduplication: active
                      </span>
                    }
                    @for (c of item.columns; track c.id) {
                      @if (c.isModified) {
                        <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded font-medium text-slate-700">
                          Col {{ c.sourceField }}: {{ c.currentTargetField }} ({{ c.currentTargetType }})
                        </span>
                      }
                    }
                  </div>

                  <!-- Action Buttons -->
                  <div class="flex items-center justify-end gap-2 pt-1 border-t border-slate-100">
                    <button
                      type="button"
                      (click)="store.promptRevertObject(item.id)"
                      class="h-7 px-2.5 text-[11px] font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded bg-white hover:bg-slate-50 cursor-pointer transition-colors">
                      Revert Object
                    </button>
                    <button
                      type="button"
                      (click)="store.routeToMapObject(item.id)"
                      class="h-7 px-3 text-[11px] font-medium text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded cursor-pointer transition-colors flex items-center gap-1.5">
                      <span>Inspect in Map</span>
                      <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                    </button>
                  </div>

                </div>
              }
            </div>

          </div>
        }

        <!-- ========================================================================= -->
        <!-- QUEUE 4: AUTO-MAPPED (Quiet by Default, Fully Inspectable)                -->
        <!-- ========================================================================= -->
        @if (store.autoMappedObjects().length > 0) {
          <div class="border border-slate-200 rounded-md bg-white overflow-hidden">
            
            <!-- Accordion Header -->
            <button
              type="button"
              (click)="isAutoMappedExpanded.set(!isAutoMappedExpanded())"
              class="w-full h-10 px-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100/80 transition-colors cursor-pointer text-left">
              <div class="flex items-center gap-2">
                <app-lucide-icon [name]="isAutoMappedExpanded() ? 'chevron-down' : 'chevron-right'" [size]="14" class="text-slate-500"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  AUTO-MAPPED &middot; {{ store.autoMappedObjects().length }}
                </span>
                <span class="text-[11px] text-slate-500 font-normal">
                  Proposal requires no operator intervention
                </span>
              </div>

              <span class="text-[11px] text-slate-600 font-medium">
                {{ isAutoMappedExpanded() ? 'Collapse' : 'Expand to inspect' }}
              </span>
            </button>

            <!-- Expanded Rows -->
            @if (isAutoMappedExpanded()) {
              <div class="divide-y divide-slate-100 border-t border-slate-200">
                @for (item of store.autoMappedObjects(); track item.id) {
                  <div class="h-9 px-4 flex items-center justify-between text-xs hover:bg-slate-50 transition-colors">
                    <div class="flex items-center gap-2 min-w-0">
                      <app-lucide-icon name="check" [size]="13" class="text-emerald-600 shrink-0"></app-lucide-icon>
                      <span class="font-medium text-slate-800 truncate">{{ item.sourceNamespace }}.{{ item.sourceName }}</span>
                      <app-lucide-icon name="arrow-right" [size]="11" class="text-slate-400 shrink-0"></app-lucide-icon>
                      <span class="font-medium text-slate-700 truncate">{{ item.currentTargetNamespace }}.{{ item.currentTargetName }}</span>
                      <span class="text-[10px] text-slate-400">({{ item.columns.length }} cols)</span>
                    </div>

                    <button
                      type="button"
                      (click)="store.routeToMapObject(item.id)"
                      class="h-6 px-2.5 rounded border border-slate-200 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 text-slate-600 font-semibold text-[11px] cursor-pointer transition-colors inline-flex items-center gap-1 shrink-0">
                      <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                      <span>Inspect</span>
                    </button>
                  </div>
                }
              </div>
            }

          </div>
        }

      </div>

    </div>
  `
})
export class MappingReviewComponent {
  public store = inject(Step5MappingStoreService);

  public readonly isAutoMappedExpanded = signal<boolean>(false);

  public readonly filterOptions: { id: MappingStatusBucket; label: string }[] = [
    { id: 'ALL', label: 'All' },
    { id: 'BLOCKED', label: 'Blocked' },
    { id: 'NEEDS_REVIEW', label: 'Needs Review' },
    { id: 'MODIFIED', label: 'Modified' },
    { id: 'AUTO_MAPPED', label: 'Auto-mapped' }
  ];

  public setStatusFilter(f: MappingStatusBucket): void {
    this.store.statusFilter.set(f);
  }
}
