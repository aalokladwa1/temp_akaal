import { Component, Input, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SecurityComplianceSummary } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-security-compliance',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between gap-6 shadow-xs h-full flex-1 overflow-hidden">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="shield" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Security / Compliance</h2>
        </div>
        <span class="text-xs text-slate-500 font-medium">Posture</span>
      </div>

      <!-- Main Content -->
      @if (!security) {
        <div class="py-8 flex flex-col items-center justify-center text-center gap-2 my-auto">
          <app-lucide-icon name="shield-check" [size]="24" class="text-slate-400"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-800">Security posture unavailable</span>
          <p class="text-[11px] text-slate-500 font-medium">Security subsystem is unconfigured.</p>
        </div>
      } @else {
        <!-- 3 Security Checklist Rows -->
        <div class="flex flex-col divide-y divide-slate-200/80 my-auto">
          
          <div class="py-2.5 first:pt-0 flex items-center justify-between">
            <span class="text-xs text-slate-800 font-medium">mTLS Wire Encryption (TLS 1.3)</span>
            <span 
              class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold select-none"
              [class.bg-emerald-50]="security.mTLSEnabled"
              [class.text-emerald-700]="security.mTLSEnabled"
              [class.border]="security.mTLSEnabled"
              [class.border-emerald-200]="security.mTLSEnabled"
              [class.bg-slate-100]="!security.mTLSEnabled"
              [class.text-slate-700]="!security.mTLSEnabled">
              <span class="w-1.5 h-1.5 rounded-full" [class.bg-emerald-500]="security.mTLSEnabled" [class.bg-slate-400]="!security.mTLSEnabled"></span>
              <span>{{ security.mTLSEnabled ? 'Enforced' : 'Disabled' }}</span>
            </span>
          </div>

          <div class="py-2.5 flex items-center justify-between">
            <span class="text-xs text-slate-800 font-medium">Vault AES-256 Checkpoint Store</span>
            <span 
              class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold select-none"
              [class.bg-emerald-50]="security.vaultEncryption"
              [class.text-emerald-700]="security.vaultEncryption"
              [class.border]="security.vaultEncryption"
              [class.border-emerald-200]="security.vaultEncryption"
              [class.bg-slate-100]="!security.vaultEncryption"
              [class.text-slate-700]="!security.vaultEncryption">
              <span class="w-1.5 h-1.5 rounded-full" [class.bg-emerald-500]="security.vaultEncryption" [class.bg-slate-400]="!security.vaultEncryption"></span>
              <span>{{ security.vaultEncryption ? 'Active' : 'Unencrypted' }}</span>
            </span>
          </div>

          <div class="py-2.5 last:pb-0 flex items-center justify-between">
            <span class="text-xs text-slate-800 font-medium">Immutable Audit Ledger</span>
            <span 
              class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold select-none"
              [class.bg-emerald-50]="security.auditLedgerActive"
              [class.text-emerald-700]="security.auditLedgerActive"
              [class.border]="security.auditLedgerActive"
              [class.border-emerald-200]="security.auditLedgerActive"
              [class.bg-slate-100]="!security.auditLedgerActive"
              [class.text-slate-700]="!security.auditLedgerActive">
              <span class="w-1.5 h-1.5 rounded-full" [class.bg-emerald-500]="security.auditLedgerActive" [class.bg-slate-400]="!security.auditLedgerActive"></span>
              <span>{{ security.auditLedgerActive ? 'Sealed' : 'Inactive' }}</span>
            </span>
          </div>

        </div>

        <!-- Distinct Separated Summary Footer Bar -->
        <div class="flex items-center justify-between text-xs text-slate-600 font-medium border-t border-slate-200 bg-slate-50/70 -mx-7 -mb-7 px-7 py-3 rounded-b-2xl">
          <div class="flex items-center gap-2 truncate max-w-[280px]">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Standard</span>
            <span class="text-xs text-slate-700 font-medium truncate">{{ security.detail }}</span>
          </div>
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 text-[11px] font-semibold select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
            <span>{{ security.posture === 'enforced' ? 'Enforced' : 'Active' }}</span>
          </span>
        </div>
      }

    </div>
  `
})
export class SecurityComplianceComponent {
  @HostBinding('class') public hostClass = 'flex flex-col h-full flex-1';
  @Input() public security: SecurityComplianceSummary | null = null;
}
