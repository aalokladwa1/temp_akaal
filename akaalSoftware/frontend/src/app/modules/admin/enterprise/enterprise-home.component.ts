/**
 * AKAAL Administration — Enterprise Home
 * Clean orientation hub providing direct access to Tenancy Hierarchy, Configuration, and Governance.
 */

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

interface EnterpriseSection {
  title: string;
  description: string;
  route: string;
  icon: string;
  actionText: string;
}

interface EnterpriseGroup {
  name: string;
  sections: EnterpriseSection[];
}

@Component({
  selector: 'app-enterprise-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Breadcrumb & Header -->
      <div class="flex flex-col gap-2">
        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Enterprise</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Tenancy hierarchy, isolation boundaries, ownership custody, quotas, and baseline configuration.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              routerLink="/administration/enterprise/settings"
              class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
              Enterprise Settings
            </a>
          </div>
        </div>
      </div>

      <!-- Domain Sections Grouped Calmly -->
      <div class="flex flex-col gap-8">
        @for (group of groups; track group.name) {
          <div class="flex flex-col gap-3">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              {{ group.name }}
            </span>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              @for (sec of group.sections; track sec.title) {
                <a
                  [routerLink]="sec.route"
                  class="rounded-xl bg-white border border-slate-200 p-5 shadow-2xs hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group flex flex-col justify-between gap-4">
                  <div class="flex flex-col gap-3">
                    <div class="w-9 h-9 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
                      <app-lucide-icon [name]="sec.icon" [size]="18"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col gap-1">
                      <h3 class="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors font-heading">
                        {{ sec.title }}
                      </h3>
                      <p class="text-xs text-slate-500 font-medium leading-relaxed">
                        {{ sec.description }}
                      </p>
                    </div>
                  </div>

                  <div class="flex items-center justify-between pt-3 border-t border-slate-100">
                    <span class="text-xs font-semibold text-blue-600 group-hover:text-blue-700">{{ sec.actionText }}</span>
                    <app-lucide-icon name="arrow-right" [size]="14" class="text-blue-600 group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
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
export class EnterpriseHomeComponent {
  public groups: EnterpriseGroup[] = [
    {
      name: 'ORGANIZATIONAL HIERARCHY',
      sections: [
        {
          title: 'Organizations',
          description: 'Top-level holding legal entities, regional subsidiaries, and operating divisions.',
          route: '/administration/enterprise/organizations',
          icon: 'building-2',
          actionText: 'Manage Organizations'
        },
        {
          title: 'Workspaces',
          description: 'Program workspaces, data domain boundaries, and migration operational containers.',
          route: '/administration/enterprise/workspaces',
          icon: 'folder-kanban',
          actionText: 'Manage Workspaces'
        },
        {
          title: 'Environments',
          description: 'Deployment tiers, production isolation barriers, and runtime freeze locks.',
          route: '/administration/enterprise/environments',
          icon: 'server',
          actionText: 'Manage Environments'
        }
      ]
    },
    {
      name: 'RESOURCE GOVERNANCE & SECURITY',
      sections: [
        {
          title: 'Projects & Boundaries',
          description: 'Network isolation perimeters, egress filtering policies, and boundary guardrails.',
          route: '/administration/enterprise/boundaries',
          icon: 'network',
          actionText: 'Manage Boundaries'
        },
        {
          title: 'Resource Ownership',
          description: 'Primary and secondary RACI custodians, guild accountability, and transfer workflows.',
          route: '/administration/enterprise/ownership',
          icon: 'user-check',
          actionText: 'Manage Ownership'
        },
        {
          title: 'Quotas & Limits',
          description: 'Concurrent migration caps, network bandwidth ceilings, and storage quotas.',
          route: '/administration/enterprise/quotas',
          icon: 'gauge',
          actionText: 'Manage Quotas'
        },
        {
          title: 'Administrative Metadata',
          description: 'Mandatory cost centers, security classification schemes, and resource taxonomy tags.',
          route: '/administration/enterprise/metadata',
          icon: 'tags',
          actionText: 'Manage Metadata'
        }
      ]
    },
    {
      name: 'PLATFORM BASELINE & CONFIGURATION',
      sections: [
        {
          title: 'Enterprise Settings',
          description: 'Tenant identifier, primary domain, KMS master key ARN, and break-glass escrow.',
          route: '/administration/enterprise/settings',
          icon: 'sliders',
          actionText: 'Configure Settings'
        }
      ]
    }
  ];
}
