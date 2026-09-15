/**
 * AKAAL Administration — SCIM 2.0 Inbound & Outbound Provisioning
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-scim',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">SCIM 2.0 Provisioning</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              RFC 7643 / RFC 7644 compliant automated user lifecycle management endpoints for Microsoft Entra ID and Okta.
            </p>
          </div>
        </div>
      </div>

      <!-- SCIM Endpoints List -->
      <div class="flex flex-col gap-6" *ngFor="let scim of identity.scimEndpoints()">
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
          <div class="flex items-start justify-between gap-4 flex-wrap pb-4 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
                <app-lucide-icon name="refresh-cw" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <span class="font-bold text-slate-900 text-base font-heading">{{ scim.name }}</span>
                <span class="text-xs text-slate-500">{{ scim.providerType }}</span>
              </div>
            </div>

            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
              {{ scim.status }}
            </span>
          </div>

          <div class="flex flex-col gap-3 bg-slate-50/50 p-4 rounded-lg border border-slate-100 text-xs font-mono">
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 font-heading">BASE SCIM 2.0 URL (Base URL for Entra / Okta App)</span>
              <span class="text-slate-800 break-all select-all font-semibold">{{ scim.endpointUrl }}</span>
            </div>
            <div class="flex items-center justify-between pt-2 border-t border-slate-200/60 font-sans">
              <span class="text-slate-500">Bearer Token Secret Hint:</span>
              <span class="font-mono text-slate-700 font-semibold">{{ scim.tokenSecretHint }} (Expires: {{ scim.tokenExpiryDate }})</span>
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
            <div class="flex flex-col">
              <span class="text-[11px] text-slate-500">Provisioned Users</span>
              <span class="text-base font-bold text-slate-900">{{ scim.provisionedUsersCount }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] text-slate-500">Deprovision Action</span>
              <span class="text-xs font-semibold text-slate-700 mt-1">{{ scim.deprovisionAction }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] text-slate-500">Sync Entities</span>
              <span class="text-xs font-semibold text-slate-700 mt-1">Users & Groups</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] text-slate-500">Last Webhook Activity</span>
              <span class="text-xs font-semibold text-slate-700 mt-1">{{ scim.lastWebhookTimestamp }}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  `
})
export class ScimComponent {
  public identity = inject(IdentityService);
}
