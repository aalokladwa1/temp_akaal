/**
 * AKAAL Administration — 5.10 Licensing & Entitlements
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PlatformAdminService } from '../../services/platform-admin.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-licensing-entitlements',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/platform-admin"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">PLATFORM</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">COMMERCIAL LICENSING</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Licensing & Entitlements</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Commercial enterprise subscription terms, compute node capacity limits, and enabled platform feature gates.
          </p>
        </div>
      </div>

      <!-- License Card -->
      @if (platformService.licensing(); as lic) {
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-6">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Subscription Edition</span>
              <span class="text-sm font-bold font-mono text-slate-900">{{ lic.edition }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Licensed Compute Nodes</span>
              <span class="text-sm font-bold text-slate-900">{{ lic.licensedNodes }} Nodes Authorized</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Throughput Capacity</span>
              <span class="text-sm font-bold text-slate-900">{{ lic.licensedCapacityTb }} TB Cumulative Sync</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">License Status</span>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 w-fit">
                {{ lic.status }} (Valid to {{ lic.expiresAt }})
              </span>
            </div>
          </div>

          <div class="border-t border-slate-200 pt-5 flex flex-col gap-3">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Enabled Feature Entitlements</span>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              @for (feat of lic.features; track feat) {
                <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-2.5 text-xs font-medium text-slate-800">
                  <app-lucide-icon name="check" [size]="14" class="text-emerald-600 shrink-0"></app-lucide-icon>
                  <span>{{ feat }}</span>
                </div>
              }
            </div>
          </div>

          <div class="border-t border-slate-200 pt-4 flex items-center justify-between text-xs text-slate-500">
            <span>Cryptographic License Key Custody: <code class="font-mono text-slate-700">{{ lic.licenseKeyRef }}</code></span>
            <span>Zero plaintext keys stored in client</span>
          </div>
        </div>
      }
    </div>
  `
})
export class LicensingEntitlementsComponent {
  public platformService = inject(PlatformAdminService);
}
