import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateTemplateService } from '../create-template.service';
import {
  ScopeRuleType,
  ScopeObjectType,
  TableCaseTransformation,
  NullabilityPolicy,
  MaskingType,
  CleansingRules
} from '../create-template.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-step3-scope-mapping',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-6 animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Scope, Mapping & Data Controls</h2>
        <p class="text-xs text-slate-500 font-normal">
          Establish object discovery filters, schema/table transformations, column data type mappings, and data privacy masking rules.
        </p>
      </div>

      <!-- SECTION 1: OBJECT SELECTION & DISCOVERY RULES -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3.5 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2.5">
          <div class="flex flex-col">
            <span class="font-bold text-slate-900">Object Discovery & Selection Rules</span>
            <span class="text-[11px] text-slate-500 font-normal">Define include/exclude patterns evaluated against source database catalogs.</span>
          </div>
          <span class="px-2 py-0.5 text-[10px] font-mono bg-slate-100 text-slate-700 rounded-md">
            {{ ts.scopeMapping().objectScopeRules.length }} rules active
          </span>
        </div>

        <!-- Rules List Table -->
        <div class="overflow-x-auto border border-slate-200 rounded-lg">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="px-3 py-2">Action</th>
                <th class="px-3 py-2">Object Type</th>
                <th class="px-3 py-2">Pattern / Wildcard</th>
                <th class="px-3 py-2">Description</th>
                <th class="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (rule of ts.scopeMapping().objectScopeRules; track rule.id) {
                <tr class="hover:bg-slate-50/70 transition-colors">
                  <td class="px-3 py-2">
                    <span
                      class="px-2 py-0.5 text-[10px] font-bold rounded-md"
                      [class]="rule.ruleType === 'INCLUDE' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                      {{ rule.ruleType }}
                    </span>
                  </td>
                  <td class="px-3 py-2 font-mono text-slate-700">{{ rule.objectType }}</td>
                  <td class="px-3 py-2 font-mono font-semibold text-slate-900">{{ rule.pattern }}</td>
                  <td class="px-3 py-2 text-slate-500 font-normal">{{ rule.description || '—' }}</td>
                  <td class="px-3 py-2 text-right">
                    <button
                      type="button"
                      (click)="ts.removeScopeRule(rule.id)"
                      class="text-rose-600 hover:text-rose-800 text-[11px] font-medium transition-colors cursor-pointer">
                      Remove
                    </button>
                  </td>
                </tr>
              }
              @if (ts.scopeMapping().objectScopeRules.length === 0) {
                <tr>
                  <td colspan="5" class="py-4 text-center text-slate-400 text-xs">
                    No scope rules configured. Click "Add rule" below to create inclusion or exclusion patterns.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Inline Add Rule Form (Using GDS Custom Select) -->
        <div class="p-3 bg-slate-50 border border-slate-200 rounded-md flex flex-col md:flex-row items-end gap-2.5">
          <div class="flex flex-col gap-1 w-full md:w-32 shrink-0">
            <span class="text-[10px] font-bold text-slate-500 uppercase">Action</span>
            <app-custom-select
              size="sm"
              [options]="ruleTypeOptions"
              [(ngModel)]="newRuleType">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1 w-full md:w-36 shrink-0">
            <span class="text-[10px] font-bold text-slate-500 uppercase">Target</span>
            <app-custom-select
              size="sm"
              [options]="objectTypeOptions"
              [(ngModel)]="newRuleObjectType">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1 flex-1 w-full">
            <span class="text-[10px] font-bold text-slate-500 uppercase">Pattern</span>
            <input
              type="text"
              [(ngModel)]="newRulePattern"
              placeholder="e.g., prod_data.* or *_archive"
              class="h-8 px-2.5 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
          </div>

          <div class="flex flex-col gap-1 flex-1 w-full">
            <span class="text-[10px] font-bold text-slate-500 uppercase">Description</span>
            <input
              type="text"
              [(ngModel)]="newRuleDescription"
              placeholder="e.g., Include core production tables"
              class="h-8 px-2.5 bg-white border border-slate-200 rounded-md text-xs text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
          </div>

          <button
            type="button"
            (click)="handleAddScopeRule()"
            [disabled]="!newRulePattern.trim()"
            class="h-8 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold transition-colors cursor-pointer disabled:opacity-40 disabled:pointer-events-none shrink-0 shadow-2xs">
            Add rule
          </button>
        </div>
      </div>

      <!-- SECTION 2: SCHEMA & TABLE MAPPINGS -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Schema Namespace Mapping -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Schema Namespace Mapping</span>
            <span class="text-[10px] text-slate-400 font-mono">{{ ts.scopeMapping().schemaMappings.length }} mapped</span>
          </div>

          <!-- Existing Schema Mappings -->
          <div class="flex flex-col gap-1.5 max-h-36 overflow-y-auto">
            @for (sm of ts.scopeMapping().schemaMappings; track sm.id) {
              <div class="flex items-center justify-between p-2 bg-slate-50 border border-slate-200 rounded-md text-xs">
                <div class="flex items-center gap-2 font-mono">
                  <span class="font-semibold text-slate-800">{{ sm.sourceSchema }}</span>
                  <span class="text-slate-400">&rarr;</span>
                  <span class="font-semibold text-blue-600">{{ sm.targetSchema }}</span>
                </div>
                <button
                  type="button"
                  (click)="ts.removeSchemaMapping(sm.id)"
                  class="text-rose-600 hover:text-rose-800 text-[10px] font-medium cursor-pointer">
                  Remove
                </button>
              </div>
            }
          </div>

          <!-- Add Schema Mapping Form -->
          <div class="flex items-center gap-2 pt-1">
            <input
              type="text"
              [(ngModel)]="newSourceSchema"
              placeholder="Source schema..."
              class="h-8 px-2.5 flex-1 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
            <span class="text-slate-400 font-mono">&rarr;</span>
            <input
              type="text"
              [(ngModel)]="newTargetSchema"
              placeholder="Target schema..."
              class="h-8 px-2.5 flex-1 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
            <button
              type="button"
              (click)="handleAddSchemaMapping()"
              [disabled]="!newSourceSchema.trim() || !newTargetSchema.trim()"
              class="h-8 px-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:pointer-events-none shrink-0 shadow-2xs transition-colors">
              Add
            </button>
          </div>
        </div>

        <!-- Table Case & Identifier Transformations -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Table & Identifier Transformations</span>
            <span class="text-[10px] text-slate-400">Case policy</span>
          </div>

          <div class="flex flex-col gap-2">
            <span class="text-[11px] font-semibold text-slate-600">Identifier Case Normalization:</span>
            <div class="grid grid-cols-2 gap-2">
              @for (tc of tableCases; track tc.value) {
                <button
                  type="button"
                  (click)="ts.updateScopeMapping({ tableCaseTransformation: tc.value })"
                  class="h-8 px-2.5 rounded-md border text-xs font-semibold transition-all cursor-pointer flex items-center justify-center"
                  [class]="ts.scopeMapping().tableCaseTransformation === tc.value
                    ? 'bg-blue-600 text-white border-blue-600 shadow-2xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'">
                  {{ tc.label }}
                </button>
              }
            </div>
          </div>

          <div class="flex flex-col gap-1 pt-1 border-t border-slate-100">
            <span class="text-[11px] font-semibold text-slate-600">Nullability Handling Policy:</span>
            <app-custom-select
              [options]="nullabilityOptions"
              [ngModel]="ts.scopeMapping().nullabilityPolicy"
              (ngModelChange)="ts.updateScopeMapping({ nullabilityPolicy: $event })">
            </app-custom-select>
          </div>
        </div>

      </div>

      <!-- SECTION 3: COLUMN DATA TYPE MAPPINGS -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex flex-col">
            <span class="font-bold text-slate-900">Column Data Type Conversion Overrides</span>
            <span class="text-[11px] text-slate-500 font-normal">Custom dialect data type mapping rules applied during extraction & DDL generation.</span>
          </div>
          <span class="text-[10px] text-slate-400 font-mono">{{ ts.scopeMapping().columnTypeOverrides.length }} overrides</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-2 max-h-36 overflow-y-auto">
          @for (co of ts.scopeMapping().columnTypeOverrides; track co.id) {
            <div class="flex items-center justify-between p-2 bg-slate-50 border border-slate-200 rounded-md text-xs">
              <div class="flex items-center gap-1.5 font-mono">
                <span class="font-semibold text-slate-800">{{ co.sourceType }}</span>
                <span class="text-slate-400">&rarr;</span>
                <span class="font-semibold text-blue-600">{{ co.targetType }}</span>
              </div>
              <button
                type="button"
                (click)="ts.removeColumnTypeOverride(co.id)"
                class="text-rose-600 hover:text-rose-800 text-[10px] font-medium cursor-pointer">
                Remove
              </button>
            </div>
          }
        </div>

        <!-- Add Type Override Form -->
        <div class="flex items-center gap-2 pt-1 border-t border-slate-100">
          <input
            type="text"
            [(ngModel)]="newSourceType"
            placeholder="Source type (e.g. NUMBER(p,s))"
            class="h-8 px-2.5 flex-1 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
          <span class="text-slate-400 font-mono">&rarr;</span>
          <input
            type="text"
            [(ngModel)]="newTargetType"
            placeholder="Target type (e.g. NUMERIC(p,s))"
            class="h-8 px-2.5 flex-1 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
          <button
            type="button"
            (click)="handleAddColumnTypeOverride()"
            [disabled]="!newSourceType.trim() || !newTargetType.trim()"
            class="h-8 px-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:pointer-events-none shrink-0 shadow-2xs transition-colors">
            Add type override
          </button>
        </div>
      </div>

      <!-- SECTION 4: DATA MASKING & CLEANSING CONTROLS -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Privacy & Masking Rules -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Data Privacy & Column Masking</span>
            <span class="text-[10px] text-slate-400 font-mono">{{ ts.scopeMapping().maskingRules.length }} rules</span>
          </div>

          <!-- Existing Masking Rules -->
          <div class="flex flex-col gap-1.5 max-h-36 overflow-y-auto">
            @for (mr of ts.scopeMapping().maskingRules; track mr.id) {
              <div class="flex items-center justify-between p-2 bg-slate-50 border border-slate-200 rounded-md text-xs">
                <div class="flex items-center gap-2">
                  <span class="px-1.5 py-0.5 text-[9px] font-bold bg-amber-50 text-amber-800 border border-amber-200 rounded">
                    {{ mr.maskingType }}
                  </span>
                  <span class="font-mono font-semibold text-slate-800">{{ mr.targetPattern }}</span>
                </div>
                <button
                  type="button"
                  (click)="ts.removeMaskingRule(mr.id)"
                  class="text-rose-600 hover:text-rose-800 text-[10px] font-medium cursor-pointer">
                  Remove
                </button>
              </div>
            }
          </div>

          <!-- Add Masking Rule Form (Using GDS Custom Select) -->
          <div class="flex flex-col gap-2 pt-1">
            <div class="flex items-center gap-2">
              <input
                type="text"
                [(ngModel)]="newMaskingPattern"
                placeholder="Column pattern (e.g. *ssn*)"
                class="h-8 px-2.5 flex-1 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
              <div class="w-40 shrink-0">
                <app-custom-select
                  size="sm"
                  [options]="maskingOptions"
                  [(ngModel)]="newMaskingType">
                </app-custom-select>
              </div>
              <button
                type="button"
                (click)="handleAddMaskingRule()"
                [disabled]="!newMaskingPattern.trim()"
                class="h-8 px-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:pointer-events-none shrink-0 shadow-2xs transition-colors">
                Add
              </button>
            </div>
          </div>
        </div>

        <!-- Cleansing & Hygiene Rules -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Data Cleansing & Hygiene Controls</span>
            <span class="text-[10px] text-slate-400">In-flight sanitize</span>
          </div>

          <div class="flex flex-col gap-3 pt-1">
            
            <label class="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.scopeMapping().cleansing.trimWhitespace"
                (change)="toggleCleansing('trimWhitespace')"
                class="rounded text-blue-600 focus:ring-0 mt-0.5" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Trim String Whitespace</span>
                <span class="text-[11px] text-slate-500 font-normal">Strip leading and trailing whitespace characters on all string fields</span>
              </div>
            </label>

            <label class="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.scopeMapping().cleansing.emptyStringToNull"
                (change)="toggleCleansing('emptyStringToNull')"
                class="rounded text-blue-600 focus:ring-0 mt-0.5" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Convert Empty Strings to NULL</span>
                <span class="text-[11px] text-slate-500 font-normal">Normalize empty quotes ("") into native SQL NULL representations</span>
              </div>
            </label>

            <label class="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.scopeMapping().cleansing.deduplicateOnPrimaryKey"
                (change)="toggleCleansing('deduplicateOnPrimaryKey')"
                class="rounded text-blue-600 focus:ring-0 mt-0.5" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Deduplicate on Primary Key</span>
                <span class="text-[11px] text-slate-500 font-normal">Enforce idempotency by picking latest record in batch on collision</span>
              </div>
            </label>

          </div>
        </div>

      </div>

    </div>
  `
})
export class Step3ScopeMappingComponent {
  public ts = inject(CreateTemplateService);

  // GDS Select Options
  public ruleTypeOptions: CustomSelectOption[] = [
    { label: 'INCLUDE', value: 'INCLUDE' },
    { label: 'EXCLUDE', value: 'EXCLUDE' }
  ];

  public objectTypeOptions: CustomSelectOption[] = [
    { label: 'TABLE', value: 'TABLE' },
    { label: 'VIEW', value: 'VIEW' },
    { label: 'SCHEMA', value: 'SCHEMA' },
    { label: 'SEQUENCE', value: 'SEQUENCE' },
    { label: 'PROCEDURE', value: 'PROCEDURE' }
  ];

  public nullabilityOptions: CustomSelectOption[] = [
    { label: 'Preserve Source Constraints', value: 'PRESERVE', desc: 'Preserve source not-null rules' },
    { label: 'Relax to Allow Nulls', value: 'ALLOW_NULL', desc: 'Safe migration to avoid load failures' },
    { label: 'Replace with Column Defaults', value: 'REPLACE_WITH_DEFAULT', desc: 'Substitute nulls with defaults' }
  ];

  public maskingOptions: CustomSelectOption[] = [
    { label: 'PII Redact', value: 'PII_REDACT' },
    { label: 'SHA-256 Hash', value: 'HASH_SHA256' },
    { label: 'Mask Email', value: 'MASK_EMAIL' },
    { label: 'Fake Generator', value: 'RANDOM_GENERATOR' },
    { label: 'Tokenize', value: 'TOKENIZE' }
  ];

  // New Rule State
  public newRuleType: ScopeRuleType = 'INCLUDE';
  public newRuleObjectType: ScopeObjectType = 'TABLE';
  public newRulePattern = '';
  public newRuleDescription = '';

  // New Schema Mapping State
  public newSourceSchema = '';
  public newTargetSchema = '';

  // New Column Type State
  public newSourceType = '';
  public newTargetType = '';

  // New Masking State
  public newMaskingPattern = '';
  public newMaskingType: MaskingType = 'PII_REDACT';

  public tableCases: { label: string; value: TableCaseTransformation }[] = [
    { label: 'Preserve Case', value: 'PRESERVE' },
    { label: 'lowercase', value: 'LOWERCASE' },
    { label: 'UPPERCASE', value: 'UPPERCASE' },
    { label: 'snake_case', value: 'SNAKE_CASE' }
  ];

  public handleAddScopeRule(): void {
    if (!this.newRulePattern.trim()) return;
    this.ts.addScopeRule({
      ruleType: this.newRuleType,
      objectType: this.newRuleObjectType,
      pattern: this.newRulePattern.trim(),
      description: this.newRuleDescription.trim() || undefined
    });
    this.newRulePattern = '';
    this.newRuleDescription = '';
  }

  public handleAddSchemaMapping(): void {
    if (!this.newSourceSchema.trim() || !this.newTargetSchema.trim()) return;
    this.ts.addSchemaMapping(this.newSourceSchema, this.newTargetSchema);
    this.newSourceSchema = '';
    this.newTargetSchema = '';
  }

  public handleAddColumnTypeOverride(): void {
    if (!this.newSourceType.trim() || !this.newTargetType.trim()) return;
    this.ts.addColumnTypeOverride(this.newSourceType, this.newTargetType);
    this.newSourceType = '';
    this.newTargetType = '';
  }

  public handleAddMaskingRule(): void {
    if (!this.newMaskingPattern.trim()) return;
    this.ts.addMaskingRule(this.newMaskingPattern, this.newMaskingType);
    this.newMaskingPattern = '';
  }

  public toggleCleansing(key: keyof CleansingRules): void {
    const curr = this.ts.scopeMapping().cleansing;
    this.ts.updateScopeMapping({
      cleansing: {
        ...curr,
        [key]: !curr[key]
      }
    });
  }
}
