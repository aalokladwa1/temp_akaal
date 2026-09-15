/**
 * AKAAL Administration — 5.8 Compliance Evidence Detail View
 */

import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { ComplianceEvidence } from '../../models/compliance.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-compliance-evidence-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/compliance/evidence"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back to Evidence</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">EVIDENCE RECORD</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-mono font-bold text-blue-600">{{ evidence()?.id || 'RECORD' }}</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">
            {{ evidence()?.title || 'Evidence Detail' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Cryptographic proof artifact captured from {{ evidence()?.originSystem }}.
          </p>
        </div>
      </div>

      <!-- Detail Card -->
      @if (evidence(); as ev) {
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-6">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Evidence Type</span>
              <span class="text-xs font-mono font-semibold text-slate-900">{{ ev.evidenceType }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Associated Control</span>
              <span class="text-xs font-mono font-bold text-blue-600">{{ ev.relatedControlCode }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Collection Timestamp</span>
              <span class="text-xs font-semibold text-slate-900">{{ ev.collectedAt }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Digest Verification Status</span>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 w-fit">
                {{ ev.verificationStatus.replace('_', ' ') }}
              </span>
            </div>
          </div>

          <div class="border-t border-slate-200 pt-5 flex flex-col gap-2">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">SHA-256 Digest Fingerprint</span>
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 break-all select-all">
              {{ ev.sha256Digest }}
            </div>
            <span class="text-[11px] text-slate-500 italic mt-1">
              Note: SHA-256 digest validation verifies cryptographic payload integrity against origin emission; it does not constitute an external notary or PKI certificate signature.
            </span>
          </div>
        </div>
      }
    </div>
  `
})
export class ComplianceEvidenceDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private complianceService = inject(ComplianceService);

  public evidence = signal<ComplianceEvidence | undefined>(undefined);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.evidence.set(this.complianceService.getEvidenceById(id));
    }
  }
}
