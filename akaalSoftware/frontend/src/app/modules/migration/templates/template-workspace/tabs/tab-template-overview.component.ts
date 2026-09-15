import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { TEMPLATE_MODE_DESCRIPTORS, TemplateMigrationMode, TemplateScope } from '../../templates.models';

@Component({
  selector: 'app-tab-template-overview',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 text-xs font-sans animate-in fade-in duration-150">
      
      @if (ws.template(); as tmpl) {
        
        <!-- SECTION 1: IDENTITY & PURPOSE SUMMARY CARD -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-slate-100 pb-4">
            <div class="flex flex-col gap-1.5 flex-1">
              <div class="flex items-center gap-2">
                <span class="px-2.5 py-0.5 text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
                  {{ getModeLabel(tmpl.mode) }}
                </span>
                <span class="px-2.5 py-0.5 text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200 rounded-md uppercase">
                  {{ tmpl.scope }} SCOPE
                </span>
                <span class="px-2 py-0.5 text-[11px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-200 rounded-md">
                  Revision {{ tmpl.revisionNumber }} ({{ tmpl.versionLabel }})
                </span>
              </div>
              <h2 class="text-lg font-bold text-slate-900 tracking-tight font-heading m-0">
                {{ tmpl.name }}
              </h2>
              <p class="text-xs text-slate-600 font-normal m-0 max-w-3xl leading-relaxed">
                {{ tmpl.description }}
              </p>
            </div>

            <!-- Quick Metadata Sidebar -->
            <div class="flex md:flex-col items-start md:items-end justify-between md:justify-center gap-2 text-right shrink-0 border-t md:border-t-0 pt-3 md:pt-0 border-slate-100">
              <div class="flex flex-col">
                <span class="text-[10px] font-bold text-slate-500 uppercase">Created By</span>
                <span class="font-medium text-slate-800">{{ tmpl.createdBy }}</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[10px] font-bold text-slate-500 uppercase">Last Updated</span>
                <span class="font-medium text-slate-800">{{ tmpl.updatedAt | date:'mediumDate' }}</span>
              </div>
            </div>
          </div>

          <!-- Applicability & Dialect Strip -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <div class="p-3 bg-slate-50 border border-slate-200 rounded-md flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Source Engine Dialect</span>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.applicabilityDetails.sourceDialect }}</span>
              <span class="text-[11px] text-slate-500 font-normal">{{ tmpl.applicabilityDetails.sourceFamily }}</span>
            </div>

            <div class="p-3 bg-slate-50 border border-slate-200 rounded-md flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Target Ingestion Engine</span>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.applicabilityDetails.targetDialect }}</span>
              <span class="text-[11px] text-slate-500 font-normal">{{ tmpl.applicabilityDetails.targetFamily }}</span>
            </div>

            <div class="p-3 bg-slate-50 border border-slate-200 rounded-md flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Engine Compatibility</span>
              <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span class="font-bold text-slate-900 text-xs">{{ tmpl.applicabilityDetails.compatibility.statusLabel }}</span>
              </div>
              <span class="text-[11px] text-slate-500 font-normal">{{ tmpl.applicabilityDetails.compatibility.certifiedVersionRange }}</span>
            </div>

          </div>
        </div>

        <!-- SECTION 2: CONFIGURATION & PRESET SUMMARY (Grouped Cards) -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          
          <!-- Defaults Card -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col justify-between gap-3">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-slate-500 uppercase">Migration Defaults</span>
                <app-lucide-icon name="sliders" [size]="14" class="text-slate-400"></app-lucide-icon>
              </div>
              <span class="text-xs font-mono font-bold text-slate-900 truncate" [title]="tmpl.configuration.migrationDefaults.migrationNamePattern">
                {{ tmpl.configuration.migrationDefaults.migrationNamePattern }}
              </span>
              <div class="flex items-center gap-1.5 pt-1">
                <span class="text-[10px] text-slate-500">Priority:</span>
                <span class="px-1.5 py-0.2 text-[10px] font-bold bg-slate-100 text-slate-700 rounded">
                  {{ tmpl.configuration.migrationDefaults.executionPriority }}
                </span>
              </div>
            </div>
            <button
              type="button"
              (click)="ws.setActiveTab('configuration')"
              class="text-blue-600 hover:text-blue-800 text-[11px] font-semibold text-left cursor-pointer">
              View configuration &rarr;
            </button>
          </div>

          <!-- Discovery & Scope Rules Card -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col justify-between gap-3">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-slate-500 uppercase">Object Scope Rules</span>
                <app-lucide-icon name="filter" [size]="14" class="text-slate-400"></app-lucide-icon>
              </div>
              <span class="text-sm font-bold text-slate-900 font-heading">
                {{ tmpl.configuration.scopeMapping.objectScopeRules.length }} Active Rules
              </span>
              <span class="text-[11px] text-slate-500 font-normal">
                {{ tmpl.configuration.scopeMapping.schemaMappings.length }} schema mappings &middot; {{ tmpl.configuration.scopeMapping.tableCaseTransformation }}
              </span>
            </div>
            <button
              type="button"
              (click)="ws.setActiveTab('configuration')"
              class="text-blue-600 hover:text-blue-800 text-[11px] font-semibold text-left cursor-pointer">
              Inspect scope &rarr;
            </button>
          </div>

          <!-- Concurrency & Performance Card -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col justify-between gap-3">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-slate-500 uppercase">Concurrency & Batch</span>
                <app-lucide-icon name="cpu" [size]="14" class="text-slate-400"></app-lucide-icon>
              </div>
              <span class="text-sm font-bold text-slate-900 font-heading">
                {{ tmpl.configuration.enterpriseConfig.performance.extractThreads }} Workers &middot; {{ tmpl.configuration.enterpriseConfig.performance.batchSize | number }} Rows
              </span>
              <span class="text-[11px] text-slate-500 font-normal">
                {{ tmpl.configuration.enterpriseConfig.performance.bufferMemoryMb }}MB Ring Buffer Threshold
              </span>
            </div>
            <button
              type="button"
              (click)="ws.setActiveTab('configuration')"
              class="text-blue-600 hover:text-blue-800 text-[11px] font-semibold text-left cursor-pointer">
              Tuning parameters &rarr;
            </button>
          </div>

          <!-- Governance & Compliance Card -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col justify-between gap-3">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-slate-500 uppercase">Governance & Launch</span>
                <app-lucide-icon name="shield-check" [size]="14" class="text-slate-400"></app-lucide-icon>
              </div>
              <span class="text-sm font-bold text-slate-900 font-heading">
                {{ tmpl.configuration.governance.approvalAndPolicy.requirePeerReview ? 'Peer Review Mandated' : 'Single Operator Launch' }}
              </span>
              <span class="text-[11px] text-slate-500 font-normal">
                Audit Logging: {{ tmpl.configuration.governance.approvalAndPolicy.auditLogLevel }}
              </span>
            </div>
            <button
              type="button"
              (click)="ws.setActiveTab('configuration')"
              class="text-blue-600 hover:text-blue-800 text-[11px] font-semibold text-left cursor-pointer">
              Governance rules &rarr;
            </button>
          </div>

        </div>

        <!-- SECTION 3: USAGE & VERSION HIGHLIGHTS (Two Columns) -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
          
          <!-- Usage Highlights -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900">Active Usage & Dependencies</span>
                <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-slate-100 text-slate-700 rounded">
                  {{ tmpl.usage.migrationCount }} migrations created
                </span>
              </div>
              <button
                type="button"
                (click)="ws.setActiveTab('usage')"
                class="text-blue-600 hover:text-blue-800 text-xs font-semibold cursor-pointer">
                View Usage
              </button>
            </div>

            <div class="flex flex-col gap-2">
              @for (p of tmpl.usage.projects.slice(0, 3); track p.projectId) {
                <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between">
                  <div class="flex flex-col gap-0.5">
                    <span class="font-semibold text-slate-900 text-xs">{{ p.projectName }}</span>
                    <span class="text-[10px] text-slate-500">{{ p.environment }} &middot; {{ p.referencingMigrationCount }} migrations bound</span>
                  </div>
                  <span class="text-[10px] font-mono text-slate-500">{{ p.lastUsedAt | date:'mediumDate' }}</span>
                </div>
              }
            </div>
          </div>

          <!-- Version & Revision History -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900">Revisions & Version Lineage</span>
                <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200 rounded">
                  {{ tmpl.versions.length }} Revisions
                </span>
              </div>
              <button
                type="button"
                (click)="ws.setActiveTab('versions')"
                class="text-blue-600 hover:text-blue-800 text-xs font-semibold cursor-pointer">
                Compare Revisions
              </button>
            </div>

            <div class="flex flex-col gap-2">
              @for (v of tmpl.versions; track v.versionLabel) {
                <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between">
                  <div class="flex flex-col gap-0.5">
                    <div class="flex items-center gap-2">
                      <span class="font-mono font-bold text-slate-900 text-xs">{{ v.versionLabel }}</span>
                      @if (v.isCurrent) {
                        <span class="px-1.5 py-0.2 text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">
                          CURRENT
                        </span>
                      }
                    </div>
                    <p class="text-[11px] text-slate-500 m-0 truncate max-w-sm">{{ v.changeSummary }}</p>
                  </div>
                  <span class="text-[10px] text-slate-500">{{ v.createdAt | date:'mediumDate' }}</span>
                </div>
              }
            </div>
          </div>

        </div>

        <!-- SECTION 4: OPERATIONAL INTENT & ADVISORY INSIGHTS (P7B / P7C Context) -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
          
          <!-- P7B Locality & Sovereignty Intent -->
          <div class="p-4 bg-slate-50 border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center gap-2 border-b border-slate-200 pb-2">
              <app-lucide-icon name="map-pin" [size]="15" class="text-slate-700"></app-lucide-icon>
              <span class="font-bold text-slate-900">Locality & Sovereignty Intent (Operational Contract)</span>
            </div>
            
            <div class="flex flex-col gap-2 text-slate-700 text-xs">
              <div class="flex items-start gap-2">
                <span class="text-slate-400 font-mono">•</span>
                <span><strong>Locality Boundary:</strong> {{ tmpl.p7bContext.localityRequirements.join(', ') }}</span>
              </div>
              <div class="flex items-start gap-2">
                <span class="text-slate-400 font-mono">•</span>
                <span><strong>Sovereignty Enforcement:</strong> {{ tmpl.p7bContext.sovereigntyConstraints.join('; ') }}</span>
              </div>
              <div class="flex items-start gap-2">
                <span class="text-slate-400 font-mono">•</span>
                <span><strong>Recovery Preference:</strong> {{ tmpl.p7bContext.recoveryPreference }}</span>
              </div>
            </div>
          </div>

          <!-- P7C Advisory Context -->
          <div class="p-4 bg-slate-50 border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center gap-2 border-b border-slate-200 pb-2">
              <app-lucide-icon name="lightbulb" [size]="15" class="text-blue-600"></app-lucide-icon>
              <span class="font-bold text-slate-900">Template Advisory Insights (Advisory Only)</span>
            </div>
            
            <p class="text-xs text-slate-600 font-normal m-0 leading-relaxed">
              {{ tmpl.p7cContext.advisorySummary }}
            </p>
            @if (tmpl.p7cContext.recommendations; as recs) {
              <ul class="m-0 pl-4 space-y-1 text-[11px] text-slate-600">
                @for (r of recs; track r) {
                  <li>{{ r }}</li>
                }
              </ul>
            }
            <span class="text-[10px] text-slate-400 italic">
              {{ tmpl.p7cContext.confidenceNote }}
            </span>
          </div>

        </div>

      }

    </div>
  `
})
export class TabTemplateOverviewComponent {
  public ws = inject(TemplateWorkspaceService);

  public getModeLabel(mode: TemplateMigrationMode): string {
    return TEMPLATE_MODE_DESCRIPTORS[mode]?.label || mode;
  }
}
