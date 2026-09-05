import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-mapping-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  host: {
    class: 'flex flex-1 flex-col w-full h-full min-h-0'
  },
  template: `
    <div class="w-full h-full flex flex-col gap-3 min-h-0 font-sans text-xs select-none">

      <!-- ========================================================================= -->
      <!-- TOP ATTENTION METRICS STRIP                                               -->
      <!-- ========================================================================= -->
      <div class="px-5 py-3 bg-white border border-slate-200 rounded-lg flex items-center justify-between shrink-0">
        <div class="flex items-center divide-x divide-slate-100 text-xs">
          
          <!-- Total Scoped Objects -->
          <div class="pr-6 flex flex-col gap-0.5">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400">Scoped Objects</span>
            <span class="text-xl font-bold text-slate-900 leading-tight">
              {{ store.metrics().totalObjects }}
            </span>
          </div>

          <!-- Automatic Mappings -->
          <div class="px-6 flex flex-col gap-0.5">
            <span class="text-[10px] uppercase font-bold tracking-wider text-emerald-600">Automatic</span>
            <span class="text-xl font-bold text-emerald-700 leading-tight">
              {{ store.metrics().autoMappedCount }}
            </span>
          </div>

          <!-- Needs Review -->
          <div class="px-6 flex flex-col gap-0.5">
            <span class="text-[10px] uppercase font-bold tracking-wider text-amber-600">Needs Review</span>
            <span class="text-xl font-bold leading-tight" [class.text-amber-600]="store.metrics().needsReviewCount > 0" [class.text-slate-400]="store.metrics().needsReviewCount === 0">
              {{ store.metrics().needsReviewCount }}
            </span>
          </div>

          <!-- Blocked -->
          <div class="px-6 flex flex-col gap-0.5">
            <span class="text-[10px] uppercase font-bold tracking-wider text-rose-600">Blocked</span>
            <span class="text-xl font-bold leading-tight" [class.text-rose-600]="store.metrics().blockedCount > 0" [class.text-slate-400]="store.metrics().blockedCount === 0">
              {{ store.metrics().blockedCount }}
            </span>
          </div>

          <!-- Modified / Your Changes -->
          <div class="px-6 flex flex-col gap-0.5">
            <span class="text-[10px] uppercase font-bold tracking-wider text-blue-600">Operator Modified</span>
            <span class="text-xl font-bold leading-tight" [class.text-blue-600]="store.metrics().modifiedCount > 0" [class.text-slate-400]="store.metrics().modifiedCount === 0">
              {{ store.metrics().modifiedCount }}
            </span>
          </div>

          @if (store.metrics().governanceRequiredCount > 0) {
            <div class="pl-6 flex flex-col gap-0.5">
              <span class="text-[10px] uppercase font-bold tracking-wider text-indigo-500">Governance</span>
              <span class="text-xl font-bold text-indigo-700 leading-tight">
                {{ store.metrics().governanceRequiredCount }} Required
              </span>
            </div>
          }

        </div>

        <!-- Quick Jump Buttons (Blue-tint hover, NOT grey-white) -->
        <div class="flex items-center gap-2.5">
          <button
            type="button"
            (click)="store.setSubWorkspace('FIELDS')"
            class="h-8 px-3.5 rounded-md border border-slate-200 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 text-slate-700 font-semibold text-xs flex items-center gap-1.5 cursor-pointer transition-colors">
            <app-lucide-icon name="table" [size]="13" class="text-slate-500"></app-lucide-icon>
            <span>Open Field Workbench</span>
          </button>
          <button
            type="button"
            (click)="store.setSubWorkspace('STRUCTURE')"
            class="h-8 px-3.5 rounded-md border border-slate-200 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 text-slate-700 font-semibold text-xs flex items-center gap-1.5 cursor-pointer transition-colors">
            <app-lucide-icon name="network" [size]="13" class="text-slate-500"></app-lucide-icon>
            <span>Routing &amp; Namespaces</span>
          </button>
        </div>

      </div>

      <!-- ========================================================================= -->
      <!-- ATTENTION QUEUE / DECISION SURFACE                                        -->
      <!-- ========================================================================= -->
      <div class="flex-1 min-h-0 bg-white border border-slate-200 rounded-lg flex flex-col overflow-hidden">
        
        <!-- Section Header & Filter Controls -->
        <div class="h-11 px-5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between shrink-0">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="list-ordered" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span class="font-bold text-slate-800 text-xs tracking-tight">Step 5 Attention Queue</span>
            <span class="text-[11px] text-slate-500 font-normal">
              — Review anomalies, collisions, lossy conversions, and required governance
            </span>
          </div>

          <!-- Restrained Filter Controls -->
          <div class="flex items-center gap-2">
            <div class="relative w-64">
              <input
                type="text"
                [(ngModel)]="searchFilter"
                (ngModelChange)="onSearchChange($event)"
                placeholder="Filter attention queue..."
                class="w-full h-8 pl-8 pr-2.5 text-xs bg-white border border-slate-200 rounded-md focus:outline-none focus:border-blue-500 text-slate-800 font-normal placeholder:text-slate-400" />
              <app-lucide-icon name="search" [size]="12" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
            </div>
          </div>
        </div>

        <!-- Scrollable Work Items List -->
        <div class="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-3">

          <!-- 1. BLOCKED QUEUE (Collision / Critical Exception) -->
          @if (store.blockedObjects().length > 0) {
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200">
                  Blocked Exceptions ({{ store.blockedObjects().length }})
                </span>
                <span class="text-xs text-slate-500">Requires operator correction before migration execution</span>
              </div>

              @for (obj of store.blockedObjects(); track obj.id) {
                <div class="p-3.5 rounded-lg border border-rose-200 bg-rose-50/30 flex items-start justify-between gap-4">
                  <div class="flex items-start gap-3 min-w-0">
                    <div class="w-7 h-7 rounded bg-rose-100 border border-rose-200 flex items-center justify-center shrink-0 mt-0.5">
                      <app-lucide-icon name="alert-octagon" [size]="14" class="text-rose-700"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col min-w-0 gap-1">
                      <div class="flex items-center gap-2">
                        <span class="font-bold text-xs text-slate-900">{{ obj.sourceNamespace }}.{{ obj.sourceName }}</span>
                        <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                        <span class="font-semibold text-xs text-slate-800">{{ obj.currentTargetNamespace }}.{{ obj.currentTargetName }}</span>
                        <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-100 text-rose-800">
                          {{ obj.sourceTypeLabel }}
                        </span>
                      </div>
                      @for (issue of obj.issues; track issue.id) {
                        <p class="text-xs text-rose-900 font-medium leading-relaxed">
                          {{ issue.reason }}
                        </p>
                        @if (issue.recommendation) {
                          <p class="text-[11px] text-slate-600 font-normal">
                            Recommendation: {{ issue.recommendation }}
                          </p>
                        }
                      }
                    </div>
                  </div>

                  <!-- Actions -->
                  <div class="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      (click)="store.routeToStructure(obj.sourceNamespace)"
                      class="h-7 px-2.5 rounded border border-rose-300 bg-white hover:bg-rose-50 text-rose-800 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <span>Reroute Target</span>
                      <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                    </button>
                    <button
                      type="button"
                      (click)="store.routeToFields(obj.id)"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 text-slate-700 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <span>Review Mapping</span>
                      <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                    </button>
                  </div>
                </div>
              }
            </div>
          }

          <!-- 2. NEEDS REVIEW QUEUE (Lossy Datatypes / Semantics) -->
          @if (store.needsReviewObjects().length > 0) {
            <div class="flex flex-col gap-2 pt-2">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-800 border border-amber-200">
                  Needs Review ({{ store.needsReviewObjects().length }})
                </span>
                <span class="text-xs text-slate-500">Datatype truncation, precision reduction, or conversion warning</span>
              </div>

              @for (obj of store.needsReviewObjects(); track obj.id) {
                <div class="p-3.5 rounded-lg border border-amber-200 bg-amber-50/20 flex items-start justify-between gap-4">
                  <div class="flex items-start gap-3 min-w-0">
                    <div class="w-7 h-7 rounded bg-amber-100 border border-amber-200 flex items-center justify-center shrink-0 mt-0.5">
                      <app-lucide-icon name="alert-triangle" [size]="14" class="text-amber-700"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col min-w-0 gap-1">
                      <div class="flex items-center gap-2">
                        <span class="font-bold text-xs text-slate-900">{{ obj.sourceNamespace }}.{{ obj.sourceName }}</span>
                        <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                        <span class="font-semibold text-xs text-slate-800">{{ obj.currentTargetNamespace }}.{{ obj.currentTargetName }}</span>
                      </div>
                      @for (issue of obj.issues; track issue.id) {
                        <p class="text-xs text-amber-900 font-medium leading-relaxed">
                          {{ issue.reason }}
                        </p>
                      }
                      @for (col of getLossyColumns(obj); track col.id) {
                        <div class="flex items-center gap-2 text-[11px] text-amber-950 font-mono pt-1">
                          <span class="font-bold text-slate-800">{{ col.sourceField }}</span>
                          <span>{{ col.sourceType }}</span>
                          <app-lucide-icon name="arrow-right" [size]="11" class="text-slate-400 shrink-0"></app-lucide-icon>
                          <span class="font-bold text-amber-800">{{ col.currentTargetField }}</span>
                          <span>{{ col.currentTargetType }}</span>
                          <span class="px-1.5 py-0.2 rounded text-[9px] bg-amber-100 text-amber-800 font-sans font-bold">
                            Lossy Conversion
                          </span>
                        </div>
                      }
                    </div>
                  </div>

                  <!-- Actions -->
                  <div class="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      (click)="store.routeToFields(obj.id)"
                      class="h-7 px-2.5 rounded border border-amber-300 bg-white hover:bg-amber-50 text-amber-900 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <span>Review Type</span>
                      <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                    </button>
                  </div>
                </div>
              }
            </div>
          }

          <!-- 3. GOVERNANCE REQUIRED QUEUE (Exclusions / FK Detachment) -->
          @if (getGovernanceObjects().length > 0) {
            <div class="flex flex-col gap-2 pt-2">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Governance Review Required ({{ getGovernanceObjects().length }})
                </span>
                <span class="text-xs text-slate-500">Exclusions affecting downstream referential integrity or dependencies</span>
              </div>

              @for (obj of getGovernanceObjects(); track obj.id) {
                <div class="p-3.5 rounded-lg border border-indigo-200 bg-indigo-50/20 flex items-start justify-between gap-4">
                  <div class="flex items-start gap-3 min-w-0">
                    <div class="w-7 h-7 rounded bg-indigo-100 border border-indigo-200 flex items-center justify-center shrink-0 mt-0.5">
                      <app-lucide-icon name="shield-alert" [size]="14" class="text-indigo-700"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col min-w-0 gap-1">
                      <div class="flex items-center gap-2">
                        <span class="font-bold text-xs text-slate-900">{{ obj.sourceNamespace }}.{{ obj.sourceName }}</span>
                        <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-200 text-slate-700">
                          Excluded
                        </span>
                      </div>
                      <p class="text-xs text-indigo-900 font-medium leading-relaxed">
                        Exclusion affects {{ obj.structuralImpact.dependentObjectsCount }} dependent object(s) ({{ obj.structuralImpact.foreignKeysCount }} foreign keys).
                      </p>
                      <p class="text-[11px] text-slate-600 font-normal">
                        Step 5 identifies required governance; formal waiver approval occurs in Step 8: Govern.
                      </p>
                    </div>
                  </div>

                  <div class="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      (click)="store.openImpactModal(obj)"
                      class="h-7 px-2.5 rounded border border-indigo-300 bg-white hover:bg-indigo-50 text-indigo-800 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <span>Review Impact</span>
                      <app-lucide-icon name="info" [size]="11"></app-lucide-icon>
                    </button>
                  </div>
                </div>
              }
            </div>
          }

          <!-- 4. YOUR CHANGES (Modified Items Summary) -->
          @if (store.modifiedObjects().length > 0) {
            <div class="flex flex-col gap-2 pt-2">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200">
                    Your Changes ({{ store.modifiedObjects().length }})
                  </span>
                  <span class="text-xs text-slate-500">Manual adjustments committed in current operator session</span>
                </div>
              </div>

              @for (obj of store.modifiedObjects(); track obj.id) {
                <div class="p-3.5 rounded-lg border border-slate-200 bg-white flex items-center justify-between gap-4">
                  <div class="flex items-center gap-3 min-w-0">
                    <div class="w-6 h-6 rounded bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0">
                      <app-lucide-icon name="pen-tool" [size]="12" class="text-blue-600"></app-lucide-icon>
                    </div>
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="font-bold text-xs text-slate-900">{{ obj.sourceNamespace }}.{{ obj.sourceName }}</span>
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                      <span class="font-semibold text-xs text-blue-700">{{ obj.currentTargetNamespace }}.{{ obj.currentTargetName }}</span>
                      @if (!obj.isIncluded) {
                        <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-100 text-slate-600">
                          Excluded
                        </span>
                      }
                    </div>
                  </div>

                  <div class="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      (click)="store.revertObjectToProposal(obj.id)"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <app-lucide-icon name="rotate-ccw" [size]="11"></app-lucide-icon>
                      <span>Revert</span>
                    </button>
                    <button
                      type="button"
                      (click)="store.routeToFields(obj.id)"
                      class="h-7 px-2.5 rounded border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <span>Review Changes</span>
                      <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                    </button>
                  </div>
                </div>
              }
            </div>
          }

          <!-- 5. AUTOMATIC MAPPINGS QUEUE (Calm, expandable overview) -->
          <div class="flex flex-col gap-2 pt-2 border-t border-slate-100 mt-2">
            <div
              (click)="isAutoMappedExpanded = !isAutoMappedExpanded"
              class="flex items-center justify-between p-3.5 rounded-lg bg-slate-50 border border-slate-200 cursor-pointer hover:bg-slate-100/70 transition-colors">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon
                  [name]="isAutoMappedExpanded ? 'chevron-down' : 'chevron-right'"
                  [size]="14"
                  class="text-slate-500"></app-lucide-icon>
                <div class="flex items-center gap-2">
                  <span class="font-bold text-xs text-slate-800">
                    Automatic Mappings ({{ store.metrics().autoMappedCount }})
                  </span>
                  <span class="text-xs text-slate-500 font-normal">
                    — Quietly resolved by AKAAL proposal engine; no manual intervention needed
                  </span>
                </div>
              </div>

              <div class="flex items-center gap-2" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="store.setSubWorkspace('FIELDS')"
                  class="h-7 px-2.5 rounded text-[11px] font-semibold text-slate-700 hover:text-blue-700 hover:bg-blue-50 hover:border-blue-200 border border-slate-200 bg-white cursor-pointer transition-colors">
                  Browse Automatic Mappings
                </button>
              </div>
            </div>

            @if (isAutoMappedExpanded) {
              <div class="flex flex-col gap-1.5 pl-4 pr-1">
                @for (obj of store.autoMappedObjects(); track obj.id) {
                  <div class="py-2.5 px-3.5 rounded-md border border-slate-100 bg-white flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <app-lucide-icon name="check-circle-2" [size]="13" class="text-emerald-600"></app-lucide-icon>
                      <span class="font-medium text-xs text-slate-800">{{ obj.sourceNamespace }}.{{ obj.sourceName }}</span>
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                      <span class="font-medium text-xs text-slate-700">{{ obj.currentTargetNamespace }}.{{ obj.currentTargetName }}</span>
                      <span class="text-[10px] text-slate-400 font-mono">({{ obj.columns.length }} fields)</span>
                    </div>
                    <button
                      type="button"
                      (click)="store.routeToFields(obj.id)"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 text-slate-700 font-semibold text-xs flex items-center gap-1.5 cursor-pointer transition-colors shrink-0">
                      <app-lucide-icon name="sliders-horizontal" [size]="11" class="text-slate-500 group-hover:text-blue-600"></app-lucide-icon>
                      <span>Customize</span>
                    </button>
                  </div>
                }
              </div>
            }

          </div>

        </div>

      </div>

    </div>
  `
})
export class MappingOverviewComponent {
  public readonly store = inject(Step5MappingStoreService);
  public searchFilter: string = '';
  public isAutoMappedExpanded: boolean = false;

  public onSearchChange(val: string): void {
    this.store.setSearchQuery(val);
  }

  public getLossyColumns(obj: any): any[] {
    return obj.columns.filter((c: any) => c.conversionSafety === 'LOSSY' || c.uiWorkState === 'NEEDS_REVIEW');
  }

  public getGovernanceObjects(): any[] {
    return this.store.objects().filter(o => o.structuralImpact?.requiresGovernanceWaiver || o.readiness === 'WAIVER_REQUIRED');
  }
}
