import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent } from '../../../../shared/components/custom-select.component';
import { DataControlCategory, PrivacyStrategy, CleansingRuleType, DeduplicationSurvivorPolicy, QualityRuleType, QualityDisposition } from './step5-mapping.models';

@Component({
  selector: 'app-mapping-controls',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  host: {
    class: 'flex flex-1 flex-col w-full h-full min-h-0'
  },
  template: `
    <div class="w-full h-full flex flex-col gap-3 min-h-0 font-sans text-xs select-none">
      
      <!-- ========================================================================= -->
      <!-- TOP DATA CONTROLS HEADER & CATEGORY NAVIGATION                            -->
      <!-- ========================================================================= -->
      <div class="p-3 bg-white border border-slate-200 rounded-lg flex items-center justify-between shrink-0">
        
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded bg-blue-50 border border-blue-200 flex items-center justify-center">
            <app-lucide-icon name="shield-check" [size]="15" class="text-blue-600"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <span class="font-bold text-xs text-slate-900">Data Controls &amp; Movement Governance</span>
            <span class="text-[11px] text-slate-500 font-normal">
              Configure privacy masking, cleansing, row filters, deduplication survivor policies, and quality assertions
            </span>
          </div>
        </div>

        <!-- Sub-Navigation Segmented Tabs -->
        <div class="flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5">
          @for (cat of categories; track cat.id) {
            <button
              type="button"
              (click)="store.setControlsCategory(cat.id)"
              class="h-7 px-3 rounded-md text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 hover:bg-blue-50 hover:text-blue-700"
              [class.bg-white]="store.activeControlsCategory() === cat.id"
              [class.text-blue-700]="store.activeControlsCategory() === cat.id"
              [class.border]="store.activeControlsCategory() === cat.id"
              [class.border-slate-200]="store.activeControlsCategory() === cat.id"
              [class.text-slate-600]="store.activeControlsCategory() !== cat.id">
              <app-lucide-icon [name]="cat.icon" [size]="12"></app-lucide-icon>
              <span>{{ cat.label }}</span>
              <span class="text-[10px] px-1.5 py-0.2 rounded font-bold"
                [class.bg-blue-100]="store.activeControlsCategory() === cat.id"
                [class.text-blue-800]="store.activeControlsCategory() === cat.id"
                [class.bg-slate-200]="store.activeControlsCategory() !== cat.id"
                [class.text-slate-600]="store.activeControlsCategory() !== cat.id">
                {{ getCategoryCount(cat.id) }}
              </span>
            </button>
          }
        </div>

      </div>

      <!-- ========================================================================= -->
      <!-- WORKSPACE CONTENT CANVAS                                                  -->
      <!-- ========================================================================= -->
      <div class="flex-1 min-h-0 bg-white border border-slate-200 rounded-lg flex flex-col overflow-hidden">
        
        <!-- ===================================================================== -->
        <!-- CATEGORY 1: PRIVACY & MASKING                                         -->
        <!-- ===================================================================== -->
        @if (store.activeControlsCategory() === 'PRIVACY') {
          <div class="flex-1 min-h-0 flex flex-col">
            <div class="h-9 px-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
              <span class="font-bold text-slate-800 text-xs">
                Privacy Rules ({{ store.privacyItems().length }} configured)
              </span>
              <span class="text-[11px] text-slate-500 font-normal">
                Keyed pseudonymization requires secret vault references; raw secrets are never stored in the UI
              </span>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto">
              <table class="w-full text-left border-collapse text-xs">
                <thead class="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider z-10">
                  <tr>
                    <th class="py-2.5 px-4">Resource / Field</th>
                    <th class="py-2.5 px-4">Privacy Strategy</th>
                    <th class="py-2.5 px-4">Configuration / Secret Reference</th>
                    <th class="py-2.5 px-4">Status</th>
                    <th class="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  @for (item of store.privacyItems(); track item.id) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-2.5 px-4">
                        <span class="font-bold text-slate-900">{{ item.objectName }}.{{ item.fieldName }}</span>
                      </td>
                      <td class="py-2.5 px-4">
                        <span class="font-semibold text-slate-800">{{ item.strategyLabel }}</span>
                      </td>
                      <td class="py-2.5 px-4 font-mono text-[11px] text-slate-600">
                        {{ item.configuration }}
                      </td>
                      <td class="py-2.5 px-4">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Ready
                        </span>
                      </td>
                      <td class="py-2.5 px-4 text-right">
                        <button
                          type="button"
                          (click)="editPrivacyItem(item)"
                          class="h-6 px-2 text-[11px] font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 rounded bg-blue-50 cursor-pointer">
                          Edit Rule
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            <!-- Privacy Item Editor (when active) -->
            @if (activePrivacyItem; as item) {
              <div class="p-4 border-t border-slate-200 bg-slate-50/80 flex flex-col gap-3 shrink-0">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-xs text-slate-900">Edit Privacy Rule: {{ item.objectName }}.{{ item.fieldName }}</span>
                  <div class="flex items-center gap-2">
                    <button
                      type="button"
                      (click)="activePrivacyItem = null"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white text-slate-600 text-xs font-semibold cursor-pointer">
                      Cancel
                    </button>
                    <button
                      type="button"
                      (click)="savePrivacyItem()"
                      class="h-7 px-3 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                      <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                      <span>Apply Privacy Rule</span>
                    </button>
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-4 bg-white p-3 rounded-md border border-slate-200">
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Strategy</label>
                    <app-custom-select
                      [options]="privacyStrategyOptions"
                      [value]="item.strategy"
                      (valueChange)="item.strategy = $event; onPrivacyStrategyChange(item)"
                      size="sm">
                    </app-custom-select>
                  </div>

                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      {{ item.strategy === 'KEYED_PSEUDONYM' ? 'Secret Reference URL' : 'Masking Configuration' }}
                    </label>
                    <input
                      type="text"
                      [(ngModel)]="item.configuration"
                      placeholder="e.g. vault://keys/customer-pseudo"
                      class="h-7 px-2 bg-slate-50 border border-slate-200 rounded text-xs font-mono text-slate-800" />
                  </div>
                </div>
              </div>
            }
          </div>
        }

        <!-- ===================================================================== -->
        <!-- CATEGORY 2: CLEANSING                                                 -->
        <!-- ===================================================================== -->
        @if (store.activeControlsCategory() === 'CLEANSING') {
          <div class="flex-1 min-h-0 flex flex-col">
            <div class="h-9 px-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
              <span class="font-bold text-slate-800 text-xs">
                Data Cleansing Transformations ({{ store.cleansingItems().length }} active)
              </span>
              <span class="text-[11px] text-slate-500 font-normal">
                Standardizes whitespace, casing, and default values during ingestion
              </span>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto">
              <table class="w-full text-left border-collapse text-xs">
                <thead class="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider z-10">
                  <tr>
                    <th class="py-2.5 px-4 w-12 text-center">Order</th>
                    <th class="py-2.5 px-4">Resource / Field</th>
                    <th class="py-2.5 px-4">Transformation Type</th>
                    <th class="py-2.5 px-4">Status</th>
                    <th class="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  @for (item of store.cleansingItems(); track item.id) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-2.5 px-4 text-center font-mono text-slate-400">#{{ item.orderIndex }}</td>
                      <td class="py-2.5 px-4 font-bold text-slate-900">{{ item.objectName }}.{{ item.fieldName }}</td>
                      <td class="py-2.5 px-4 font-semibold text-slate-800">{{ item.ruleTypeLabel }}</td>
                      <td class="py-2.5 px-4">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Ready
                        </span>
                      </td>
                      <td class="py-2.5 px-4 text-right">
                        <button
                          type="button"
                          (click)="editCleansingItem(item)"
                          class="h-6 px-2 text-[11px] font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 rounded bg-blue-50 cursor-pointer">
                          Edit
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            @if (activeCleansingItem; as item) {
              <div class="p-4 border-t border-slate-200 bg-slate-50/80 flex flex-col gap-3 shrink-0">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-xs text-slate-900">Edit Cleansing Rule: {{ item.objectName }}.{{ item.fieldName }}</span>
                  <div class="flex items-center gap-2">
                    <button
                      type="button"
                      (click)="activeCleansingItem = null"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white text-slate-600 text-xs font-semibold cursor-pointer">
                      Cancel
                    </button>
                    <button
                      type="button"
                      (click)="saveCleansingItem()"
                      class="h-7 px-3 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                      <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                      <span>Apply Cleansing Rule</span>
                    </button>
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-4 bg-white p-3 rounded-md border border-slate-200">
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Operation</label>
                    <app-custom-select
                      [options]="cleansingOperationOptions"
                      [value]="item.ruleType"
                      (valueChange)="item.ruleType = $event"
                      size="sm">
                    </app-custom-select>
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Parameter Value</label>
                    <input
                      type="text"
                      [(ngModel)]="item.paramValue"
                      placeholder="Optional parameter or fallback literal"
                      class="h-7 px-2 bg-slate-50 border border-slate-200 rounded text-xs text-slate-800" />
                  </div>
                </div>
              </div>
            }
          </div>
        }

        <!-- ===================================================================== -->
        <!-- CATEGORY 3: FILTERING                                                 -->
        <!-- ===================================================================== -->
        @if (store.activeControlsCategory() === 'FILTERING') {
          <div class="flex-1 min-h-0 flex flex-col">
            <div class="h-9 px-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
              <span class="font-bold text-slate-800 text-xs">
                Object Row Filters ({{ store.filterItems().length }} registered)
              </span>
              <span class="text-[11px] text-slate-500 font-normal">
                Filtering operates at table/collection extraction time
              </span>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto">
              <table class="w-full text-left border-collapse text-xs">
                <thead class="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider z-10">
                  <tr>
                    <th class="py-2.5 px-4">Object</th>
                    <th class="py-2.5 px-4">Row Scope</th>
                    <th class="py-2.5 px-4">SQL Filter Predicate</th>
                    <th class="py-2.5 px-4">Status</th>
                    <th class="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  @for (item of store.filterItems(); track item.id) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-2.5 px-4 font-bold text-slate-900">{{ item.objectName }}</td>
                      <td class="py-2.5 px-4">
                        <span class="font-semibold" [class.text-blue-700]="item.mode === 'CUSTOM'" [class.text-slate-600]="item.mode === 'ALL'">
                          {{ item.mode === 'CUSTOM' ? 'Custom Filter' : 'All Rows' }}
                        </span>
                      </td>
                      <td class="py-2.5 px-4 font-mono text-[11px] text-slate-700">
                        {{ item.predicate || '—' }}
                      </td>
                      <td class="py-2.5 px-4">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Ready
                        </span>
                      </td>
                      <td class="py-2.5 px-4 text-right">
                        <button
                          type="button"
                          (click)="editFilterItem(item)"
                          class="h-6 px-2 text-[11px] font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 rounded bg-blue-50 cursor-pointer">
                          Edit Predicate
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            @if (activeFilterItem; as item) {
              <div class="p-4 border-t border-slate-200 bg-slate-50/80 flex flex-col gap-3 shrink-0">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-xs text-slate-900">Configure Row Filter: {{ item.objectName }}</span>
                  <div class="flex items-center gap-2">
                    <button
                      type="button"
                      (click)="activeFilterItem = null"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white text-slate-600 text-xs font-semibold cursor-pointer">
                      Cancel
                    </button>
                    <button
                      type="button"
                      (click)="saveFilterItem()"
                      class="h-7 px-3 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                      <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                      <span>Apply Filter</span>
                    </button>
                  </div>
                </div>

                <div class="grid grid-cols-3 gap-4 bg-white p-3 rounded-md border border-slate-200">
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Row Scope Mode</label>
                    <app-custom-select
                      [options]="rowScopeModeOptions"
                      [value]="item.mode"
                      (valueChange)="item.mode = $event"
                      size="sm">
                    </app-custom-select>
                  </div>
                  <div class="col-span-2 flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">WHERE Clause Predicate</label>
                    <input
                      type="text"
                      [(ngModel)]="item.predicate"
                      placeholder="e.g. tx_date >= '2023-01-01' AND status != 'CANCELLED'"
                      class="h-7 px-2 bg-slate-50 border border-slate-200 rounded text-xs font-mono text-slate-800" />
                  </div>
                </div>
              </div>
            }
          </div>
        }

        <!-- ===================================================================== -->
        <!-- CATEGORY 4: DEDUPLICATION                                             -->
        <!-- ===================================================================== -->
        @if (store.activeControlsCategory() === 'DEDUPLICATION') {
          <div class="flex-1 min-h-0 flex flex-col">
            <div class="h-9 px-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
              <span class="font-bold text-slate-800 text-xs">
                Deduplication Policies ({{ store.deduplicationItems().length }} active)
              </span>
              <span class="text-[11px] text-slate-500 font-normal">
                Canonical backend survivor policies: First, Last, Min/Max, Newest/Oldest, Priority Matrix
              </span>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto">
              <table class="w-full text-left border-collapse text-xs">
                <thead class="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider z-10">
                  <tr>
                    <th class="py-2.5 px-4">Object</th>
                    <th class="py-2.5 px-4">Duplicate Keys</th>
                    <th class="py-2.5 px-4">Survivor Policy</th>
                    <th class="py-2.5 px-4">Disposition</th>
                    <th class="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  @for (item of store.deduplicationItems(); track item.id) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-2.5 px-4 font-bold text-slate-900">{{ item.objectName }}</td>
                      <td class="py-2.5 px-4 font-mono text-[11px] text-slate-700">
                        {{ item.keyFields.join(', ') }}
                      </td>
                      <td class="py-2.5 px-4 font-semibold text-slate-800">{{ item.survivorPolicyLabel }}</td>
                      <td class="py-2.5 px-4 font-mono text-[10px] text-slate-600">{{ item.disposition }}</td>
                      <td class="py-2.5 px-4 text-right">
                        <button
                          type="button"
                          (click)="editDedupItem(item)"
                          class="h-6 px-2 text-[11px] font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 rounded bg-blue-50 cursor-pointer">
                          Configure
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            @if (activeDedupItem; as item) {
              <div class="p-4 border-t border-slate-200 bg-slate-50/80 flex flex-col gap-3 shrink-0">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-xs text-slate-900">Configure Deduplication: {{ item.objectName }}</span>
                  <div class="flex items-center gap-2">
                    <button
                      type="button"
                      (click)="activeDedupItem = null"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white text-slate-600 text-xs font-semibold cursor-pointer">
                      Cancel
                    </button>
                    <button
                      type="button"
                      (click)="saveDedupItem()"
                      class="h-7 px-3 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                      <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                      <span>Apply Deduplication</span>
                    </button>
                  </div>
                </div>

                <div class="grid grid-cols-3 gap-4 bg-white p-3 rounded-md border border-slate-200">
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Duplicate Key Columns</label>
                    <input
                      type="text"
                      [(ngModel)]="dedupKeyInput"
                      placeholder="e.g. tax_id, email"
                      class="h-7 px-2 bg-slate-50 border border-slate-200 rounded text-xs font-mono text-slate-800" />
                  </div>

                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Survivor Policy</label>
                    <app-custom-select
                      [options]="survivorPolicySelectOptions()"
                      [value]="item.survivorPolicy"
                      (valueChange)="item.survivorPolicy = $event; onDedupPolicyChange(item)"
                      size="sm">
                    </app-custom-select>
                  </div>

                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Duplicate Disposition</label>
                    <app-custom-select
                      [options]="dedupDispositionOptions"
                      [value]="item.disposition"
                      (valueChange)="item.disposition = $event"
                      size="sm">
                    </app-custom-select>
                  </div>
                </div>
              </div>
            }
          </div>
        }

        <!-- ===================================================================== -->
        <!-- CATEGORY 5: QUALITY                                                   -->
        <!-- ===================================================================== -->
        @if (store.activeControlsCategory() === 'QUALITY') {
          <div class="flex-1 min-h-0 flex flex-col">
            <div class="h-9 px-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
              <span class="font-bold text-slate-800 text-xs">
                Data Quality Assertions ({{ store.qualityItems().length }} active)
              </span>
              <span class="text-[11px] text-slate-500 font-normal">
                Verifies non-nullability, length, numeric limits, and regex constraints during pipeline execution
              </span>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto">
              <table class="w-full text-left border-collapse text-xs">
                <thead class="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider z-10">
                  <tr>
                    <th class="py-2.5 px-4">Resource / Field</th>
                    <th class="py-2.5 px-4">Assertion Rule</th>
                    <th class="py-2.5 px-4">Constraint Value</th>
                    <th class="py-2.5 px-4">Failure Disposition</th>
                    <th class="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  @for (item of store.qualityItems(); track item.id) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-2.5 px-4 font-bold text-slate-900">
                        {{ item.objectName }}{{ item.fieldName ? '.' + item.fieldName : '' }}
                      </td>
                      <td class="py-2.5 px-4 font-semibold text-slate-800">{{ item.ruleLabel }}</td>
                      <td class="py-2.5 px-4 font-mono text-[11px] text-slate-600">
                        {{ item.constraintValue || '—' }}
                      </td>
                      <td class="py-2.5 px-4 font-mono text-[10px] text-slate-700">
                        {{ item.dispositionLabel }}
                      </td>
                      <td class="py-2.5 px-4 text-right">
                        <button
                          type="button"
                          (click)="editQualityItem(item)"
                          class="h-6 px-2 text-[11px] font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 rounded bg-blue-50 cursor-pointer">
                          Edit
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            @if (activeQualityItem; as item) {
              <div class="p-4 border-t border-slate-200 bg-slate-50/80 flex flex-col gap-3 shrink-0">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-xs text-slate-900">Edit Quality Assertion: {{ item.objectName }}.{{ item.fieldName }}</span>
                  <div class="flex items-center gap-2">
                    <button
                      type="button"
                      (click)="activeQualityItem = null"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white text-slate-600 text-xs font-semibold cursor-pointer">
                      Cancel
                    </button>
                    <button
                      type="button"
                      (click)="saveQualityItem()"
                      class="h-7 px-3 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                      <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                      <span>Apply Quality Rule</span>
                    </button>
                  </div>
                </div>

                <div class="grid grid-cols-3 gap-4 bg-white p-3 rounded-md border border-slate-200">
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Assertion Type</label>
                    <app-custom-select
                      [options]="qualityRuleTypeOptions"
                      [value]="item.ruleType"
                      (valueChange)="item.ruleType = $event"
                      size="sm">
                    </app-custom-select>
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Constraint Expression</label>
                    <input
                      type="text"
                      [(ngModel)]="item.constraintValue"
                      placeholder="e.g. < 1000000 or ^[A-Z0-9]+$"
                      class="h-7 px-2 bg-slate-50 border border-slate-200 rounded text-xs font-mono text-slate-800" />
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Malformed Disposition</label>
                    <app-custom-select
                      [options]="qualityDispositionOptions"
                      [value]="item.disposition"
                      (valueChange)="item.disposition = $event"
                      size="sm">
                    </app-custom-select>
                  </div>
                </div>
              </div>
            }
          </div>
        }

      </div>

    </div>
  `
})
export class MappingControlsComponent {
  public readonly store = inject(Step5MappingStoreService);

  public readonly categories = [
    { id: 'PRIVACY' as DataControlCategory, label: 'Privacy', icon: 'eye-off' },
    { id: 'CLEANSING' as DataControlCategory, label: 'Cleansing', icon: 'sparkles' },
    { id: 'FILTERING' as DataControlCategory, label: 'Filtering', icon: 'filter' },
    { id: 'DEDUPLICATION' as DataControlCategory, label: 'Deduplication', icon: 'copy-slash' },
    { id: 'QUALITY' as DataControlCategory, label: 'Quality', icon: 'check-circle' }
  ];

  public activePrivacyItem: any = null;
  public activeCleansingItem: any = null;
  public activeFilterItem: any = null;
  public activeDedupItem: any = null;
  public dedupKeyInput: string = '';
  public activeQualityItem: any = null;

  public readonly privacyStrategyOptions = [
    { label: 'Static Redact', value: 'STATIC_REDACT' },
    { label: 'Partial Mask', value: 'PARTIAL_MASK' },
    { label: 'Nullify', value: 'NULLIFY' },
    { label: 'Cryptographic Hash (SHA-256)', value: 'HASH' },
    { label: 'Keyed Pseudonym (Vault Key)', value: 'KEYED_PSEUDONYM' },
    { label: 'Format-Preserving Mask', value: 'FORMAT_PRESERVING_MASK' }
  ];

  public readonly cleansingOperationOptions = [
    { label: 'Trim Leading & Trailing Whitespace', value: 'TRIM' },
    { label: 'Uppercase Characters', value: 'UPPERCASE' },
    { label: 'Lowercase Characters', value: 'LOWERCASE' },
    { label: 'Default Fallback on NULL', value: 'DEFAULT' },
    { label: 'Regex Replace', value: 'REGEX_REPLACE' }
  ];

  public readonly rowScopeModeOptions = [
    { label: 'All Rows (Extract Complete Table)', value: 'ALL' },
    { label: 'Custom SQL Predicate', value: 'CUSTOM' }
  ];

  public survivorPolicySelectOptions(): { label: string; value: string }[] {
    return this.store.survivorPolicyOptions().map(p => ({ label: p.label, value: p.id }));
  }

  public readonly dedupDispositionOptions = [
    { label: 'Log & Discard Duplicate', value: 'LOG_AND_DISCARD' },
    { label: 'Reject Duplicate Group', value: 'REJECT_GROUP' },
    { label: 'Quarantine to Dead-Letter Storage', value: 'QUARANTINE_GROUP' },
    { label: 'Fail Job Immediately', value: 'FAIL_JOB' }
  ];

  public readonly qualityRuleTypeOptions = [
    { label: 'Must Not Be NULL', value: 'NOT_NULL' },
    { label: 'Maximum Length Constraint', value: 'MAX_LENGTH' },
    { label: 'Numeric Overflow Limit', value: 'NUMERIC_OVERFLOW' },
    { label: 'Value Range Constraint', value: 'VALUE_RANGE' },
    { label: 'Regex Pattern Match', value: 'REGEX_MATCH' },
    { label: 'Enumerated Value Set', value: 'ENUM_VALUES' }
  ];

  public readonly qualityDispositionOptions = [
    { label: 'Fail Job Immediately', value: 'FAIL_JOB' },
    { label: 'Reject Record to Dead-Letter', value: 'REJECT_RECORD' },
    { label: 'Quarantine Record', value: 'QUARANTINE_RECORD' },
    { label: 'Substitute Default Value', value: 'USE_DEFAULT' },
    { label: 'Substitute NULL Value', value: 'USE_NULL' },
    { label: 'Explicitly Truncate to Max Length', value: 'EXPLICIT_TRUNCATE' }
  ];

  public getCategoryCount(cat: DataControlCategory): number {
    const m = this.store.metrics();
    switch (cat) {
      case 'PRIVACY': return m.totalPrivacyCount;
      case 'CLEANSING': return m.totalCleansingCount;
      case 'FILTERING': return m.totalFilterCount;
      case 'DEDUPLICATION': return m.totalDedupCount;
      case 'QUALITY': return m.totalQualityCount;
    }
  }

  // Privacy Actions
  public editPrivacyItem(item: any): void {
    this.activePrivacyItem = { ...item };
  }

  public onPrivacyStrategyChange(item: any): void {
    if (item.strategy === 'KEYED_PSEUDONYM') {
      item.strategyLabel = 'Keyed Pseudonym';
      if (!item.configuration || !item.configuration.startsWith('vault://')) {
        item.configuration = 'vault://keys/customer-pseudo';
      }
    } else if (item.strategy === 'PARTIAL_MASK') {
      item.strategyLabel = 'Partial Mask';
      item.configuration = 'Preserve last 4 chars';
    } else if (item.strategy === 'HASH') {
      item.strategyLabel = 'Cryptographic Hash';
      item.configuration = 'SHA-256';
    } else if (item.strategy === 'NULLIFY') {
      item.strategyLabel = 'Nullify';
      item.configuration = 'NULL';
    } else {
      item.strategyLabel = item.strategy;
    }
  }

  public savePrivacyItem(): void {
    if (!this.activePrivacyItem) return;
    this.store.privacyDraft.set(this.activePrivacyItem);
    this.store.applyPrivacyDraft();
    this.activePrivacyItem = null;
  }

  // Cleansing Actions
  public editCleansingItem(item: any): void {
    this.activeCleansingItem = { ...item };
  }

  public saveCleansingItem(): void {
    if (!this.activeCleansingItem) return;
    this.store.cleansingDraft.set(this.activeCleansingItem);
    this.store.applyCleansingDraft();
    this.activeCleansingItem = null;
  }

  // Filter Actions
  public editFilterItem(item: any): void {
    this.activeFilterItem = { ...item };
  }

  public saveFilterItem(): void {
    if (!this.activeFilterItem) return;
    this.store.filterDraft.set(this.activeFilterItem);
    this.store.applyFilterDraft();
    this.activeFilterItem = null;
  }

  // Dedup Actions
  public editDedupItem(item: any): void {
    this.activeDedupItem = { ...item };
    this.dedupKeyInput = item.keyFields.join(', ');
  }

  public onDedupPolicyChange(item: any): void {
    const opt = this.store.survivorPolicyOptions().find(o => o.id === item.survivorPolicy);
    if (opt) {
      item.survivorPolicyLabel = opt.label;
    }
  }

  public saveDedupItem(): void {
    if (!this.activeDedupItem) return;
    this.activeDedupItem.keyFields = this.dedupKeyInput.split(',').map(s => s.trim()).filter(Boolean);
    this.store.dedupDraft.set(this.activeDedupItem);
    this.store.applyDedupDraft();
    this.activeDedupItem = null;
  }

  // Quality Actions
  public editQualityItem(item: any): void {
    this.activeQualityItem = { ...item };
  }

  public saveQualityItem(): void {
    if (!this.activeQualityItem) return;
    this.store.qualityDraft.set(this.activeQualityItem);
    this.store.applyQualityDraft();
    this.activeQualityItem = null;
  }
}
