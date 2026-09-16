import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MonitoringService } from '../services/monitoring.service';
import { PlatformHealthArea } from '../models/monitoring.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-monitoring-platform-health',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <!-- Platform & Data Path Health (Section 5) -->
    <div class="p-6 rounded-2xl bg-white dark:bg-[#141517] border border-slate-200 dark:border-[#232428] shadow-2xs flex flex-col gap-4 select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-white/[0.08] flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="server" [size]="16" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider font-heading">Platform &amp; Data Path Health</span>
        </div>
        <a
          routerLink="/monitoring/platform"
          class="h-7 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/80 hover:bg-blue-50 dark:hover:bg-blue-950/40 text-slate-700 dark:text-slate-300 hover:text-blue-700 dark:hover:text-blue-400 border border-slate-200 dark:border-slate-700 hover:border-blue-200 dark:hover:border-blue-800/40 text-xs font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 group cursor-pointer">
          <span>Platform Operations</span>
          <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all"></app-lucide-icon>
        </a>
      </div>

      <!-- 6 Major Operational Areas Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        @for (area of ms.platformHealth(); track area.key) {
          <div 
            class="p-4 rounded-xl border transition-all flex flex-col justify-between gap-3 shadow-2xs hover:border-slate-300 dark:hover:border-slate-600 hover:shadow-xs"
            [ngClass]="{
              'bg-white dark:bg-[#1a1b1e] border-slate-200 dark:border-[#26272b]': area.health === 'HEALTHY',
              'bg-amber-50/40 dark:bg-[#1a1b1e] border-amber-300 dark:border-amber-500/80 shadow-[0_0_12px_rgba(245,158,11,0.12)]': area.health === 'DEGRADED',
              'bg-rose-50/40 dark:bg-[#1a1b1e] border-rose-300 dark:border-rose-500/80 shadow-[0_0_12px_rgba(244,63,94,0.12)]': area.health === 'UNHEALTHY',
              'bg-slate-50 dark:bg-[#1a1b1e] border-slate-200 dark:border-[#26272b]': area.health === 'UNKNOWN'
            }">
            
            <!-- Top: Title & Status Badge -->
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-bold text-slate-900 dark:text-slate-100 font-heading">{{ area.title }}</span>
              
              @if (area.health === 'HEALTHY') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span>Healthy</span>
                </span>
              } @else if (area.health === 'DEGRADED') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                  <span>Degraded</span>
                </span>
              } @else if (area.health === 'UNHEALTHY') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-700/60">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                  <span>Unhealthy</span>
                </span>
              } @else {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                  <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                  <span>Unknown</span>
                </span>
              }
            </div>

            <!-- Bottom: Degraded Alert Warning (if abnormal) or Nominal Metric -->
            <div class="pt-2 border-t border-slate-100 dark:border-white/[0.08] flex items-center justify-between text-xs">
              @if (area.degraded_summary) {
                <div class="flex items-center gap-1.5 text-amber-800 dark:text-amber-400 font-semibold truncate">
                  <app-lucide-icon name="alert-circle" [size]="13" class="text-amber-600 dark:text-amber-400 shrink-0"></app-lucide-icon>
                  <span class="truncate">{{ area.degraded_summary }}</span>
                </div>
              } @else {
                <span class="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                  {{ area.active_count }} / {{ area.total_count }} active nodes
                </span>
                <span class="text-emerald-700 dark:text-emerald-400 font-semibold text-[11px]">100% nominal</span>
              }
            </div>

          </div>
        }
      </div>

    </div>
  `
})
export class MonitoringPlatformHealthComponent {
  public ms = inject(MonitoringService);
}
