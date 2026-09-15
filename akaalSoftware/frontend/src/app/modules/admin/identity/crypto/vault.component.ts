/**
 * AKAAL Administration — Secrets & Vault
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-vault',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity/crypto" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Cryptography & Secrets
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Vault & Secrets Engines</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              HashiCorp Vault cluster integration, KV versioned secrets, dynamic database credentials, and secret leasing.
            </p>
          </div>
        </div>
      </div>

      <!-- Vault Engines List -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div *ngFor="let v of identity.vaultEngines()" class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5">
          <div class="flex flex-col gap-4">
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600">
                  <app-lucide-icon name="lock" [size]="20"></app-lucide-icon>
                </div>
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900 text-sm font-heading">{{ v.engineName }}</span>
                  <span class="text-xs text-slate-500 font-mono">{{ v.engineType }}</span>
                </div>
              </div>
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                {{ v.status }}
              </span>
            </div>

            <div class="flex flex-col gap-2 bg-slate-50/50 p-3 rounded-lg border border-slate-100 text-xs font-mono text-slate-700">
              <div class="flex items-center justify-between">
                <span class="text-slate-400 font-sans">Mount Path:</span>
                <span class="font-bold text-purple-700">{{ v.mountPath }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400 font-sans">Auth Method:</span>
                <span>{{ v.authMethod }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-400 font-sans">Lease TTL:</span>
                <span>{{ v.leaseTtlHours }}h (Max: {{ v.maxLeaseTtlHours }}h)</span>
              </div>
            </div>

            <div class="flex items-center justify-between text-xs text-slate-600 pt-2 border-t border-slate-100">
              <span>Managed Secret Keys: <strong class="text-slate-900">{{ v.managedSecretsCount }}</strong></span>
              <span class="text-[11px] text-slate-400">Last rotated: {{ v.lastRotatedAt }}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  `
})
export class VaultComponent {
  public identity = inject(IdentityService);
}
