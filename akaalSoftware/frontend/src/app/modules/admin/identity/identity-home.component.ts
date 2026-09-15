/**
 * AKAAL Administration — 5.4 Identity & Security Home
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../services/identity.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-identity-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Top Navigation -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Administration
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Identity & Security</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Enterprise authentication, directory federation, zero-trust workload identity, and hardware-backed cryptographic key management.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Zero-Trust Baseline Enforced
            </span>
          </div>
        </div>
      </div>

      <!-- Quick Metrics Ribbon -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">FIDO2 / MFA Enrolled</span>
            <app-lucide-icon name="shield-check" [size]="16" class="text-slate-400"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ identity.mfaConfig().totalEnrolledUsers }}</div>
          <span class="text-[11px] text-emerald-600 font-medium font-mono">{{ identity.mfaConfig().fido2AdoptionRatePercent }}% adoption &bull; All tenants</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Active SSO Providers</span>
            <app-lucide-icon name="key" [size]="16" class="text-slate-400"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ identity.ssoProviders().length }}</div>
          <span class="text-[11px] text-blue-600 font-medium font-mono">OIDC &amp; SAML 2.0 Connected</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Workload Identities</span>
            <app-lucide-icon name="cpu" [size]="16" class="text-slate-400"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ identity.workloadIdentities().length }}</div>
          <span class="text-[11px] text-slate-500 font-medium">SPIFFE &amp; K8s SAs Active</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Crypto Keys &amp; PKI</span>
            <app-lucide-icon name="lock" [size]="16" class="text-slate-400"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ identity.certificates().length + identity.kmsKeys().length }}</div>
          <span class="text-[11px] text-emerald-600 font-medium font-mono">FIPS 140-2 L3 HSM Protected</span>
        </div>
      </div>

      <!-- Core 4 Pillars of 5.4 Identity & Security -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Pillar 1: Authentication -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="key" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">3 Modules</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Authentication & Access Policies</h2>
              <p class="text-xs text-slate-600 mt-1">
                Password complexity policies, session TTL limits, FIDO2/WebAuthn hardware MFA, and enterprise SSO integrations.
              </p>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100">
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">Policies</span>
                <span class="text-xs font-bold text-slate-800">{{ identity.authPolicies().length }} Active</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">MFA Mode</span>
                <span class="text-xs font-bold text-emerald-600">Strict FIDO2</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">SSO</span>
                <span class="text-xs font-bold text-slate-800">{{ identity.ssoProviders().length }} IdPs</span>
              </div>
            </div>
          </div>
          <a
            routerLink="/administration/identity/auth"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage Authentication</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Pillar 2: Directory & Federation -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="network" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">3 Protocols</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Directory & Federation</h2>
              <p class="text-xs text-slate-600 mt-1">
                Active Directory / LDAP synchronization, SCIM 2.0 automated provisioning, and cross-tenant trust contracts.
              </p>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100">
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">LDAP / AD</span>
                <span class="text-xs font-bold text-emerald-600">Connected</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">SCIM 2.0</span>
                <span class="text-xs font-bold text-slate-800">{{ identity.scimEndpoints().length }} Endpoints</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">Federation</span>
                <span class="text-xs font-bold text-slate-800">{{ identity.federationTrusts().length }} Trusts</span>
              </div>
            </div>
          </div>
          <a
            routerLink="/administration/identity/directory"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage Directory & Federation</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Pillar 3: Workload Identity -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="cpu" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">Zero-Trust Non-Human</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Workload & Machine Identity</h2>
              <p class="text-xs text-slate-600 mt-1">
                SPIFFE/SPIRE attestation, Kubernetes projected service accounts, AWS IAM federated role assumptions.
              </p>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100">
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">SPIRE Server</span>
                <span class="text-xs font-bold text-emerald-600">{{ identity.spiffeConfig().status }}</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">Active SVIDs</span>
                <span class="text-xs font-bold text-slate-800">{{ identity.spiffeConfig().activeSvidsCount }}</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">Workloads</span>
                <span class="text-xs font-bold text-slate-800">{{ identity.workloadIdentities().length }} Registered</span>
              </div>
            </div>
          </div>
          <a
            routerLink="/administration/identity/workload"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage Workload Identity</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Pillar 4: Cryptography & Secrets -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="lock" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">HSM & Vault</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Cryptography & Secrets Management</h2>
              <p class="text-xs text-slate-600 mt-1">
                Internal PKI X.509 certificate management, HashiCorp Vault secrets engines, KMS BYOK envelope keys, and rotation rules.
              </p>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100">
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">PKI Certs</span>
                <span class="text-xs font-bold text-slate-800">{{ identity.certificates().length }} Installed</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">Vault Engines</span>
                <span class="text-xs font-bold text-slate-800">{{ identity.vaultEngines().length }} Connected</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[11px] text-slate-500">Auto-Rotation</span>
                <span class="text-xs font-bold text-emerald-600">{{ identity.rotationRules().length }} Active Rules</span>
              </div>
            </div>
          </div>
          <a
            routerLink="/administration/identity/crypto"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage Cryptography & Secrets</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

      </div>
    </div>
  `
})
export class IdentityHomeComponent {
  public identity = inject(IdentityService);
}
