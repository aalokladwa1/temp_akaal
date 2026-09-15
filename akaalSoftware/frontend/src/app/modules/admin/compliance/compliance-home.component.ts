/**
 * AKAAL Administration — 5.8 Compliance Home
 * Master navigation and responsibility hub for Control Frameworks, Controls, and Evidence.
 * Strictly adheres to Zero-Fake Law: no false compliance badges, no arbitrary percentage scores.
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
  selector: 'app-compliance-home',
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
              <span class="text-xs font-medium text-slate-500">COMPLIANCE CONTROL PLANE</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Compliance</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Regulatory control framework mappings, technical safeguard verifications, exceptions governance, and cryptographic audit evidence.
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
export class ComplianceHomeComponent {
  public groups: ResponsibilityGroup[] = [
    {
      title: 'FRAMEWORKS',
      items: [
        {
          id: 'control-frameworks',
          name: 'Control Frameworks',
          description: 'Canonical regulatory catalogs (GDPR, PCI-DSS, HIPAA, SOC 2, ISO 27001) and mapped safeguard scopes.',
          route: '/administration/compliance/frameworks/catalog',
          icon: 'shield-check'
        },
        {
          id: 'framework-views',
          name: 'Framework Views',
          description: 'Focused regulatory compliance perspective and domain-level technical control status.',
          route: '/administration/compliance/frameworks/views',
          icon: 'layers'
        },
        {
          id: 'custom-frameworks',
          name: 'Custom Frameworks',
          description: 'Enterprise internal security guidelines, sovereign government mandates, and bespoke policy specifications.',
          route: '/administration/compliance/frameworks/custom',
          icon: 'file-text'
        }
      ]
    },
    {
      title: 'CONTROLS',
      items: [
        {
          id: 'control-mapping',
          name: 'Control Mapping',
          description: 'Explicit relationships binding regulatory control requirements to AKAAL platform technical execution controls.',
          route: '/administration/compliance/controls/mapping',
          icon: 'git-fork'
        },
        {
          id: 'compliance-exceptions',
          name: 'Compliance Exceptions',
          description: 'Audited regulatory waivers, non-standard system configurations, and time-bounded compliance exemptions.',
          route: '/administration/compliance/controls/exceptions',
          icon: 'file-warning'
        }
      ]
    },
    {
      title: 'EVIDENCE',
      items: [
        {
          id: 'compliance-evidence',
          name: 'Compliance Evidence',
          description: 'Tamper-evident execution digests, cryptographic hash attestations, and immutable validation records.',
          route: '/administration/compliance/evidence',
          icon: 'file-check-2'
        }
      ]
    }
  ];
}
