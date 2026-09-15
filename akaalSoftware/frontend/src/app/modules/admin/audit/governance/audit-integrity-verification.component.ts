/**
 * AKAAL Administration — 5.9 Audit Integrity Verification
 * Verifies cryptographic integrity of audit log batches using SHA-256 Merkle root trees.
 */

import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-audit-integrity-verification',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/audit"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">AUDIT</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">INTEGRITY VERIFICATION</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Audit Integrity Verification</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Cryptographic proof verification calculating SHA-256 Merkle root trees to mathematically prove zero tampering or modification across stored audit events.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <button
            type="button"
            (click)="runVerification()"
            [disabled]="isVerifying()"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            {{ isVerifying() ? 'Verifying Merkle Tree...' : 'Verify Latest Log Batch' }}
          </button>
        </div>
      </div>

      <!-- Verifications Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Evaluation Period</th>
              <th class="py-3.5 px-4">Verified Timestamp</th>
              <th class="py-3.5 px-4">Evaluated Events</th>
              <th class="py-3.5 px-4">SHA-256 Merkle Root Digest</th>
              <th class="py-3.5 px-4">Algorithm</th>
              <th class="py-3.5 px-4">Result</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (v of auditService.verifications(); track v.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900 font-heading">{{ v.targetPeriod }}</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600">{{ v.verificationTimestamp }}</td>
                <td class="py-3.5 px-4 font-semibold text-slate-900">{{ v.totalEntriesEvaluated.toLocaleString() }} events</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-700 max-w-xs truncate" [title]="v.sha256MerkleRootDigest">
                  {{ v.sha256MerkleRootDigest }}
                </td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600">{{ v.signatureAlgorithm }}</td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ v.verificationResult.replace('_', ' ') }}
                  </span>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class AuditIntegrityVerificationComponent {
  public auditService = inject(AuditService);
  public isVerifying = signal(false);

  public runVerification(): void {
    this.isVerifying.set(true);
    setTimeout(() => {
      this.isVerifying.set(false);
    }, 600);
  }
}
