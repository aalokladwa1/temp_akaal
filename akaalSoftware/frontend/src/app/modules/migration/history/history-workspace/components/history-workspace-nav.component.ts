import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HistoryWorkspaceService } from '../history-workspace.service';
import {
  HistoryWorkspaceTab,
  HISTORY_WORKSPACE_TABS,
  WorkspaceTabDescriptor
} from '../history-workspace.models';

@Component({
  selector: 'app-history-workspace-nav',
  standalone: true,
  imports: [CommonModule],
  template: `
    <nav class="bg-white border-b border-slate-200 px-6 overflow-x-auto select-none" aria-label="History Workspace Sections">
      <div class="flex items-center space-x-1 min-w-max" role="tablist">
        @for (tab of tabs; track tab.id) {
          <button
            type="button"
            role="tab"
            [id]="'tab-' + tab.id"
            [attr.aria-selected]="hws.activeTab() === tab.id"
            [attr.aria-controls]="'panel-' + tab.id"
            (click)="selectTab(tab.id)"
            (keydown)="onKeyDown($event, tab.id)"
            class="group inline-flex items-center gap-2 py-3 px-3.5 text-xs font-medium border-b-2 transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
            [ngClass]="{
              'border-slate-900 text-slate-900 font-bold': hws.activeTab() === tab.id,
              'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300': hws.activeTab() !== tab.id
            }">
            <span>{{ tab.label }}</span>

            <!-- Contextual Badges -->
            @if (getTabBadge(tab.id); as badge) {
              <span class="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-semibold"
                [ngClass]="badge.class">
                {{ badge.text }}
              </span>
            }
          </button>
        }
      </div>
    </nav>
  `
})
export class HistoryWorkspaceNavComponent {
  public hws = inject(HistoryWorkspaceService);
  private router = inject(Router);

  public tabs: WorkspaceTabDescriptor[] = HISTORY_WORKSPACE_TABS;

  public selectTab(tabId: HistoryWorkspaceTab): void {
    this.hws.setActiveTab(tabId);
    
    // Update route URL seamlessly without reload
    const record = this.hws.currentRecord();
    if (record) {
      const isMigrationPrefix = this.router.url.startsWith('/migration');
      const basePath = isMigrationPrefix
        ? `/migration/history/${record.migrationId}`
        : `/history/${record.migrationId}`;
      this.router.navigate([basePath, tabId], { replaceUrl: true });
    }
  }

  public getTabBadge(tabId: HistoryWorkspaceTab): { text: string; class: string } | null {
    const record = this.hws.currentRecord();
    if (!record) return null;

    switch (tabId) {
      case 'governance':
        if (record.governance && record.governance.length > 0) {
          const req = record.governance[0];
          return {
            text: `${req.quorumSatisfied}/${req.quorumRequired}`,
            class: req.makerCheckerSatisfied ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
          };
        }
        return null;

      case 'validation':
        if (record.validationRuns && record.validationRuns.length > 0) {
          const val = record.validationRuns[0];
          if (val.discrepancyCount > 0) {
            return {
              text: `${val.discrepancyCount} diffs`,
              class: 'bg-amber-50 text-amber-700 border border-amber-200'
            };
          }
        }
        return null;

      case 'cutover':
        if (!record.cutover.isApplicableToMode) {
          return {
            text: 'N/A',
            class: 'bg-slate-100 text-slate-500 border border-slate-200'
          };
        }
        return null;

      case 'evidence':
        if (record.evidence && record.evidence.integrity === 'SHA256_VERIFIED') {
          return {
            text: 'Sealed',
            class: 'bg-emerald-50 text-emerald-700 border border-emerald-200'
          };
        }
        return null;

      default:
        return null;
    }
  }

  public onKeyDown(event: KeyboardEvent, currentTab: HistoryWorkspaceTab): void {
    const currentIndex = this.tabs.findIndex(t => t.id === currentTab);
    let nextIndex = -1;

    if (event.key === 'ArrowRight') {
      nextIndex = (currentIndex + 1) % this.tabs.length;
      event.preventDefault();
    } else if (event.key === 'ArrowLeft') {
      nextIndex = (currentIndex - 1 + this.tabs.length) % this.tabs.length;
      event.preventDefault();
    } else if (event.key === 'Home') {
      nextIndex = 0;
      event.preventDefault();
    } else if (event.key === 'End') {
      nextIndex = this.tabs.length - 1;
      event.preventDefault();
    }

    if (nextIndex >= 0) {
      const nextTab = this.tabs[nextIndex];
      this.selectTab(nextTab.id);
      const btn = document.getElementById('tab-' + nextTab.id);
      btn?.focus();
    }
  }
}
