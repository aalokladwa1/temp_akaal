/**
 * AKAAL Administration — SPIFFE / SPIRE Configuration
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-spiffe',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity/workload" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Workload Identity
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">SPIFFE / SPIRE Infrastructure</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              SPIFFE-compliant software identity issuance, SPIRE server clustering, and mutual TLS attestation plugins.
            </p>
          </div>
        </div>
      </div>

      <!-- Spire Server Status Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-6">
        <div class="flex items-start justify-between gap-4 flex-wrap pb-4 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
              <app-lucide-icon name="shield-check" [size]="20"></app-lucide-icon>
            </div>
            <div class="flex flex-col">
              <span class="font-bold text-slate-900 text-base font-heading">SPIRE Server Cluster — {{ cfg.trustDomain }}</span>
              <span class="text-xs text-slate-500 font-mono">{{ cfg.spireServerEndpoint }}</span>
            </div>
          </div>

          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            {{ cfg.status }}
          </span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div class="bg-slate-50/60 p-3.5 rounded-lg border border-slate-100 flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 font-heading">CA KEY ALGORITHM</span>
            <span class="text-slate-800 font-semibold">{{ cfg.caKeyAlgorithm }}</span>
          </div>

          <div class="bg-slate-50/60 p-3.5 rounded-lg border border-slate-100 flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 font-heading">SVID DEFAULT TTL</span>
            <span class="text-slate-800 font-semibold">{{ cfg.svidDefaultTtlHours }} Hours (Max: {{ cfg.svidMaxTtlHours }}h)</span>
          </div>

          <div class="bg-slate-50/60 p-3.5 rounded-lg border border-slate-100 flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 font-heading">ACTIVE SPIRE AGENTS</span>
            <span class="text-emerald-600 font-semibold">{{ cfg.agentsConnectedCount }} Agents Connected</span>
          </div>
        </div>

        <!-- Attestation Plugins & Federated Domains -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-slate-100">
          <div class="flex flex-col gap-2">
            <span class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Node & Workload Attestation Plugins</span>
            <div class="flex flex-wrap gap-1.5">
              <span *ngFor="let p of cfg.attestationPlugins" class="px-2 py-1 rounded bg-slate-100 font-mono text-xs text-slate-800 border border-slate-200">
                {{ p }}
              </span>
            </div>
          </div>

          <div class="flex flex-col gap-2">
            <span class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Federated Trust Domains (Cross-SVID Trust)</span>
            <div class="flex flex-wrap gap-1.5">
              <span *ngFor="let d of cfg.federatedTrustDomains" class="px-2 py-1 rounded bg-blue-50 font-mono text-xs text-blue-800 border border-blue-200">
                {{ d }}
              </span>
            </div>
          </div>
        </div>
      </div>

    </div>
  `
})
export class SpiffeComponent {
  public identity = inject(IdentityService);
  public cfg = this.identity.spiffeConfig();
}
