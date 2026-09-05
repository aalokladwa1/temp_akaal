import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent } from '../../../../shared/components/custom-select.component';
import { ColumnMappingContract } from './step5-mapping.models';

@Component({
  selector: 'app-mapping-fields',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  host: {
    class: 'flex flex-1 w-full h-full min-h-0'
  },
  template: `
    <div class="w-full h-full flex gap-3 min-h-0 font-sans text-xs select-none">
      
      <!-- ========================================================================= -->
      <!-- LEFT PANE: SCOPED OBJECT NAVIGATOR (~22%)                                 -->
      <!-- ========================================================================= -->
      <aside class="w-72 bg-white border border-slate-200 rounded-lg flex flex-col shrink-0 overflow-hidden">
        
        <div class="p-3 border-b border-slate-200 bg-slate-50/50 flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-800 text-xs tracking-tight">Scoped Objects</span>
            <span class="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
              {{ store.filteredObjects().length }}
            </span>
          </div>
          <div class="relative">
            <input
              type="text"
              [(ngModel)]="objectSearchQuery"
              placeholder="Search objects..."
              class="w-full h-7 pl-8 pr-2.5 text-xs bg-white border border-slate-200 rounded-md focus:outline-none focus:border-blue-500 text-slate-800 placeholder:text-slate-400 font-normal" />
            <app-lucide-icon name="search" [size]="12" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
          </div>
        </div>

        <div class="flex-1 min-h-0 overflow-y-auto p-2 flex flex-col gap-1">
          @for (obj of filteredObjectsList(); track obj.id) {
            <div
              (click)="store.selectObject(obj.id)"
              class="p-2.5 rounded-md border flex items-center justify-between cursor-pointer transition-colors hover:border-slate-300"
              [class.border-blue-500]="store.selectedObjectId() === obj.id"
              [class.bg-blue-50]="store.selectedObjectId() === obj.id"
              [class.border-slate-200]="store.selectedObjectId() !== obj.id"
              [class.bg-white]="store.selectedObjectId() !== obj.id">
              
              <div class="flex flex-col min-w-0 gap-0.5">
                <div class="flex items-center gap-1.5">
                  <span class="font-bold text-xs text-slate-900 truncate">{{ obj.sourceName }}</span>
                  <span class="text-[10px] font-mono text-slate-400">({{ obj.columns.length }})</span>
                </div>
                <div class="flex items-center gap-1 text-[11px] text-slate-500 truncate">
                  <span>{{ obj.sourceNamespace }}</span>
                  <app-lucide-icon name="arrow-right" [size]="10" class="text-slate-400 shrink-0"></app-lucide-icon>
                  <span class="text-slate-700 font-medium">{{ obj.currentTargetName }}</span>
                </div>
              </div>

              <div class="flex items-center gap-1 shrink-0">
                @if (obj.status === 'BLOCKED') {
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-rose-100 text-rose-800">Blocked</span>
                } @else if (obj.status === 'NEEDS_REVIEW') {
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-100 text-amber-900">Review</span>
                } @else if (obj.isModified) {
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-blue-100 text-blue-800">Modified</span>
                } @else {
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-50 text-emerald-700">Auto</span>
                }
              </div>

            </div>
          }
        </div>

      </aside>

      <!-- ========================================================================= -->
      <!-- RIGHT PANE: BROAD FIELD MAPPING WORKBENCH (~78%)                          -->
      <!-- ========================================================================= -->
      <section aria-label="Field Mappings Workbench" class="flex-1 bg-white border border-slate-200 rounded-lg flex flex-col min-w-0 overflow-hidden">
        
        @if (store.selectedObject(); as obj) {
          
          <!-- Top Header Strip for Selected Object -->
          <div class="p-3.5 border-b border-slate-200 bg-slate-50/50 flex flex-col gap-2 shrink-0">
            
            <div class="flex items-center justify-between">
              <!-- Object Breadcrumb & Summary -->
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded bg-white border border-slate-200 flex items-center justify-center">
                  <app-lucide-icon name="table" [size]="15" class="text-slate-700"></app-lucide-icon>
                </div>
                <div class="flex flex-col">
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-xs text-slate-900">{{ obj.sourceNamespace }}.{{ obj.sourceName }}</span>
                    <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                    <span class="font-bold text-xs text-blue-700">{{ obj.currentTargetNamespace }}.{{ obj.currentTargetName }}</span>
                    @if (obj.isModified) {
                      <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                        Modified
                      </span>
                    }
                  </div>
                  <div class="flex items-center gap-3 text-[11px] text-slate-500 font-medium">
                    <span>{{ obj.columns.length }} fields</span>
                    <span>·</span>
                    <span class="text-emerald-700">{{ getCount(obj, 'AUTO_MAPPED') }} Automatic</span>
                    <span>·</span>
                    <span class="text-blue-700">{{ getCount(obj, 'MODIFIED') }} Modified</span>
                    <span>·</span>
                    <span class="text-amber-700">{{ getCount(obj, 'NEEDS_REVIEW') }} Review</span>
                  </div>
                </div>
              </div>

              <!-- Top Actions: Add Generated Field & Revert Object -->
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  (click)="store.addGeneratedTargetField()"
                  class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 text-slate-700 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                  <app-lucide-icon name="plus-circle" [size]="12" class="text-blue-600"></app-lucide-icon>
                  <span>Add Generated Field</span>
                </button>

                @if (obj.isModified) {
                  <button
                    type="button"
                    (click)="store.revertObjectToProposal(obj.id)"
                    class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 text-slate-600 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                    <app-lucide-icon name="rotate-ccw" [size]="11"></app-lucide-icon>
                    <span>Revert Object Changes</span>
                  </button>
                }
              </div>
            </div>

            <!-- Contextual Bulk Actions Bar (Appears when >= 1 field checkbox selected) -->
            @if (store.selectedFieldIds().size > 0) {
              <div class="px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-md flex items-center justify-between animate-in fade-in duration-100">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-blue-900">
                    {{ store.selectedFieldIds().size }} field(s) selected
                  </span>
                </div>
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    (click)="store.bulkIncludeFields(true)"
                    class="h-6 px-2 text-[11px] font-semibold text-blue-800 bg-white border border-blue-300 rounded hover:bg-blue-50 cursor-pointer">
                    Include Selected
                  </button>
                  <button
                    type="button"
                    (click)="store.bulkIncludeFields(false)"
                    class="h-6 px-2 text-[11px] font-semibold text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50 cursor-pointer">
                    Exclude Selected
                  </button>
                  <button
                    type="button"
                    (click)="store.selectedFieldIds().clear()"
                    class="h-6 px-2 text-[11px] font-medium text-slate-500 hover:text-slate-700 cursor-pointer">
                    Clear Selection
                  </button>
                </div>
              </div>
            }

          </div>

          <!-- Broad Field Mapping Table (Upper Region) -->
          <div
            class="overflow-y-auto border-b border-slate-200 transition-all duration-150"
            [class.flex-1]="!store.activeFieldDetailId()"
            [class.min-h-0]="!store.activeFieldDetailId()"
            [class.h-[48%]]="store.activeFieldDetailId()"
            [class.max-h-[50%]]="store.activeFieldDetailId()">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider z-10">
                <tr>
                  <th class="py-2.5 px-3 w-8 text-center">
                    <input
                      type="checkbox"
                      [checked]="isAllSelected(obj)"
                      (change)="onSelectAllToggle($event)"
                      class="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                  </th>
                  <th class="py-2.5 px-3">Source Field</th>
                  <th class="py-2.5 px-3">Source Type</th>
                  <th class="py-2.5 px-2 text-center w-8">
                    <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 inline-block"></app-lucide-icon>
                  </th>
                  <th class="py-2.5 px-3">Target Field</th>
                  <th class="py-2.5 px-3">Target Type</th>
                  <th class="py-2.5 px-3">Status / Controls</th>
                  <th class="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (col of obj.columns; track col.id) {
                  <!-- Standard Row -->
                  <tr
                    (click)="store.toggleFieldDetail(col.id)"
                    class="cursor-pointer transition-colors"
                    [class.bg-blue-50]="store.activeFieldDetailId() === col.id"
                    [class.border-l-2]="store.activeFieldDetailId() === col.id"
                    [class.border-blue-600]="store.activeFieldDetailId() === col.id"
                    [class.hover:bg-slate-50]="store.activeFieldDetailId() !== col.id">
                    
                    <!-- Checkbox -->
                    <td class="py-2.5 px-3 text-center" (click)="$event.stopPropagation()">
                      <input
                        type="checkbox"
                        [checked]="store.selectedFieldIds().has(col.id)"
                        (change)="store.toggleFieldSelection(col.id)"
                        class="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                    </td>

                    <!-- Source Field -->
                    <td class="py-2.5 px-3 font-semibold text-slate-900">
                      <div class="flex items-center gap-1.5">
                        <span>{{ col.sourceField }}</span>
                        @if (col.isGenerated) {
                          <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                            Generated
                          </span>
                        }
                      </div>
                    </td>

                    <!-- Source Type -->
                    <td class="py-2.5 px-3 text-slate-500 font-mono text-[11px]">
                      {{ col.sourceType }}
                    </td>

                    <!-- Arrow -->
                    <td class="py-2.5 px-2 text-center text-slate-400">
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 inline-block"></app-lucide-icon>
                    </td>

                    <!-- Target Field -->
                    <td class="py-2.5 px-3">
                      <span class="font-bold text-slate-900" [class.line-through]="!col.isIncluded" [class.text-slate-400]="!col.isIncluded">
                        {{ col.currentTargetField }}
                      </span>
                    </td>

                    <!-- Target Type -->
                    <td class="py-2.5 px-3">
                      <div class="flex items-center gap-1.5 font-mono text-[11px]">
                        <span class="font-semibold text-slate-800">{{ col.currentTargetType }}</span>
                        @if (col.conversionSafety === 'LOSSY') {
                          <span class="px-1.5 py-0.2 rounded text-[9px] font-sans font-bold bg-amber-100 text-amber-900">
                            Lossy
                          </span>
                        }
                      </div>
                    </td>

                    <!-- Status / Active Controls -->
                    <td class="py-2.5 px-3">
                      <div class="flex items-center gap-1.5 flex-wrap">
                        @if (col.status === 'BLOCKED') {
                          <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                            Blocked
                          </span>
                        } @else if (col.status === 'NEEDS_REVIEW') {
                          <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                            Needs Review
                          </span>
                        } @else if (col.isModified) {
                          <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                            Modified
                          </span>
                        } @else {
                          <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700">
                            Auto
                          </span>
                        }

                        @if (col.privacyOptionId && col.privacyOptionId !== 'NONE') {
                          <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-100 text-slate-600">
                            Privacy
                          </span>
                        }
                        @if (col.cleansingOptionId && col.cleansingOptionId !== 'NONE') {
                          <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-100 text-slate-600">
                            Cleanse
                          </span>
                        }
                      </div>
                    </td>

                    <!-- Actions -->
                    <td class="py-2.5 px-3 text-right" (click)="$event.stopPropagation()">
                      <button
                        type="button"
                        (click)="store.toggleFieldDetail(col.id)"
                        class="h-6 px-2 text-[11px] font-semibold border rounded cursor-pointer transition-colors"
                        [class.text-blue-700]="store.activeFieldDetailId() === col.id"
                        [class.bg-blue-50]="store.activeFieldDetailId() === col.id"
                        [class.border-blue-300]="store.activeFieldDetailId() === col.id"
                        [class.text-slate-600]="store.activeFieldDetailId() !== col.id"
                        [class.bg-white]="store.activeFieldDetailId() !== col.id"
                        [class.border-slate-200]="store.activeFieldDetailId() !== col.id"
                        [class.hover:bg-blue-50]="store.activeFieldDetailId() !== col.id"
                        [class.hover:text-blue-700]="store.activeFieldDetailId() !== col.id">
                        {{ store.activeFieldDetailId() === col.id ? 'Close' : 'Customize' }}
                      </button>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>

          <!-- ========================================================================= -->
          <!-- BROAD LOWER DETAIL DOCK (Dedicated Scannable Workbench Region)             -->
          <!-- ========================================================================= -->
          @if (store.activeFieldDetailId() && store.fieldDraft(); as draft) {
            <div class="flex-1 min-h-0 bg-slate-50/60 border-t border-slate-200 flex flex-col overflow-y-auto p-4 gap-3.5 animate-in fade-in duration-100">
              
              <!-- Dock Header with State, Info & Actions -->
              <div class="flex items-center justify-between shrink-0">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-xs text-slate-900">Customize Field: {{ draft.sourceField }}</span>
                  <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                  <span class="font-bold text-xs text-blue-700">{{ draft.currentTargetField }}</span>
                  @if (draft.isModified) {
                    <span class="text-[10px] text-slate-500 font-medium">
                      (Original proposal: {{ draft.originalProposal.targetField }} {{ draft.originalProposal.targetType }})
                    </span>
                  }
                </div>

                <div class="flex items-center gap-2">
                  @if (draft.isModified || store.isFieldDirty()) {
                    <button
                      type="button"
                      (click)="store.revertFieldToProposal(draft.id)"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <app-lucide-icon name="rotate-ccw" [size]="11"></app-lucide-icon>
                      <span>Revert to Proposal</span>
                    </button>
                  }

                  <button
                    type="button"
                    [disabled]="!store.isFieldDirty()"
                    (click)="store.applyFieldDraft()"
                    class="h-7 px-3 rounded font-semibold text-xs flex items-center gap-1.5 transition-colors"
                    [class.bg-blue-600]="store.isFieldDirty()"
                    [class.text-white]="store.isFieldDirty()"
                    [class.cursor-pointer]="store.isFieldDirty()"
                    [class.hover:bg-blue-700]="store.isFieldDirty()"
                    [class.bg-slate-100]="!store.isFieldDirty()"
                    [class.text-slate-400]="!store.isFieldDirty()"
                    [class.cursor-not-allowed]="!store.isFieldDirty()">
                    <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                    <span>Apply Field Override</span>
                  </button>

                  <button
                    type="button"
                    (click)="store.toggleFieldDetail(draft.id)"
                    class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 font-semibold text-xs cursor-pointer transition-colors"
                    title="Close detail panel">
                    <span>Close</span>
                  </button>
                </div>
              </div>

              <!-- Lossiness Alert (if applicable) -->
              @if (draft.conversionSafety === 'LOSSY' || (draft.lossinessReasons && draft.lossinessReasons.length > 0)) {
                <div class="p-3 bg-amber-50 border border-amber-200 rounded-md flex flex-col gap-1.5 shrink-0">
                  <div class="flex items-center gap-2 text-amber-900 font-bold text-xs">
                    <app-lucide-icon name="alert-triangle" [size]="14" class="text-amber-700"></app-lucide-icon>
                    <div class="flex items-center gap-1.5">
                      <span>Lossy Conversion Detected: {{ draft.sourceType }}</span>
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-amber-700 shrink-0"></app-lucide-icon>
                      <span>{{ draft.currentTargetType }}</span>
                    </div>
                  </div>
                  <ul class="list-disc list-inside text-[11px] text-amber-950 font-normal pl-1 space-y-0.5">
                    @for (reason of draft.lossinessReasons; track reason) {
                      <li>{{ reason }} — Truncation or scale reduction may lose data during migration</li>
                    }
                  </ul>
                  <div class="pt-1 flex items-center gap-2">
                    <span class="text-[11px] text-amber-900 font-semibold shrink-0">Operator Rationale:</span>
                    <input
                      type="text"
                      [ngModel]="draft.operatorReason"
                      (ngModelChange)="store.patchFieldDraft({operatorReason: $event})"
                      placeholder="Provide reason for intentional lossy override..."
                      class="flex-1 h-7 px-2.5 bg-white border border-slate-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded text-xs text-slate-800 font-medium placeholder:text-slate-400 focus:outline-none transition-colors" />
                  </div>
                </div>
              }

              <!-- Primary Edit Fields Grid -->
              <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-white p-3.5 rounded-lg border border-slate-200 shrink-0">
                
                <!-- Target Field Name -->
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Field Name</label>
                  <input
                    type="text"
                    [ngModel]="draft.currentTargetField"
                    (ngModelChange)="store.patchFieldDraft({currentTargetField: $event})"
                    class="h-7 px-2 text-xs bg-slate-50 border border-slate-200 rounded text-slate-900 font-medium focus:border-blue-500 focus:bg-white focus:outline-none" />
                </div>

                <!-- Target Data Type -->
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Data Type</label>
                  <app-custom-select
                    [options]="getTargetTypeOptions(draft)"
                    [value]="draft.currentTargetType"
                    (valueChange)="store.patchFieldDraft({currentTargetType: $event})"
                    size="sm">
                  </app-custom-select>
                </div>

                <!-- Precision / Scale / Length (Contextual) -->
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Precision / Scale</label>
                  <div class="flex items-center gap-2">
                    <input
                      type="number"
                      [ngModel]="draft.currentPrecision"
                      (ngModelChange)="store.patchFieldDraft({currentPrecision: $event})"
                      placeholder="Prec"
                      title="Precision"
                      class="w-20 h-7 px-2 text-xs bg-slate-50 border border-slate-200 rounded text-slate-900 focus:border-blue-500 focus:bg-white focus:outline-none" />
                    <span class="text-slate-400">,</span>
                    <input
                      type="number"
                      [ngModel]="draft.currentScale"
                      (ngModelChange)="store.patchFieldDraft({currentScale: $event})"
                      placeholder="Scale"
                      title="Scale"
                      class="w-20 h-7 px-2 text-xs bg-slate-50 border border-slate-200 rounded text-slate-900 focus:border-blue-500 focus:bg-white focus:outline-none" />
                  </div>
                </div>

                <!-- Inclusion -->
                <div class="flex items-center pt-4">
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      [ngModel]="draft.isIncluded"
                      (ngModelChange)="store.patchFieldDraft({isIncluded: $event})"
                      class="rounded border-slate-300 text-blue-600 focus:ring-0" />
                    <span class="text-xs font-semibold text-slate-800">Include in Migration</span>
                  </label>
                </div>

              </div>

              <!-- Advanced Data Controls for this Field -->
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3.5 rounded-lg border border-slate-200 shrink-0">
                
                <!-- Privacy Strategy -->
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Field Privacy Rule</label>
                  <app-custom-select
                    [options]="privacyOptionsList()"
                    [value]="draft.privacyOptionId"
                    (valueChange)="store.patchFieldDraft({privacyOptionId: $event})"
                    size="sm">
                  </app-custom-select>
                </div>

                <!-- Privacy Parameter / Vault Reference -->
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Secret / Mask Param</label>
                  <input
                    type="text"
                    [ngModel]="draft.privacyParam"
                    (ngModelChange)="store.patchFieldDraft({privacyParam: $event})"
                    placeholder="e.g. vault://keys/salt or preserve_last=4"
                    class="h-7 px-2 text-xs bg-slate-50 border border-slate-200 rounded text-slate-900 font-mono focus:border-blue-500 focus:bg-white focus:outline-none" />
                </div>

                <!-- Cleansing Rule & Shortcut -->
                <div class="flex flex-col gap-1">
                  <div class="flex items-center justify-between">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Cleansing Rule</label>
                    <button
                      type="button"
                      (click)="store.routeToControls('CLEANSING')"
                      class="text-[10px] font-semibold text-blue-600 hover:text-blue-800 cursor-pointer flex items-center gap-0.5">
                      <span>Open in Controls</span>
                      <app-lucide-icon name="arrow-up-right" [size]="10"></app-lucide-icon>
                    </button>
                  </div>
                  <app-custom-select
                    [options]="cleansingOptionsList()"
                    [value]="draft.cleansingOptionId"
                    (valueChange)="store.patchFieldDraft({cleansingOptionId: $event})"
                    size="sm">
                  </app-custom-select>
                </div>

              </div>

            </div>
          }

        } @else {
          <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
            <app-lucide-icon name="table-2" [size]="28" class="text-slate-300 mb-2"></app-lucide-icon>
            <span class="font-bold text-xs text-slate-600">No Object Selected</span>
            <span class="text-[11px] text-slate-400">Select a scoped resource from the left pane to begin mapping fields</span>
          </div>
        }

      </section>

    </div>
  `
})
export class MappingFieldsComponent {
  public readonly store = inject(Step5MappingStoreService);
  public objectSearchQuery: string = '';

  public filteredObjectsList(): any[] {
    const list = this.store.objects();
    const q = this.objectSearchQuery.trim().toLowerCase();
    if (!q) return list;
    return list.filter(o =>
      o.sourceName.toLowerCase().includes(q) ||
      o.currentTargetName.toLowerCase().includes(q) ||
      o.sourceNamespace.toLowerCase().includes(q)
    );
  }

  public getCount(obj: any, status: string): number {
    return obj.columns.filter((c: any) => c.status === status).length;
  }

  public isAllSelected(obj: any): boolean {
    if (!obj || obj.columns.length === 0) return false;
    const set = this.store.selectedFieldIds();
    return obj.columns.every((c: any) => set.has(c.id));
  }

  public onSelectAllToggle(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.store.toggleSelectAllFields(checked);
  }

  public getTargetTypeOptions(draft: any): { label: string; value: string }[] {
    const opts = draft.targetTypeOptions || [draft.currentTargetType, 'VARCHAR', 'TEXT', 'BIGINT', 'DECIMAL'];
    return opts.map((opt: string) => ({ label: opt, value: opt }));
  }

  public privacyOptionsList(): { label: string; value: string }[] {
    return this.store.privacyOptions().map(p => ({ label: p.label, value: p.id }));
  }

  public cleansingOptionsList(): { label: string; value: string }[] {
    return this.store.cleansingOptions().map(c => ({ label: c.label, value: c.id }));
  }
}
