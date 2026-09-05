import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OperationalEvent } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-recent-activity',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-6 rounded-2xl bg-white border border-slate-200 flex flex-col gap-4 shadow-xs">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="activity" [size]="18" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-sm font-bold text-slate-900 font-heading">Recent Activity</h2>
        </div>
        <span class="text-[11px] text-slate-500 font-medium">Audit Trail</span>
      </div>

      <!-- Activity Stream (Compact, Low-Profile Height) -->
      @if (events.length === 0) {
        <div class="py-3 flex items-center justify-center gap-3 text-center">
          <div class="w-7 h-7 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 shrink-0">
            <app-lucide-icon name="clock" [size]="14"></app-lucide-icon>
          </div>
          <div class="text-left">
            <span class="text-xs font-bold text-slate-800 inline-block mr-2">No recent activity reported</span>
            <span class="text-[11px] text-slate-500 font-medium">Events will stream here automatically as migration operations execute.</span>
          </div>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-200/80 max-h-48 overflow-y-auto">
          @for (ev of events; track ev.id) {
            <div class="py-2.5 first:pt-0 last:pb-0 flex items-center justify-between gap-4 text-xs">
              <div class="flex items-center gap-3">
                <div class="w-2 h-2 rounded-full bg-blue-600 shrink-0"></div>
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900 text-xs">{{ ev.description }}</span>
                  <span class="text-[11px] text-slate-500 font-medium">Operator: {{ ev.operator }} &bull; {{ ev.migrationName }}</span>
                </div>
              </div>

              <span class="text-xs font-mono text-slate-400 font-medium tabular-nums shrink-0">{{ ev.timestamp }}</span>
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
