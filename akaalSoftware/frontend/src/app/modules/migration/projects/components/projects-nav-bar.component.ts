import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

export type ProjectsTabType = 'portfolio' | 'projects' | 'initiatives';

@Component({
  selector: 'app-projects-nav-bar',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex items-center justify-between gap-4 border-b border-slate-200 pb-3 flex-wrap">
      
      <!-- GDS Option B Segmented Slider Tabs (Plain Labels, No Unproven Count Badges) -->
      <div class="p-1 bg-slate-100/90 border border-slate-200/70 rounded-lg flex items-center gap-1 select-none">
        
        <!-- 1. Portfolio Overview -->
        <button
          type="button"
          (click)="selectTab('portfolio')"
          class="px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer"
          [class.bg-white]="activeTab() === 'portfolio'"
          [class.text-slate-900]="activeTab() === 'portfolio'"
          [class.shadow-2xs]="activeTab() === 'portfolio'"
          [class.text-slate-600]="activeTab() !== 'portfolio'"
          [class.hover:text-slate-900]="activeTab() !== 'portfolio'">
          <app-lucide-icon name="layout-dashboard" [size]="14" [class.text-blue-600]="activeTab() === 'portfolio'"></app-lucide-icon>
          <span>Portfolio</span>
        </button>

        <!-- 2. Projects Discovery -->
        <button
          type="button"
          (click)="selectTab('projects')"
          class="px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer"
          [class.bg-white]="activeTab() === 'projects'"
          [class.text-slate-900]="activeTab() === 'projects'"
          [class.shadow-2xs]="activeTab() === 'projects'"
          [class.text-slate-600]="activeTab() !== 'projects'"
          [class.hover:text-slate-900]="activeTab() !== 'projects'">
          <app-lucide-icon name="layers" [size]="14" [class.text-blue-600]="activeTab() === 'projects'"></app-lucide-icon>
          <span>Projects</span>
        </button>

        <!-- 3. Initiatives Discovery -->
        <button
          type="button"
          (click)="selectTab('initiatives')"
          class="px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer"
          [class.bg-white]="activeTab() === 'initiatives'"
          [class.text-slate-900]="activeTab() === 'initiatives'"
          [class.shadow-2xs]="activeTab() === 'initiatives'"
          [class.text-slate-600]="activeTab() !== 'initiatives'"
          [class.hover:text-slate-900]="activeTab() !== 'initiatives'">
          <app-lucide-icon name="target" [size]="14" [class.text-blue-600]="activeTab() === 'initiatives'"></app-lucide-icon>
          <span>Initiatives</span>
        </button>

      </div>

      <!-- Context Subtext -->
      <div class="text-xs text-slate-500 font-medium hidden sm:block">
        @switch (activeTab()) {
          @case ('portfolio') {
            <span>Portfolio orientation and high-level operational activity</span>
          }
          @case ('projects') {
            <span>Governed operational workspaces for migration &amp; validation</span>
          }
          @case ('initiatives') {
            <span>Strategic multi-project transformation programs</span>
          }
        }
      </div>

    </div>
  `
})
export class ProjectsNavBarComponent {
  public activeTab = input<ProjectsTabType>('portfolio');
  public tabChange = output<ProjectsTabType>();

  public selectTab(tab: ProjectsTabType): void {
    this.tabChange.emit(tab);
  }
}
