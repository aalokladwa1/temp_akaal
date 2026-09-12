/**
 * AKAAL Administration — 5.10 Updates & Upgrade Management
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PlatformAdminService } from '../../services/platform-admin.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-updates-management',
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
              <span class="text-xs font-medium text-slate-500">UPGRADE MANAGEMENT</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Updates & Upgrade Management</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Controlled platform version releases, component pre-flight readiness verification, and rollout plans.
          </p>
        </div>
      </div>

      <!-- Release Information Card -->
      @if (platformService.upgradeInfo(); as upg) {
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-6">
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Available Target Release</span>
              <span class="text-xl font-bold font-mono text-slate-900">v{{ upg.targetVersion }}</span>
            </div>

            <div class="flex items-center gap-2">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                {{ upg.severity }}
              </span>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Pre-flight Verified
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t border-slate-200 text-xs">
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Release Target Date</span>
              <span class="font-semibold text-slate-900">{{ upg.releaseDate }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Schema Compatibility</span>
              <span class="font-semibold text-emerald-700">Non-Breaking Forward Compatible</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Release Documentation</span>
              <a [href]="upg.releaseNotesUrl" target="_blank" class="text-blue-600 hover:underline font-mono">
                View Release Notes & Integrity Manifest
              </a>
            </div>
          </div>

          <div class="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-center justify-between">
            <span>
              All pre-flight migration safety assertions passed. Automated rollbacks are enabled.
            </span>
            <a
              routerLink="/administration/platform-admin/lifecycle/maintenance"
              class="text-blue-600 font-semibold hover:underline">
              Schedule Upgrade in Maintenance Window
            </a>
          </div>
        </div>
      }
    </div>
  `
})
export class UpdatesManagementComponent {
  public platformService = inject(PlatformAdminService);
}
