/**
 * AKAAL Administration — LDAP / Active Directory
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-ldap',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Active Directory & LDAP Sync</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Directory connection topology, query filters, search scopes, and automated background sync intervals.
            </p>
          </div>
        </div>
      </div>

      <!-- LDAP Config Cards -->
      <div class="flex flex-col gap-6" *ngFor="let cfg of identity.ldapConfigs()">
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-6">
          <div class="flex items-start justify-between gap-4 flex-wrap pb-4 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="server" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <span class="font-bold text-slate-900 text-base font-heading">{{ cfg.name }}</span>
                <span class="text-xs text-slate-500 font-mono">{{ cfg.directoryType }} ({{ cfg.serverUrl }}:{{ cfg.port }})</span>
              </div>
            </div>

            <div class="flex items-center gap-3">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                {{ cfg.status }}
              </span>
              <button
                (click)="identity.triggerLdapSync(cfg.id)"
                class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs cursor-pointer flex items-center gap-1.5">
                <app-lucide-icon name="refresh-cw" [size]="12"></app-lucide-icon>
                <span>Trigger Sync Now</span>
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div class="bg-slate-50/60 p-3.5 rounded-lg border border-slate-100 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 font-heading">BASE DN</span>
              <span class="text-slate-800 break-all">{{ cfg.baseDn }}</span>
            </div>

            <div class="bg-slate-50/60 p-3.5 rounded-lg border border-slate-100 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 font-heading">BIND PRINCIPAL DN</span>
              <span class="text-slate-800 break-all">{{ cfg.bindDn }}</span>
            </div>

            <div class="bg-slate-50/60 p-3.5 rounded-lg border border-slate-100 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 font-heading">USER SEARCH FILTER</span>
              <span class="text-slate-800 break-all">{{ cfg.userSearchFilter }}</span>
            </div>

            <div class="bg-slate-50/60 p-3.5 rounded-lg border border-slate-100 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 font-heading">GROUP SEARCH FILTER</span>
              <span class="text-slate-800 break-all">{{ cfg.groupSearchFilter }}</span>
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-100">
            <div class="flex flex-col">
              <span class="text-[11px] text-slate-500">Synced Users</span>
              <span class="text-base font-bold text-slate-900">{{ cfg.syncedUsersCount }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] text-slate-500">Synced Groups</span>
              <span class="text-base font-bold text-slate-900">{{ cfg.syncedGroupsCount }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] text-slate-500">Group-Role Mappings</span>
              <span class="text-base font-bold text-slate-900">{{ cfg.groupRoleMappingsCount }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] text-slate-500">Last Sync</span>
              <span class="text-xs font-semibold text-slate-700 mt-1">{{ cfg.lastSyncTimestamp }}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  `
})
export class LdapComponent {
  public identity = inject(IdentityService);
}
