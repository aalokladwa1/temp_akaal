/**
 * AKAAL Monitoring — Part 3 of 4: Platform Navigation Component
 * Stable rectangular underline tabs across all 8 Platform Operations areas (NO pills, NO capsules).
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { PLATFORM_TABS, PlatformTabKey } from '../models/platform-monitoring.models';
import { PlatformMonitoringService } from '../services/platform-monitoring.service';

@Component({
  selector: 'app-platform-nav',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full bg-white border-b border-slate-200 select-none">
      <nav class="flex items-center gap-1 sm:gap-2 overflow-x-auto no-scrollbar px-1" aria-label="Platform Operations Areas">
        @for (tab of tabs; track tab.key) {
          <button
            type="button"
            (click)="onSelectTab(tab.key)"
            class="group relative py-3.5 px-3 sm:px-4 text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer inline-flex items-center gap-2 border-b-2"
            [ngClass]="{
              'border-blue-600 text-blue-600': pms.selectedTab() === tab.key,
              'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300': pms.selectedTab() !== tab.key
            }">
            <span>{{ tab.label }}</span>

            <!-- Contextual counter for conditions / alerts -->
            @if (tab.key === 'overview' && pms.conditions().length > 0) {
              <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                {{ pms.conditions().length }}
              </span>
            }
          </button>
        }
      </nav>
    </div>
  `
})
export class PlatformNavComponent {
  public pms = inject(PlatformMonitoringService);
  private router = inject(Router);
  public tabs = PLATFORM_TABS;

  public onSelectTab(tabKey: PlatformTabKey): void {
    this.pms.selectTab(tabKey);
    this.router.navigate(['/monitoring/platform', tabKey]);
  }
}
