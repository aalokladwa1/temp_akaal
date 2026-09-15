import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ReportDetailEnvelopeDTO } from '../../models/reports.models';
import { 
  MigrationReportPayload,
  SchemaCompatibilityReportPayload,
  ValidationReconciliationReportPayload,
  DataQualityReportPayload,
  PerformanceReportPayload,
  CDCReportPayload,
  CutoverFailbackReportPayload,
  RecoveryReliabilityReportPayload,
  SecurityReportPayload,
  ComplianceReportPayload,
  GovernanceApprovalReportPayload,
  AuditReportPayload,
  InfrastructureFleetReportPayload,
  ExecutiveReportPayload,
  ReportPayloadUnion
} from '../../models/report-payloads.models';
import { ReportsService } from '../../services/reports.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

// Import 14 Type-Specific Bodies
import { MigrationReportBodyComponent } from './type-specific/migration-report-body.component';
import { SchemaCompatibilityReportBodyComponent } from './type-specific/schema-compatibility-report-body.component';
import { ValidationReconciliationReportBodyComponent } from './type-specific/validation-reconciliation-report-body.component';
import { DataQualityReportBodyComponent } from './type-specific/data-quality-report-body.component';
import { PerformanceReportBodyComponent } from './type-specific/performance-report-body.component';
import { CdcReportBodyComponent } from './type-specific/cdc-report-body.component';
import { CutoverFailbackReportBodyComponent } from './type-specific/cutover-failback-report-body.component';
import { RecoveryReliabilityReportBodyComponent } from './type-specific/recovery-reliability-report-body.component';
import { SecurityReportBodyComponent } from './type-specific/security-report-body.component';
import { ComplianceReportBodyComponent } from './type-specific/compliance-report-body.component';
import { GovernanceApprovalReportBodyComponent } from './type-specific/governance-approval-report-body.component';
import { AuditReportBodyComponent } from './type-specific/audit-report-body.component';
import { InfrastructureFleetReportBodyComponent } from './type-specific/infrastructure-fleet-report-body.component';
import { ExecutiveReportBodyComponent } from './type-specific/executive-report-body.component';

export type ReportDetailTab = 'OVERVIEW' | 'FINDINGS' | 'SCOPE' | 'PROVENANCE' | 'EVIDENCE';

@Component({
  selector: 'app-report-detail-frame',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideIconComponent,
    MigrationReportBodyComponent,
    SchemaCompatibilityReportBodyComponent,
    ValidationReconciliationReportBodyComponent,
    DataQualityReportBodyComponent,
    PerformanceReportBodyComponent,
    CdcReportBodyComponent,
    CutoverFailbackReportBodyComponent,
    RecoveryReliabilityReportBodyComponent,
    SecurityReportBodyComponent,
    ComplianceReportBodyComponent,
    GovernanceApprovalReportBodyComponent,
    AuditReportBodyComponent,
    InfrastructureFleetReportBodyComponent,
    ExecutiveReportBodyComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full select-none animate-in fade-in duration-150">
      
      <!-- Top Action & Navigation Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1.5 max-w-3xl">
          <div class="flex items-center gap-2 flex-wrap">
            <button
              (click)="onBack()"
              class="h-7 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs mr-1">
              <app-lucide-icon name="arrow-left" [size]="13"></app-lucide-icon>
              <span>Back</span>
            </button>
            <span class="text-slate-300">•</span>
            <span class="text-xs font-bold text-blue-600 uppercase tracking-wider font-heading">{{ report.category_label }}</span>
            <span class="text-slate-300">•</span>
            <span class="text-xs font-medium text-slate-500">{{ report.subject_name }}</span>
          </div>

          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ report.title }}</h1>
          
          <div class="flex items-center gap-3 text-xs text-slate-500 flex-wrap pt-0.5">
            <span class="font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[11px] font-semibold">{{ report.id }}</span>
            <span>•</span>
            <span>Generated <strong class="text-slate-700 font-mono">{{ report.generated_at | date:'yyyy-MM-dd HH:mm:ss' }}</strong></span>
            @if (report.outcome) {
              <span>•</span>
              <span 
                class="px-2 py-0.5 rounded text-[10px] font-bold"
                [ngClass]="{
                  'bg-emerald-50 text-emerald-700 border border-emerald-200': report.outcome === 'SATISFIED' || report.outcome === 'CONVERGED' || report.outcome === 'RECONCILED',
                  'bg-amber-50 text-amber-700 border border-amber-200': report.outcome === 'DEFECTS_FOUND' || report.outcome === 'IN_PROGRESS',
                  'bg-rose-50 text-rose-700 border border-rose-200': report.outcome === 'BLOCKED',
                  'bg-slate-100 text-slate-600': report.outcome === 'NOT_APPLICABLE' || report.outcome === 'UNKNOWN'
                }">
                {{ report.outcome }}
              </span>
            }
          </div>
        </div>

        <div class="flex items-center gap-3 pt-1">
          <button
            (click)="onExport()"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Export Report
          </button>
        </div>
      </div>

      <!-- 5 Underline Navigation Tabs -->
      <div class="flex items-center gap-6 border-b border-slate-200 -mt-2">
        <button
          (click)="activeTab.set('OVERVIEW')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer"
          [ngClass]="activeTab() === 'OVERVIEW' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Overview
        </button>

        <button
          (click)="activeTab.set('FINDINGS')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer"
          [ngClass]="activeTab() === 'FINDINGS' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Findings &amp; Results
        </button>

        <button
          (click)="activeTab.set('SCOPE')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer"
          [ngClass]="activeTab() === 'SCOPE' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Scope &amp; Inputs
        </button>

        <button
          (click)="activeTab.set('PROVENANCE')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer"
          [ngClass]="activeTab() === 'PROVENANCE' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Trust &amp; Provenance
        </button>

        <button
          (click)="activeTab.set('EVIDENCE')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer"
          [ngClass]="activeTab() === 'EVIDENCE' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Related Evidence ({{ report.related_evidence.length }})
        </button>
      </div>

      <!-- TAB 1: OVERVIEW -->
      @if (activeTab() === 'OVERVIEW') {
        <div class="flex flex-col gap-6 animate-in fade-in duration-100">
          
          <!-- Summary Statement Card -->
          <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              REPORT SUMMARY STATEMENT
            </span>
            <p class="text-sm font-medium text-slate-800 leading-relaxed">
              {{ report.summary }}
            </p>
          </div>

          <!-- Key Technical Context Grid -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            
            <div class="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Subject Target</span>
              <span class="text-sm font-bold text-slate-900 truncate">{{ report.subject_name }}</span>
              <span class="text-xs text-slate-500">{{ report.subject_type }}</span>
            </div>

            <div class="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Category Domain</span>
              <span class="text-sm font-bold text-slate-900">{{ report.category_label }}</span>
              <span class="text-xs text-slate-500 font-mono">{{ report.category }}</span>
            </div>

            <div class="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Engine Subsystem</span>
              <span class="text-sm font-bold text-slate-900 truncate">{{ report.trust_and_provenance.producer_engine }}</span>
              <span class="text-xs text-slate-500 font-mono">{{ report.trust_and_provenance.producer_version }}</span>
            </div>

            <div class="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Integrity State</span>
              <div class="flex items-center gap-2 pt-0.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ report.trust_and_provenance.integrity_state }}
                </span>
                <span class="text-xs text-slate-500">{{ report.trust_and_provenance.completeness }}</span>
              </div>
            </div>

          </div>

          <!-- Quick Navigation Callouts -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div 
              (click)="activeTab.set('FINDINGS')"
              class="p-5 bg-white border border-slate-200 hover:border-blue-300 rounded-xl shadow-2xs flex items-center justify-between gap-4 cursor-pointer transition-colors group">
              <div class="flex flex-col gap-1">
                <h4 class="text-sm font-bold text-slate-900 group-hover:text-blue-600 font-heading">Examine Technical Findings &amp; Tables</h4>
                <p class="text-xs text-slate-500">View detailed domain metrics, partition transfers, stage durations, and evaluations.</p>
              </div>
              <span class="text-slate-400 group-hover:text-blue-600 transition-colors">
                <app-lucide-icon name="chevron-right" [size]="18"></app-lucide-icon>
              </span>
            </div>

            <div 
              (click)="activeTab.set('PROVENANCE')"
              class="p-5 bg-white border border-slate-200 hover:border-blue-300 rounded-xl shadow-2xs flex items-center justify-between gap-4 cursor-pointer transition-colors group">
              <div class="flex flex-col gap-1">
                <h4 class="text-sm font-bold text-slate-900 group-hover:text-blue-600 font-heading">Verify Cryptographic Fingerprint</h4>
                <p class="text-xs text-slate-500">Inspect the SHA-256 fingerprint, producer engine version, and audit run bindings.</p>
              </div>
              <span class="text-slate-400 group-hover:text-blue-600 transition-colors">
                <app-lucide-icon name="chevron-right" [size]="18"></app-lucide-icon>
              </span>
            </div>
          </div>

        </div>
      }

      <!-- TAB 2: FINDINGS & RESULTS (14 Type-Specific Bodies) -->
      @if (activeTab() === 'FINDINGS') {
        <div class="flex flex-col gap-6 animate-in fade-in duration-100">
          
          @if (report.payload.kind === 'MIGRATION') {
            <app-migration-report-body [payload]="asMigration(report.payload)"></app-migration-report-body>
          }
          @else if (report.payload.kind === 'SCHEMA_COMPATIBILITY') {
            <app-schema-compatibility-report-body [payload]="asSchemaCompatibility(report.payload)"></app-schema-compatibility-report-body>
          }
          @else if (report.payload.kind === 'VALIDATION_RECONCILIATION') {
            <app-validation-reconciliation-report-body [payload]="asValidationReconciliation(report.payload)"></app-validation-reconciliation-report-body>
          }
          @else if (report.payload.kind === 'DATA_QUALITY') {
            <app-data-quality-report-body [payload]="asDataQuality(report.payload)"></app-data-quality-report-body>
          }
          @else if (report.payload.kind === 'PERFORMANCE') {
            <app-performance-report-body [payload]="asPerformance(report.payload)"></app-performance-report-body>
          }
          @else if (report.payload.kind === 'CDC') {
            <app-cdc-report-body [payload]="asCdc(report.payload)"></app-cdc-report-body>
          }
          @else if (report.payload.kind === 'CUTOVER_FAILBACK') {
            <app-cutover-failback-report-body [payload]="asCutoverFailback(report.payload)"></app-cutover-failback-report-body>
          }
          @else if (report.payload.kind === 'RECOVERY_RELIABILITY') {
            <app-recovery-reliability-report-body [payload]="asRecoveryReliability(report.payload)"></app-recovery-reliability-report-body>
          }
          @else if (report.payload.kind === 'SECURITY') {
            <app-security-report-body [payload]="asSecurity(report.payload)"></app-security-report-body>
          }
          @else if (report.payload.kind === 'COMPLIANCE') {
            <app-compliance-report-body [payload]="asCompliance(report.payload)"></app-compliance-report-body>
          }
          @else if (report.payload.kind === 'GOVERNANCE_APPROVAL') {
            <app-governance-approval-report-body [payload]="asGovernanceApproval(report.payload)"></app-governance-approval-report-body>
          }
          @else if (report.payload.kind === 'AUDIT') {
            <app-audit-report-body [payload]="asAudit(report.payload)"></app-audit-report-body>
          }
          @else if (report.payload.kind === 'INFRASTRUCTURE_FLEET') {
            <app-infrastructure-fleet-report-body [payload]="asInfrastructureFleet(report.payload)"></app-infrastructure-fleet-report-body>
          }
          @else if (report.payload.kind === 'EXECUTIVE') {
            <app-executive-report-body [payload]="asExecutive(report.payload)"></app-executive-report-body>
          }

        </div>
      }

      <!-- TAB 3: SCOPE & INPUTS -->
      @if (activeTab() === 'SCOPE') {
        <div class="flex flex-col gap-6 animate-in fade-in duration-100">
          
          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <div class="p-4 bg-slate-50/80 border-b border-slate-200">
              <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">EXECUTION BOUNDS &amp; ENVIRONMENT</h3>
            </div>
            
            <div class="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 text-xs">
              
              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Tenant</span>
                <span class="font-semibold text-slate-900">{{ report.scope_and_inputs.tenant || 'Default Enterprise' }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Workspace</span>
                <span class="font-semibold text-slate-900">{{ report.scope_and_inputs.workspace || 'Default Workspace' }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Project Name</span>
                <span class="font-semibold text-slate-900">{{ report.scope_and_inputs.project_name || 'N/A' }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Migration / Validation Subject</span>
                <span class="font-semibold text-slate-900">{{ report.scope_and_inputs.migration_name || report.scope_and_inputs.validation_name || report.subject_name }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Run ID Binding</span>
                <code class="font-mono text-[11px] text-slate-800 bg-slate-100 px-2 py-0.5 rounded w-fit">{{ report.scope_and_inputs.run_id || 'N/A' }}</code>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Plan Version</span>
                <span class="font-mono text-slate-800">{{ report.scope_and_inputs.plan_version || '1.0' }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Execution Engine Mode</span>
                <span class="font-semibold text-slate-900">{{ report.scope_and_inputs.execution_mode || 'Dual-Engine Standard' }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Source Endpoint</span>
                <span class="font-mono text-[11px] text-slate-700 truncate">{{ report.scope_and_inputs.source_instance || 'N/A' }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Target Endpoint</span>
                <span class="font-mono text-[11px] text-slate-700 truncate">{{ report.scope_and_inputs.target_instance || 'N/A' }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Evaluation Window Start</span>
                <span class="font-mono text-slate-700">{{ (report.scope_and_inputs.time_window_start | date:'yyyy-MM-dd HH:mm:ss') || 'N/A' }}</span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-slate-500 font-medium">Evaluation Window End</span>
                <span class="font-mono text-slate-700">{{ (report.scope_and_inputs.time_window_end | date:'yyyy-MM-dd HH:mm:ss') || 'N/A' }}</span>
              </div>

            </div>
          </div>

        </div>
      }

      <!-- TAB 4: TRUST & PROVENANCE -->
      @if (activeTab() === 'PROVENANCE') {
        <div class="flex flex-col gap-6 animate-in fade-in duration-100">
          
          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <div class="p-4 bg-slate-50/80 border-b border-slate-200">
              <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">CRYPTOGRAPHIC INTEGRITY &amp; PROVENANCE RECORD</h3>
            </div>

            <div class="p-6 flex flex-col gap-6 text-xs">
              
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                
                <div class="flex flex-col gap-1">
                  <span class="text-slate-500 font-medium">Report Identifier</span>
                  <span class="font-mono font-bold text-slate-900">{{ report.trust_and_provenance.report_id }}</span>
                </div>

                <div class="flex flex-col gap-1">
                  <span class="text-slate-500 font-medium">Producer Engine</span>
                  <span class="font-semibold text-slate-900">{{ report.trust_and_provenance.producer_engine }}</span>
                </div>

                <div class="flex flex-col gap-1">
                  <span class="text-slate-500 font-medium">Producer Engine Version</span>
                  <span class="font-mono text-slate-800">{{ report.trust_and_provenance.producer_version }}</span>
                </div>

                <div class="flex flex-col gap-1">
                  <span class="text-slate-500 font-medium">Run / Plan Binding</span>
                  <span class="font-mono text-slate-800 text-[11px]">{{ report.trust_and_provenance.run_or_plan_binding }}</span>
                </div>

                <div class="flex flex-col gap-1">
                  <span class="text-slate-500 font-medium">Integrity State</span>
                  <div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {{ report.trust_and_provenance.integrity_state }}
                    </span>
                  </div>
                </div>

                <div class="flex flex-col gap-1">
                  <span class="text-slate-500 font-medium">Completeness State</span>
                  <span class="font-semibold text-slate-900">{{ report.trust_and_provenance.completeness }}</span>
                </div>

              </div>

              <!-- Cryptographic Fingerprint Block -->
              <div class="flex flex-col gap-1.5 p-4 rounded-lg bg-slate-50 border border-slate-200">
                <span class="text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">Artifact SHA-256 Digest Fingerprint</span>
                <code class="font-mono text-xs text-slate-900 select-all break-all">{{ report.trust_and_provenance.artifact_sha256_fingerprint }}</code>
              </div>

              <!-- Evidence References -->
              @if (report.trust_and_provenance.evidence_references && report.trust_and_provenance.evidence_references.length > 0) {
                <div class="flex flex-col gap-2">
                  <span class="text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">Referenced Cryptographic Manifests</span>
                  <div class="flex flex-wrap gap-2">
                    @for (ref of report.trust_and_provenance.evidence_references; track ref) {
                      <span class="px-2.5 py-1 rounded bg-slate-100 text-slate-800 font-mono text-[11px] border border-slate-200">
                        {{ ref }}
                      </span>
                    }
                  </div>
                </div>
              }

            </div>
          </div>

        </div>
      }

      <!-- TAB 5: RELATED EVIDENCE -->
      @if (activeTab() === 'EVIDENCE') {
        <div class="flex flex-col gap-6 animate-in fade-in duration-100">
          
          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <div class="p-4 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between">
              <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">ATTACHED EVIDENCE PACKAGES &amp; MANIFESTS</h3>
              <span class="text-xs text-slate-500">{{ report.related_evidence.length }} artifacts attached</span>
            </div>

            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Artifact Title</th>
                  <th class="py-3 px-4">Type</th>
                  <th class="py-3 px-4 font-mono">SHA-256 Digest</th>
                  <th class="py-3 px-4">Integrity</th>
                  <th class="py-3 px-4">Created</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (ev of report.related_evidence; track ev.id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ ev.title }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ ev.artifact_type }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-[11px] text-slate-500 max-w-[200px] truncate" [title]="ev.sha256_digest">
                      {{ ev.sha256_digest.substring(0, 16) }}...
                    </td>
                    <td class="py-3.5 px-4">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {{ ev.integrity_state }}
                      </span>
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ ev.created_at | date:'yyyy-MM-dd HH:mm' }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <a
                        [routerLink]="ev.deep_link_route"
                        class="h-7 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center gap-1 cursor-pointer transition-colors shadow-2xs">
                        <span>View in Portal</span>
                        <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                      </a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

        </div>
      }

    </div>
  `
})
export class ReportDetailFrameComponent {
  @Input({ required: true }) public report!: ReportDetailEnvelopeDTO;

  public activeTab = signal<ReportDetailTab>('OVERVIEW');

  constructor(private reportsService: ReportsService) {}

  public onBack(): void {
    this.reportsService.closeReport();
  }

  public onExport(): void {
    this.reportsService.openExportModal(this.report);
  }

  // Cast helpers for type-specific payloads
  public asMigration(p: ReportPayloadUnion): MigrationReportPayload {
    return p as MigrationReportPayload;
  }

  public asSchemaCompatibility(p: ReportPayloadUnion): SchemaCompatibilityReportPayload {
    return p as SchemaCompatibilityReportPayload;
  }

  public asValidationReconciliation(p: ReportPayloadUnion): ValidationReconciliationReportPayload {
    return p as ValidationReconciliationReportPayload;
  }

  public asDataQuality(p: ReportPayloadUnion): DataQualityReportPayload {
    return p as DataQualityReportPayload;
  }

  public asPerformance(p: ReportPayloadUnion): PerformanceReportPayload {
    return p as PerformanceReportPayload;
  }

  public asCdc(p: ReportPayloadUnion): CDCReportPayload {
    return p as CDCReportPayload;
  }

  public asCutoverFailback(p: ReportPayloadUnion): CutoverFailbackReportPayload {
    return p as CutoverFailbackReportPayload;
  }

  public asRecoveryReliability(p: ReportPayloadUnion): RecoveryReliabilityReportPayload {
    return p as RecoveryReliabilityReportPayload;
  }

  public asSecurity(p: ReportPayloadUnion): SecurityReportPayload {
    return p as SecurityReportPayload;
  }

  public asCompliance(p: ReportPayloadUnion): ComplianceReportPayload {
    return p as ComplianceReportPayload;
  }

  public asGovernanceApproval(p: ReportPayloadUnion): GovernanceApprovalReportPayload {
    return p as GovernanceApprovalReportPayload;
  }

  public asAudit(p: ReportPayloadUnion): AuditReportPayload {
    return p as AuditReportPayload;
  }

  public asInfrastructureFleet(p: ReportPayloadUnion): InfrastructureFleetReportPayload {
    return p as InfrastructureFleetReportPayload;
  }

  public asExecutive(p: ReportPayloadUnion): ExecutiveReportPayload {
    return p as ExecutiveReportPayload;
  }
}
