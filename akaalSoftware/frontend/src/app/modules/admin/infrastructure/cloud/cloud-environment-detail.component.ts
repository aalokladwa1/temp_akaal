/**
 * AKAAL Administration — 5.7 Cloud Environment Detail
 */

import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-cloud-environment-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/cloud/environments" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Cloud Environments
          </a>
        </div>

        @if (environment(); as env) {
          <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
            <div class="flex flex-col gap-1">
              <div class="flex items-center gap-3">
                <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ env.name }}</h1>
                <span class="px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-slate-100 text-slate-800 border border-slate-200">
                  {{ env.provider }}
                </span>
                <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ env.status }}
                </span>
              </div>
              <p class="text-sm font-medium text-slate-600 max-w-3xl">
                Tenant / Account: <span class="font-mono text-slate-800 font-semibold">{{ env.accountIdOrTenant }}</span> &bull; Default Region: <span class="font-mono text-slate-800">{{ env.defaultRegion }}</span>
              </p>
            </div>
          </div>
        }
      </div>

      @if (environment(); as env) {
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <div class="lg:col-span-2 flex flex-col gap-6">
            
            <!-- Regions & Sites Scope Card -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Configured Regional Scope</h2>
              <div class="flex flex-wrap gap-2">
                @for (region of env.configuredRegions; track region) {
                  <span class="px-3 py-1 bg-slate-50 text-slate-800 border border-slate-200 rounded-lg text-xs font-mono font-medium">
                    {{ region }}
                  </span>
                }
              </div>
            </div>

            <!-- Associated Execution Sites -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Associated Execution Sites</h2>
              <div class="flex flex-col gap-2">
                @for (siteId of env.executionSiteIds; track siteId) {
                  <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs">
                    <span class="font-mono font-bold text-slate-800">{{ siteId }}</span>
                    <span class="text-slate-500 font-semibold">Registered Compute Target</span>
                  </div>
                }
              </div>
            </div>

            <!-- Administrative Tags -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-3">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Administrative Governance Tags</h2>
              <div class="flex flex-wrap gap-2">
                @for (t of env.tags; track t) {
                  <span class="px-2.5 py-1 bg-slate-100 text-slate-700 border border-slate-200 rounded-md text-xs font-medium">
                    {{ t }}
                  </span>
                }
              </div>
            </div>

          </div>

          <!-- Column 3: Credential Custody Sidebar -->
          <div class="flex flex-col gap-6">
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Credential Custody Reference</h2>

              <div class="flex flex-col gap-3 text-xs">
                <div class="flex flex-col gap-1">
                  <span class="text-slate-500 font-medium">Vault Secret Path</span>
                  <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-[11px] text-slate-800 break-all select-all">
                    {{ env.credentialRef }}
                  </div>
                </div>

                <div class="p-3 bg-blue-50/50 border border-blue-100 rounded-lg text-xs text-blue-800 mt-2">
                  <span class="font-semibold block mb-0.5">Zero-Plaintext Safeguard</span>
                  No cloud API keys or client secrets are stored or displayed in plaintext. Custody is securely delegated to HashiCorp Vault.
                </div>
              </div>
            </div>
          </div>

        </div>
      }

    </div>
  `
})
export class CloudEnvironmentDetailComponent {
  private service = inject(InfrastructureService);
  private route = inject(ActivatedRoute);

  public environment = computed(() => {
    const id = this.route.snapshot.paramMap.get('id');
    return id ? this.service.getEnvironmentById(id) : undefined;
  });
}
