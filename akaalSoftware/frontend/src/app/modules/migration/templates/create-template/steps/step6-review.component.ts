import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CreateTemplateService } from '../create-template.service';
import { TEMPLATE_MODE_DESCRIPTORS } from '../../templates.models';

@Component({
  selector: 'app-step6-review',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6 animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Review & Create Template</h2>
        <p class="text-xs text-slate-500 font-normal">
          Inspect the complete cohesive template configuration across all operational dimensions before final instantiation.
        </p>
      </div>

      <!-- High-Level Metric Header Strip (Harmonious UI Theme) -->
      <div class="p-4 bg-slate-50 border border-slate-200 rounded-lg flex flex-wrap items-center justify-between gap-4 shadow-2xs">
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
              {{ modeDescriptor().label }}
            </span>
            <span class="px-2.5 py-0.5 text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200 rounded-md uppercase">
              {{ ts.definition().scope }}
            </span>
          </div>
          <h3 class="text-base font-bold text-slate-900 tracking-tight m-0 font-heading">
            {{ ts.definition().name || 'Untitled Migration Template' }}
          </h3>
          <p class="text-xs text-slate-600 font-normal m-0 max-w-xl">
            {{ ts.definition().description || 'No description provided.' }}
          </p>
        </div>

        <div class="flex items-center gap-4 shrink-0">
          <div class="flex flex-col text-right">
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Applicability</span>
            <span class="text-xs font-semibold text-slate-800">
              {{ providerDisplay(ts.definition().sourceProvider) }} &rarr; {{ providerDisplay(ts.definition().targetProvider) }}
            </span>
          </div>
        </div>
      </div>

      <!-- GROUP 1: DEFINITION & APPLICABILITY -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex items-center gap-2">
            <span class="w-5 h-5 rounded-md bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-[10px]">1</span>
            <span class="font-bold text-slate-900">Definition & Applicability</span>
          </div>
          <button
            type="button"
            (click)="ts.goToStep(1)"
            class="text-blue-600 hover:text-blue-800 text-xs font-semibold cursor-pointer">
            Edit
          </button>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Template Name</span>
            <span class="font-semibold text-slate-900">{{ ts.definition().name }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Availability Scope</span>
            <span class="font-semibold text-slate-900">{{ ts.definition().scope }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Source Provider</span>
            <span class="font-semibold text-slate-900">{{ providerDisplay(ts.definition().sourceProvider) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Target Provider</span>
            <span class="font-semibold text-slate-900">{{ providerDisplay(ts.definition().targetProvider) }}</span>
          </div>
        </div>
      </div>

      <!-- GROUP 2: MIGRATION DEFAULTS -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex items-center gap-2">
            <span class="w-5 h-5 rounded-md bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-[10px]">2</span>
            <span class="font-bold text-slate-900">Migration Defaults & Operator Requirements</span>
          </div>
          <button
            type="button"
            (click)="ts.goToStep(2)"
            class="text-blue-600 hover:text-blue-800 text-xs font-semibold cursor-pointer">
            Edit
          </button>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Naming Pattern</span>
            <span class="font-mono font-semibold text-slate-900">{{ ts.migrationDefaults().migrationNamePattern }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Execution Priority</span>
            <span class="font-semibold text-slate-900">{{ ts.migrationDefaults().executionPriority }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Source Connection Policy</span>
            <span class="font-medium text-slate-800">{{ ts.migrationDefaults().sourceConnectionPolicy }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Target Connection Policy</span>
            <span class="font-medium text-slate-800">{{ ts.migrationDefaults().targetConnectionPolicy }}</span>
          </div>
        </div>
      </div>

      <!-- GROUP 3: SCOPE, MAPPING & DATA CONTROLS -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex items-center gap-2">
            <span class="w-5 h-5 rounded-md bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-[10px]">3</span>
            <span class="font-bold text-slate-900">Scope, Mapping & Data Controls</span>
          </div>
          <button
            type="button"
            (click)="ts.goToStep(3)"
            class="text-blue-600 hover:text-blue-800 text-xs font-semibold cursor-pointer">
            Edit
          </button>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Object Scope Rules</span>
            <span class="font-semibold text-slate-900">{{ ts.scopeMapping().objectScopeRules.length }} rules active</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Schema Mappings</span>
            <span class="font-semibold text-slate-900">{{ ts.scopeMapping().schemaMappings.length }} mappings</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Identifier Case Policy</span>
            <span class="font-semibold text-slate-900">{{ ts.scopeMapping().tableCaseTransformation }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Privacy Masking</span>
            <span class="font-semibold text-slate-900">{{ ts.scopeMapping().maskingRules.length }} masking rules</span>
          </div>
        </div>
      </div>

      <!-- GROUP 4: ENTERPRISE CONFIGURATION -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex items-center gap-2">
            <span class="w-5 h-5 rounded-md bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-[10px]">4</span>
            <span class="font-bold text-slate-900">Enterprise Configuration & Engine Parameters</span>
          </div>
          <button
            type="button"
            (click)="ts.goToStep(4)"
            class="text-blue-600 hover:text-blue-800 text-xs font-semibold cursor-pointer">
            Edit
          </button>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Parallel Workers</span>
            <span class="font-semibold text-slate-900">{{ ts.enterpriseConfig().performance.extractThreads }} Threads</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Batch Size</span>
            <span class="font-semibold text-slate-900">{{ ts.enterpriseConfig().performance.batchSize | number }} Rows</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Fault Recovery</span>
            <span class="font-medium text-slate-800">{{ ts.enterpriseConfig().checkpointRecovery.errorHandlingPolicy }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Validation Preset</span>
            <span class="font-medium text-slate-800">{{ ts.enterpriseConfig().validationPresets.sampleDataHashRate }}</span>
          </div>
        </div>
      </div>

      <!-- GROUP 5: GOVERNANCE & REUSE RULES -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex items-center gap-2">
            <span class="w-5 h-5 rounded-md bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-[10px]">5</span>
            <span class="font-bold text-slate-900">Governance & Reuse Guardrails</span>
          </div>
          <button
            type="button"
            (click)="ts.goToStep(5)"
            class="text-blue-600 hover:text-blue-800 text-xs font-semibold cursor-pointer">
            Edit
          </button>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Performance Override</span>
            <span class="font-semibold text-slate-900">{{ ts.governance().overridability.performanceSettings }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Peer Approval</span>
            <span class="font-semibold text-slate-900">{{ ts.governance().approvalAndPolicy.requirePeerReview ? 'Mandatory' : 'Optional' }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Audit Log Level</span>
            <span class="font-semibold text-slate-900">{{ ts.governance().approvalAndPolicy.auditLogLevel }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Vault Provider</span>
            <span class="font-mono text-xs font-semibold text-slate-900">{{ ts.governance().secretReferenceRules.vaultProvider }}</span>
          </div>
        </div>
      </div>

    </div>
  `
})
export class Step6ReviewComponent {
  public ts = inject(CreateTemplateService);

  public modeDescriptor = () => {
    const m = this.ts.definition().mode;
    return TEMPLATE_MODE_DESCRIPTORS[m] || TEMPLATE_MODE_DESCRIPTORS.M1_BULK;
  };

  public providerDisplay(id: string): string {
    const map: Record<string, string> = {
      oracle: 'Oracle',
      postgresql: 'PostgreSQL',
      mysql: 'MySQL',
      sqlserver: 'SQL Server',
      mongodb: 'MongoDB',
      snowflake: 'Snowflake',
      bigquery: 'BigQuery',
      kafka: 'Kafka',
      s3: 'Amazon S3',
      universal: 'Universal Any'
    };
    return map[id?.toLowerCase()] || id || 'Unspecified';
  }
}
