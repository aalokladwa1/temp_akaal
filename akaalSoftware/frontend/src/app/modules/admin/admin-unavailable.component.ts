/**
 * AKAAL Administration — Planned Domain Orientation Surface
 * Truthfully displays planned governance domains without fake mocks or misleading status.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-admin-unavailable',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <div class="flex items-center gap-2 text-xs font-semibold text-slate-500">
        <a routerLink="/administration" class="hover:text-slate-900 transition-colors">Administration</a>
        <span class="text-slate-300">/</span>
        <span class="text-slate-800">{{ domainName() }}</span>
      </div>

      <div class="p-12 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col items-center justify-center text-center gap-4 max-w-2xl mx-auto my-12">
        <div class="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-500">
          <app-lucide-icon name="clock" [size]="24"></app-lucide-icon>
        </div>

        <div class="flex flex-col gap-1.5">
          <h2 class="text-lg font-bold text-slate-900 font-heading">{{ domainName() }}</h2>
          <p class="text-xs text-slate-600 leading-relaxed">
            This domain is planned in the administration governance roadmap. Current operational capabilities are active within Enterprise Tenancy &amp; Architecture.
          </p>
        </div>

        <div class="pt-2 flex items-center gap-3">
          <a
            routerLink="/administration/enterprise"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Open Enterprise Domain
          </a>
          <a
            routerLink="/administration"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Back to Administration
          </a>
        </div>
      </div>

    </div>
  `
})
export class AdminUnavailableComponent {
  private router = inject(Router);

  private friendlyTitles: Record<string, string> = {
    'people': 'People & Access',
    'governance-centre': 'Governance Centre',
    'identity-security': 'Identity & Security',
    'templates-config': 'Template & Configuration Library',
    'connectors-plugins': 'Connector & Plugin Center',
    'cloud-infra': 'Cloud & Infrastructure',
    'compliance': 'Compliance',
    'audit': 'Audit',
    'platform-admin': 'Platform Administration',
    'integrations-notifications': 'Integrations & Notifications'
  };

  public domainName(): string {
    const segments = this.router.url.split('?')[0].split('/').filter(Boolean);
    const last = segments[segments.length - 1];
    return this.friendlyTitles[last] || (last ? last.replace(/-/g, ' ') : 'Administration Domain');
  }
}
