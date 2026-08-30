import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SubsystemStatus } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-platform-status',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200/90 flex flex-col gap-6 shadow-xs h-full">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="server" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Platform Status</h2>
        </div>
        <span class="text-xs text-slate-600 font-semibold">{{ subsystems.length }} subsystems</span>
      </div>

      <!-- Subsystems Vertical List -->
      <div class="flex flex-col divide-y divide-slate-100">
        @for (sub of subsystems; track sub.name) {
          <div class="py-3.5 first:pt-0 last:pb-0 flex items-center justify-between gap-4">
            <div class="flex items-center gap-3.5">
              <div class="w-8 h-8 rounded-xl bg-slate-50 border border-slate-200/60 flex items-center justify-center text-slate-700">
                @switch (sub.name) {
                  @case ('DevKros Engine Core') { <app-lucide-icon name="server" [size]="16"></app-lucide-icon> }
                  @case ('Named Pipe IPC') { <app-lucide-icon name="network" [size]="16"></app-lucide-icon> }
                  @case ('Worker Concurrency Pool') { <app-lucide-icon name="cpu" [size]="16"></app-lucide-icon> }
                  @default { <app-lucide-icon name="hard-drive" [size]="16"></app-lucide-icon> }
                }
              </div>
              <div class="flex flex-col">
                <span class="text-xs font-bold text-slate-900">{{ sub.name }}</span>
                <span class="text-[11px] text-slate-600 font-medium">{{ sub.detail || 'Not reported' }}</span>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <span 
                class="px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider"
                [class.bg-emerald-50]="sub.status === 'healthy'"
                [class.text-emerald-700]="sub.status === 'healthy'"
                [class.border]="sub.status === 'healthy'"
                [class.border-emerald-200]="sub.status === 'healthy'"
                [class.bg-amber-50]="sub.status === 'degraded'"
                [class.text-amber-700]="sub.status === 'degraded'"
                [class.bg-rose-50]="sub.status === 'unhealthy'"
                [class.text-rose-700]="sub.status === 'unhealthy'"
                [class.bg-slate-100]="sub.status === 'unavailable' || sub.status === 'unknown'"
                [class.text-slate-700]="sub.status === 'unavailable' || sub.status === 'unknown'">
                {{ sub.status }}
              </span>
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class PlatformStatusComponent {
  @Input() public subsystems: SubsystemStatus[] = [];
}
