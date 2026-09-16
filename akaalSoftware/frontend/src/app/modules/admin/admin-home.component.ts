/**
 * AKAAL Administration — Master Landing Hub
 * Clean orientation and routing entrance across 3 frozen responsibility groups and 11 domains.
 */

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';

interface DomainItem {
  id: string;
  name: string;
  route: string;
  icon: string;
  isImplemented: boolean;
  statusLabel?: string;
}

interface DomainGroup {
  title: string;
  domains: DomainItem[];
}

@Component({
  selector: 'app-admin-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-200">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 dark:border-white/[0.08] flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight font-heading">Administration</h1>
          <p class="text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-400 max-w-3xl flex items-center gap-2 flex-wrap">
            <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Control Plane Active</span>
            </span>
            <span>11 control plane domains active &bull; Multi-tenant security governance &amp; infrastructure operational</span>
          </p>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <a
            routerLink="/administration/enterprise/settings"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center justify-center cursor-pointer transition-all duration-150 active:scale-[0.98] shadow-2xs">
            Enterprise Settings
          </a>
        </div>
      </div>

      <!-- Domain Responsibility Groups -->
      <div class="flex flex-col gap-8">
        @for (group of groups; track group.title) {
          <div class="flex flex-col gap-3">
            <span class="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-heading">
              {{ group.title }}
            </span>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              @for (domain of group.domains; track domain.id) {
                <a
                  [routerLink]="domain.route"
                  class="h-16 flex items-center justify-between px-4 bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-[#26272b] rounded-xl hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-[#202226] hover:-translate-y-0.5 transition-all duration-200 cursor-pointer select-none group shadow-2xs">
                  
                  <div class="flex items-center gap-3.5 min-w-0">
                    <div 
                      class="w-9 h-9 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center justify-center shrink-0 transition-colors"
                      [ngClass]="domain.isImplemented ? 'text-blue-600 dark:text-blue-400 group-hover:bg-blue-50 dark:group-hover:bg-blue-950/40 group-hover:border-blue-200 dark:group-hover:border-blue-800/40' : 'text-slate-400 dark:text-slate-500'">
                      <app-lucide-icon [name]="domain.icon" [size]="18"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col min-w-0">
                      <span 
                        class="text-xs font-semibold truncate transition-colors"
                        [ngClass]="domain.isImplemented ? 'text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 font-heading' : 'text-slate-700 dark:text-slate-300'">
                        {{ domain.name }}
                      </span>
                      @if (!domain.isImplemented) {
                        <span class="text-[10px] font-medium text-slate-400 dark:text-slate-500">Planned Capability</span>
                      }
                    </div>
                  </div>

                  <div class="flex items-center gap-1.5 shrink-0">
                    @if (domain.isImplemented) {
                      <app-lucide-icon 
                        name="arrow-right" 
                        [size]="14" 
                        class="text-slate-400 dark:text-slate-500 group-hover:text-blue-600 dark:group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all">
                      </app-lucide-icon>
                    }
                  </div>
                </a>
              }
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class AdminHomeComponent {
  public groups: DomainGroup[] = [
    {
      title: 'ORGANIZATION & ACCESS',
      domains: [
        { id: 'enterprise', name: 'Enterprise', route: '/administration/enterprise', icon: 'building-2', isImplemented: true },
        { id: 'people', name: 'People & Access', route: '/administration/people', icon: 'users', isImplemented: true },
        { id: 'governance-centre', name: 'Governance Centre', route: '/administration/governance-centre', icon: 'scale', isImplemented: true },
        { id: 'identity-security', name: 'Identity & Security', route: '/administration/identity', icon: 'key-round', isImplemented: true }
      ]
    },
    {
      title: 'PLATFORM & CONFIGURATION',
      domains: [
        { id: 'templates-config', name: 'Template & Configuration Library', route: '/administration/templates-library', icon: 'library', isImplemented: true },
        { id: 'connectors-plugins', name: 'Connector & Plugin Center', route: '/administration/connectors', icon: 'plug', isImplemented: true },
        { id: 'cloud-infra', name: 'Cloud & Infrastructure', route: '/administration/infrastructure', icon: 'cloud', isImplemented: true }
      ]
    },
    {
      title: 'CONTROL & OPERATIONS',
      domains: [
        { id: 'compliance', name: 'Compliance', route: '/administration/compliance', icon: 'file-check-2', isImplemented: true },
        { id: 'audit', name: 'Audit', route: '/administration/audit', icon: 'history', isImplemented: true },
        { id: 'platform-admin', name: 'Platform Administration', route: '/administration/platform-admin', icon: 'sliders-horizontal', isImplemented: true },
        { id: 'integrations-notifications', name: 'Integrations & Notifications', route: '/administration/integrations', icon: 'bell', isImplemented: true }
      ]
    }
  ];
}
