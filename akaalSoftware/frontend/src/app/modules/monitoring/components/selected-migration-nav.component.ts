import { Component, inject, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MIGRATION_TABS, MigrationTabKey } from '../models/migration-monitoring.models';
import { MigrationMonitoringService } from '../services/migration-monitoring.service';

@Component({
  selector: 'app-selected-migration-nav',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full bg-white border-b border-slate-200 select-none">
      <nav class="flex items-center gap-1 sm:gap-2 overflow-x-auto no-scrollbar px-1" aria-label="Migration Investigation Areas">
        @for (tab of tabs; track tab.key) {
          <button
            type="button"
            (click)="onSelectTab(tab.key)"
            class="group relative py-3.5 px-3 sm:px-4 text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer inline-flex items-center gap-2 border-b-2"
            [ngClass]="{
              'border-blue-600 text-blue-600': mms.selectedTab() === tab.key,
              'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300': mms.selectedTab() !== tab.key
            }">
            <span>{{ tab.label }}</span>

            <!-- Contextual Badge Counters (e.g. Alerts/Anomalies) -->
            @if (tab.key === 'alerts' && alertCount > 0) {
              <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                {{ alertCount }}
              </span>
            }
          </button>
        }
      </nav>
    </div>
  `
})
export class SelectedMigrationNavComponent {
  @Input() migrationId: string = '';
  @Input() alertCount: number = 0;

  public mms = inject(MigrationMonitoringService);
  private router = inject(Router);
  public tabs = MIGRATION_TABS;

  public onSelectTab(tabKey: MigrationTabKey): void {
    this.mms.selectTab(tabKey);
    if (this.migrationId) {
      this.router.navigate(['/monitoring/migrations', this.migrationId, tabKey]);
    }
  }
}
