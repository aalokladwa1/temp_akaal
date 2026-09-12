/**
 * AKAAL Administration — Cryptography & Secrets Hub
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-crypto-home',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Cryptography & Secrets Management</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Internal PKI certificate authorities, HashiCorp Vault secrets engines, KMS BYOK master keys, and automated credential rotation.
            </p>
          </div>
        </div>
      </div>

      <!-- Feature Cards Grid (4 modules) -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        <!-- Certificates / PKI -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="award" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-blue-600 font-mono">{{ identity.certificates().length }} CERTS</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Certificates & PKI</h2>
              <p class="text-xs text-slate-600 mt-1">
                Internal Certificate Authorities, X.509 server TLS and client mTLS certificate inventory.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/crypto/certificates"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage PKI</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Secrets & Vault -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="lock" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-slate-700 font-mono">{{ identity.vaultEngines().length }} ENGINES</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Vault & Secrets Engines</h2>
              <p class="text-xs text-slate-600 mt-1">
                HashiCorp Vault cluster integration, KV versioned secrets, and dynamic database credentials.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/crypto/vault"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage Vault</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- KMS / CMK / BYOK -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="key" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-slate-700 font-mono">{{ identity.kmsKeys().length }} MASTER KEYS</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">KMS / CMK / BYOK</h2>
              <p class="text-xs text-slate-600 mt-1">
                Customer Managed Keys, FIPS 140-2 Level 3 HSM hardware module backing, and envelope wrapping.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/crypto/kms"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage KMS</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Secret Rotation -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="refresh-cw" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-slate-700 font-mono">{{ identity.rotationRules().length }} RULES</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Automated Rotation</h2>
              <p class="text-xs text-slate-600 mt-1">
                Periodic zero-downtime rotation schedules for DB passwords, API tokens, and master wrapping keys.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/crypto/rotation"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage Rotation</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

      </div>
    </div>
  `
})
export class CryptoHomeComponent {
  public identity = inject(IdentityService);
}
