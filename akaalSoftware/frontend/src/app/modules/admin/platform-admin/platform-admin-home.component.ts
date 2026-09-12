/**
 * AKAAL Administration — 5.10 Platform Administration Home
 * Master navigation hub for Platform, Lifecycle, Commercial, Resilience, and Support.
 * Strictly separates configuration from live monitoring telemetry.
 */

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

interface ResponsibilityGroup {
  title: string;
  items: {
    id: string;
    name: string;
    description: string;
    route: string;
    icon: string;
  }[];
}

@Component({
  selector: 'app-platform-admin-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">ADMINISTRATION</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">PLATFORM CONTROL PLANE</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Platform Administration</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Core cluster configurations, daemon node topologies, deployment orchestrator bindings, version management, licensing entitlements, and recovery resilience.
          </p>
        </div>
      </div>

      <!-- Responsibility Groups -->
      <div class="flex flex-col gap-8">
        @for (group of groups; track group.title) {
          <div class="flex flex-col gap-3">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              {{ group.title }}
            </span>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              @for (item of group.items; track item.id) {
                <a
                  [routerLink]="item.route"
                  class="flex items-start justify-between p-4 bg-white border border-slate-200 rounded-xl hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group shadow-2xs">
                  
                  <div class="flex items-start gap-3.5 min-w-0">
                    <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0 text-blue-600 group-hover:bg-blue-100 transition-colors">
                      <app-lucide-icon [name]="item.icon" [size]="18"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col min-w-0">
                      <span class="text-xs font-bold text-slate-900 group-hover:text-blue-600 font-heading transition-colors">
                        {{ item.name }}
                      </span>
                      <span class="text-xs font-medium text-slate-500 mt-1 line-clamp-2">
                        {{ item.description }}
                      </span>
                    </div>
                  </div>

                  <div class="shrink-0 pt-1">
                    <app-lucide-icon 
                      name="arrow-right" 
                      [size]="14" 
                      class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all">
                    </app-lucide-icon>
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
export class PlatformAdminHomeComponent {
  public groups: ResponsibilityGroup[] = [
    {
      title: 'PLATFORM',
      items: [
        {
          id: 'platform-config',
          name: 'Platform Configuration',
          description: 'Global parameters controlling concurrency, session timeouts, and transport boundaries.',
          route: '/administration/platform-admin/platform/config',
          icon: 'sliders-horizontal'
        },
        {
          id: 'nodes-services',
          name: 'Nodes & Services Configuration',
          description: 'Desired replication topology, memory/CPU reservations, and socket bindings for platform daemons.',
          route: '/administration/platform-admin/platform/services',
          icon: 'server'
        },
        {
          id: 'deployment',
          name: 'Deployment Configuration',
          description: 'Target deployment environments, Kubernetes rollout strategies, and active profiles.',
          route: '/administration/platform-admin/platform/deployment',
          icon: 'terminal'
        }
      ]
    },
    {
      title: 'LIFECYCLE',
      items: [
        {
          id: 'versions',
          name: 'Versions',
          description: 'Canonical versions of AKAAL components, engine protocols, and database schema migrations.',
          route: '/administration/platform-admin/lifecycle/versions',
          icon: 'git-commit'
        },
        {
          id: 'updates',
          name: 'Updates & Upgrade Management',
          description: 'Release channels, pre-flight readiness checks, and platform component upgrade paths.',
          route: '/administration/platform-admin/lifecycle/updates',
          icon: 'arrow-up-circle'
        },
        {
          id: 'maintenance',
          name: 'Maintenance Windows',
          description: 'Scheduled maintenance periods, node drain authorizations, and planned outage controls.',
          route: '/administration/platform-admin/lifecycle/maintenance',
          icon: 'calendar'
        }
      ]
    },
    {
      title: 'COMMERCIAL',
      items: [
        {
          id: 'licensing',
          name: 'Licensing & Entitlements',
          description: 'Enterprise license tier, active feature entitlements, licensed node capacity, and expiration terms.',
          route: '/administration/platform-admin/commercial/licensing',
          icon: 'award'
        }
      ]
    },
    {
      title: 'RESILIENCE',
      items: [
        {
          id: 'backup-restore',
          name: 'Backup & Restore',
          description: 'Control plane state snapshots, configuration catalog archives, and disaster recovery restore workflows.',
          route: '/administration/platform-admin/resilience/backup-restore',
          icon: 'hard-drive'
        }
      ]
    },
    {
      title: 'SUPPORT',
      items: [
        {
          id: 'support-diagnostics',
          name: 'Support & Diagnostics',
          description: 'Generate sanitized diagnostic bundles, environment health reports, and support ticket packages.',
          route: '/administration/platform-admin/support/diagnostics',
          icon: 'life-buoy'
        }
      ]
    }
  ];
}
