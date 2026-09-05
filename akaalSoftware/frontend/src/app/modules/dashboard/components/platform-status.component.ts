import { Component, Input, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SubsystemStatus } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-platform-status',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between gap-6 shadow-xs h-full flex-1">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="server" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Platform Status</h2>
        </div>
        <span class="text-xs text-slate-500 font-medium">{{ subsystems.length }} subsystems</span>
      </div>

      <!-- Subsystems Vertical List with Darkened Dividers -->
      <div class="flex flex-col divide-y divide-slate-200/80">
        @for (sub of subsystems; track sub.name) {
          <div class="py-2.5 first:pt-0 last:pb-0 flex items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-700 shrink-0">
                @switch (sub.name) {
                  @case ('DevKros Engine Core') { <app-lucide-icon name="server" [size]="16"></app-lucide-icon> }
                  @case ('Named Pipe IPC') { <app-lucide-icon name="network" [size]="16"></app-lucide-icon> }
                  @case ('Worker Concurrency Pool') { <app-lucide-icon name="cpu" [size]="16"></app-lucide-icon> }
                  @default { <app-lucide-icon name="hard-drive" [size]="16"></app-lucide-icon> }
                }
              </div>
              <div class="flex flex-col">
                <span class="text-xs font-bold text-slate-900">{{ sub.name }}</span>
                <span class="text-[11px] text-slate-500 font-medium truncate max-w-[200px] sm:max-w-xs">{{ sub.detail || 'Not reported' }}</span>
              </div>
            </div>

            <!-- GDS Option A Status Badge -->
            <div class="flex items-center gap-2 shrink-0">
              @if (sub.status === 'healthy') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 select-none">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span>Healthy</span>
                </span>
              } @else if (sub.status === 'degraded') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 select-none">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                  <span>Degraded</span>
                </span>
              } @else if (sub.status === 'unhealthy') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 select-none">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                  <span>Unhealthy</span>
                </span>
              } @else {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 select-none">
                  <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                  <span>Offline</span>
                </span>
              }
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class PlatformStatusComponent {
  @HostBinding('class') public hostClass = 'flex flex-col h-full flex-1';
  @Input() public subsystems: SubsystemStatus[] = [];
}
