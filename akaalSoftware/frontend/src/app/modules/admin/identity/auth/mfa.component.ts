/**
 * AKAAL Administration — MFA Configuration
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-mfa',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity/auth" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Authentication
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Multi-Factor Authentication (MFA)</h1>
            <p class="text-sm font-medium text-slate-600">
              Configure hardware-backed FIDO2 / WebAuthn token enforcement, TOTP authenticator methods, and device trust caching.
            </p>
          </div>
        </div>
      </div>

      <!-- Adoption Metrics Callout -->
      <div class="grid grid-cols-3 gap-4 bg-blue-50/40 border border-blue-100 rounded-xl p-4">
        <div class="flex flex-col gap-0.5">
          <span class="text-[11px] font-bold text-blue-700 uppercase tracking-wider font-heading">Enrolled Users</span>
          <span class="text-xl font-bold text-slate-900">{{ config.totalEnrolledUsers }}</span>
        </div>
        <div class="flex flex-col gap-0.5">
          <span class="text-[11px] font-bold text-blue-700 uppercase tracking-wider font-heading">Hardware Keys (Yubikey)</span>
          <span class="text-xl font-bold text-slate-900">{{ config.totalHardwareKeysRegistered }}</span>
        </div>
        <div class="flex flex-col gap-0.5">
          <span class="text-[11px] font-bold text-blue-700 uppercase tracking-wider font-heading">FIDO2 Adoption</span>
          <span class="text-xl font-bold text-emerald-600">{{ config.fido2AdoptionRatePercent }}%</span>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <h2 class="text-sm font-bold text-slate-900 font-heading">Permitted Verification Factors</h2>

        <div class="flex flex-col gap-4">
          <label class="flex items-start gap-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50/60 cursor-pointer transition-colors">
            <input type="checkbox" [(ngModel)]="config.enforceFido2WebAuthn" class="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900 font-heading">FIDO2 / WebAuthn Biometrics & Security Keys</span>
              <span class="text-[11px] text-slate-600">Phishing-resistant passkeys, TouchID, Windows Hello, and YubiKey NFC/USB authenticators.</span>
            </div>
          </label>

          <label class="flex items-start gap-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50/60 cursor-pointer transition-colors">
            <input type="checkbox" [(ngModel)]="config.enforceTotp" class="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900 font-heading">Time-based One-Time Password (TOTP App)</span>
              <span class="text-[11px] text-slate-600">Standard RFC 6238 6-digit dynamic codes (Google Authenticator, 1Password, Duo).</span>
            </div>
          </label>

          <label class="flex items-start gap-3 p-3.5 rounded-lg border border-slate-200 hover:bg-slate-50/60 cursor-pointer transition-colors">
            <input type="checkbox" [(ngModel)]="config.allowHardwareSecurityKeys" class="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900 font-heading">Hardware Security Token Dedicated Registration</span>
              <span class="text-[11px] text-slate-600">Requires physical presence PIN confirmation for elevated sessions.</span>
            </div>
          </label>

          <div class="p-3.5 rounded-lg border border-amber-200 bg-amber-50/50 flex flex-col gap-2">
            <span class="text-xs font-bold text-amber-800 font-heading">Legacy Insecure Factors (Deprecated)</span>
            <div class="flex items-center gap-6">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" [(ngModel)]="config.allowSmsOtpWithWarning" class="rounded border-slate-300 text-amber-600 focus:ring-amber-500" />
                <span class="text-xs text-amber-900 font-medium">Allow SMS OTP</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" [(ngModel)]="config.allowEmailOtpWithWarning" class="rounded border-slate-300 text-amber-600 focus:ring-amber-500" />
                <span class="text-xs text-amber-900 font-medium">Allow Email OTP</span>
              </label>
            </div>
            <span class="text-[11px] text-amber-700">SMS and Email OTP are susceptible to SIM-swapping and relay attacks. Disabled by default in high-compliance tiers.</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Remember Device</label>
            <input
              type="number"
              [(ngModel)]="config.rememberDeviceDays"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
            <span class="text-[10px] text-slate-500">Days before re-challenge</span>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Enrollment Grace</label>
            <input
              type="number"
              [(ngModel)]="config.gracePeriodDays"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
            <span class="text-[10px] text-slate-500">Days allowed to setup MFA</span>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Backup Codes</label>
            <input
              type="number"
              [(ngModel)]="config.backupCodesCount"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
            <span class="text-[10px] text-slate-500">One-time emergency codes</span>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <button
            (click)="saveMfa()"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs cursor-pointer">
            Save MFA Configuration
          </button>
        </div>
      </div>
    </div>
  `
})
export class MfaComponent {
  public identity = inject(IdentityService);
  public config = { ...this.identity.mfaConfig() };

  public saveMfa(): void {
    this.identity.updateMfaConfig(this.config);
  }
}
