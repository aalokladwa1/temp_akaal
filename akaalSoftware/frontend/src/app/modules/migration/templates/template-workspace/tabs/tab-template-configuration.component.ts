import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';
import { TEMPLATE_MODE_DESCRIPTORS } from '../../templates.models';

@Component({
  selector: 'app-tab-template-configuration',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 text-xs font-sans animate-in fade-in duration-150">
      
      @if (ws.template(); as tmpl) {
        
        <!-- TOP CONTROL & IMMUTABILITY CALLOUT STRIP -->
        <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 bg-white border border-slate-200 rounded-lg shadow-2xs">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-900 text-sm">Reusable Migration Configuration</span>
              @if (ws.isEditingConfig()) {
                <span class="px-2 py-0.5 text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 rounded-md">
                  EDITING SESSION ACTIVE
                </span>
              }
            </div>
            <p class="text-xs text-slate-500 m-0 font-normal">
              Presets and governance constraints materialized into new migrations created from this template.
            </p>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            @if (!ws.isEditingConfig()) {
              <button
                type="button"
                (click)="ws.startEditingConfig()"
                class="h-8 px-4 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors cursor-pointer shadow-2xs">
                Edit configuration
              </button>
            } @else {
              <button
                type="button"
                (click)="ws.saveEditingConfig()"
                class="h-8 px-4 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors cursor-pointer shadow-2xs">
                Save configuration
              </button>
              <button
                type="button"
                (click)="ws.cancelEditingConfig()"
                class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-semibold text-xs transition-colors cursor-pointer shadow-2xs">
                Cancel
              </button>
            }
          </div>
        </div>

        @if (ws.configSaveMessage()) {
          <div class="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-md text-xs font-medium flex items-center gap-2">
            <app-lucide-icon name="check" [size]="15" class="text-emerald-600"></app-lucide-icon>
            <span>{{ ws.configSaveMessage() }}</span>
          </div>
        }

        <!-- RUNNING MIGRATION IMMUTABILITY CALLOUT (Permanent Law) -->
        <div class="p-3.5 bg-slate-100 border border-slate-200 rounded-lg flex items-start gap-3">
          <app-lucide-icon name="shield-check" [size]="16" class="text-slate-700 shrink-0 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-0.5">
            <span class="font-bold text-slate-900">Materialization & Immutability Law</span>
            <p class="text-[11px] text-slate-600 font-normal m-0 leading-relaxed">
              Modifying template configuration only affects future migration instances. Initialized and historical migrations retain their materialized configuration independently and are never mutated.
            </p>
          </div>
        </div>

        <!-- SECTION 1: MIGRATION DEFINITION DEFAULTS -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Migration Definition Defaults</span>
            <span class="text-[10px] text-slate-500 font-mono">Section 1</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <div class="flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Naming Pattern</span>
              @if (!ws.isEditingConfig()) {
                <span class="font-mono font-bold text-slate-900 text-xs">{{ tmpl.configuration.migrationDefaults.migrationNamePattern }}</span>
              } @else {
                <input
                  type="text"
                  [ngModel]="ws.editDraft().migrationDefaults.migrationNamePattern"
                  (ngModelChange)="updateDefaultsDraft({ migrationNamePattern: $event })"
                  class="h-8 px-2.5 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
              }
              <span class="text-[10px] text-slate-500">Tokens: {{ '{{PROJECT}}, {{ENV}}, {{SEQ}}' }}</span>
            </div>

            <div class="flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Default Execution Priority</span>
              @if (!ws.isEditingConfig()) {
                <span class="font-semibold text-slate-900 text-xs">{{ tmpl.configuration.migrationDefaults.executionPriority }}</span>
              } @else {
                <app-custom-select
                  size="sm"
                  [options]="priorityOptions"
                  [ngModel]="ws.editDraft().migrationDefaults.executionPriority"
                  (ngModelChange)="updateDefaultsDraft({ executionPriority: $event })">
                </app-custom-select>
              }
              <span class="text-[10px] text-slate-500">Determines task dispatcher priority queue</span>
            </div>

            <div class="flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Source Connection Policy</span>
              <span class="font-semibold text-slate-900 text-xs">{{ tmpl.configuration.migrationDefaults.sourceConnectionPolicy }}</span>
              <span class="text-[10px] text-slate-500">Target Policy: {{ tmpl.configuration.migrationDefaults.targetConnectionPolicy }}</span>
            </div>

          </div>
        </div>

        <!-- SECTION 2: OBJECT SCOPE & DISCOVERY RULES -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Object Scope & Selection Filters</span>
            <span class="text-[10px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
              {{ tmpl.configuration.scopeMapping.objectScopeRules.length }} rules configured
            </span>
          </div>

          <!-- Rules Table -->
          <div class="overflow-x-auto border border-slate-200 rounded-md">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase">
                  <th class="px-3 py-2">Action</th>
                  <th class="px-3 py-2">Type</th>
                  <th class="px-3 py-2">Pattern</th>
                  <th class="px-3 py-2">Description</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (rule of tmpl.configuration.scopeMapping.objectScopeRules; track rule.id) {
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
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <!-- SECTION 3: MAPPING, TRANSFORMATIONS & DATA PRIVACY -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Schema Mappings & Case Policy -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
              <span class="font-bold text-slate-900">Schema & Identifier Mappings</span>
              <span class="text-[10px] text-slate-500">Case: {{ tmpl.configuration.scopeMapping.tableCaseTransformation }}</span>
            </div>

            <div class="flex flex-col gap-1.5">
              @for (sm of tmpl.configuration.scopeMapping.schemaMappings; track sm.id) {
                <div class="p-2 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between font-mono text-xs">
                  <span class="font-semibold text-slate-800">{{ sm.sourceSchema }}</span>
                  <span class="text-slate-500">&rarr;</span>
                  <span class="font-semibold text-blue-600">{{ sm.targetSchema }}</span>
                </div>
              }
              @if (tmpl.configuration.scopeMapping.schemaMappings.length === 0) {
                <span class="text-slate-500 italic">No explicit schema mappings (direct 1:1 mapping applied)</span>
              }
            </div>
          </div>

          <!-- Privacy Masking Rules -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
              <span class="font-bold text-slate-900">Data Privacy & Masking</span>
              <span class="text-[10px] text-slate-500 font-mono">{{ tmpl.configuration.scopeMapping.maskingRules.length }} active rules</span>
            </div>

            <div class="flex flex-col gap-1.5">
              @for (mr of tmpl.configuration.scopeMapping.maskingRules; track mr.id) {
                <div class="p-2 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between text-xs">
                  <span class="font-mono font-semibold text-slate-800">{{ mr.targetPattern }}</span>
                  <span class="px-2 py-0.5 text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200 rounded-md">
                    {{ mr.maskingType }}
                  </span>
                </div>
              }
              @if (tmpl.configuration.scopeMapping.maskingRules.length === 0) {
                <span class="text-slate-500 italic">No masking rules active for this template</span>
              }
            </div>
          </div>

        </div>

        <!-- SECTION 4: ENTERPRISE PERFORMANCE & MODE TUNING -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Performance & Mode Engine Parameters</span>
            <span class="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              {{ getModeLabel(tmpl.mode) }} Mode Engine
            </span>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Extract Concurrency</span>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.configuration.enterpriseConfig.performance.extractThreads }} Workers</span>
            </div>

            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Batch Commit Size</span>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.configuration.enterpriseConfig.performance.batchSize | number }} Rows</span>
            </div>

            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Buffer Memory Cap</span>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.configuration.enterpriseConfig.performance.bufferMemoryMb }} MB</span>
            </div>

            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Checkpoint Frequency</span>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.configuration.enterpriseConfig.checkpointRecovery.commitIntervalRows | number }} Rows</span>
            </div>

          </div>
        </div>

        <!-- SECTION 5: GOVERNANCE & OPERATOR OVERRIDABILITY -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Governance & Overridability Constraints</span>
            <span class="text-[10px] text-slate-500">Security Guardrails</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <div class="p-3 bg-slate-50 border border-slate-200 rounded-md flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Performance Settings Overridability</span>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.configuration.governance.overridability.performanceSettings }}</span>
              <span class="text-[10px] text-slate-500">Governs runtime worker and batch adjustments</span>
            </div>

            <div class="p-3 bg-slate-50 border border-slate-200 rounded-md flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Mapping Rules Overridability</span>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.configuration.governance.overridability.mappingRules }}</span>
              <span class="text-[10px] text-slate-500">Controls column mapping and masking mutations</span>
            </div>

            <div class="p-3 bg-slate-50 border border-slate-200 rounded-md flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Approval Policy</span>
              <span class="font-bold text-slate-900 text-xs">
                {{ tmpl.configuration.governance.approvalAndPolicy.requirePeerReview ? 'Dual Peer-Review Mandated' : 'Single Operator Launch' }}
              </span>
              <span class="text-[10px] text-slate-500">Audit Level: {{ tmpl.configuration.governance.approvalAndPolicy.auditLogLevel }}</span>
            </div>

          </div>
        </div>

      }

    </div>
  `
})
export class TabTemplateConfigurationComponent {
  public ws = inject(TemplateWorkspaceService);

  public priorityOptions: CustomSelectOption[] = [
    { label: 'Low Priority', value: 'LOW' },
    { label: 'Normal Priority', value: 'NORMAL' },
    { label: 'High Priority', value: 'HIGH' },
    { label: 'Critical Priority', value: 'CRITICAL' }
  ];

  public getModeLabel(mode: string): string {
    return (TEMPLATE_MODE_DESCRIPTORS as any)[mode]?.label || mode;
  }

  public updateDefaultsDraft(partial: any): void {
    const draft = this.ws.editDraft();
    this.ws.updateEditDraft({
      migrationDefaults: {
        ...draft.migrationDefaults,
        ...partial
      }
    });
  }
}
