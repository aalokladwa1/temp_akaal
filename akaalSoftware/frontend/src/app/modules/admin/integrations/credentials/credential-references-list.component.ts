/**
 * AKAAL Administration — 5.11 Integration Credential References List
 * Zero-plaintext custody rule: encapsulates Vault and KMS URIs only.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IntegrationsService } from '../../services/integrations.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-credential-references-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/integrations"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">INTEGRATIONS</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">CREDENTIAL REFERENCES</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Integration Credential References</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Encapsulated Vault secrets and KMS keys bound to outbound channels. All secret material is stored within external hardware or KMS authorities.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <a
            routerLink="/administration/identity/crypto/vault"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Manage Secrets in Vault (5.4)
          </a>
        </div>
      </div>

      <!-- Credential References Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Credential Name</th>
              <th class="py-3.5 px-4">Provider Type</th>
              <th class="py-3.5 px-4">Encapsulated Vault URI</th>
              <th class="py-3.5 px-4">Bound Integrations</th>
              <th class="py-3.5 px-4">Last Rotated</th>
              <th class="py-3.5 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (ref of integrationsService.credentialRefs(); track ref.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900 font-heading">{{ ref.name }}</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-700">{{ ref.providerType }}</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-blue-600 max-w-md truncate" [title]="ref.vaultUri">
                  {{ ref.vaultUri }}
                </td>
                <td class="py-3.5 px-4 font-semibold text-slate-900">{{ ref.associatedIntegrationsCount }} Integrations</td>
                <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">{{ ref.lastRotatedAt }}</td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ ref.status }}
                  </span>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class CredentialReferencesListComponent {
  public integrationsService = inject(IntegrationsService);
}
