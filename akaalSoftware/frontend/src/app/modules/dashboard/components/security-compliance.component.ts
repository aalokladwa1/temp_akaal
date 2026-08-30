import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SecurityComplianceSummary } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-security-compliance',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200/90 flex flex-col gap-6 shadow-xs h-full">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="shield" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Security / Compliance</h2>
        </div>
        <span class="text-xs text-slate-600 font-semibold">Posture</span>
      </div>

      @if (!security) {
        <div class="py-12 flex flex-col items-center justify-center text-center gap-2">
          <app-lucide-icon name="shield-check" [size]="24" class="text-slate-400"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-800">Security posture data is not currently available</span>
          <p class="text-[11px] text-slate-600 font-medium">Security subsystem unconfigured.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-100">
          
          <div class="py-3.5 first:pt-0 flex items-center justify-between">
            <span class="text-xs text-slate-800 font-medium">mTLS Wire Encryption (TLS 1.3)</span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide bg-emerald-50 text-emerald-700 border border-emerald-200/70">
              {{ security.mTLSEnabled ? 'ENFORCED' : 'DISABLED' }}
            </span>
          </div>

          <div class="py-3.5 flex items-center justify-between">
            <span class="text-xs text-slate-800 font-medium">Vault AES-256 Checkpoint Store</span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide bg-emerald-50 text-emerald-700 border border-emerald-200/70">
              {{ security.vaultEncryption ? 'ACTIVE' : 'UNENCRYPTED' }}
            </span>
          </div>

          <div class="py-3.5 last:pb-0 flex items-center justify-between">
            <span class="text-xs text-slate-800 font-medium">Immutable Audit Ledger</span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide bg-blue-50 text-blue-700 border border-blue-200/70">
              {{ security.auditLedgerActive ? 'SEALED' : 'INACTIVE' }}
            </span>
          </div>

        </div>

        <div class="flex items-center justify-between pt-3 text-xs text-slate-600 font-medium border-t border-slate-100">
          <span>Standard: {{ security.detail }}</span>
          <span class="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/60 text-xs font-bold">
            {{ security.posture | uppercase }}
          </span>
        </div>
      }

    </div>
  `
})
export class SecurityComplianceComponent {
  @Input() public security: SecurityComplianceSummary | null = null;
}
