/**
 * AKAAL Administration — Directory & Federation Hub
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-directory-home',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Directory & Federation</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Synchronize users & groups with Active Directory, expose SCIM 2.0 provisioning endpoints, and manage cross-tenant trust contracts.
            </p>
          </div>
        </div>
      </div>

      <!-- Feature Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <!-- LDAP / AD -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="folder-tree" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-emerald-600 font-mono">{{ identity.ldapConfigs().length }} CONNECTED</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Active Directory & LDAP Sync</h2>
              <p class="text-xs text-slate-600 mt-1">
                Scheduled directory query sync, OU filtering, and nested group-to-role entitlement mappings.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/directory/ldap"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage LDAP / AD</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- SCIM 2.0 -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="refresh-cw" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-slate-700 font-mono">{{ identity.scimEndpoints().length }} ENDPOINTS</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">SCIM 2.0 Automated Provisioning</h2>
              <p class="text-xs text-slate-600 mt-1">
                Real-time webhook provisioning and deprovisioning synchronization from Microsoft Entra and Okta.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/directory/scim"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage SCIM 2.0</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Identity Federation -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="link-2" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-slate-700 font-mono">{{ identity.federationTrusts().length }} TRUSTS</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Cross-Tenant Identity Federation</h2>
              <p class="text-xs text-slate-600 mt-1">
                Mutual trust domains, cross-account claim mappings, and secure federation exchange contracts.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/identity/directory/federation"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage Federation</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

      </div>
    </div>
  `
})
export class DirectoryHomeComponent {
  public identity = inject(IdentityService);
}
