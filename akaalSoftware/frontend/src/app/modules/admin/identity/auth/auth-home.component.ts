/**
 * AKAAL Administration — 5.4 Authentication Hub
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-auth-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Identity & Security
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Authentication Management</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Configure baseline authentication security parameters, multi-factor authentication (MFA), and Single Sign-On (SSO) identity providers.
            </p>
          </div>
        </div>
      </div>

      <!-- Authentication Feature Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <!-- Feature 1: Auth Policies -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="shield" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-blue-600 font-mono">{{ identity.authPolicies().length }} POLICIES</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Authentication Policies</h2>
              <p class="text-xs text-slate-600 mt-1">
                Password complexity thresholds, lockout durations, session idle timeouts, and IP fencing rules.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/auth/policies"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Configure Policies</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Feature 2: MFA Configuration -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="smartphone" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-slate-700 font-mono">{{ identity.mfaConfig().fido2AdoptionRatePercent }}% FIDO2</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Multi-Factor Authentication (MFA)</h2>
              <p class="text-xs text-slate-600 mt-1">
                FIDO2 / WebAuthn hardware security keys, TOTP authenticator apps, and step-up challenge thresholds.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/auth/mfa"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Configure MFA</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Feature 3: SSO Providers -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="globe" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-slate-700 font-mono">{{ identity.ssoProviders().length }} IDPS</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Single Sign-On (SSO)</h2>
              <p class="text-xs text-slate-600 mt-1">
                OpenID Connect (OIDC) and SAML 2.0 federation with Microsoft Entra ID, Okta, and PingIdentity.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/auth/sso"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Configure SSO</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

      </div>
    </div>
  `
})
export class AuthHomeComponent {
  public identity = inject(IdentityService);
}
