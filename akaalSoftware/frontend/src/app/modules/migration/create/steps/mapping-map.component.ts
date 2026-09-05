import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { ColumnMappingContract, ObjectMappingContract } from './step5-mapping.models';

/**
 * MappingMapComponent
 *
 * Full operator control mapping studio for Step 5.
 * Features a scoped object navigator on the left and a dense, protected-width
 * mapping workspace on the right with inline focused field detail controls.
 *
 * Strictly adheres to Zero Shadow, Zero Blur, and Roboto typography.
 */
@Component({
  selector: 'app-mapping-map',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex-1 flex gap-3 min-h-0 select-none font-sans text-xs">
      
      <!-- ========================================================================= -->
      <!-- LEFT PANE: SCOPED OBJECT NAVIGATOR (Width 288px-320px, Dense List)         -->
      <!-- ========================================================================= -->
      <div class="w-72 lg:w-80 bg-white border border-slate-200 rounded-md flex flex-col min-h-0 shrink-0 overflow-hidden">
        
        <!-- Navigator Header & Search -->
        <div class="p-3 border-b border-slate-200 bg-slate-50 flex flex-col gap-2 shrink-0">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">SCOPED OBJECTS</span>
            <span class="text-[10px] font-medium text-slate-500">{{ store.filteredObjects().length }} items</span>
          </div>

          <!-- Quick Search -->
          <div class="h-7.5 px-2.5 bg-white border border-slate-200 rounded flex items-center gap-1.5 text-xs">
            <app-lucide-icon name="search" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
            <input
              type="text"
              [ngModel]="navigatorSearch()"
              (ngModelChange)="navigatorSearch.set($event)"
              placeholder="Filter objects..."
              aria-label="Filter objects in navigator"
              class="w-full text-xs text-slate-800 placeholder:text-slate-500 focus:outline-none border-none bg-transparent" />
          </div>
        </div>

        <!-- Object List (Scrollable) -->
        <div class="flex-1 overflow-y-auto divide-y divide-slate-100 min-h-0">
          @for (obj of displayedNavigatorObjects(); track obj.id) {
            <button
              type="button"
              (click)="store.selectObject(obj.id)"
              class="w-full px-3.5 py-2.5 text-left flex items-center justify-between transition-colors cursor-pointer"
              [class.bg-blue-50]="store.selectedObjectId() === obj.id"
              [class.hover:bg-slate-50]="store.selectedObjectId() !== obj.id">
              
              <div class="flex items-center gap-2 min-w-0">
                <!-- Status Dot Indicator -->
                @if (obj.status === 'BLOCKED') {
                  <span class="w-2 h-2 rounded-full bg-rose-600 shrink-0" title="Blocked"></span>
                } @else if (obj.status === 'NEEDS_REVIEW') {
                  <span class="w-2 h-2 rounded-full bg-amber-500 shrink-0" title="Needs Review"></span>
                } @else if (obj.status === 'MODIFIED') {
                  <span class="w-2 h-2 rounded-full bg-blue-600 shrink-0" title="Modified"></span>
                } @else {
                  <span class="w-2 h-2 rounded-full bg-emerald-600 shrink-0" title="Auto-mapped"></span>
                }

                <div class="flex flex-col min-w-0">
                  <span class="font-medium text-slate-900 text-xs truncate" [class.font-bold]="store.selectedObjectId() === obj.id">
                    {{ obj.sourceName }}
                  </span>
                  <span class="text-[10px] text-slate-600 truncate">
                    {{ obj.sourceNamespace }} &middot; {{ obj.sourceTypeLabel }}
                  </span>
                </div>
              </div>

              <!-- Column Count Badge -->
              <span class="text-[10px] font-medium text-slate-600 shrink-0">
                {{ obj.columns.length }}
              </span>

            </button>
          }

          @if (displayedNavigatorObjects().length === 0) {
            <div class="p-6 text-center text-slate-400 text-xs">
              No matching objects.
            </div>
          }
        </div>

      </div>

      <!-- ========================================================================= -->
      <!-- RIGHT PANE: DETAILED MAPPING WORKSPACE                                     -->
      <!-- ========================================================================= -->
      @if (store.selectedObject(); as sel) {
        <div class="flex-1 bg-white border border-slate-200 rounded-md flex flex-col min-h-0 overflow-hidden">
          
          <!-- 1. Object Mapping Header & High-Level Routing -->
          <div class="p-3.5 border-b border-slate-200 bg-slate-50/80 flex flex-col gap-3 shrink-0">
            
            <div class="flex items-center justify-between gap-3 flex-wrap">
              
              <!-- Source & Status Identification -->
              <div class="flex items-center gap-2 min-w-0">
                <app-lucide-icon name="table" [size]="16" class="text-slate-600 shrink-0"></app-lucide-icon>
                <div class="flex flex-col">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-bold text-slate-900">{{ sel.sourceNamespace }}.{{ sel.sourceName }}</span>
                    <span class="text-xs text-slate-500 font-normal">({{ sel.sourceTypeLabel }})</span>
                    @if (sel.estimatedRows) {
                      <span class="text-[11px] font-medium text-slate-500">&middot; {{ formatNumber(sel.estimatedRows) }} rows</span>
                    }
                  </div>
                </div>
              </div>

              <!-- Status Badge & Revert -->
              <div class="flex items-center gap-2">
                @if (sel.status === 'BLOCKED') {
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                    BLOCKED
                  </span>
                } @else if (sel.status === 'NEEDS_REVIEW') {
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                    NEEDS REVIEW
                  </span>
                } @else if (sel.status === 'MODIFIED') {
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    MODIFIED
                  </span>
                } @else {
                  <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    AUTO-MAPPED
                  </span>
                }

                @if (sel.isModified) {
                  <button
                    type="button"
                    (click)="store.promptRevertObject(sel.id)"
                    class="h-6 px-2 text-[11px] font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded bg-white hover:bg-slate-50 cursor-pointer transition-colors"
                    title="Revert all changes for this object to original proposal">
                    Revert Object
                  </button>
                }
              </div>

            </div>

            <!-- Routing Controls Row (Target Namespace & Target Object Name) -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1.5 border-t border-slate-200/60 items-end">
              
              <!-- Target Namespace -->
              <div class="flex flex-col gap-1">
                <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Namespace</label>
                <input
                  type="text"
                  [ngModel]="sel.currentTargetNamespace"
                  (ngModelChange)="store.updateTargetNamespace(sel.id, $event)"
                  aria-label="Target Namespace"
                  class="h-8 px-2.5 rounded border border-slate-200 text-xs text-slate-800 focus:outline-none focus:border-blue-500" />
              </div>

              <!-- Target Object Name -->
              <div class="flex flex-col gap-1">
                <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Object Name</label>
                <input
                  type="text"
                  [ngModel]="sel.currentTargetName"
                  (ngModelChange)="store.updateTargetObjectName(sel.id, $event)"
                  aria-label="Target Object Name"
                  class="h-8 px-2.5 rounded border border-slate-200 text-xs text-slate-800 focus:outline-none focus:border-blue-500" />
              </div>

              <!-- Inclusion Toggle & Object Controls Trigger -->
              <div class="flex items-center justify-between gap-2 h-8">
                <label class="flex items-center gap-2 cursor-pointer select-none text-xs font-medium text-slate-700">
                  <input
                    type="checkbox"
                    [checked]="sel.isIncluded"
                    (change)="store.toggleObjectInclusion(sel.id)"
                    class="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                  <span>Include in Scope</span>
                </label>

                <button
                  type="button"
                  (click)="showObjectControls.set(!showObjectControls())"
                  class="h-8 px-3 text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded cursor-pointer transition-colors flex items-center gap-1.5">
                  <app-lucide-icon [name]="showObjectControls() ? 'chevron-up' : 'sliders'" [size]="12" class="text-slate-500"></app-lucide-icon>
                  <span>Data Controls</span>
                </button>
              </div>

            </div>

            <!-- Object-Level Data Controls (Row Filter & Deduplication) -->
            @if (showObjectControls()) {
              <div class="p-3 bg-white border border-slate-200 rounded-md flex flex-col gap-3 animate-in fade-in duration-100">
                <div class="text-[11px] font-bold text-slate-700 border-b border-slate-100 pb-1 flex items-center justify-between">
                  <span>Object-Level Data Controls</span>
                  <span class="text-[10px] text-slate-400 font-normal">Scoped row predicates and deduplication policies</span>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <!-- Row Filter -->
                  <div class="flex flex-col gap-1.5">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Row Scope Filter</label>
                    <div class="flex items-center gap-3">
                      <label class="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                        <input
                          type="radio"
                          name="rowFilterMode"
                          [checked]="sel.rowFilterMode === 'ALL'"
                          (change)="store.setRowFilter(sel.id, 'ALL')" />
                        <span>All rows</span>
                      </label>
                      <label class="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                        <input
                          type="radio"
                          name="rowFilterMode"
                          [checked]="sel.rowFilterMode === 'CUSTOM'"
                          (change)="store.setRowFilter(sel.id, 'CUSTOM', sel.rowFilterPredicate || 'WHERE ')" />
                        <span>Custom filter</span>
                      </label>
                    </div>

                    @if (sel.rowFilterMode === 'CUSTOM') {
                      <input
                        type="text"
                        [ngModel]="sel.rowFilterPredicate"
                        (ngModelChange)="store.setRowFilter(sel.id, 'CUSTOM', $event)"
                        placeholder="WHERE created_at >= '2025-01-01' AND status = 'ACTIVE'"
                        class="h-7 px-2 rounded border border-slate-200 text-[11px] text-slate-800 focus:outline-none focus:border-blue-500 mt-1" />
                    }
                  </div>

                  <!-- Deduplication -->
                  <div class="flex flex-col gap-1.5">
                    <div class="flex items-center justify-between">
                      <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Deduplication</label>
                      <label class="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                        <input
                          type="checkbox"
                          [checked]="sel.deduplication.enabled"
                          (change)="toggleDedupEnabled(sel)" />
                        <span>Enable Dedup</span>
                      </label>
                    </div>

                    @if (sel.deduplication.enabled) {
                      <div class="flex flex-col gap-1.5 mt-1">
                        <input
                          type="text"
                          [ngModel]="sel.deduplication.keyFields.join(', ')"
                          (ngModelChange)="updateDedupKeys(sel, $event)"
                          placeholder="Key columns: acc_id, cust_id"
                          class="h-7 px-2 rounded border border-slate-200 text-[11px] text-slate-800 focus:outline-none focus:border-blue-500" />

                        <select
                          [ngModel]="sel.deduplication.survivorPolicyOptionId || 'FIRST_ARRIVED'"
                          (ngModelChange)="updateDedupPolicy(sel, $event)"
                          class="h-7 px-2 rounded border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:border-blue-500">
                          @for (pol of store.survivorPolicyOptions(); track pol.id) {
                            <option [value]="pol.id">{{ pol.label }}</option>
                          }
                        </select>
                      </div>
                    }
                  </div>
                </div>
              </div>
            }

            <!-- Object Issues / Collision Banner -->
            @if (sel.issues.length > 0) {
              @for (iss of sel.issues; track iss.id) {
                <div class="p-3 rounded-md flex flex-col gap-1 text-xs"
                  [class.bg-rose-50]="iss.severity === 'BLOCKED'"
                  [class.text-rose-800]="iss.severity === 'BLOCKED'"
                  [class.border]="true"
                  [class.border-rose-200]="iss.severity === 'BLOCKED'"
                  [class.bg-amber-50]="iss.severity === 'NEEDS_REVIEW'"
                  [class.text-amber-800]="iss.severity === 'NEEDS_REVIEW'"
                  [class.border-amber-200]="iss.severity === 'NEEDS_REVIEW'">
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5 font-bold">
                      <app-lucide-icon [name]="iss.severity === 'BLOCKED' ? 'alert-circle' : 'alert-triangle'" [size]="13" class="shrink-0"></app-lucide-icon>
                      <span>{{ iss.title }}</span>
                    </div>
                    @if (iss.recommendation) {
                      <span class="text-[11px] opacity-90 shrink-0 font-medium">Guidance: {{ iss.recommendation }}</span>
                    }
                  </div>
                  <p class="font-normal leading-relaxed pl-5 text-[11px]">{{ iss.reason }}</p>
                </div>
              }
            }

          </div>

          <!-- 2. Protected Width Column Grid (Source | Source Type | -> | Target | Target Type | Include) -->
          <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
            
            <!-- Grid Header -->
            <div class="h-9 bg-slate-100/80 border-b border-slate-200 px-4 flex items-center text-[10px] font-bold uppercase tracking-wider text-slate-600 shrink-0 select-none">
              <div class="flex-1 min-w-[140px] px-2">Source Field</div>
              <div class="w-36 lg:w-44 px-2">Source Type</div>
              <div class="w-8 flex items-center justify-center text-slate-400">
                <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
              </div>
              <div class="flex-1 min-w-[160px] px-2">Target Field</div>
              <div class="w-40 lg:w-48 px-2">Target Type</div>
              <div class="w-16 px-1 text-center">Include</div>
              <div class="w-20 px-1 text-right">Settings</div>
            </div>

            <!-- Column Rows (Scrollable with Inline Details) -->
            <div class="flex-1 overflow-y-auto divide-y divide-slate-100 min-h-0">
              @for (col of sel.columns; track col.id) {
                <div class="flex flex-col transition-colors" [class.bg-blue-50]="store.activeFieldDetailId() === col.id">
                  
                  <!-- Main Row -->
                  <div class="h-9 px-4 flex items-center text-xs hover:bg-slate-50 transition-colors">
                    
                    <!-- Source Field with Exception Marker -->
                    <div class="flex-1 min-w-[140px] px-2 flex items-center gap-1.5 min-w-0">
                      @if (col.status === 'BLOCKED') {
                        <span class="w-1.5 h-1.5 rounded-full bg-rose-600 shrink-0" title="Blocked"></span>
                      } @else if (col.status === 'NEEDS_REVIEW') {
                        <span class="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" title="Needs Review"></span>
                      } @else if (col.isModified) {
                        <span class="w-1.5 h-1.5 rounded-full bg-blue-600 shrink-0" title="Modified"></span>
                      }
                      <span class="font-medium text-slate-900 truncate" [title]="col.sourceField">{{ col.sourceField }}</span>
                    </div>

                    <!-- Source Type -->
                    <div class="w-36 lg:w-44 px-2 text-[11px] text-slate-500 truncate" [title]="col.sourceType">
                      {{ col.sourceType }}
                    </div>

                    <!-- Direction Arrow -->
                    <div class="w-8 flex items-center justify-center text-slate-300 select-none">
                      <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                    </div>

                    <!-- Target Field (Inline Editable) -->
                    <div class="flex-1 min-w-[160px] px-2">
                      <input
                        type="text"
                        [ngModel]="col.currentTargetField"
                        (ngModelChange)="store.updateTargetFieldName(sel.id, col.id, $event)"
                        [attr.aria-label]="'Target field name for ' + col.sourceField"
                        class="h-7 w-full px-2 rounded border border-transparent hover:border-slate-200 focus:border-blue-500 text-xs text-slate-900 bg-transparent focus:bg-white transition-colors" />
                    </div>

                    <!-- Target Type -->
                    <div class="w-40 lg:w-48 px-2">
                      <select
                        [ngModel]="col.currentTargetType"
                        (ngModelChange)="store.updateTargetFieldType(sel.id, col.id, $event)"
                        [attr.aria-label]="'Target data type for ' + col.sourceField"
                        class="h-7 w-full px-1.5 rounded border border-transparent hover:border-slate-200 focus:border-blue-500 text-xs text-slate-800 bg-transparent focus:bg-white transition-colors cursor-pointer">
                        @for (opt of col.targetTypeOptions || defaultTypeOptions; track opt) {
                          <option [value]="opt">{{ opt }}</option>
                        }
                      </select>
                    </div>

                    <!-- Inclusion Checkbox -->
                    <div class="w-16 px-1 flex items-center justify-center">
                      <input
                        type="checkbox"
                        [checked]="col.isIncluded"
                        (change)="store.toggleColumnInclusion(sel.id, col.id)"
                        [attr.aria-label]="'Include ' + col.sourceField + ' column in migration'"
                        class="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                    </div>

                    <!-- Inline Detail Toggle Button -->
                    <div class="w-20 px-1 text-right">
                      <button
                        type="button"
                        (click)="store.toggleFieldDetail(col.id)"
                        class="h-6.5 px-2.5 text-[11px] font-medium text-slate-600 hover:text-blue-600 hover:bg-slate-100 rounded cursor-pointer transition-colors inline-flex items-center gap-1"
                        [class.text-blue-700]="store.activeFieldDetailId() === col.id"
                        [class.bg-blue-100]="store.activeFieldDetailId() === col.id">
                        <span>Detail</span>
                        <app-lucide-icon [name]="store.activeFieldDetailId() === col.id ? 'chevron-up' : 'chevron-down'" [size]="11"></app-lucide-icon>
                      </button>
                    </div>

                  </div>

                  <!-- Inline Focused Field Detail (Revealed on Click) -->
                  @if (store.activeFieldDetailId() === col.id) {
                    <div class="px-6 py-3.5 bg-slate-50/90 border-t border-b border-slate-200 flex flex-col gap-3.5 animate-in fade-in duration-100 text-xs">
                      
                      <!-- Row 1: Parameter Overrides (Length, Precision, Scale, Default Expression) -->
                      <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
                        
                        <!-- Length (If applicable) -->
                        @if (isLengthApplicable(col.currentTargetType)) {
                          <div class="flex flex-col gap-1">
                            <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Length</label>
                            <input
                              type="number"
                              [ngModel]="col.length"
                              (ngModelChange)="store.updateTargetFieldType(sel.id, col.id, col.currentTargetType, { length: +$event })"
                              class="h-7 px-2 rounded border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:border-blue-500" />
                          </div>
                        }

                        <!-- Precision & Scale (If applicable) -->
                        @if (isNumericApplicable(col.currentTargetType)) {
                          <div class="flex flex-col gap-1">
                            <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Precision</label>
                            <input
                              type="number"
                              [ngModel]="col.precision"
                              (ngModelChange)="store.updateTargetFieldType(sel.id, col.id, col.currentTargetType, { precision: +$event })"
                              class="h-7 px-2 rounded border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:border-blue-500" />
                          </div>
                          <div class="flex flex-col gap-1">
                            <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Scale</label>
                            <input
                              type="number"
                              [ngModel]="col.scale"
                              (ngModelChange)="store.updateTargetFieldType(sel.id, col.id, col.currentTargetType, { scale: +$event })"
                              class="h-7 px-2 rounded border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:border-blue-500" />
                          </div>
                        }

                        <!-- Default Expression Override -->
                        <div class="flex flex-col gap-1 sm:col-span-2">
                          <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target Default Expression</label>
                          <input
                            type="text"
                            [ngModel]="col.currentDefaultExpression || col.defaultExpression || ''"
                            (ngModelChange)="store.updateDefaultExpression(sel.id, col.id, $event)"
                            placeholder="e.g. 'ACTIVE' or CURRENT_TIMESTAMP"
                            class="h-7 px-2 rounded border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:border-blue-500" />
                        </div>

                      </div>

                      <!-- Row 2: Privacy & Cleansing Controls (Capability-Driven) -->
                      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-200/60">
                        
                        <!-- Privacy Control -->
                        <div class="flex flex-col gap-1.5">
                          <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Privacy &amp; Masking</label>
                          <select
                            [ngModel]="col.privacyOptionId || 'NONE'"
                            (ngModelChange)="store.updatePrivacyControl(sel.id, col.id, $event === 'NONE' ? null : $event, col.privacyParam)"
                            class="h-7 px-2 rounded border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:border-blue-500">
                            @for (p of store.privacyOptions(); track p.id) {
                              <option [value]="p.id">{{ p.label }}</option>
                            }
                          </select>

                          @if (col.privacyOptionId && col.privacyOptionId !== 'NONE') {
                            @if (getPrivacyOption(col.privacyOptionId)?.requiresParam) {
                              <input
                                type="text"
                                [ngModel]="col.privacyParam"
                                (ngModelChange)="store.updatePrivacyControl(sel.id, col.id, col.privacyOptionId, $event)"
                                [placeholder]="getPrivacyOption(col.privacyOptionId)?.paramPlaceholder || 'Parameter reference'"
                                class="h-7 px-2 rounded border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:border-blue-500 mt-1" />
                            }
                          }
                        </div>

                        <!-- Cleansing Control -->
                        <div class="flex flex-col gap-1.5">
                          <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Cleansing Transformation</label>
                          <select
                            [ngModel]="col.cleansingOptionId || 'NONE'"
                            (ngModelChange)="store.updateCleansingControl(sel.id, col.id, $event === 'NONE' ? null : $event)"
                            class="h-7 px-2 rounded border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:border-blue-500">
                            @for (cl of store.cleansingOptions(); track cl.id) {
                              <option [value]="cl.id">{{ cl.label }}</option>
                            }
                          </select>
                        </div>

                      </div>

                      <!-- Footer of Inline Detail: Proposal Reference + Close -->
                      <div class="flex items-center justify-between pt-2 border-t border-slate-200/60 text-[11px] text-slate-500">
                        <div class="flex items-center gap-1.5">
                          <span>Original Proposal:</span>
                          <code class="font-sans bg-white px-1.5 py-0.5 border border-slate-200 rounded text-[10px] text-slate-700">
                            {{ col.proposedTargetField }} ({{ col.proposedTargetType }})
                          </code>
                        </div>

                        <button
                          type="button"
                          (click)="store.toggleFieldDetail(col.id)"
                          class="text-blue-600 hover:text-blue-800 font-medium cursor-pointer">
                          Done
                        </button>
                      </div>

                    </div>
                  }

                </div>
              }
            </div>

          </div>

        </div>
      }

    </div>
  `
})
export class MappingMapComponent {
  public store = inject(Step5MappingStoreService);

  public readonly navigatorSearch = signal<string>('');
  public readonly showObjectControls = signal<boolean>(false);

  public readonly defaultTypeOptions = ['VARCHAR', 'TEXT', 'BIGINT', 'NUMERIC', 'BOOLEAN', 'TIMESTAMP', 'JSONB'];

  public displayedNavigatorObjects = () => {
    const list = this.store.objects();
    const q = this.navigatorSearch().trim().toLowerCase();
    if (!q) return list;
    return list.filter(o => o.sourceName.toLowerCase().includes(q) || o.currentTargetName.toLowerCase().includes(q));
  };

  public formatNumber(val: number | null | undefined): string {
    if (!val) return '0';
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (val >= 1000) return `${(val / 1000).toFixed(1)}k`;
    return val.toString();
  }

  public isLengthApplicable(type: string): boolean {
    const t = (type || '').toUpperCase();
    return t.includes('VARCHAR') || t.includes('CHAR');
  }

  public isNumericApplicable(type: string): boolean {
    const t = (type || '').toUpperCase();
    return t.includes('NUMERIC') || t.includes('DECIMAL') || t.includes('NUMBER');
  }

  public getPrivacyOption(id: string | null | undefined) {
    if (!id) return null;
    return this.store.privacyOptions().find(p => p.id === id);
  }

  public toggleDedupEnabled(sel: ObjectMappingContract): void {
    this.store.updateDeduplication(sel.id, {
      ...sel.deduplication,
      enabled: !sel.deduplication.enabled
    });
  }

  public updateDedupKeys(sel: ObjectMappingContract, keysStr: string): void {
    const keys = keysStr.split(',').map(k => k.trim()).filter(k => k.length > 0);
    this.store.updateDeduplication(sel.id, {
      ...sel.deduplication,
      keyFields: keys
    });
  }

  public updateDedupPolicy(sel: ObjectMappingContract, policyId: string): void {
    this.store.updateDeduplication(sel.id, {
      ...sel.deduplication,
      survivorPolicyOptionId: policyId
    });
  }
}
