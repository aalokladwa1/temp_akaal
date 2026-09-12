import { Component, Input, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ReportsService } from '../services/reports.service';
import { EvidenceDetailEnvelopeDTO, formatEvidenceType } from '../models/evidence.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

export type EvidenceDetailTab = 'OVERVIEW' | 'SCOPE' | 'PROVENANCE' | 'INTEGRITY' | 'RELATED';

@Component({
  selector: 'app-evidence-detail-frame',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full animate-in fade-in duration-150" *ngIf="envelope">
      
      <!-- Top Header & Contextual Actions -->
      <div class="flex items-start justify-between gap-6 pb-4 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center gap-2">
            <button
              (click)="service.clearSelectedEvidence()"
              class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 cursor-pointer transition-colors">
              <app-lucide-icon name="arrow-left" [size]="12"></app-lucide-icon>
              <span>Back to Evidence</span>
            </button>
            <span class="text-slate-300">•</span>
            <span class="text-xs font-medium text-slate-500 uppercase tracking-wider">{{ formatType(envelope.artifact_type) }}</span>
          </div>

          <!-- Human-Readable Identity First -->
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">
            {{ envelope.title }}
          </h1>

          <div class="flex items-center gap-3 text-xs text-slate-500 flex-wrap">
            <span>Subject: <strong class="text-slate-700">{{ envelope.subject_name }}</strong></span>
            <span>•</span>
            <span>Authority: <strong class="text-slate-700">{{ envelope.producer_authority }}</strong></span>
            <span>•</span>
            <span>Created: {{ envelope.created_at | date:'yyyy-MM-dd HH:mm' }}</span>
          </div>
        </div>

        <div class="flex items-center gap-3 pt-1">
          <button
            (click)="service.verifyArtifactTarget(envelope.id)"
            class="h-9 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
            Verify Digest
          </button>

          <button
            (click)="service.downloadEvidenceArtifact(envelope.id)"
            class="h-9 px-3.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
            Download Proof
          </button>
        </div>
      </div>

      <!-- Local Navigation Tabs -->
      <div class="flex items-center gap-6 border-b border-slate-200 -mt-2 overflow-x-auto">
        <button
          (click)="activeTab.set('OVERVIEW')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
          [ngClass]="activeTab() === 'OVERVIEW' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Overview
        </button>

        @if (envelope.scope) {
          <button
            (click)="activeTab.set('SCOPE')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="activeTab() === 'SCOPE' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Scope &amp; Context
          </button>
        }

        @if (envelope.provenance) {
          <button
            (click)="activeTab.set('PROVENANCE')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="activeTab() === 'PROVENANCE' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Provenance
          </button>
        }

        @if (envelope.integrity) {
          <button
            (click)="activeTab.set('INTEGRITY')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="activeTab() === 'INTEGRITY' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Trust &amp; Integrity
          </button>
        }

        <button
          (click)="activeTab.set('RELATED')"
          class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
          [ngClass]="activeTab() === 'RELATED' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
          Related Artifacts
        </button>
      </div>

      <!-- TAB 1: OVERVIEW -->
      @if (activeTab() === 'OVERVIEW') {
        <div class="flex flex-col gap-6">
          <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-3">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Evidence Purpose &amp; Summary</h2>
            <p class="text-xs text-slate-600 leading-relaxed">
              {{ envelope.summary }}
            </p>
          </div>

          <!-- Secondary Technical Metadata -->
          <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-4">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Artifact Metadata</h2>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Evidence ID</span>
                <span class="font-mono text-slate-800 font-semibold">{{ envelope.id }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Artifact Type</span>
                <span class="text-slate-800 font-semibold">{{ formatType(envelope.artifact_type) }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Producer Authority</span>
                <span class="text-slate-800 font-semibold">{{ envelope.producer_authority }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Recorded Date</span>
                <span class="text-slate-800 font-semibold">{{ envelope.created_at | date:'yyyy-MM-dd HH:mm:ss' }}</span>
              </div>
            </div>
          </div>

          <!-- Raw Content Preview if available -->
          @if (envelope.raw_content_preview) {
            <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-3">
              <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Raw Artifact Preview</h2>
              <pre class="p-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 font-mono text-[11px] overflow-x-auto leading-relaxed shadow-2xs">{{ envelope.raw_content_preview }}</pre>
            </div>
          }
        </div>
      }

      <!-- TAB 2: SCOPE & CONTEXT -->
      @else if (activeTab() === 'SCOPE' && envelope.scope) {
        <div class="flex flex-col gap-6">
          <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-4">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Operational Scope &amp; Bindings</h2>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 text-xs">
              @if (envelope.scope.tenant) {
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-400 font-medium">Tenant</span>
                  <span class="font-semibold text-slate-800">{{ envelope.scope.tenant }}</span>
                </div>
              }
              @if (envelope.scope.workspace) {
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-400 font-medium">Workspace</span>
                  <span class="font-semibold text-slate-800">{{ envelope.scope.workspace }}</span>
                </div>
              }
              @if (envelope.scope.project_name) {
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-400 font-medium">Project</span>
                  <span class="font-semibold text-slate-800">{{ envelope.scope.project_name }}</span>
                </div>
              }
              @if (envelope.scope.migration_name) {
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-400 font-medium">Migration Binding</span>
                  <span class="font-semibold text-slate-800">{{ envelope.scope.migration_name }}</span>
                </div>
              }
              @if (envelope.scope.validation_name) {
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-400 font-medium">Validation Binding</span>
                  <span class="font-semibold text-slate-800">{{ envelope.scope.validation_name }}</span>
                </div>
              }
              @if (envelope.scope.run_id) {
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-400 font-medium">Execution Run ID</span>
                  <span class="font-mono font-semibold text-slate-800">{{ envelope.scope.run_id }}</span>
                </div>
              }
              @if (envelope.scope.time_window_start) {
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-400 font-medium">Time Window</span>
                  <span class="font-semibold text-slate-800">
                    {{ envelope.scope.time_window_start | date:'yyyy-MM-dd HH:mm' }}
                    @if (envelope.scope.time_window_end) {
                      → {{ envelope.scope.time_window_end | date:'HH:mm' }}
                    }
                  </span>
                </div>
              }
              @if (envelope.scope.target_object_scope) {
                <div class="flex flex-col gap-0.5 col-span-full">
                  <span class="text-slate-400 font-medium">Target Object Scope</span>
                  <span class="font-semibold text-slate-800">{{ envelope.scope.target_object_scope }}</span>
                </div>
              }
            </div>
          </div>
        </div>
      }

      <!-- TAB 3: PROVENANCE -->
      @else if (activeTab() === 'PROVENANCE' && envelope.provenance) {
        <div class="flex flex-col gap-6">
          <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-4">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Generation Provenance</h2>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-5 text-xs">
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Producer Authority</span>
                <span class="font-semibold text-slate-800">{{ envelope.provenance.producer_authority }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Created Timestamp</span>
                <span class="font-semibold text-slate-800">{{ envelope.provenance.created_at | date:'yyyy-MM-dd HH:mm:ss' }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Subject Context</span>
                <span class="font-semibold text-slate-800">{{ envelope.provenance.subject_context }}</span>
              </div>
              @if (envelope.provenance.run_or_plan_binding) {
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-400 font-medium">Execution / Plan Binding</span>
                  <span class="font-mono font-semibold text-slate-800">{{ envelope.provenance.run_or_plan_binding }}</span>
                </div>
              }
            </div>

            @if (envelope.provenance.canonical_reference) {
              <div class="flex flex-col gap-1 pt-3 border-t border-slate-100 text-xs">
                <span class="text-slate-400 font-medium">Canonical Storage Reference</span>
                <span class="font-mono text-slate-700 bg-slate-50 p-2 rounded-lg border border-slate-200">{{ envelope.provenance.canonical_reference }}</span>
              </div>
            }
          </div>
        </div>
      }

      <!-- TAB 4: TRUST & INTEGRITY -->
      @else if (activeTab() === 'INTEGRITY' && envelope.integrity) {
        <div class="flex flex-col gap-6">
          <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-5">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
              <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Integrity &amp; Digest Verification</h2>
              <div>
                @if (envelope.integrity.verification_status === 'VERIFIED') {
                  <span class="text-emerald-700 font-semibold text-xs inline-flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    <span>Fingerprint Verified</span>
                  </span>
                } @else if (envelope.integrity.verification_status === 'MISMATCH') {
                  <span class="text-rose-700 font-semibold text-xs inline-flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                    <span>Fingerprint Mismatch</span>
                  </span>
                } @else {
                  <span class="text-slate-500 font-semibold text-xs">Verification Not Recorded</span>
                }
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Algorithm</span>
                <span class="font-semibold text-slate-800">{{ envelope.integrity.fingerprint_algorithm || 'SHA-256' }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Verification Method</span>
                <span class="font-semibold text-slate-800">{{ envelope.integrity.verification_method || 'SHA-256 Digest Match' }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Verified Timestamp</span>
                <span class="font-semibold text-slate-800">{{ (envelope.integrity.verified_at | date:'yyyy-MM-dd HH:mm:ss') || 'Not verified' }}</span>
              </div>
            </div>

            @if (envelope.integrity.fingerprint) {
              <div class="flex flex-col gap-1 pt-3 border-t border-slate-100">
                <span class="text-xs text-slate-400 font-medium">SHA-256 Digest Fingerprint</span>
                <span class="font-mono text-xs text-slate-700 select-all bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  {{ envelope.integrity.fingerprint }}
                </span>
              </div>
            }

            @if (envelope.integrity.merkle_root) {
              <div class="flex flex-col gap-1 pt-2">
                <span class="text-xs text-slate-400 font-medium">Merkle Tree Root Digest</span>
                <span class="font-mono text-xs text-slate-700 select-all bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  {{ envelope.integrity.merkle_root }}
                </span>
              </div>
            }
          </div>
        </div>
      }

      <!-- TAB 5: RELATED ARTIFACTS -->
      @else if (activeTab() === 'RELATED') {
        <div class="flex flex-col gap-6">
          <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-4">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Associated Reports &amp; Certifications</h2>
            
            <div class="divide-y divide-slate-100 text-xs">
              @if (envelope.related_report_ids && envelope.related_report_ids.length > 0) {
                @for (repId of envelope.related_report_ids; track repId) {
                  <div class="py-3 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <span class="font-mono text-slate-400 font-medium">{{ repId }}</span>
                      <span class="text-slate-700 font-medium">Associated Report Document</span>
                    </div>
                    <a
                      [routerLink]="['/reports/library']"
                      [queryParams]="{ reportId: repId }"
                      class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer">
                      <span>Open Report</span>
                      <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                    </a>
                  </div>
                }
              }

              @if (envelope.related_certificate_ids && envelope.related_certificate_ids.length > 0) {
                @for (certId of envelope.related_certificate_ids; track certId) {
                  <div class="py-3 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <span class="font-mono text-slate-400 font-medium">{{ certId }}</span>
                      <span class="text-slate-700 font-medium">Associated Certification Assertion</span>
                    </div>
                    <a
                      [routerLink]="['/reports/certification']"
                      [queryParams]="{ certId: certId }"
                      class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer">
                      <span>Open Certification</span>
                      <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                    </a>
                  </div>
                }
              }

              @if (envelope.related_dossier_ids && envelope.related_dossier_ids.length > 0) {
                @for (dossierId of envelope.related_dossier_ids; track dossierId) {
                  <div class="py-3 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <span class="font-mono text-slate-400 font-medium">{{ dossierId }}</span>
                      <span class="text-slate-700 font-medium">Parent Evidence Dossier</span>
                    </div>
                    <button
                      (click)="service.selectDossier(dossierId)"
                      class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer">
                      <span>Inspect Dossier</span>
                      <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                    </button>
                  </div>
                }
              }

              @if (!envelope.related_report_ids?.length && !envelope.related_certificate_ids?.length && !envelope.related_dossier_ids?.length) {
                <p class="text-xs text-slate-500 py-2">
                  No directly linked reports or certificates recorded for this evidence artifact.
                </p>
              }
            </div>
          </div>
        </div>
      }

    </div>
  `
})
export class EvidenceDetailFrameComponent {
  @Input() public envelope!: EvidenceDetailEnvelopeDTO;
  public service = inject(ReportsService);
  public activeTab = signal<EvidenceDetailTab>('OVERVIEW');

  public formatType(type: string): string {
    return formatEvidenceType(type);
  }
}
