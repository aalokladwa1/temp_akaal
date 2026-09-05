import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step6ConfigurationStoreService } from '../../../../core/services/step6-configuration-store.service';
import { AdvancedGroupId, AdvancedFieldDescriptor } from './step6-configuration.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-configuration-advanced',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="w-full h-full flex flex-col md:flex-row gap-4 min-h-[560px] font-sans text-xs select-none">
      
      <!-- ========================================================================= -->
      <!-- LEFT PANE: ADVANCED NAVIGATOR (~24% width)                                -->
      <!-- ========================================================================= -->
      <aside class="w-full md:w-64 lg:w-72 bg-white border border-slate-200 rounded-lg flex flex-col shrink-0 overflow-hidden">
        
        <!-- Top Search Box -->
        <div class="p-3 border-b border-slate-200 bg-slate-50/50 flex flex-col gap-2">
          <div class="relative w-full">
            <input
              type="text"
              [ngModel]="store.advancedSearchQuery()"
              (ngModelChange)="store.advancedSearchQuery.set($event)"
              placeholder="Search parameters, groups, engines..."
              class="w-full h-8 pl-8 pr-7 text-xs bg-white border border-slate-200 rounded-md focus:outline-none focus:border-blue-600 text-slate-800 placeholder:text-slate-400 font-normal" />
            <app-lucide-icon name="search" [size]="13" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
            @if (store.advancedSearchQuery()) {
              <button
                type="button"
                (click)="store.advancedSearchQuery.set('')"
                class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer">
                <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
              </button>
            }
          </div>

          <div class="flex items-center justify-between text-[11px] text-slate-500 px-0.5">
            <span class="font-semibold uppercase tracking-wider text-[10px] text-slate-400">8 Parameter Groups</span>
            @if (store.totalOverridesCount() > 0) {
              <span class="px-1.5 py-0.2 rounded font-bold font-mono text-[10px] bg-blue-50 text-blue-700 border border-blue-200">
                {{ store.totalOverridesCount() }} override{{ store.totalOverridesCount() > 1 ? 's' : '' }}
              </span>
            }
          </div>
        </div>

        <!-- 8 Group Navigation Items -->
        <nav class="flex-1 overflow-y-auto p-1.5 flex flex-col gap-0.5">
          @for (group of store.advancedGroups(); track group.id) {
            <button
              type="button"
              (click)="selectGroup(group.id)"
              class="w-full text-left px-3 py-2 rounded-md transition-colors flex items-center justify-between cursor-pointer group"
              [class.bg-blue-50]="store.activeAdvancedGroupId() === group.id && !store.advancedSearchQuery()"
              [class.text-blue-700]="store.activeAdvancedGroupId() === group.id && !store.advancedSearchQuery()"
              [class.font-semibold]="store.activeAdvancedGroupId() === group.id && !store.advancedSearchQuery()"
              [class.text-slate-700]="store.activeAdvancedGroupId() !== group.id || !!store.advancedSearchQuery()"
              [class.hover:bg-slate-50]="store.activeAdvancedGroupId() !== group.id || !!store.advancedSearchQuery()">
              
              <div class="flex items-center gap-2.5 min-w-0">
                <app-lucide-icon
                  [name]="group.icon"
                  [size]="14"
                  [class.text-blue-600]="store.activeAdvancedGroupId() === group.id && !store.advancedSearchQuery()"
                  [class.text-slate-400]="store.activeAdvancedGroupId() !== group.id || !!store.advancedSearchQuery()"
                  class="shrink-0"></app-lucide-icon>
                <div class="flex flex-col min-w-0">
                  <span class="truncate text-xs">{{ group.label }}</span>
                  @if (group.id === 'MODE_CONFIG') {
                    <span class="text-[10px] text-slate-400 font-normal truncate">{{ store.modeDisplayTitle() }}</span>
                  } @else if (group.id === 'PROVIDER_OPTIONS') {
                    <span class="text-[10px] text-slate-400 font-normal truncate">{{ store.sourceProvider() }} &rarr; {{ store.targetProvider() }}</span>
                  }
                </div>
              </div>

              @if (group.overrideCount > 0) {
                <span class="px-1.5 py-0.2 rounded text-[10px] font-bold font-mono bg-blue-100 text-blue-700 border border-blue-200 shrink-0">
                  {{ group.overrideCount }}
                </span>
              }
            </button>
          }
        </nav>

        <!-- Bottom Reset All Button -->
        @if (store.totalOverridesCount() > 0) {
          <div class="p-2.5 border-t border-slate-200 bg-slate-50/70 flex items-center justify-between">
            <span class="text-[11px] text-slate-500 font-medium">Reset all custom parameters</span>
            <button
              type="button"
              (click)="store.resetAllOverrides()"
              class="h-6 px-2 text-[10px] font-semibold text-rose-700 bg-white hover:bg-rose-50 border border-rose-200 rounded cursor-pointer transition-colors">
              Reset All
            </button>
          </div>
        }

      </aside>

      <!-- ========================================================================= -->
      <!-- RIGHT PANE: CONFIGURATION CANVAS (~76% width)                             -->
      <!-- ========================================================================= -->
      <main class="flex-1 bg-white border border-slate-200 rounded-lg flex flex-col min-h-0 overflow-hidden">
        
        <!-- Canvas Header -->
        <div class="px-5 py-3 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between shrink-0">
          <div class="flex flex-col gap-0.5">
            <div class="flex items-center gap-2">
              <h3 class="text-xs font-bold text-slate-900 tracking-tight">
                {{ currentGroupTitle() }}
              </h3>
              @if (store.advancedSearchQuery()) {
                <span class="text-[11px] text-blue-700 font-medium bg-blue-50 border border-blue-200 px-2 py-0.2 rounded">
                  Search Results ({{ store.filteredAdvancedFields().length }})
                </span>
              }
            </div>
            <p class="text-[11px] text-slate-500 font-normal">
              {{ currentGroupDescription() }}
            </p>
          </div>

          <!-- Group Action: Reset Group Overrides -->
          @if (currentGroupOverrideCount() > 0 && !store.advancedSearchQuery()) {
            <button
              type="button"
              (click)="resetCurrentGroupOverrides()"
              class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors shrink-0">
              <app-lucide-icon name="rotate-ccw" [size]="11" class="text-slate-400"></app-lucide-icon>
              <span>Reset Group ({{ currentGroupOverrideCount() }})</span>
            </button>
          }
        </div>

        <!-- Scrollable Fields List -->
        <div class="flex-1 overflow-y-auto p-5 flex flex-col gap-6">
          
          <!-- Empty State (No fields match search) -->
          @if (store.filteredAdvancedFields().length === 0) {
            <div class="py-16 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
              <app-lucide-icon name="search" [size]="20" class="text-slate-300"></app-lucide-icon>
              <span class="text-xs font-semibold text-slate-600">No configuration parameters match your search</span>
              <button
                type="button"
                (click)="store.advancedSearchQuery.set('')"
                class="text-xs font-semibold text-blue-600 hover:text-blue-700 cursor-pointer pt-1">
                Clear Search Filter
              </button>
            </div>
          }

          <!-- Grouped Fields Sections -->
          @for (subgroup of groupedFields(); track subgroup.name) {
            <div class="flex flex-col gap-3">
              
              <!-- Subgroup Header -->
              <div class="flex items-center gap-2 pb-1 border-b border-slate-100">
                <span class="text-[11px] font-bold text-slate-800 uppercase tracking-wider">
                  {{ subgroup.name }}
                </span>
              </div>

              <!-- Field Cards Grid -->
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
                @for (field of subgroup.fields; track field.id) {
                  <div
                    class="p-3.5 rounded-lg border transition-colors flex flex-col justify-between gap-3 bg-white"
                    [class.border-blue-300]="field.isOverridden"
                    [class.bg-blue-50]="field.isOverridden"
                    [class.border-slate-200]="!field.isOverridden && !field.isPolicyLocked"
                    [class.border-amber-200]="field.isPolicyLocked"
                    [class.bg-amber-50]="field.isPolicyLocked">
                    
                    <!-- Top: Label & Policy Lock Badge -->
                    <div class="flex flex-col gap-1">
                      <div class="flex items-center justify-between gap-2">
                        <label class="text-xs font-bold text-slate-900 leading-tight">
                          {{ field.label }}
                        </label>

                        @if (field.isPolicyLocked) {
                          <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1 shrink-0">
                            <app-lucide-icon name="lock" [size]="10" class="text-amber-700"></app-lucide-icon>
                            <span>Locked Policy</span>
                          </span>
                        } @else if (field.isOverridden) {
                          <span class="px-1.5 py-0.2 rounded text-[10px] font-bold font-mono bg-blue-100 text-blue-700 border border-blue-200 shrink-0">
                            Overridden
                          </span>
                        }
                      </div>

                      <p class="text-[11px] text-slate-500 leading-normal font-normal">
                        {{ field.description }}
                      </p>
                    </div>

                    <!-- Middle: Input Control (GDS Controls Only) -->
                    <div class="pt-1">
                      
                      <!-- Type: Number Input -->
                      @if (field.type === 'number') {
                        <div class="flex items-center gap-2">
                          <input
                            type="number"
                            [ngModel]="field.effectiveValue"
                            (change)="onNumberInputChange(field, $event)"
                            (keydown.enter)="onNumberInputChange(field, $event); $any($event.target).blur()"
                            [disabled]="!!field.isPolicyLocked"
                            [min]="field.min || 0"
                            [max]="field.max || 1000000"
                            class="w-32 h-8 px-2.5 text-xs bg-white border border-slate-200 rounded-md font-mono text-slate-900 focus:outline-none focus:border-blue-600 disabled:bg-slate-100 disabled:text-slate-400" />
                          @if (field.unit) {
                            <span class="text-xs font-mono text-slate-500">{{ field.unit }}</span>
                          }
                        </div>
                      }

                      <!-- Type: Select Dropdown -->
                      @if (field.type === 'select' && field.options) {
                        <div class="w-full">
                          <app-custom-select
                            [options]="field.options"
                            [value]="field.effectiveValue"
                            [disabled]="!!field.isPolicyLocked"
                            (valueChange)="onSelectChange(field, $event)"
                            size="sm">
                          </app-custom-select>
                        </div>
                      }

                      <!-- Type: Text Input -->
                      @if (field.type === 'string') {
                        <input
                          type="text"
                          [ngModel]="field.effectiveValue"
                          (change)="onTextInputChange(field, $event)"
                          (keydown.enter)="onTextInputChange(field, $event); $any($event.target).blur()"
                          [disabled]="!!field.isPolicyLocked"
                          class="w-full h-8 px-2.5 text-xs bg-white border border-slate-200 rounded-md text-slate-900 font-mono focus:outline-none focus:border-blue-600 disabled:bg-slate-100 disabled:text-slate-400" />
                      }

                    </div>

                    <!-- Bottom: Provenance & Reset Action -->
                    <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                      
                      <!-- Provenance Indicator -->
                      <div class="flex items-center gap-1.5 text-slate-500">
                        @if (field.isPolicyLocked) {
                          <span class="text-amber-800 font-medium">Production policy lock</span>
                        } @else if (field.isOverridden) {
                          <span class="text-blue-700 font-medium">Overridden for migration</span>
                          <span class="text-slate-400">&middot; default: {{ field.defaultValue }}</span>
                        } @else {
                          <span class="text-slate-400">Preset default: {{ field.defaultValue }}{{ field.unit ? ' ' + field.unit : '' }}</span>
                        }
                      </div>

                      <!-- Reset button -->
                      @if (field.isOverridden) {
                        <button
                          type="button"
                          (click)="store.resetAdvancedField(field.id)"
                          class="text-slate-500 hover:text-rose-600 font-semibold cursor-pointer transition-colors">
                          Reset
                        </button>
                      }
                    </div>

                  </div>
                }
              </div>

            </div>
          }

        </div>

      </main>

    </div>
  `
})
export class ConfigurationAdvancedComponent {
  public store = inject(Step6ConfigurationStoreService);

  public selectGroup(groupId: AdvancedGroupId): void {
    this.store.activeAdvancedGroupId.set(groupId);
    this.store.advancedSearchQuery.set('');
  }

  public currentGroupTitle = computed<string>(() => {
    if (this.store.advancedSearchQuery()) {
      return `Configuration Search: "${this.store.advancedSearchQuery()}"`;
    }
    const g = this.store.advancedGroups().find(gr => gr.id === this.store.activeAdvancedGroupId());
    return g ? g.label : 'Advanced Configuration';
  });

  public currentGroupDescription = computed<string>(() => {
    if (this.store.advancedSearchQuery()) {
      return 'Showing all matching parameters across all 8 configuration domains.';
    }
    const g = this.store.advancedGroups().find(gr => gr.id === this.store.activeAdvancedGroupId());
    return g ? g.description : '';
  });

  public currentGroupOverrideCount = computed<number>(() => {
    const g = this.store.advancedGroups().find(gr => gr.id === this.store.activeAdvancedGroupId());
    return g ? g.overrideCount : 0;
  });

  public groupedFields = computed(() => {
    const fields = this.store.filteredAdvancedFields();
    const map = new Map<string, AdvancedFieldDescriptor[]>();

    for (const f of fields) {
      const groupName = f.subGroup || 'General Settings';
      if (!map.has(groupName)) {
        map.set(groupName, []);
      }
      map.get(groupName)!.push(f);
    }

    return Array.from(map.entries()).map(([name, groupFields]) => ({
      name,
      fields: groupFields
    }));
  });

  public onNumberInputChange(field: AdvancedFieldDescriptor, event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input) return;
    const raw = input.value.trim();
    if (raw === '') {
      input.value = String(field.effectiveValue);
      return;
    }
    const val = Number(raw);
    if (isNaN(val)) {
      input.value = String(field.effectiveValue);
      return;
    }
    if (val === field.effectiveValue) {
      return;
    }
    this.store.setAdvancedField(field.id, val);
  }

  public onTextInputChange(field: AdvancedFieldDescriptor, event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input) return;
    const val = input.value.trim();
    if (val === field.effectiveValue) {
      return;
    }
    this.store.setAdvancedField(field.id, val);
  }

  public onSelectChange(field: AdvancedFieldDescriptor, value: any): void {
    if (value === field.effectiveValue) {
      return;
    }
    this.store.setAdvancedField(field.id, value);
  }

  public resetCurrentGroupOverrides(): void {
    const fields = this.store.advancedFields().filter(f => f.groupId === this.store.activeAdvancedGroupId());
    for (const f of fields) {
      if (f.isOverridden) {
        this.store.resetAdvancedField(f.id);
      }
    }
  }
}
