/**
 * AKAAL Administration — 5.11 Integrations & Notifications Home
 * Master navigation hub for Notifications, Event Delivery, Enterprise Integrations, and Credentials.
 * Strictly separates credential references from secret storage.
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
  selector: 'app-integrations-home',
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
              <span class="text-xs font-medium text-slate-500">INTEGRATIONS & NOTIFICATIONS</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Integrations & Notifications</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Outbound notification channels, event routing filters, enterprise SIEM collectors, ITSM incident management, and credential reference registries.
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
export class IntegrationsHomeComponent {
  public groups: ResponsibilityGroup[] = [
    {
      title: 'NOTIFICATIONS',
      items: [
        {
          id: 'notification-channels',
          name: 'Notification Channels',
          description: 'Configure outbound delivery endpoints for Email/SMTP, Slack webhooks, Microsoft Teams, and PagerDuty.',
          route: '/administration/integrations/notifications/channels',
          icon: 'bell'
        },
        {
          id: 'notification-policies',
          name: 'Notification Policies',
          description: 'Define alert routing rules by severity, escalation timers, and operator quiet hours suppression.',
          route: '/administration/integrations/notifications/policies',
          icon: 'shield-check'
        }
      ]
    },
    {
      title: 'EVENT DELIVERY',
      items: [
        {
          id: 'event-routing',
          name: 'Event Routing',
          description: 'Granular filter patterns matching administrative, security, governance, and migration event taxonomy.',
          route: '/administration/integrations/events/routing',
          icon: 'share-2'
        }
      ]
    },
    {
      title: 'ENTERPRISE INTEGRATIONS',
      items: [
        {
          id: 'siem-integrations',
          name: 'SIEM Integrations',
          description: 'External security collectors including Splunk HEC, Datadog intake, and TLS Syslog daemons.',
          route: '/administration/integrations/enterprise/siem',
          icon: 'radio'
        },
        {
          id: 'itsm-integrations',
          name: 'ITSM / Ticketing',
          description: 'Enterprise IT service management integration with ServiceNow instances and Jira Software queues.',
          route: '/administration/integrations/enterprise/itsm',
          icon: 'ticket'
        }
      ]
    },
    {
      title: 'CREDENTIALS',
      items: [
        {
          id: 'credential-references',
          name: 'Integration Credential References',
          description: 'Encapsulated Vault and KMS reference URIs utilized by outbound integration channels. Zero plaintext tokens.',
          route: '/administration/integrations/credentials',
          icon: 'key-round'
        }
      ]
    }
  ];
}
