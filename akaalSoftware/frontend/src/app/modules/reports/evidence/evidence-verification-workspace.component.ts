import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReportsService } from '../services/reports.service';

@Component({
  selector: 'app-evidence-verification-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="flex flex-col gap-6 w-full animate-in fade-in duration-150">
      
      <!-- Section Title -->
      <div>
        <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Integrity Verification Console</h2>
        <p class="text-xs text-slate-500 mt-0.5">
          SHA-256 fingerprint matching and digest verification for evidence proofs, certificates, and packages.
        </p>
      </div>

      <!-- Verification Input Card -->
      <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <label for="evidence-verification-target" class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Target Artifact Identifier</label>
          <p class="text-xs text-slate-500">
            Enter an Evidence ID, Certificate ID, or Package ID to verify its stored digest against canonical computation.
          </p>
        </div>

        <div class="flex items-center gap-3 flex-wrap">
          <input
            id="evidence-verification-target"
            type="text"
            [(ngModel)]="targetInput"
            placeholder="e.g. EV-2026-MIG-01, CERT-MIG-2026-001, PKG-2026-001"
            class="flex-1 min-w-[280px] px-3.5 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-slate-50 hover:bg-white transition-colors font-mono" />

          <button
            (click)="onVerify()"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
            Verify Fingerprint
          </button>
        </div>

        <!-- Quick Select Pills -->
        <div class="flex items-center gap-2 pt-2 border-t border-slate-100 flex-wrap text-xs text-slate-500">
          <span class="font-medium text-slate-400">Quick Select:</span>
          @for (id of quickTargets; track id) {
            <button
              (click)="targetInput = id; onVerify()"
              class="px-2.5 py-1 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-mono text-[11px] cursor-pointer transition-colors">
              {{ id }}
            </button>
          }
        </div>
      </div>

      <!-- Verification Result Display -->
      @if (service.activeVerificationResult(); as res) {
        <div class="p-6 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-4 animate-in fade-in duration-150">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Verification Result</span>
            <div>
              @if (res.result_status === 'VERIFIED') {
                <span class="text-emerald-700 font-semibold text-xs inline-flex items-center gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span>Fingerprint Verified</span>
                </span>
              } @else if (res.result_status === 'MISMATCH') {
                <span class="text-rose-700 font-semibold text-xs inline-flex items-center gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                  <span>Fingerprint Mismatch</span>
                </span>
              } @else {
                <span class="text-slate-500 font-semibold text-xs inline-flex items-center gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                  <span>Verification Unavailable</span>
                </span>
              }
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            <div class="flex flex-col gap-0.5">
              <span class="text-slate-400 font-medium">Target Identifier</span>
              <span class="font-mono font-semibold text-slate-800">{{ res.target_identifier }}</span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-slate-400 font-medium">Method</span>
              <span class="font-semibold text-slate-800">{{ res.method }}</span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-slate-400 font-medium">Verified Timestamp</span>
              <span class="font-semibold text-slate-800">{{ res.verified_at | date:'yyyy-MM-dd HH:mm:ss' }}</span>
            </div>
          </div>

          @if (res.stored_fingerprint) {
            <div class="flex flex-col gap-1 pt-2 border-t border-slate-100 text-xs">
              <span class="text-slate-400 font-medium">Stored SHA-256 Digest</span>
              <span class="font-mono text-slate-700 bg-slate-50 p-2 rounded-lg border border-slate-200 select-all">
                {{ res.stored_fingerprint }}
              </span>
            </div>
          }

          <div class="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100 leading-relaxed">
            {{ res.detail_notes }}
          </div>
        </div>
      }

      <!-- Historical Verification Activity Table -->
      <div class="flex flex-col gap-3">
        <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
          Recent Verification Activity ({{ service.verificationHistory().length }})
        </h3>

        <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
                <th class="py-3 px-4">Target Identifier</th>
                <th class="py-3 px-4">Target Type</th>
                <th class="py-3 px-4">Method</th>
                <th class="py-3 px-4">Verified At</th>
                <th class="py-3 px-4">Result</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              @for (item of service.verificationHistory(); track item.target_identifier + item.verified_at) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3 px-4 font-mono font-semibold text-slate-900">
                    {{ item.target_identifier }}
                  </td>
                  <td class="py-3 px-4 text-slate-600">
                    {{ item.target_type }}
                  </td>
                  <td class="py-3 px-4 text-slate-500">
                    {{ item.method }}
                  </td>
                  <td class="py-3 px-4 text-slate-500 whitespace-nowrap">
                    {{ item.verified_at | date:'yyyy-MM-dd HH:mm:ss' }}
                  </td>
                  <td class="py-3 px-4">
                    @if (item.result_status === 'VERIFIED') {
                      <span class="text-emerald-700 font-medium inline-flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        <span>Fingerprint Verified</span>
                      </span>
                    } @else if (item.result_status === 'MISMATCH') {
                      <span class="text-rose-700 font-medium inline-flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                        <span>Mismatch</span>
                      </span>
                    } @else {
                      <span class="text-slate-500 font-medium">Unavailable</span>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class EvidenceVerificationWorkspaceComponent {
  public service = inject(ReportsService);
  public targetInput = '';
  public quickTargets = [
    'EV-2026-MIG-01',
    'EV-2026-VAL-01',
    'CERT-MIG-2026-001',
    'PKG-2026-001'
  ];

  public onVerify(): void {
    if (this.targetInput.trim()) {
      this.service.verifyArtifactTarget(this.targetInput.trim());
    }
  }
}
