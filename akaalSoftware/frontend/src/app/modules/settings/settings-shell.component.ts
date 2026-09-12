import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';
import { SettingsNavSection } from './models/settings.models';

export const SETTINGS_NAV_SECTIONS: SettingsNavSection[] = [
  {
    title: 'WORKSTATION PREFERENCES',
    categories: [
      {
        id: 'general',
        label: 'General',
        path: '/settings/general',
        icon: 'sliders',
        description: 'Landing view, localization, data units, and safety gates',
        status: 'ACTIVE'
      },
      {
        id: 'appearance',
        label: 'Appearance',
        path: '/settings/appearance',
        icon: 'palette',
        description: 'Themes, high contrast, color vision, and motion',
        status: 'ACTIVE'
      }
    ]
  },
  {
    title: 'OPERATIONAL DEFAULTS',
    categories: [
      {
        id: 'runtime-migration',
        label: 'Runtime & Migration',
        path: '/settings/runtime-migration',
        icon: 'workflow',
        description: 'Pipeline concurrency, batches, and buffer thresholds',
        status: 'ACTIVE'
      },
      {
        id: 'connectors',
        label: 'Connector Defaults',
        path: '/settings/connectors',
        icon: 'plug',
        description: 'Connection pools, timeouts, and network proxies',
        status: 'ACTIVE'
      },
      {
        id: 'storage',
        label: 'Storage & Retention',
        path: '/settings/storage',
        icon: 'hard-drive',
        description: 'Scratch disk budgets, cache epochs, and compression',
        status: 'ACTIVE'
      }
    ]
  },
  {
    title: 'SYSTEM & INTELLIGENCE',
    categories: [
      {
        id: 'notifications',
        label: 'Notifications',
        path: '/settings/notifications',
        icon: 'bell',
        description: 'Desktop alerts, barrier audio cues, and sound chimes',
        status: 'ACTIVE'
      },
      {
        id: 'integrations',
        label: 'Integrations',
        path: '/settings/integrations',
        icon: 'layers',
        description: 'Local CLI discovery, cloud bindings, and tools',
        status: 'ACTIVE'
      },
      {
        id: 'ai-intelligence',
        label: 'AI & Intelligence',
        path: '/settings/ai-intelligence',
        icon: 'bot',
        description: 'Model endpoints, schema anonymization, and advice',
        status: 'ACTIVE'
      },
      {
        id: 'logging',
        label: 'Logging & Diagnostics',
        path: '/settings/logging',
        icon: 'file-text',
        description: 'Log verbosity, rotation rules, and bundle exports',
        status: 'ACTIVE'
      },
      {
        id: 'advanced',
        label: 'Advanced',
        path: '/settings/advanced',
        icon: 'terminal',
        description: 'IPC timeouts, engine flags, and reset routines',
        status: 'ACTIVE'
      }
    ]
  }
];

@Component({
  selector: 'app-settings-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 font-sans max-w-7xl mx-auto animate-in fade-in duration-150">
      
      <!-- Top Title Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold text-slate-500 tracking-wider uppercase font-mono">
              SETTINGS &bull; WORKSTATION CONTROL
            </span>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight">
            Settings
          </h1>
          <p class="text-xs text-slate-500 max-w-3xl">
            Configure client workstation preferences, visual themes, localization formats, and operational defaults.
          </p>
        </div>

        <!-- Workstation Local Indicator -->
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 text-xs shrink-0 self-start sm:self-auto">
          <span class="w-2 h-2 rounded-sm bg-emerald-500"></span>
          <span class="font-medium text-[11px]">Workstation Local Scope</span>
        </div>
      </div>

      <!-- Split Layout: Left Persistent Navigation + Right Focused Canvas -->
      <div class="flex flex-col md:flex-row items-start gap-8">
        
        <!-- Left Navigation Panel (Persistent Desktop Navigation) -->
        <nav 
          aria-label="Settings Navigation"
          class="w-full md:w-72 shrink-0 flex flex-col gap-6 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          
          @for (section of navSections; track section.title) {
            <div class="flex flex-col gap-1.5">
              <div class="px-2 py-1 text-[10px] font-bold text-slate-600 uppercase tracking-wider font-mono">
                {{ section.title }}
              </div>

              <div class="flex flex-col gap-0.5">
                @for (cat of section.categories; track cat.id) {
                  <a
                    [routerLink]="cat.path"
                    routerLinkActive="bg-blue-50 text-blue-700 font-semibold border-blue-200/90 shadow-2xs"
                    class="flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 border border-transparent transition-all group cursor-pointer select-none">
                    
                    <div class="flex items-center gap-2.5 min-w-0">
                      <app-lucide-icon 
                        [name]="cat.icon" 
                        [size]="15" 
                        class="text-slate-500 group-hover:text-slate-800 shrink-0">
                      </app-lucide-icon>
                      <span class="truncate">{{ cat.label }}</span>
                    </div>

                    @if (cat.badge) {
                      <span class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-slate-100 text-slate-500 border border-slate-200 shrink-0">
                        {{ cat.badge }}
                      </span>
                    }
                  </a>
                }
              </div>
            </div>
          }

        </nav>

        <!-- Right Main Outlet -->
        <main class="flex-1 min-w-0 w-full">
          <router-outlet></router-outlet>
        </main>

      </div>

    </div>
  `
})
export class SettingsShellComponent {
  public navSections = SETTINGS_NAV_SECTIONS;
}
