/**
 * AKAAL Administration — Certificates & PKI
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-certificates',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Certificates & PKI</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Internal Root and Intermediate Certificate Authorities, TLS/mTLS certificate inventory, and validity monitoring.
            </p>
          </div>
        </div>
      </div>

      <!-- Certificates Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Common Name (CN)</th>
              <th class="py-3 px-4">Type</th>
              <th class="py-3 px-4">Issuer</th>
              <th class="py-3 px-4">Algorithm</th>
              <th class="py-3 px-4">Valid To / Days Left</th>
              <th class="py-3 px-4">Bound Services</th>
              <th class="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let c of identity.certificates()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4">
                <div class="flex flex-col">
                  <span class="font-mono font-bold text-slate-900">{{ c.commonName }}</span>
                  <span class="text-[10px] text-slate-400 font-mono">SN: {{ c.serialNumber }}</span>
                </div>
              </td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ c.type }}
                </span>
              </td>
              <td class="py-3 px-4 text-slate-700 font-medium">{{ c.issuerName }}</td>
              <td class="py-3 px-4 font-mono text-slate-700">{{ c.algorithm }}</td>
              <td class="py-3 px-4">
                <div class="flex flex-col">
                  <span class="text-slate-900 font-medium">{{ c.validTo }}</span>
                  <span class="text-[11px] font-bold" [ngClass]="c.daysRemaining < 30 ? 'text-amber-600' : 'text-slate-500'">
                    {{ c.daysRemaining }} days remaining
                  </span>
                </div>
              </td>
              <td class="py-3 px-4 font-bold text-slate-800">{{ c.boundServicesCount }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  [ngClass]="{
                    'bg-emerald-50 text-emerald-700 border border-emerald-200': c.status === 'VALID',
                    'bg-amber-50 text-amber-700 border border-amber-200': c.status === 'EXPIRING_SOON',
                    'bg-rose-50 text-rose-700 border border-rose-200': c.status === 'EXPIRED'
                  }">
                  {{ c.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class CertificatesComponent {
  public identity = inject(IdentityService);
}
