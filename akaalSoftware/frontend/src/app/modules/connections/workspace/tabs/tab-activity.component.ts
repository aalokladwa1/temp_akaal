import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { ActivityCategory } from '../connection-workspace.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-tab-activity',
  standalone: true,
  imports: [CommonModule, LucideIconComponent, CustomSelectComponent],
  template: `
    @if (ws.connection(); as conn) {
      <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
        
        <!-- Top Header & Filter Controls -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-3">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
              Activity &amp; Governance History
            </h2>
            <p class="text-xs text-slate-500 font-normal">
              Chronological log of configuration modifications, verification tests, secret rotations, and lifecycle actions.
            </p>
          </div>

          <!-- Category Filter (GDS Select) -->
          <div class="w-56">
            <app-custom-select
              [options]="categoryOptions"
              [value]="ws.activityCategoryFilter()"
              [size]="'sm'"
              (valueChange)="onCategoryChange($event)">
            </app-custom-select>
          </div>
        </div>

        <!-- Activity Timeline / List -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-6">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="history" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                Audit Timeline ({{ ws.filteredActivities().length }} Events)
              </span>
            </div>
          </div>

          @if (ws.filteredActivities().length > 0) {
            <div class="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
              
              @for (act of ws.filteredActivities(); track act.id) {
                <div class="relative flex items-start justify-between gap-4 group">
                  
                  <!-- Timeline Node Dot / Icon -->
                  <div class="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-white border-2 border-slate-300 flex items-center justify-center text-slate-500 group-hover:border-blue-500 group-hover:text-blue-600 transition-colors shadow-2xs">
                    <app-lucide-icon [name]="act.icon || 'activity'" [size]="10"></app-lucide-icon>
                  </div>

                  <!-- Event Content -->
                  <div class="flex flex-col gap-1 pr-4 min-w-0">
                    <div class="flex items-center gap-2.5 flex-wrap">
                      <span class="font-bold text-slate-900 text-xs">{{ act.title }}</span>
                      
                      @if (act.stateBadge; as b) {
                        <span
                          class="px-2 py-0.2 rounded text-[10px] font-semibold"
                          [class.bg-emerald-50]="b.type === 'success'"
                          [class.text-emerald-700]="b.type === 'success'"
                          [class.border-emerald-200]="b.type === 'success'"
                          [class.border]="true"
                          [class.bg-amber-50]="b.type === 'warning'"
                          [class.text-amber-700]="b.type === 'warning'"
                          [class.border-amber-200]="b.type === 'warning'"
                          [class.bg-rose-50]="b.type === 'danger'"
                          [class.text-rose-700]="b.type === 'danger'"
                          [class.border-rose-200]="b.type === 'danger'"
                          [class.bg-blue-50]="b.type === 'info'"
                          [class.text-blue-700]="b.type === 'info'"
                          [class.border-blue-200]="b.type === 'info'"
                          [class.bg-slate-100]="b.type === 'neutral'"
                          [class.text-slate-700]="b.type === 'neutral'"
                          [class.border-slate-200]="b.type === 'neutral'">
                          {{ b.label }}
                        </span>
                      }
                    </div>

                    <p class="text-xs text-slate-600 leading-relaxed">{{ act.description }}</p>

                    <div class="flex items-center gap-2 text-[11px] text-slate-400 pt-0.5">
                      <span class="font-mono text-slate-500">Actor: {{ act.actor }}</span>
                      <span>&bull;</span>
                      <span>Category: {{ act.category }}</span>
                    </div>
                  </div>

                  <!-- Timestamp -->
                  <div class="text-right shrink-0">
                    <div class="text-[11px] font-mono font-medium text-slate-500">{{ act.timestamp | date:'medium' }}</div>
                  </div>

                </div>
              }

            </div>
          } @else {
            <div class="p-8 text-center text-slate-400 text-xs bg-slate-50 rounded-lg border border-dashed border-slate-200">
              No activity records match the selected category filter.
            </div>
          }
        </div>

      </div>
    }
  `
})
export class TabActivityComponent {
  public ws = inject(ConnectionWorkspaceService);

  public categoryOptions: CustomSelectOption[] = [
    { label: 'All Activity Events', value: 'ALL' },
    { label: 'Configuration Changes', value: 'CONFIG' },
    { label: 'Connection Tests & Probes', value: 'TEST' },
    { label: 'Security & Secret Events', value: 'SECURITY' },
    { label: 'Lifecycle & Governance', value: 'LIFECYCLE' }
  ];

  public onCategoryChange(val: string): void {
    this.ws.activityCategoryFilter.set(val as ActivityCategory);
  }
}
