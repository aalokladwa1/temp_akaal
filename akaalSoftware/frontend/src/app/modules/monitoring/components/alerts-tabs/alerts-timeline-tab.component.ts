/**
 * AKAAL Monitoring — Part 4 of 4: Operational Timeline Tab Component
 * Chronological sequence of alert triggers, incident lifecycle transitions,
 * suppressions, acknowledgments, and notification dispatches.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AlertsMonitoringService } from '../../services/alerts-monitoring.service';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-alerts-timeline-tab',
  standalone: true,
  imports: [CommonModule, CustomSelectComponent, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Search & Category Filter Bar -->
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        
        <!-- Search input -->
        <div class="relative flex-1">
          <app-lucide-icon name="search" [size]="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
          <input
            type="text"
            [value]="ams.timelineSearchQuery()"
            (input)="onSearchInput($event)"
            placeholder="Search timeline events by summary, entity name, or payload..."
            class="w-full pl-9 pr-4 py-2 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 transition-all"
          />
        </div>

        <!-- Category Filter Dropdown -->
        <div class="w-full sm:w-64">
          <app-custom-select
            [options]="categoryOptions"
            [value]="ams.timelineCategoryFilter()"
            (valueChange)="ams.timelineCategoryFilter.set($event)"
            placeholder="Filter Event Category">
          </app-custom-select>
        </div>

      </div>

      <!-- 2. Operational Timeline Stream -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-6">
        
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="history" [size]="16" class="text-blue-600"></app-lucide-icon>
            <h3 class="text-sm font-bold text-slate-900">Chronological Event Stream</h3>
          </div>
          <span class="text-xs font-mono font-medium text-slate-500">
            {{ ams.filteredTimeline().length }} events recorded
          </span>
        </div>

        @if (ams.filteredTimeline().length === 0) {
          <div class="p-8 text-center text-xs text-slate-500">
            No events match the selected timeline filters.
          </div>
        } @else {
          <div class="relative pl-6 border-l-2 border-slate-200 flex flex-col gap-6">
            @for (item of ams.filteredTimeline(); track item.id) {
              <div class="relative flex flex-col gap-2 group">
                
                <!-- Timeline Node Bullet -->
                <span 
                  class="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full border-2 border-white ring-2 ring-slate-100"
                  [ngClass]="{
                    'bg-rose-500': item.severity === 'CRITICAL',
                    'bg-amber-500': item.severity === 'WARNING',
                    'bg-blue-500': item.severity === 'INFO'
                  }">
                </span>

                <!-- Event Meta Header -->
                <div class="flex items-center justify-between gap-3 flex-wrap text-xs">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[11px]">
                      {{ item.timestamp | date:'HH:mm:ss' }}
                    </span>

                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-rose-50 text-rose-700 border border-rose-200': item.category === 'ALERT_FIRING' || item.category === 'DEGRADATION_DETECTED',
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': item.category === 'ALERT_RECOVERY' || item.category === 'NOTIFICATION_DELIVERY',
                        'bg-purple-50 text-purple-700 border border-purple-200': item.category === 'INCIDENT_LIFECYCLE',
                        'bg-blue-50 text-blue-700 border border-blue-200': item.category === 'ACKNOWLEDGEMENT',
                        'bg-slate-100 text-slate-700': item.category === 'SUPPRESSION'
                      }">
                      {{ ams.formatText(item.category) }}
                    </span>

                    <span class="text-slate-400">&bull;</span>

                    <div class="flex items-center gap-1.5">
                      <span class="text-slate-500 font-medium">{{ ams.formatText(item.entity_type) }}:</span>
                      <span class="font-bold text-slate-800">{{ item.entity_name }}</span>
                    </div>
                  </div>

                  @if (item.deep_link_route) {
                    <button
                      type="button"
                      (click)="onNavigate(item.deep_link_route)"
                      class="text-[11px] font-bold text-blue-600 hover:text-blue-800 cursor-pointer inline-flex items-center gap-1">
                      <span>View Target</span>
                      <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                    </button>
                  }
                </div>

                <!-- Event Summary -->
                <p class="text-xs text-slate-800 font-medium leading-relaxed pl-1">
                  {{ item.summary }}
                </p>

                <!-- Monospace Payload Preview if present -->
                @if (item.payload_preview) {
                  <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 font-mono text-[11px] text-slate-600 break-all">
                    {{ item.payload_preview }}
                  </div>
                }

              </div>
            }
          </div>
        }

      </div>

    </div>
  `
})
export class AlertsTimelineTabComponent {
  public ams = inject(AlertsMonitoringService);
  private router = inject(Router);

  public categoryOptions: SelectOption[] = [
    { label: 'All Event Categories', value: 'ALL' },
    { label: 'Alert Firing', value: 'ALERT_FIRING' },
    { label: 'Alert Recovery', value: 'ALERT_RECOVERY' },
    { label: 'Incident Lifecycle', value: 'INCIDENT_LIFECYCLE' },
    { label: 'Acknowledgements', value: 'ACKNOWLEDGEMENT' },
    { label: 'Suppressions', value: 'SUPPRESSION' },
    { label: 'Notification Delivery', value: 'NOTIFICATION_DELIVERY' },
    { label: 'Degradation Detected', value: 'DEGRADATION_DETECTED' }
  ];

  public onSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.ams.timelineSearchQuery.set(target.value);
  }

  public onNavigate(route: string): void {
    if (route) {
      this.router.navigateByUrl(route);
    }
  }
}
