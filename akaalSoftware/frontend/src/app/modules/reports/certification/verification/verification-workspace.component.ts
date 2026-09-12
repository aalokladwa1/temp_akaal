import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ReportsService } from '../../services/reports.service';
import { VerificationResultDTO } from '../../models/certification.models';

@Component({
  selector: 'app-verification-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="flex flex-col gap-6 w-full select-none animate-in fade-in duration-150">
      
      <!-- Workspace Header -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div class="flex flex-col">
          <h2 class="text-lg font-bold text-slate-900 font-heading">
            Verification Console
          </h2>
          <p class="text-xs text-slate-500">
            Cryptographic SHA-256 fingerprint matching and artifact integrity verification.
          </p>
        </div>
      </div>

      <!-- Verification Input Console -->
      <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4 max-w-3xl">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-bold text-slate-800 font-heading">Target Certification or Evidence Identifier</label>
          <span class="text-[11px] text-slate-500">Enter a certification ID or evidence artifact identifier to verify its stored digest against canonical computation.</span>
        </div>

        <div class="flex items-center gap-3 flex-wrap">
          <input
            type="text"
            [(ngModel)]="targetInput"
            placeholder="e.g. CERT-MIG-2026-001, EV-2026-VAL-01"
            class="flex-1 min-w-[280px] h-9 px-3 text-xs font-mono rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
          />

          <button
            (click)="onRunVerification()"
            [disabled]="!targetInput.trim() || isVerifying()"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:pointer-events-none text-white font-semibold text-xs transition-colors cursor-pointer shadow-2xs">
            {{ isVerifying() ? 'Verifying...' : 'Verify Fingerprint' }}
          </button>
        </div>

        <!-- Quick Select Helper -->
        <div class="flex items-center gap-2 text-xs text-slate-500 flex-wrap pt-1">
          <span class="font-medium text-[11px]">Quick Select:</span>
          @for (cert of rs.allCertifications().slice(0, 4); track cert.id) {
            <button
              (click)="targetInput = cert.id; onRunVerification()"
              class="px-2 py-0.5 rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-mono text-[11px] cursor-pointer transition-colors">
              {{ cert.id }}
            </button>
          }
        </div>
      </div>

      <!-- Verification Result Section -->
      @if (activeResult(); as res) {
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-5 max-w-3xl animate-in fade-in duration-150">
          
          <div class="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-slate-100">
            <div class="flex flex-col gap-0.5">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Verification Result</span>
              <h3 class="text-base font-bold text-slate-900 font-heading font-mono">{{ res.target_identifier }}</h3>
            </div>

            <span 
              class="px-3 py-1 rounded-md text-xs font-bold"
              [ngClass]="{
                'bg-emerald-50 text-emerald-700 border border-emerald-200': res.result_status === 'VERIFIED',
                'bg-rose-50 text-rose-700 border border-rose-200': res.result_status === 'MISMATCH',
                'bg-slate-100 text-slate-700': res.result_status === 'UNAVAILABLE' || res.result_status === 'ERROR'
              }">
              {{ res.result_status === 'VERIFIED' ? 'Fingerprint Verified' : (res.result_status === 'MISMATCH' ? 'Fingerprint Mismatch' : 'Verification Unavailable') }}
            </span>
          </div>

          <!-- Result Details -->
          <div class="flex flex-col gap-3 text-xs text-slate-700">
            <div class="flex justify-between py-1 border-b border-slate-100">
              <span class="text-slate-500 font-medium">Verification Method:</span>
              <strong class="font-mono text-slate-900">{{ res.method }}</strong>
            </div>

            <div class="flex justify-between py-1 border-b border-slate-100">
              <span class="text-slate-500 font-medium">Verified Timestamp:</span>
              <span class="font-mono text-slate-700">{{ res.verified_at | date:'yyyy-MM-dd HH:mm:ss UTC' }}</span>
            </div>

            @if (res.stored_fingerprint) {
              <div class="flex flex-col gap-1 py-1">
                <span class="text-slate-500 font-medium">Stored Canonical Fingerprint:</span>
                <code class="p-2 bg-slate-50 border border-slate-200 rounded-md font-mono text-[11px] text-slate-800 break-all select-all">
                  {{ res.stored_fingerprint }}
                </code>
              </div>
            }

            @if (res.computed_fingerprint) {
              <div class="flex flex-col gap-1 py-1">
                <span class="text-slate-500 font-medium">Observed Computed Fingerprint:</span>
                <code class="p-2 bg-slate-50 border border-slate-200 rounded-md font-mono text-[11px] text-slate-800 break-all select-all">
                  {{ res.computed_fingerprint }}
                </code>
              </div>
            }

            <div class="pt-2 border-t border-slate-100">
              <span class="text-slate-500 font-medium block mb-1">Observation Notes:</span>
              <p class="text-xs text-slate-700 leading-relaxed">{{ res.detail_notes }}</p>
            </div>
          </div>

        </div>
      }

    </div>
  `
})
export class VerificationWorkspaceComponent implements OnInit {
  public rs = inject(ReportsService);
  private route = inject(ActivatedRoute);

  public targetInput = '';
  public isVerifying = signal<boolean>(false);

  public activeResult = this.rs.activeVerificationResult;

  public ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if (params['verifyTarget']) {
        this.targetInput = params['verifyTarget'];
        this.onRunVerification();
      }
    });
  }

  public onRunVerification(): void {
    const id = this.targetInput.trim();
    if (!id) return;
    this.isVerifying.set(true);
    setTimeout(() => {
      this.rs.verifyArtifactTarget(id);
      this.isVerifying.set(false);
    }, 250);
  }
}
