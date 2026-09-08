import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { ConnectionWorkspaceTab } from '../connection-workspace.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

export interface TabDef {
  key: ConnectionWorkspaceTab;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-workspace-nav',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <nav class="bg-white border-b border-slate-200 px-6 lg:px-8 select-none">
      <div class="max-w-[1680px] mx-auto flex items-center gap-8 overflow-x-auto no-scrollbar">
        
        @for (tab of tabs; track tab.key) {
          <button
            type="button"
            (click)="ws.setActiveTab(tab.key)"
            [class.border-blue-600]="ws.activeTab() === tab.key"
            [class.text-blue-600]="ws.activeTab() === tab.key"
            [class.font-bold]="ws.activeTab() === tab.key"
            [class.border-transparent]="ws.activeTab() !== tab.key"
            [class.text-slate-600]="ws.activeTab() !== tab.key"
            [class.font-medium]="ws.activeTab() !== tab.key"
            class="h-12 border-b-2 text-xs flex items-center gap-2 hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer">
            <app-lucide-icon [name]="tab.icon" [size]="14"></app-lucide-icon>
            <span>{{ tab.label }}</span>
            
            <!-- Usage Count Indicator -->
            @if (tab.key === 'usage' && ws.connection()?.usage?.projects?.length; as count) {
              <span class="px-1.5 py-0.2 text-[10px] font-mono font-bold rounded bg-slate-100 text-slate-600 border border-slate-200">
                {{ count }}
              </span>
            }

            <!-- Activity Count Indicator -->
            @if (tab.key === 'activity' && ws.connection()?.activities?.length; as actCount) {
              <span class="px-1.5 py-0.2 text-[10px] font-mono font-bold rounded bg-slate-100 text-slate-600 border border-slate-200">
                {{ actCount }}
              </span>
            }

            <!-- Stale Verification Dot on Capabilities -->
            @if (tab.key === 'capabilities' && ws.isVerificationStale()) {
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500" title="Verification is stale"></span>
            }
          </button>
        }

      </div>
    </nav>
  `
})
export class WorkspaceNavComponent {
  public ws = inject(ConnectionWorkspaceService);

  public tabs: TabDef[] = [
    { key: 'overview', label: 'Overview', icon: 'layout-dashboard' },
    { key: 'configuration', label: 'Configuration', icon: 'sliders' },
    { key: 'capabilities', label: 'Capabilities', icon: 'shield-check' },
    { key: 'usage', label: 'Usage', icon: 'folder-git-2' },
    { key: 'activity', label: 'Activity', icon: 'history' },
    { key: 'settings', label: 'Settings', icon: 'settings' }
  ];
}
