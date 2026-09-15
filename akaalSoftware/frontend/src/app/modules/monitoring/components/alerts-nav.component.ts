/**
 * AKAAL Monitoring — Part 4 of 4: Alerts Navigation Component
 * Stable rectangular underline tabs across all 6 Alerts & Incidents areas (NO pills, NO capsules).
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AlertsTabKey } from '../models/alerts-monitoring.models';
import { AlertsMonitoringService } from '../services/alerts-monitoring.service';

@Component({
  selector: 'app-alerts-nav',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full bg-white border-b border-slate-200 select-none">
      <nav class="flex items-center gap-1 sm:gap-2 overflow-x-auto no-scrollbar px-1" aria-label="Alerts and Incidents Areas">
        @for (tab of ams.tabDefinitions(); track tab.key) {
          <button
            type="button"
            (click)="onSelectTab(tab.key)"
            class="group relative py-3.5 px-3 sm:px-4 text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer inline-flex items-center gap-2 border-b-2"
            [ngClass]="{
              'border-blue-600 text-blue-600': ams.selectedTab() === tab.key,
              'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300': ams.selectedTab() !== tab.key
            }">
            <span>{{ tab.label }}</span>

            <!-- Contextual badge counter -->
            @if (tab.badgeCount !== undefined && tab.badgeCount > 0) {
              <span 
                class="px-1.5 py-0.2 rounded text-[10px] font-bold"
                [ngClass]="{
                  'bg-rose-100 text-rose-800': tab.key === 'incidents' || (tab.key === 'active' && ams.summary().critical_alerts_count > 0) || (tab.key === 'notifications' && tab.badgeCount > 0),
                  'bg-amber-100 text-amber-800': tab.key === 'evaluation' || (tab.key === 'active' && ams.summary().critical_alerts_count === 0)
                }">
                {{ tab.badgeCount }}
              </span>
            }
          </button>
        }
      </nav>
    </div>
  `
})
export class AlertsNavComponent {
  public ams = inject(AlertsMonitoringService);
  private router = inject(Router);

  public onSelectTab(tabKey: AlertsTabKey): void {
    this.ams.selectTab(tabKey);
    this.router.navigate(['/monitoring/alerts', tabKey]);
  }
}
