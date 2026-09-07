import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { WorkstationWorkspaceTab } from '../validation-workstation.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-workstation-nav',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <nav class="bg-white border-b border-slate-200 px-6 lg:px-8">
      <div class="max-w-[1680px] mx-auto flex items-center gap-8 overflow-x-auto no-scrollbar">
        
        <!-- Tab 1: Overview (Fully authorized & implemented) -->
        <button
          type="button"
          (click)="store.setActiveTab('overview')"
          [class.border-blue-600]="store.activeTab() === 'overview'"
          [class.text-blue-600]="store.activeTab() === 'overview'"
          [class.border-transparent]="store.activeTab() !== 'overview'"
          [class.text-slate-600]="store.activeTab() !== 'overview'"
          class="h-12 border-b-2 font-medium text-xs flex items-center gap-2 hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer">
          <app-lucide-icon name="layout-dashboard" [size]="14" />
          <span>Overview</span>
        </button>

        <!-- Tab 2: Discrepancies (Stub with contextual transition) -->
        <button
          type="button"
          (click)="store.setActiveTab('discrepancies')"
          [class.border-blue-600]="store.activeTab() === 'discrepancies'"
          [class.text-blue-600]="store.activeTab() === 'discrepancies'"
          [class.border-transparent]="store.activeTab() !== 'discrepancies'"
          [class.text-slate-600]="store.activeTab() !== 'discrepancies'"
          class="h-12 border-b-2 font-medium text-xs flex items-center gap-2 hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer">
          <app-lucide-icon name="alert-triangle" [size]="14" />
          <span>Discrepancies</span>
          @if (getDiscrepancyCount() > 0) {
            <span class="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-rose-100 text-rose-700 border border-rose-200">
              {{ getDiscrepancyCount() }}
            </span>
          }
        </button>

        <!-- Tab 3: Repair & Revalidation (Stub with contextual transition) -->
        <button
          type="button"
          (click)="store.setActiveTab('repair')"
          [class.border-blue-600]="store.activeTab() === 'repair'"
          [class.text-blue-600]="store.activeTab() === 'repair'"
          [class.border-transparent]="store.activeTab() !== 'repair'"
          [class.text-slate-600]="store.activeTab() !== 'repair'"
          class="h-12 border-b-2 font-medium text-xs flex items-center gap-2 hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer">
          <app-lucide-icon name="wrench" [size]="14" />
          <span>Repair &amp; Revalidation</span>
          @if (store.state().remediation.revalidationCount; as count) {
            @if (count > 0) {
              <span class="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-blue-100 text-blue-700 border border-blue-200">
                {{ count }}
              </span>
            }
          }
        </button>

        <!-- Tab 4: Results & Evidence (Stub with contextual transition) -->
        <button
          type="button"
          (click)="store.setActiveTab('evidence')"
          [class.border-blue-600]="store.activeTab() === 'evidence'"
          [class.text-blue-600]="store.activeTab() === 'evidence'"
          [class.border-transparent]="store.activeTab() !== 'evidence'"
          [class.text-slate-600]="store.activeTab() !== 'evidence'"
          class="h-12 border-b-2 font-medium text-xs flex items-center gap-2 hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer">
          <app-lucide-icon name="file-text" [size]="14" />
          <span>Results &amp; Evidence</span>
          @if (store.state().technicalDrawer.evidenceHash) {
            <span class="w-2 h-2 rounded-sm bg-emerald-500" title="Evidence bundle signed"></span>
          }
        </button>
      </div>
    </nav>
  `
})
export class WorkstationNavComponent {
  readonly store = inject(ValidationWorkstationService);

  getDiscrepancyCount(): number {
    const diffRows = this.store.state().coverage.find(c => c.dimension === 'Records');
    return diffRows?.differencesDetected || 0;
  }
}
