/**
 * AKAAL Administration — Identity Federation
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-federation',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity/directory" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Directory & Federation
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Cross-Tenant Identity Federation</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Mutual trust domains, cross-account claim mappings, and secure token exchange relationships.
            </p>
          </div>
        </div>
      </div>

      <!-- Federation Trusts Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Trust Domain</th>
              <th class="py-3 px-4">Partner Tenant</th>
              <th class="py-3 px-4">Protocol</th>
              <th class="py-3 px-4">Allowed Claim Scopes</th>
              <th class="py-3 px-4">Cross Principals</th>
              <th class="py-3 px-4">Expiration</th>
              <th class="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let fed of identity.federationTrusts()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4 font-mono font-bold text-slate-900">{{ fed.trustDomain }}</td>
              <td class="py-3 px-4 font-medium text-slate-800">{{ fed.partnerTenantName }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                  {{ fed.trustProtocol }}
                </span>
              </td>
              <td class="py-3 px-4">
                <div class="flex flex-wrap gap-1">
                  <span *ngFor="let sc of fed.allowedClaimScopes" class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100">
                    {{ sc }}
                  </span>
                </div>
              </td>
              <td class="py-3 px-4 font-bold text-slate-800">{{ fed.crossTenantPrincipalsCount }}</td>
              <td class="py-3 px-4 text-slate-600 font-mono">{{ fed.expiresAt }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ fed.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class FederationComponent {
  public identity = inject(IdentityService);
}
