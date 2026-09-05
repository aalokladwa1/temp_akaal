import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-mapping-structure',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  host: {
    class: 'flex flex-1 w-full h-full min-h-0'
  },
  template: `
    <div class="w-full h-full flex gap-3 min-h-0 font-sans text-xs select-none">
      
      <!-- ========================================================================= -->
      <!-- LEFT PANE: SOURCE STRUCTURE & NAMESPACES (~25%)                           -->
      <!-- ========================================================================= -->
      <aside class="w-72 bg-white border border-slate-200 rounded-lg flex flex-col shrink-0 overflow-hidden">
        
        <!-- Header & Search -->
        <div class="p-3 border-b border-slate-200 flex flex-col gap-2 bg-slate-50/50">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-800 text-xs tracking-tight">Source Structure</span>
            <span class="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
              {{ store.namespaces().length }} Schemas
            </span>
          </div>
          <div class="relative">
            <input
              type="text"
              [(ngModel)]="searchQuery"
              placeholder="Search schemas &amp; tables..."
              class="w-full h-7 pl-8 pr-2.5 text-xs bg-white border border-slate-200 rounded-md focus:outline-none focus:border-blue-500 text-slate-800 placeholder:text-slate-400 font-normal" />
            <app-lucide-icon name="search" [size]="12" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
          </div>
        </div>

        <!-- Namespace & Objects Tree List -->
        <div class="flex-1 min-h-0 overflow-y-auto p-2 flex flex-col gap-1">
          @for (ns of filteredNamespaces(); track ns.sourceNamespace) {
            <div class="flex flex-col rounded-md overflow-hidden border border-transparent"
              [class.border-blue-200]="store.selectedNamespaceName() === ns.sourceNamespace"
              [class.bg-blue-50]="store.selectedNamespaceName() === ns.sourceNamespace">
              
              <!-- Namespace Header Row -->
              <div
                (click)="store.selectNamespace(ns.sourceNamespace)"
                class="px-2.5 py-2 flex items-center justify-between cursor-pointer rounded hover:bg-slate-100 transition-colors"
                [class.bg-blue-50]="store.selectedNamespaceName() === ns.sourceNamespace"
                [class.text-blue-900]="store.selectedNamespaceName() === ns.sourceNamespace">
                <div class="flex items-center gap-2 min-w-0">
                  <app-lucide-icon name="folder" [size]="13" class="text-slate-500 shrink-0"></app-lucide-icon>
                  <span class="font-bold text-xs truncate">{{ ns.sourceNamespace }}</span>
                </div>
                <div class="flex items-center gap-1.5">
                  @if (ns.origin === 'MODIFIED') {
                    <span class="w-1.5 h-1.5 rounded-full bg-blue-600" title="Modified by operator"></span>
                  }
                  <span class="text-[10px] text-slate-400 font-mono">{{ getObjectsInNamespace(ns.sourceNamespace).length }}</span>
                </div>
              </div>

              <!-- Children Objects in Namespace -->
              @if (store.selectedNamespaceName() === ns.sourceNamespace) {
                <div class="flex flex-col pl-5 pr-1 py-1 gap-0.5">
                  @for (obj of getObjectsInNamespace(ns.sourceNamespace); track obj.id) {
                    <div
                      (click)="store.selectObject(obj.id)"
                      class="px-2 py-1.5 rounded flex items-center justify-between cursor-pointer transition-colors hover:bg-slate-100"
                      [class.bg-blue-100]="store.selectedObjectId() === obj.id"
                      [class.text-blue-950]="store.selectedObjectId() === obj.id"
                      [class.font-semibold]="store.selectedObjectId() === obj.id"
                      [class.text-slate-700]="store.selectedObjectId() !== obj.id">
                      <div class="flex items-center gap-2 min-w-0">
                        <app-lucide-icon name="table-2" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                        <span class="truncate text-xs">{{ obj.sourceName }}</span>
                      </div>
                      <div class="flex items-center gap-1">
                        @if (obj.status === 'BLOCKED') {
                          <span class="w-1.5 h-1.5 rounded-full bg-rose-600" title="Blocked"></span>
                        } @else if (obj.status === 'NEEDS_REVIEW') {
                          <span class="w-1.5 h-1.5 rounded-full bg-amber-500" title="Needs Review"></span>
                        } @else if (obj.isModified) {
                          <span class="w-1.5 h-1.5 rounded-full bg-blue-600" title="Modified"></span>
                        }
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>

      </aside>

      <!-- ========================================================================= -->
      <!-- RIGHT PANE: WORKSPACE & OBJECT ROUTING (~75%)                             -->
      <!-- ========================================================================= -->
      <section aria-label="Mapping Structure Workbench" class="flex-1 bg-white border border-slate-200 rounded-lg flex flex-col min-w-0 overflow-hidden">
        
        <!-- Top Workspace Bar: Selected Namespace Configuration -->
        @if (store.selectedNamespace(); as ns) {
          <div class="p-4 border-b border-slate-200 bg-slate-50/50 flex flex-col gap-3 shrink-0">
            
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded bg-white border border-slate-200 flex items-center justify-center">
                  <app-lucide-icon name="network" [size]="14" class="text-slate-700"></app-lucide-icon>
                </div>
                <div class="flex flex-col">
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-xs text-slate-900">Schema Routing: {{ ns.sourceNamespace }}</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded font-semibold"
                      [class.bg-blue-50]="ns.origin === 'MODIFIED'"
                      [class.text-blue-700]="ns.origin === 'MODIFIED'"
                      [class.border]="ns.origin === 'MODIFIED'"
                      [class.border-blue-200]="ns.origin === 'MODIFIED'"
                      [class.bg-slate-100]="ns.origin !== 'MODIFIED'"
                      [class.text-slate-600]="ns.origin !== 'MODIFIED'">
                      {{ ns.origin === 'MODIFIED' ? 'Modified by operator' : 'Automatic proposal · Editable' }}
                    </span>
                  </div>
                  <span class="text-[11px] text-slate-500">
                    Routing rules apply across {{ ns.affectedObjectsCount }} contained objects
                  </span>
                </div>
              </div>

              <!-- Namespace Action Buttons (Apply & Revert) -->
              <div class="flex items-center gap-2">
                @if (ns.origin === 'MODIFIED' || store.isNamespaceDirty()) {
                  <button
                    type="button"
                    (click)="store.revertNamespaceToProposal(ns.sourceNamespace)"
                    class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                    <app-lucide-icon name="rotate-ccw" [size]="11"></app-lucide-icon>
                    <span>Revert to Proposal</span>
                  </button>
                }

                <button
                  type="button"
                  [disabled]="!store.isNamespaceDirty()"
                  (click)="store.applyNamespaceDraft()"
                  class="h-7 px-3 rounded font-semibold text-xs flex items-center gap-1.5 transition-colors"
                  [class.bg-blue-600]="store.isNamespaceDirty()"
                  [class.text-white]="store.isNamespaceDirty()"
                  [class.cursor-pointer]="store.isNamespaceDirty()"
                  [class.bg-slate-100]="!store.isNamespaceDirty()"
                  [class.text-slate-400]="!store.isNamespaceDirty()"
                  [class.cursor-not-allowed]="!store.isNamespaceDirty()">
                  <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                  <span>Apply Namespace</span>
                </button>
              </div>
            </div>

            <!-- Editable Controls Row (Draft Mode) -->
            @if (store.namespaceDraft(); as draft) {
              <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-1">
                
                <!-- Target Schema -->
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Namespace</label>
                  <input
                    type="text"
                    [(ngModel)]="draft.currentTargetNamespace"
                    placeholder="e.g. public, prod_schema"
                    class="h-8 px-2.5 bg-white border border-slate-200 rounded-md text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>

                <!-- Prefix -->
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Prefix</label>
                  <input
                    type="text"
                    [(ngModel)]="draft.prefix"
                    placeholder="e.g. tbl_, stg_"
                    class="h-8 px-2.5 bg-white border border-slate-200 rounded-md text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>

                <!-- Suffix -->
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Suffix</label>
                  <input
                    type="text"
                    [(ngModel)]="draft.suffix"
                    placeholder="e.g. _v2, _hist"
                    class="h-8 px-2.5 bg-white border border-slate-200 rounded-md text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>

                <!-- Advanced Routing Toggle -->
                <div class="flex flex-col justify-end">
                  <button
                    type="button"
                    (click)="showAdvancedRouting = !showAdvancedRouting"
                    class="h-8 px-3 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center justify-between cursor-pointer">
                    <span>Advanced Pattern</span>
                    <app-lucide-icon [name]="showAdvancedRouting ? 'chevron-up' : 'chevron-down'" [size]="13" class="text-slate-400"></app-lucide-icon>
                  </button>
                </div>

              </div>

              <!-- Collapsible Advanced Pattern Routing -->
              @if (showAdvancedRouting) {
                <div class="p-3 bg-white border border-slate-200 rounded-md flex flex-col gap-2 mt-1">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Regex / Pattern Routing (Contract-Shaped)</span>
                  <div class="grid grid-cols-2 gap-3">
                    <div class="flex flex-col gap-1">
                      <label class="text-[11px] text-slate-600">Match Pattern</label>
                      <input
                        type="text"
                        [(ngModel)]="draft.advancedPattern"
                        placeholder="^TXN_(.*)$"
                        class="h-7 px-2 bg-slate-50 border border-slate-200 rounded text-xs font-mono" />
                    </div>
                    <div class="flex flex-col gap-1">
                      <label class="text-[11px] text-slate-600">Replacement</label>
                      <input
                        type="text"
                        [(ngModel)]="draft.advancedReplacement"
                        placeholder="transactions_$1"
                        class="h-7 px-2 bg-slate-50 border border-slate-200 rounded text-xs font-mono" />
                    </div>
                  </div>
                  <span class="text-[10px] text-slate-400">Note: Canonical regex execution and validation evaluates downstream in P7.D akaalPipeline.</span>
                </div>
              }
            }

          </div>
        }

        <!-- Middle & Lower: Table of Objects in Selected Namespace -->
        <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
          
          <!-- Table Control Bar -->
          <div class="h-9 px-4 border-b border-slate-200 bg-white flex items-center justify-between shrink-0">
            <span class="font-bold text-slate-800 text-xs">
              Mapped Objects in {{ store.selectedNamespaceName() }} ({{ currentNamespaceObjects().length }})
            </span>
            <span class="text-[11px] text-slate-500 font-normal">
              Select an object to inspect structural impact or customize routing
            </span>
          </div>

          <!-- Objects Grid -->
          <div class="flex-1 min-h-0 overflow-y-auto">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider z-10">
                <tr>
                  <th class="py-2 px-4 w-10 text-center">Inc</th>
                  <th class="py-2 px-4">Source Object</th>
                  <th class="py-2 px-2 text-center w-8">
                    <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 inline-block"></app-lucide-icon>
                  </th>
                  <th class="py-2 px-4">Target Namespace &amp; Table</th>
                  <th class="py-2 px-4">Status</th>
                  <th class="py-2 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (obj of currentNamespaceObjects(); track obj.id) {
                  <tr
                    (click)="store.selectObject(obj.id)"
                    class="cursor-pointer hover:bg-slate-50 transition-colors"
                    [class.bg-blue-50]="store.selectedObjectId() === obj.id">
                    
                    <!-- Inclusion Checkbox -->
                    <td class="py-2.5 px-4 text-center" (click)="$event.stopPropagation()">
                      <input
                        type="checkbox"
                        [checked]="obj.isIncluded"
                        (change)="toggleInclusion(obj)"
                        class="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                    </td>

                    <!-- Source -->
                    <td class="py-2.5 px-4">
                      <div class="flex items-center gap-2">
                        <app-lucide-icon name="table-2" [size]="13" class="text-slate-400"></app-lucide-icon>
                        <span class="font-bold text-slate-900">{{ obj.sourceName }}</span>
                        <span class="text-[10px] text-slate-400">({{ obj.columns.length }} fields)</span>
                      </div>
                    </td>

                    <!-- Arrow -->
                    <td class="py-2.5 px-2 text-center text-slate-400">
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 inline-block"></app-lucide-icon>
                    </td>

                    <!-- Target -->
                    <td class="py-2.5 px-4">
                      <div class="flex items-center gap-1.5">
                        <span class="font-medium text-slate-600">{{ obj.currentTargetNamespace }}.</span>
                        <span class="font-bold text-slate-900" [class.line-through]="!obj.isIncluded" [class.text-slate-400]="!obj.isIncluded">
                          {{ obj.currentTargetName }}
                        </span>
                      </div>
                    </td>

                    <!-- Status -->
                    <td class="py-2.5 px-4">
                      @if (obj.status === 'BLOCKED') {
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                          Blocked
                        </span>
                      } @else if (obj.status === 'NEEDS_REVIEW') {
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                          Needs Review
                        </span>
                      } @else if (obj.isModified) {
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                          Modified
                        </span>
                      } @else {
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Automatic
                        </span>
                      }
                    </td>

                    <!-- Actions -->
                    <td class="py-2.5 px-4 text-right" (click)="$event.stopPropagation()">
                      <div class="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          (click)="store.openImpactModal(obj)"
                          class="h-6 px-2 text-[11px] font-semibold text-slate-600 hover:text-slate-900 border border-slate-200 rounded bg-white hover:bg-slate-50 cursor-pointer">
                          Impact
                        </button>
                        <button
                          type="button"
                          (click)="store.routeToFields(obj.id)"
                          class="h-6 px-2 text-[11px] font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 rounded bg-blue-50 hover:bg-blue-100 cursor-pointer">
                          Edit Fields
                        </button>
                      </div>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>

          <!-- Bottom Selected Object Details & Structural Impact Strip -->
          @if (store.selectedObject(); as selObj) {
            <div class="p-3.5 border-t border-slate-200 bg-slate-50/70 flex flex-col gap-3 shrink-0">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-xs text-slate-900">Selected Object: {{ selObj.sourceNamespace }}.{{ selObj.sourceName }}</span>
                  <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                  <span class="font-bold text-xs text-blue-700">{{ selObj.currentTargetNamespace }}.{{ selObj.currentTargetName }}</span>
                </div>

                <div class="flex items-center gap-2">
                  @if (selObj.isModified || store.isObjectDirty()) {
                    <button
                      type="button"
                      (click)="store.revertObjectToProposal(selObj.id)"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <app-lucide-icon name="rotate-ccw" [size]="11"></app-lucide-icon>
                      <span>Revert to Proposal</span>
                    </button>
                  }

                  <button
                    type="button"
                    [disabled]="!store.isObjectDirty()"
                    (click)="store.applyObjectDraft()"
                    class="h-7 px-3 rounded font-semibold text-xs flex items-center gap-1.5 transition-colors"
                    [class.bg-blue-600]="store.isObjectDirty()"
                    [class.text-white]="store.isObjectDirty()"
                    [class.cursor-pointer]="store.isObjectDirty()"
                    [class.bg-slate-100]="!store.isObjectDirty()"
                    [class.text-slate-400]="!store.isObjectDirty()"
                    [class.cursor-not-allowed]="!store.isObjectDirty()">
                    <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                    <span>Apply Changes</span>
                  </button>
                </div>
              </div>

              <!-- Object Editable Form in Draft -->
              @if (store.objectDraft(); as objDraft) {
                <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-white p-3 rounded-md border border-slate-200">
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Namespace</label>
                    <input
                      type="text"
                      [(ngModel)]="objDraft.currentTargetNamespace"
                      class="h-7 px-2 text-xs bg-slate-50 border border-slate-200 rounded text-slate-800 font-medium" />
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Object Name</label>
                    <input
                      type="text"
                      [(ngModel)]="objDraft.currentTargetName"
                      class="h-7 px-2 text-xs bg-slate-50 border border-slate-200 rounded text-slate-800 font-medium" />
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Row Scope</label>
                    <app-custom-select
                      [options]="rowScopeOptions"
                      [value]="objDraft.rowFilterMode"
                      (valueChange)="objDraft.rowFilterMode = $event"
                      size="sm">
                    </app-custom-select>
                  </div>
                  <div class="flex items-center justify-between pt-4">
                    <label class="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        [(ngModel)]="objDraft.isIncluded"
                        class="rounded border-slate-300 text-blue-600 focus:ring-0" />
                        <span class="text-xs font-semibold text-slate-800">Include Object</span>
                    </label>
                    <button
                      type="button"
                      (click)="store.openImpactModal(selObj)"
                      class="h-7 px-2 text-[11px] font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded border border-indigo-200 cursor-pointer">
                      View Impact ({{ selObj.structuralImpact.dependentObjectsCount }})
                    </button>
                  </div>
                </div>
              }

              <!-- Structural Impact Summary Strip -->
              <div class="flex items-center gap-6 text-[11px] text-slate-600 pt-0.5">
                <span class="flex items-center gap-1.5 font-medium">
                  <app-lucide-icon name="key" [size]="12" class="text-emerald-600"></app-lucide-icon>
                  <span class="font-bold text-slate-800">Primary Key:</span>
                  <span class="text-emerald-700">{{ selObj.structuralImpact.primaryKeyStatus }}</span>
                </span>
                <span class="h-3 w-[1px] bg-slate-300"></span>
                <span class="flex items-center gap-1.5 font-medium">
                  <app-lucide-icon name="link-2" [size]="12" class="text-slate-400"></app-lucide-icon>
                  <span class="font-bold text-slate-800">Foreign Keys:</span>
                  <span>{{ selObj.structuralImpact.rewiredFkCount }} rewired of {{ selObj.structuralImpact.foreignKeysCount }}</span>
                </span>
                <span class="h-3 w-[1px] bg-slate-300"></span>
                <span class="flex items-center gap-1.5 font-medium">
                  <app-lucide-icon name="list-ordered" [size]="12" class="text-slate-400"></app-lucide-icon>
                  <span class="font-bold text-slate-800">Indexes:</span>
                  <span>{{ selObj.structuralImpact.indexesCount }} mapped</span>
                </span>
                <span class="h-3 w-[1px] bg-slate-300"></span>
                <span class="flex items-center gap-1.5 font-medium">
                  <app-lucide-icon name="network" [size]="12" class="text-indigo-600"></app-lucide-icon>
                  <span class="font-bold text-slate-800">Dependent Objects:</span>
                  <span class="font-bold text-indigo-700">{{ selObj.structuralImpact.dependentObjectsCount }}</span>
                </span>
              </div>

            </div>
          }

        </div>

      </section>

    </div>
  `
})
export class MappingStructureComponent {
  public readonly store = inject(Step5MappingStoreService);
  public searchQuery: string = '';
  public showAdvancedRouting: boolean = false;

  public readonly rowScopeOptions = [
    { label: 'All rows (No filter)', value: 'ALL' },
    { label: 'Custom SQL Predicate', value: 'CUSTOM' }
  ];

  public filteredNamespaces(): any[] {
    const list = this.store.namespaces();
    const q = this.searchQuery.trim().toLowerCase();
    if (!q) return list;
    return list.filter(n =>
      n.sourceNamespace.toLowerCase().includes(q) ||
      n.currentTargetNamespace.toLowerCase().includes(q) ||
      this.getObjectsInNamespace(n.sourceNamespace).some(o => o.sourceName.toLowerCase().includes(q))
    );
  }

  public getObjectsInNamespace(nsName: string): any[] {
    return this.store.objects().filter(o => o.sourceNamespace === nsName);
  }

  public currentNamespaceObjects(): any[] {
    const curNs = this.store.selectedNamespaceName();
    if (!curNs) return [];
    return this.getObjectsInNamespace(curNs);
  }

  public toggleInclusion(obj: any): void {
    if (obj.isIncluded && obj.structuralImpact.dependentObjectsCount > 0) {
      // Prompt impact before excluding
      this.store.openImpactModal(obj);
    } else {
      this.store.objects.update(list =>
        list.map(o => (o.id === obj.id ? { ...o, isIncluded: !o.isIncluded, isModified: true, status: 'MODIFIED' } : o))
      );
    }
  }
}
