import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationDiscrepanciesService } from '../validation-discrepancies.service';
import { ScopeNavigatorItem } from '../validation-discrepancies.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-discrepancies-navigator',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <aside class="bg-white border border-slate-200/80 rounded-xl p-5 shadow-2xs flex flex-col gap-4 w-full lg:w-72 shrink-0">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
            <app-lucide-icon name="folder-tree" [size]="13"></app-lucide-icon>
          </div>
          <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
            Scope Objects
          </h3>
        </div>
        <span class="text-[11px] font-semibold text-slate-500 font-mono bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
          {{ store.navigator().length }} Objects
        </span>
      </div>

      <!-- Tree / List Container (Bounded scrollable container matching table height) -->
      <div class="flex flex-col gap-1.5 overflow-y-auto max-h-[380px] pr-1">
        
        <!-- Object Nodes -->
        @for (obj of store.navigator(); track obj.objectName) {
          <div class="flex flex-col gap-1">
            
            <!-- Object Header Row -->
            <div
              (click)="selectObject(obj.objectName)"
              [class.bg-blue-50]="store.selectedObjectFilter() === obj.objectName && store.selectedPartitionFilter() === null"
              [class.text-blue-700]="store.selectedObjectFilter() === obj.objectName && store.selectedPartitionFilter() === null"
              [class.border-blue-200]="store.selectedObjectFilter() === obj.objectName && store.selectedPartitionFilter() === null"
              [class.border-slate-100]="store.selectedObjectFilter() !== obj.objectName || store.selectedPartitionFilter() !== null"
              class="w-full flex items-center justify-between px-3 py-2 rounded-lg border text-left text-xs font-semibold hover:bg-slate-50 transition-colors cursor-pointer group">
              
              <div class="flex items-center gap-2 min-w-0">
                <!-- Expand toggle button if partitions exist -->
                @if (obj.partitions.length > 0) {
                  <button
                    type="button"
                    (click)="toggleExpand(obj.objectName, $event)"
                    class="p-0.5 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-600 cursor-pointer">
                    <app-lucide-icon [name]="isExpanded(obj.objectName) ? 'chevron-down' : 'chevron-right'" [size]="13"></app-lucide-icon>
                  </button>
                } @else {
                  <app-lucide-icon name="table" [size]="13" class="text-slate-400 shrink-0 ml-1"></app-lucide-icon>
                }

                <span class="truncate font-mono text-[11.5px]" [title]="obj.objectName">{{ obj.objectName }}</span>
              </div>

              <span class="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-50 text-rose-700 border border-rose-200">
                {{ obj.totalFindings }}
              </span>
            </div>

            <!-- Partition Children (If expanded & localized) -->
            @if (isExpanded(obj.objectName) && obj.partitions.length > 0) {
              <div class="flex flex-col gap-0.5 pl-6 pt-0.5 border-l-2 border-slate-100 ml-4">
                @for (part of obj.partitions; track part.partitionId) {
                  <button
                    type="button"
                    (click)="selectPartition(part.partitionId, obj.objectName)"
                    [class.bg-blue-50]="store.selectedPartitionFilter() === part.partitionId"
                    [class.text-blue-700]="store.selectedPartitionFilter() === part.partitionId"
                    [class.border-blue-200]="store.selectedPartitionFilter() === part.partitionId"
                    [class.border-transparent]="store.selectedPartitionFilter() !== part.partitionId"
                    class="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md border text-left text-[11px] font-medium hover:bg-slate-50 transition-colors cursor-pointer">
                    <div class="flex items-center gap-1.5 min-w-0">
                      <app-lucide-icon name="grid-2x2" [size]="11" class="text-slate-400 shrink-0"></app-lucide-icon>
                      <span class="truncate font-mono">{{ part.partitionId }}</span>
                    </div>
                    <span class="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold text-slate-600 bg-slate-100">
                      {{ part.findingsCount }}
                    </span>
                  </button>
                }
              </div>
            }

            <!-- Truthful Localization Unavailable Note (When object lacks localized partitions) -->
            @if (!obj.localizationAvailable && store.selectedObjectFilter() === obj.objectName) {
              <div class="pl-5 pt-1 pb-0.5 text-[10.5px] text-slate-400 flex items-center gap-1.5">
                <app-lucide-icon name="info" [size]="11" class="text-slate-400 shrink-0"></app-lucide-icon>
                <span>Partition localization unavailable</span>
              </div>
            }

          </div>
        }

      </div>
    </aside>
  `
})
export class DiscrepanciesNavigatorComponent {
  readonly store = inject(ValidationDiscrepanciesService);

  private expandedMap = signal<Record<string, boolean>>({
    'public.customers': true,
    'public.orders': true
  });

  isExpanded(objectName: string): boolean {
    return !!this.expandedMap()[objectName];
  }

  toggleExpand(objectName: string, event: MouseEvent): void {
    event.stopPropagation();
    this.expandedMap.update(curr => ({
      ...curr,
      [objectName]: !curr[objectName]
    }));
  }

  selectObject(objectName: string): void {
    if (this.store.selectedObjectFilter() === objectName && this.store.selectedPartitionFilter() === null) {
      this.store.setObjectFilter(null);
    } else {
      this.store.setObjectFilter(objectName);
    }
  }

  selectPartition(partitionId: string, objectName: string): void {
    if (this.store.selectedPartitionFilter() === partitionId) {
      this.store.setPartitionFilter(null, objectName);
    } else {
      this.store.setPartitionFilter(partitionId, objectName);
    }
  }
}
