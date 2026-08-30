import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OperationalEvent } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-recent-activity',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200/90 flex flex-col gap-6 shadow-xs">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="activity" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Recent Activity</h2>
        </div>
        <span class="text-xs text-slate-600 font-semibold">Audit Trail</span>
      </div>

      <!-- Activity Stream -->
      @if (events.length === 0) {
        <div class="py-12 flex flex-col items-center justify-center text-center gap-2">
          <app-lucide-icon name="clock" [size]="24" class="text-slate-400"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-800">No recent activity has been reported</span>
          <p class="text-[11px] text-slate-600 font-medium">Events will populate as operations execute.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-100">
          @for (ev of events; track ev.id) {
            <div class="py-4 first:pt-0 last:pb-0 flex items-start justify-between gap-4 text-xs">
              <div class="flex items-start gap-3.5">
                <div class="w-2.5 h-2.5 rounded-full bg-blue-600 mt-1.5 shrink-0"></div>
                <div class="flex flex-col gap-1">
                  <span class="font-bold text-slate-900 text-sm">{{ ev.description }}</span>
                  <span class="text-xs text-slate-600 font-medium">Operator: {{ ev.operator }} &bull; {{ ev.migrationName }}</span>
                </div>
              </div>

              <span class="text-xs text-slate-500 font-medium shrink-0">{{ ev.timestamp }}</span>
            </div>
          }
        </div>
      }

    </div>
  `
})
export class RecentActivityComponent {
  @Input() public events: OperationalEvent[] = [];
}
