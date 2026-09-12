import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { TEMPLATE_WORKSPACE_TABS, TemplateWorkspaceTab, TabNavigationItem } from '../template-workspace.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-template-workspace-nav',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <nav aria-label="Template Workspace Navigation" class="bg-white border-b border-slate-200 px-6 lg:px-8 select-none">
      <div role="tablist" class="max-w-[1680px] mx-auto flex items-center gap-8 overflow-x-auto no-scrollbar">
        
        @for (tab of tabs; track tab.key) {
          <button
            type="button"
            role="tab"
            [attr.aria-selected]="ws.activeTab() === tab.key"
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
            
            <!-- Versions Count Indicator -->
            @if (tab.key === 'versions' && ws.template()?.versions?.length; as vCount) {
              <span class="px-1.5 py-0.2 text-[10px] font-mono font-bold rounded bg-slate-100 text-slate-600 border border-slate-200">
                {{ vCount }}
              </span>
            }

            <!-- Usage Count Indicator -->
            @if (tab.key === 'usage' && ws.template()?.usage?.migrations?.length; as count) {
              <span class="px-1.5 py-0.2 text-[10px] font-mono font-bold rounded bg-slate-100 text-slate-600 border border-slate-200">
                {{ count }}
              </span>
            }

            <!-- Activity Count Indicator -->
            @if (tab.key === 'activity' && ws.template()?.activities?.length; as actCount) {
              <span class="px-1.5 py-0.2 text-[10px] font-mono font-bold rounded bg-slate-100 text-slate-600 border border-slate-200">
                {{ actCount }}
              </span>
            }
          </button>
        }

      </div>
    </nav>
  `
})
export class TemplateWorkspaceNavComponent {
  public ws = inject(TemplateWorkspaceService);
  public tabs: TabNavigationItem[] = TEMPLATE_WORKSPACE_TABS;
}
