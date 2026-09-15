import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MonitoringService } from '../services/monitoring.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-monitoring-needs-attention',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <!-- Needs Attention (Section 3) -->
    <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4 select-none">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Needs Attention</span>
          <span 
            class="px-2 py-0.5 rounded-md text-[11px] font-semibold border"
            [ngClass]="ms.needsAttention().length > 0 
              ? 'bg-amber-50 text-amber-700 border-amber-200' 
              : 'bg-slate-100 text-slate-700 border-slate-200'">
            {{ ms.needsAttention().length }}
          </span>
        </div>
      </div>

      <!-- Content: Calm Healthy Empty State or Curated Triage Items -->
      @if (ms.needsAttention().length === 0) {
        <div class="py-10 flex flex-col items-center justify-center text-center gap-1.5 text-slate-500">
          <app-lucide-icon name="shield-check" [size]="28" class="text-emerald-500"></app-lucide-icon>
          <span class="text-xs font-semibold text-slate-800">
            No current operational conditions require attention.
          </span>
          <p class="text-[11px] text-slate-500 font-medium">
            All registered pipelines, connectors, and platform resources are executing normally.
          </p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-100">
          @for (item of ms.needsAttention(); track item.id) {
            <div class="py-3.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              
              <!-- Left: Condition Details -->
              <div class="flex items-start gap-3 min-w-0">
                
                <!-- Severity Indicator Dot (Circular) -->
                <div 
                  class="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  [ngClass]="{
                    'bg-rose-600': item.severity === 'CRITICAL',
                    'bg-amber-500': item.severity === 'WARNING',
                    'bg-blue-500': item.severity === 'INFO',
                    'bg-slate-400': item.severity === 'UNKNOWN'
                  }">
                </div>

                <div class="flex flex-col min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-xs font-bold text-slate-900">{{ item.condition_title }}</span>
                    <span class="text-slate-300">&bull;</span>
                    <span class="text-xs font-semibold text-blue-700 truncate">{{ item.entity_name }}</span>
                  </div>

                  <p class="text-xs text-slate-600 font-normal mt-0.5 leading-snug">
                    {{ item.condition_detail }}
                  </p>

                  <!-- Metadata Strip: Duration & Direction -->
                  <div class="flex items-center gap-3 mt-1.5 text-[11px] text-slate-500 font-mono">
                    <span class="flex items-center gap-1">
                      <span class="font-sans font-medium text-slate-400">Duration:</span>
                      <span class="font-bold text-slate-700">{{ item.duration_label }}</span>
                    </span>
                    <span>&bull;</span>
                    <span class="flex items-center gap-1">
                      <span class="font-sans font-medium text-slate-400">Direction:</span>
                      <span 
                        class="font-bold capitalize"
                        [ngClass]="{
                          'text-emerald-700': item.direction === 'improving',
                          'text-slate-700': item.direction === 'stable',
                          'text-rose-700': item.direction === 'worsening',
                          'text-slate-500': item.direction === 'unknown'
                        }">
                        {{ item.direction }}
                      </span>
                    </span>
                  </div>
                </div>

              </div>

              <!-- Right: Investigation Deep Link (Secondary Action Button) -->
              <div class="shrink-0 sm:self-center">
                <a
                  [routerLink]="item.deep_link_route"
                  class="h-8 px-3 rounded-lg border border-slate-200 hover:border-blue-300 bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs font-semibold transition-colors inline-flex items-center gap-1.5 cursor-pointer shadow-2xs group">
                  <span>{{ item.deep_link_label || 'Investigate' }}</span>
                  <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all"></app-lucide-icon>
                </a>
              </div>

            </div>
          }
        </div>
      }

    </div>
  `
})
export class MonitoringNeedsAttentionComponent {
  public ms = inject(MonitoringService);
}
