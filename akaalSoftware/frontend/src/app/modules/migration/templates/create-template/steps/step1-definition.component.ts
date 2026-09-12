import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateTemplateService } from '../create-template.service';
import { TemplateMigrationMode, TemplateScope, TEMPLATE_MODE_DESCRIPTORS } from '../../templates.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-step1-definition',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-6 animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Definition & Applicability</h2>
        <p class="text-xs text-slate-500 font-normal">
          Establish the template's identity, organizational availability boundary, provider compatibility, and supported migration operational mode.
        </p>
      </div>

      <!-- General Information Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        
        <!-- Template Name -->
        <div class="flex flex-col gap-1.5 md:col-span-2">
          <label for="template-name" class="font-semibold text-slate-800 flex items-center gap-1">
            <span>Template Name</span>
            <span class="text-rose-500">*</span>
          </label>
          <input
            id="template-name"
            type="text"
            [ngModel]="ts.definition().name"
            (ngModelChange)="ts.updateDefinition({ name: $event })"
            placeholder="e.g., Oracle to Snowflake Enterprise Core Replication"
            class="h-9 px-3 bg-white border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors shadow-2xs" />
          <span class="text-[11px] text-slate-500 font-normal">
            Unique, human-readable identifier for engineers and operators when provisioning new migrations.
          </span>
        </div>

        <!-- Description -->
        <div class="flex flex-col gap-1.5 md:col-span-2">
          <label for="template-desc" class="font-semibold text-slate-800">
            Description & Usage Purpose
          </label>
          <textarea
            id="template-desc"
            rows="2"
            [ngModel]="ts.definition().description"
            (ngModelChange)="ts.updateDefinition({ description: $event })"
            placeholder="Describe the target workloads, table volume expectations, schema transformations, and SLA defaults..."
            class="p-3 bg-white border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors shadow-2xs resize-none"></textarea>
        </div>

      </div>

      <!-- Availability Boundary / Scope Selector -->
      <div class="flex flex-col gap-2.5">
        <label class="font-semibold text-slate-800">
          Availability Scope Boundary
        </label>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          
          <!-- Organization -->
          <div
            (click)="ts.updateDefinition({ scope: 'ORGANIZATION' })"
            class="p-3.5 rounded-lg border transition-all cursor-pointer flex flex-col gap-1.5"
            [class]="ts.definition().scope === 'ORGANIZATION'
              ? 'bg-blue-50/50 border-blue-600 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Organization</span>
              <span
                class="w-3.5 h-3.5 rounded-full border flex items-center justify-center"
                [class]="ts.definition().scope === 'ORGANIZATION' ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                @if (ts.definition().scope === 'ORGANIZATION') {
                  <span class="w-1.5 h-1.5 rounded-full bg-white"></span>
                }
              </span>
            </div>
            <p class="text-[11px] text-slate-600 font-normal leading-relaxed m-0">
              Universal availability across all workspaces, business units, and projects within the enterprise.
            </p>
          </div>

          <!-- Workspace -->
          <div
            (click)="ts.updateDefinition({ scope: 'WORKSPACE' })"
            class="p-3.5 rounded-lg border transition-all cursor-pointer flex flex-col gap-1.5"
            [class]="ts.definition().scope === 'WORKSPACE'
              ? 'bg-blue-50/50 border-blue-600 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Workspace</span>
              <span
                class="w-3.5 h-3.5 rounded-full border flex items-center justify-center"
                [class]="ts.definition().scope === 'WORKSPACE' ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                @if (ts.definition().scope === 'WORKSPACE') {
                  <span class="w-1.5 h-1.5 rounded-full bg-white"></span>
                }
              </span>
            </div>
            <p class="text-[11px] text-slate-600 font-normal leading-relaxed m-0">
              Shared across all migration initiatives and pipelines inside the current workspace perimeter.
            </p>
          </div>

          <!-- Project -->
          <div
            (click)="ts.updateDefinition({ scope: 'PROJECT' })"
            class="p-3.5 rounded-lg border transition-all cursor-pointer flex flex-col gap-1.5"
            [class]="ts.definition().scope === 'PROJECT'
              ? 'bg-blue-50/50 border-blue-600 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Project</span>
              <span
                class="w-3.5 h-3.5 rounded-full border flex items-center justify-center"
                [class]="ts.definition().scope === 'PROJECT' ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                @if (ts.definition().scope === 'PROJECT') {
                  <span class="w-1.5 h-1.5 rounded-full bg-white"></span>
                }
              </span>
            </div>
            <p class="text-[11px] text-slate-600 font-normal leading-relaxed m-0">
              Restricted exclusively to migrations bound to a designated target project.
            </p>
          </div>

        </div>
      </div>

      <!-- Source & Target Applicability Pair (GDS Custom Select Dropdowns) -->
      <div class="flex flex-col gap-2.5">
        <label class="font-semibold text-slate-800">
          Source & Target Applicability
        </label>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Source Provider Picker -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-2 shadow-2xs">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Source Provider</span>
              <span class="px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600 rounded-md">Extracted Engine</span>
            </div>
            
            <app-custom-select
              [options]="providerOptions"
              [ngModel]="ts.definition().sourceProvider"
              (ngModelChange)="ts.updateDefinition({ sourceProvider: $event })"
              [searchable]="true"
              searchPlaceholder="Search source engine...">
            </app-custom-select>

            <span class="text-[11px] text-slate-500 font-normal">
              Specifies the source engine dialect, CDC log mechanism, and extraction drivers.
            </span>
          </div>

          <!-- Target Provider Picker -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-2 shadow-2xs">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Target Provider</span>
              <span class="px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600 rounded-md">Ingestion Engine</span>
            </div>
            
            <app-custom-select
              [options]="providerOptions"
              [ngModel]="ts.definition().targetProvider"
              (ngModelChange)="ts.updateDefinition({ targetProvider: $event })"
              [searchable]="true"
              searchPlaceholder="Search ingestion engine...">
            </app-custom-select>

            <span class="text-[11px] text-slate-500 font-normal">
              Specifies the ingestion engine dialect, DDL converter, and bulk loading interfaces.
            </span>
          </div>

        </div>
      </div>

      <!-- Supported Migration Operational Mode (Pure Human-Readable Mode Name, Zero MN Badges) -->
      <div class="flex flex-col gap-2.5">
        <label class="font-semibold text-slate-800 flex items-center gap-1.5">
          <span>Supported Migration Operational Mode</span>
          <span class="text-rose-500">*</span>
        </label>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          @for (m of supportedModes; track m.code) {
            <div
              (click)="ts.updateDefinition({ mode: m.code })"
              class="p-3.5 rounded-lg border transition-all cursor-pointer flex flex-col gap-2"
              [class]="ts.definition().mode === m.code
                ? 'bg-blue-50/50 border-blue-600 shadow-xs ring-1 ring-blue-600/30'
                : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'">
              
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-900 text-xs">{{ m.label }}</span>
                <span
                  class="w-3.5 h-3.5 rounded-full border flex items-center justify-center shrink-0"
                  [class]="ts.definition().mode === m.code ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                  @if (ts.definition().mode === m.code) {
                    <span class="w-1.5 h-1.5 rounded-full bg-white"></span>
                  }
                </span>
              </div>

              <p class="text-[11px] text-slate-600 font-normal leading-relaxed m-0">
                {{ m.description }}
              </p>
            </div>
          }
        </div>
      </div>

    </div>
  `
})
export class Step1DefinitionComponent {
  public ts = inject(CreateTemplateService);

  public providerOptions: CustomSelectOption[] = [
    { label: 'Oracle Database', value: 'oracle', desc: 'Relational & CDC' },
    { label: 'PostgreSQL', value: 'postgresql', desc: 'Relational & Distributed SQL' },
    { label: 'Snowflake Data Cloud', value: 'snowflake', desc: 'Cloud Data Warehouse' },
    { label: 'MySQL', value: 'mysql', desc: 'Relational' },
    { label: 'Microsoft SQL Server', value: 'sqlserver', desc: 'Relational & CDC' },
    { label: 'MongoDB', value: 'mongodb', desc: 'Document & NoSQL' },
    { label: 'Google BigQuery', value: 'bigquery', desc: 'Cloud Data Warehouse' },
    { label: 'Apache Kafka', value: 'kafka', desc: 'Streaming & Event Bus' },
    { label: 'Amazon S3', value: 's3', desc: 'Object Storage & Lakehouse' },
    { label: 'Universal Any Dialect', value: 'universal', desc: 'Generic Compatibility' }
  ];

  public supportedModes = [
    TEMPLATE_MODE_DESCRIPTORS.M1_BULK,
    TEMPLATE_MODE_DESCRIPTORS.M2_BULK_CDC,
    TEMPLATE_MODE_DESCRIPTORS.M3_CDC,
    TEMPLATE_MODE_DESCRIPTORS.M4_INCREMENTAL,
    TEMPLATE_MODE_DESCRIPTORS.M5_STATE_SYNC,
    TEMPLATE_MODE_DESCRIPTORS.M6_SCHEMA_ONLY,
    TEMPLATE_MODE_DESCRIPTORS.M7_DATA_ONLY
  ];
}
