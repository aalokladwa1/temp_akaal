/**
 * AKAAL Administration — Single Sign-On (SSO) Home
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-sso-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity/auth" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Authentication
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Single Sign-On (SSO)</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Federate authentication with enterprise identity providers via OIDC and SAML 2.0 with JIT account provisioning.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              routerLink="/administration/identity/auth/sso/create"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs">
              Add Identity Provider
            </a>
          </div>
        </div>
      </div>

      <!-- IdP Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div *ngFor="let sso of identity.ssoProviders()" class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5">
          <div class="flex flex-col gap-4">
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center font-bold text-slate-700 font-heading">
                  {{ sso.protocol === 'OIDC' ? 'OIDC' : 'SAML' }}
                </div>
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900 text-sm font-heading">{{ sso.name }}</span>
                  <span class="text-xs text-slate-500">{{ sso.providerType }}</span>
                </div>
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {{ sso.status }}
              </span>
            </div>

            <div class="flex flex-col gap-2 bg-slate-50/50 p-3 rounded-lg border border-slate-100 text-xs font-mono text-slate-700">
              <div class="flex items-center justify-between truncate">
                <span class="text-slate-400 font-sans">Issuer / EntityID:</span>
                <span class="truncate max-w-[280px]">{{ sso.entityIdOrIssuer }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400 font-sans">Client ID / SP:</span>
                <span>{{ sso.clientId }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400 font-sans">JIT Provisioning:</span>
                <span class="font-sans font-semibold" [ngClass]="sso.jitProvisioningEnabled ? 'text-emerald-600' : 'text-slate-500'">
                  {{ sso.jitProvisioningEnabled ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>

            <div class="flex items-center justify-between text-xs text-slate-600 pt-2 border-t border-slate-100">
              <span>Active Authenticated Users: <strong class="text-slate-900">{{ sso.activeUsersCount }}</strong></span>
              <span class="text-[11px] text-slate-400">Last activity: {{ sso.lastAuthEvent }}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  `
})
export class SsoHomeComponent {
  public identity = inject(IdentityService);
}
