import { Component, Input, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ReportsService } from '../../services/reports.service';
import { 
  CertificationDetailEnvelopeDTO, 
  formatCertificationDecision,
  formatCriterionOutcome 
} from '../../models/certification.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

export type CertificationDetailTab = 
  | 'OVERVIEW'
  | 'CRITERIA'
  | 'EVIDENCE'
  | 'GOVERNANCE'
  | 'TRUST'
  | 'REPORTS';

@Component({
  selector: 'app-certification-detail-frame',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
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
            <span class="text-xs font-semibold text-slate-600 uppercase tracking-wider font-heading">
              {{ cert.domain === 'MIGRATION' ? 'Migration Certification' : 'Validation Certification' }}
            </span>
            <span class="text-slate-300">•</span>
            <span class="text-xs font-medium text-slate-500">{{ cert.subject_name }}</span>
          </div>

          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ cert.title }}</h1>
          
          <div class="flex items-center gap-3 text-xs text-slate-500 flex-wrap pt-0.5">
            <span class="font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[11px] font-semibold">{{ cert.id }}</span>
            <span>•</span>
            <span>Issued <strong class="text-slate-700 font-mono">{{ cert.issued_at | date:'yyyy-MM-dd HH:mm' }}</strong></span>
            <span>•</span>
            <span 
              class="px-2 py-0.5 rounded text-[10px] font-bold"
              [ngClass]="{
                'bg-emerald-50 text-emerald-700 border border-emerald-200': cert.decision === 'CERTIFIED',
                'bg-rose-50 text-rose-700 border border-rose-200': cert.decision === 'NOT_CERTIFIED' || cert.decision === 'REVOKED',
                'bg-amber-50 text-amber-800 border border-amber-200': cert.decision === 'EXPIRED' || cert.decision === 'PENDING_EVALUATION',
                'bg-slate-50 text-slate-700 border border-slate-200': cert.decision === 'CERTIFICATION_NOT_ISSUED' || cert.decision === 'UNKNOWN'
              }">
              {{ formatDecision(cert.decision) }}
            </span>
          </div>
        </div>

        <div class="flex items-center gap-3 pt-1">
          <button
            (click)="onVerifyIntegrity()"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors cursor-pointer shadow-2xs">
            Verify Integrity
          </button>
        </div>
      </div>

      <!-- 6 Canonical Underline Navigation Tabs -->
      <div class="flex items-center gap-6 border-b border-slate-200 -mt-2 overflow-x-auto">
        <button
          (click)="activeTab.set('OVERVIEW')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
          [ngClass]="activeTab() === 'OVERVIEW' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Overview
        </button>

        <button
          (click)="activeTab.set('CRITERIA')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0 flex items-center gap-1.5"
          [ngClass]="activeTab() === 'CRITERIA' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          <span>Criteria &amp; Assertions</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-600 font-mono">{{ cert.criteria.length }}</span>
        </button>

        <button
          (click)="activeTab.set('EVIDENCE')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0 flex items-center gap-1.5"
          [ngClass]="activeTab() === 'EVIDENCE' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          <span>Evidence Basis</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-600 font-mono">{{ cert.evidence.length }}</span>
        </button>

        @if (cert.governance) {
          <button
            (click)="activeTab.set('GOVERNANCE')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="activeTab() === 'GOVERNANCE' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Governance &amp; Decision
          </button>
        }

        <button
          (click)="activeTab.set('TRUST')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
          [ngClass]="activeTab() === 'TRUST' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Trust &amp; Integrity
        </button>

        @if (cert.related_report_ids.length > 0) {
          <button
            (click)="activeTab.set('REPORTS')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0 flex items-center gap-1.5"
            [ngClass]="activeTab() === 'REPORTS' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            <span>Related Reports</span>
            <span class="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-600 font-mono">{{ cert.related_report_ids.length }}</span>
          </button>
        }
      </div>

      <!-- TAB 1: OVERVIEW -->
      @if (activeTab() === 'OVERVIEW') {
        <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
          
          <!-- Summary Card -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
            <div class="flex flex-col gap-1">
              <h3 class="text-sm font-bold text-slate-900 font-heading">Certification Overview &amp; Scope</h3>
              <p class="text-xs text-slate-600 leading-relaxed">{{ cert.summary }}</p>
            </div>

            <div class="pt-3 border-t border-slate-100 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Scope Specification</span>
              <p class="text-xs text-slate-700 leading-relaxed">{{ cert.scope_summary }}</p>
            </div>
          </div>

          <!-- Type-Specific Domain Sections -->
          @if (cert.domain === 'MIGRATION' && cert.migration_payload) {
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              
              <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Execution Outcome Basis</h4>
                <div class="flex flex-col gap-2 text-xs text-slate-700">
                  <div class="flex justify-between py-1 border-b border-slate-100">
                    <span class="text-slate-500">Execution Mode:</span>
                    <strong class="font-mono text-slate-800">{{ cert.migration_payload.execution_mode }}</strong>
                  </div>
                  <div class="flex justify-between py-1 border-b border-slate-100">
                    <span class="text-slate-500">Execution Outcome:</span>
                    <strong class="text-slate-800">{{ cert.migration_payload.execution_outcome }}</strong>
                  </div>
                  <div class="pt-1">
                    <span class="text-slate-500 block mb-1">Transferred Scope:</span>
                    <p class="text-xs text-slate-700 leading-relaxed">{{ cert.migration_payload.transferred_scope_summary }}</p>
                  </div>
                </div>
              </div>

              <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Checkpoint &amp; Recovery Evidence</h4>
                <p class="text-xs text-slate-700 leading-relaxed">{{ cert.migration_payload.checkpoint_recovery_evidence_summary }}</p>
                
                @if (cert.migration_payload.cutover_evidence_summary) {
                  <div class="pt-3 border-t border-slate-100">
                    <span class="text-slate-500 block mb-1 text-xs">Cutover Evidence:</span>
                    <p class="text-xs text-slate-700 leading-relaxed">{{ cert.migration_payload.cutover_evidence_summary }}</p>
                  </div>
                }
              </div>

            </div>
          } @else if (cert.domain === 'VALIDATION' && cert.validation_payload) {
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              
              <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Reconciliation &amp; Parity Basis</h4>
                <div class="flex flex-col gap-2 text-xs text-slate-700">
                  <div class="pt-1">
                    <span class="text-slate-500 block mb-1">Source &harr; Target Comparison:</span>
                    <p class="text-xs text-slate-700 leading-relaxed">{{ cert.validation_payload.source_target_comparison_summary }}</p>
                  </div>
                  <div class="pt-2 border-t border-slate-100">
                    <span class="text-slate-500 block mb-1">Row Count Reconciliation:</span>
                    <p class="text-xs text-slate-700 leading-relaxed">{{ cert.validation_payload.count_reconciliation_summary }}</p>
                  </div>
                </div>
              </div>

              <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Integrity &amp; Discrepancy Findings</h4>
                <p class="text-xs text-slate-700 leading-relaxed">{{ cert.validation_payload.checksum_merkle_summary }}</p>
                <div class="pt-2 border-t border-slate-100">
                  <span class="text-slate-500 block mb-1 text-xs">Discrepancy Resolution:</span>
                  <p class="text-xs text-slate-700 leading-relaxed">{{ cert.validation_payload.discrepancies_summary }}</p>
                </div>
                @if (cert.validation_payload.repair_revalidation_summary) {
                  <div class="pt-2 border-t border-slate-100">
                    <span class="text-slate-500 block mb-1 text-xs">Repair &amp; Revalidation:</span>
                    <p class="text-xs text-slate-700 leading-relaxed">{{ cert.validation_payload.repair_revalidation_summary }}</p>
                  </div>
                }
              </div>

            </div>
          }

          <!-- Exceptions & Limitations Section -->
          @if (cert.exceptions.length > 0) {
            <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="alert-circle" [size]="16" class="text-amber-600"></app-lucide-icon>
                <h3 class="text-sm font-bold text-slate-900 font-heading">Exceptions &amp; Operational Limitations</h3>
              </div>
              <div class="divide-y divide-slate-100 text-xs">
                @for (exc of cert.exceptions; track exc.id) {
                  <div class="py-2.5 flex flex-col gap-1">
                    <div class="flex items-center justify-between">
                      <strong class="text-slate-800">{{ exc.condition }}</strong>
                      <span class="text-[10px] font-mono text-slate-400">Updated: {{ exc.updated_at | date:'yyyy-MM-dd' }}</span>
                    </div>
                    <p class="text-slate-600 leading-relaxed">{{ exc.detail }}</p>
                  </div>
                }
              </div>
            </div>
          }

        </div>
      }

      <!-- TAB 2: CRITERIA & ASSERTIONS -->
      @if (activeTab() === 'CRITERIA') {
        <div class="flex flex-col gap-5 select-none animate-in fade-in duration-150">
          
          <div class="flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900 font-heading">Formal Criteria &amp; Assertions</h3>
            <p class="text-xs text-slate-500">
              Evaluated criteria supporting this formal certification. Each outcome is backed by canonical observation data.
            </p>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Criterion / Assertion</th>
                  <th class="py-3 px-4">Required Condition</th>
                  <th class="py-3 px-4">Observed Result</th>
                  <th class="py-3 px-4">Outcome</th>
                  <th class="py-3 px-4 text-right">Evidence Ref</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (crit of cert.criteria; track crit.id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    
                    <td class="py-3.5 px-4 font-semibold text-slate-900 max-w-xs">
                      {{ crit.name }}
                    </td>

                    <td class="py-3.5 px-4 text-slate-600 max-w-xs">
                      {{ crit.required_condition }}
                    </td>

                    <td class="py-3.5 px-4 text-slate-800 max-w-xs leading-relaxed">
                      {{ crit.observed_result }}
                    </td>

                    <td class="py-3.5 px-4">
                      <span 
                        class="px-2.5 py-1 rounded-md text-[11px] font-bold inline-block"
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border border-emerald-200': crit.outcome === 'SATISFIED',
                          'bg-rose-50 text-rose-700 border border-rose-200': crit.outcome === 'NOT_SATISFIED',
                          'bg-amber-50 text-amber-800 border border-amber-200': crit.outcome === 'EXCEPTION' || crit.outcome === 'NOT_EVALUATED',
                          'bg-slate-100 text-slate-700': crit.outcome === 'NOT_APPLICABLE' || crit.outcome === 'UNKNOWN'
                        }">
                        {{ formatOutcome(crit.outcome) }}
                      </span>
                    </td>

                    <td class="py-3.5 px-4 text-right font-mono text-[11px] text-slate-500">
                      {{ crit.evidence_ref || '—' }}
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>

        </div>
      }

      <!-- TAB 3: EVIDENCE BASIS -->
      @if (activeTab() === 'EVIDENCE') {
        <div class="flex flex-col gap-5 select-none animate-in fade-in duration-150">
          
          <div class="flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900 font-heading">Supporting Evidence Basis</h3>
            <p class="text-xs text-slate-500">
              Canonical proof material and verification manifests attached to this certification record.
            </p>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Evidence Artifact</th>
                  <th class="py-3 px-4">Type</th>
                  <th class="py-3 px-4">SHA-256 Digest</th>
                  <th class="py-3 px-4">Integrity State</th>
                  <th class="py-3 px-4 hidden md:table-cell">Created</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (ev of cert.evidence; track ev.id) {
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
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border border-emerald-200': ev.integrity_state === 'VERIFIED',
                          'bg-amber-50 text-amber-800 border border-amber-200': ev.integrity_state === 'PENDING',
                          'bg-slate-100 text-slate-700': ev.integrity_state === 'UNVERIFIED' || ev.integrity_state === 'UNAVAILABLE'
                        }">
                        {{ ev.integrity_state === 'VERIFIED' ? 'Integrity Verified' : ev.integrity_state }}
                      </span>
                    </td>

                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px] hidden md:table-cell">
                      {{ ev.created_at | date:'yyyy-MM-dd HH:mm' }}
                    </td>

                    <td class="py-3.5 px-4 text-right">
                      <button
                        (click)="onVerifyEvidence(ev.id)"
                        class="h-7 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center gap-1 cursor-pointer transition-colors shadow-2xs">
                        <span>Verify</span>
                        <app-lucide-icon name="check-check" [size]="12"></app-lucide-icon>
                      </button>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>

        </div>
      }

      <!-- TAB 4: GOVERNANCE & DECISION -->
      @if (activeTab() === 'GOVERNANCE' && cert.governance) {
        <div class="flex flex-col gap-5 select-none animate-in fade-in duration-150">
          
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
            <div class="flex items-center justify-between flex-wrap gap-2">
              <div class="flex flex-col gap-0.5">
                <h3 class="text-sm font-bold text-slate-900 font-heading">
                  Governance Barrier: {{ cert.governance.barrier_name }}
                </h3>
                <span class="text-xs text-slate-500">Dual-control approvals and condition records</span>
              </div>

              <span class="px-2.5 py-1 rounded-md text-xs font-bold bg-slate-100 text-slate-800">
                Decision Status: {{ cert.governance.decision_status }}
              </span>
            </div>

            @if (cert.governance.required_quorum) {
              <div class="text-xs text-slate-600">
                Quorum: <strong class="text-slate-900">{{ cert.governance.approvals_received || 0 }}</strong> of <strong class="text-slate-900">{{ cert.governance.required_quorum }}</strong> required approvals recorded
              </div>
            }

            @if (cert.governance.approvers && cert.governance.approvers.length > 0) {
              <div class="pt-3 border-t border-slate-100">
                <h4 class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Recorded Approvers</h4>
                <div class="divide-y divide-slate-100 text-xs">
                  @for (appr of cert.governance.approvers; track appr.actor_name) {
                    <div class="py-2 flex items-center justify-between">
                      <div class="flex items-center gap-2">
                        <strong class="text-slate-800">{{ appr.actor_name }}</strong>
                        <span class="text-slate-400 font-mono text-[11px]">({{ appr.role }})</span>
                      </div>
                      <div class="flex items-center gap-3">
                        <span class="text-slate-500 font-mono text-[11px]">{{ appr.timestamp | date:'yyyy-MM-dd HH:mm' }}</span>
                        <span class="font-semibold text-emerald-700">{{ appr.decision }}</span>
                      </div>
                    </div>
                  }
                </div>
              </div>
            }

            @if (cert.governance.conditions && cert.governance.conditions.length > 0) {
              <div class="pt-3 border-t border-slate-100">
                <h4 class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Governance Conditions</h4>
                <ul class="list-disc list-inside text-xs text-slate-600 space-y-1">
                  @for (cond of cert.governance.conditions; track cond) {
                    <li>{{ cond }}</li>
                  }
                </ul>
              </div>
            }
          </div>

        </div>
      }

      <!-- TAB 5: TRUST & INTEGRITY -->
      @if (activeTab() === 'TRUST') {
        <div class="flex flex-col gap-5 select-none animate-in fade-in duration-150">
          
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
            <h3 class="text-sm font-bold text-slate-900 font-heading">Cryptographic Digest &amp; Producer Provenance</h3>
            
            <div class="flex flex-col gap-3 text-xs text-slate-700">
              <div class="flex flex-col gap-1 py-2 border-b border-slate-100">
                <span class="text-slate-500 font-medium">Producer Authority:</span>
                <strong class="text-slate-900">{{ cert.integrity.producer_authority }}</strong>
              </div>

              <div class="flex flex-col gap-1 py-2 border-b border-slate-100">
                <span class="text-slate-500 font-medium">Verification Method:</span>
                <strong class="text-slate-900 font-mono">{{ cert.integrity.verification_method }}</strong>
              </div>

              <div class="flex flex-col gap-1 py-2 border-b border-slate-100">
                <span class="text-slate-500 font-medium">Artifact SHA-256 Fingerprint:</span>
                <div class="flex items-center gap-2">
                  <code class="p-2 bg-slate-50 border border-slate-200 rounded-md font-mono text-[11px] text-slate-800 break-all select-all flex-1">
                    {{ cert.integrity.sha256_fingerprint }}
                  </code>
                </div>
              </div>

              <div class="flex items-center justify-between py-2">
                <div class="flex items-center gap-2">
                  <span class="text-slate-500 font-medium">Integrity Verification State:</span>
                  <span 
                    class="px-2 py-0.5 rounded text-[10px] font-bold"
                    [ngClass]="{
                      'bg-emerald-50 text-emerald-700 border border-emerald-200': cert.integrity.verification_status === 'VERIFIED',
                      'bg-rose-50 text-rose-700 border border-rose-200': cert.integrity.verification_status === 'MISMATCH',
                      'bg-slate-100 text-slate-700': cert.integrity.verification_status === 'UNVERIFIED' || cert.integrity.verification_status === 'UNAVAILABLE'
                    }">
                    {{ cert.integrity.verification_status === 'VERIFIED' ? 'Fingerprint Verified' : cert.integrity.verification_status }}
                  </span>
                </div>

                <button
                  (click)="onVerifyIntegrity()"
                  class="h-7 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs transition-colors cursor-pointer shadow-2xs">
                  Run Verification
                </button>
              </div>
            </div>
          </div>

        </div>
      }

      <!-- TAB 6: RELATED REPORTS -->
      @if (activeTab() === 'REPORTS') {
        <div class="flex flex-col gap-5 select-none animate-in fade-in duration-150">
          
          <div class="flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900 font-heading">Linked Technical Reports</h3>
            <p class="text-xs text-slate-500">
              Technical reports in the Report Library associated with this certification domain.
            </p>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Report Identifier</th>
                  <th class="py-3 px-4">Subject</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (repId of cert.related_report_ids; track repId) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono font-semibold text-slate-900">
                      {{ repId }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600 font-medium">
                      {{ cert.subject_name }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <button
                        (click)="onOpenReport(repId)"
                        class="h-7 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center gap-1 cursor-pointer transition-colors shadow-2xs">
                        <span>Open in Report Library</span>
                        <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                      </button>
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
export class CertificationDetailFrameComponent {
  @Input({ required: true }) public cert!: CertificationDetailEnvelopeDTO;

  private rs = inject(ReportsService);
  private router = inject(Router);

  public activeTab = signal<CertificationDetailTab>('OVERVIEW');

  public formatDecision = formatCertificationDecision;
  public formatOutcome = formatCriterionOutcome;

  public onBack(): void {
    this.rs.clearSelectedCertification();
  }

  public onVerifyIntegrity(): void {
    this.rs.verifyArtifactTarget(this.cert.id);
  }

  public onVerifyEvidence(evidenceId: string): void {
    this.rs.verifyArtifactTarget(evidenceId);
  }

  public onOpenReport(reportId: string): void {
    this.router.navigate(['/reports/library'], { queryParams: { reportId } });
  }
}
