import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

interface SpecialistWorkspace {
  title: string;
  route: string;
  icon: string;
}

@Component({
  selector: 'app-reports-workspace-nav',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-2.5 select-none">
      <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
        PRIMARY SPECIALIST WORKSPACES
      </span>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        @for (item of workspaces; track item.title) {
          <a
            [routerLink]="item.route"
            class="h-14 flex items-center justify-between px-4 bg-white border border-slate-200 rounded-xl hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group shadow-2xs">
            
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-8 h-8 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0 group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors text-slate-600">
                <app-lucide-icon 
                  [name]="item.icon" 
                  [size]="16" 
                  class="shrink-0">
                </app-lucide-icon>
              </div>
              <span class="text-xs font-semibold text-slate-800 group-hover:text-blue-600 transition-colors truncate">
                {{ item.title }}
              </span>
            </div>

            <app-lucide-icon 
              name="arrow-right" 
              [size]="14" 
              class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all shrink-0">
            </app-lucide-icon>
          </a>
        }
      </div>
    </div>
  `
})
export class ReportsWorkspaceNavComponent {
  public workspaces: SpecialistWorkspace[] = [
    {
      title: 'Report Library',
      route: '/reports/library',
      icon: 'library'
    },
    {
      title: 'Trust & Certification',
      route: '/reports/certification',
      icon: 'shield-check'
    },
    {
      title: 'Evidence Portal',
      route: '/reports/evidence',
      icon: 'package-check'
    }
  ];
}
