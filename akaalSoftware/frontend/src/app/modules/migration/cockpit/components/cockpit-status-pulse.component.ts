import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { OperationalPulseMetric } from '../cockpit.models';

@Component({
  selector: 'app-cockpit-status-pulse',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
      <!-- Zone 1: 5-Second Status Glance -->
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-5 pb-5 border-b border-slate-100">
        <div class="flex items-start gap-4">
          <div [ngClass]="getStatusIconBgClasses()" class="w-11 h-11 rounded-lg flex items-center justify-center shrink-0 border">
            <app-lucide-icon [name]="getStatusIconName()" [size]="22" [class]="getStatusIconColorClasses()" />
          </div>
          <div class="flex flex-col gap-1.5">
            <div class="flex items-center gap-2.5">
              <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">
                {{ cleanText(store.statusPulse().stateHeading) }}
              </h2>
              <span class="text-xs text-slate-300 font-medium">&middot;</span>
              <span class="text-xs font-semibold text-slate-600">
                {{ cleanText(store.statusPulse().phaseSubtitle) }}
              </span>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-600">
              <span class="text-slate-400 font-medium">Current Task:</span>
              <span class="font-mono font-medium text-slate-800">{{ cleanText(store.statusPulse().activeTaskDescription) }}</span>
            </div>
          </div>
        </div>

        <!-- Duration & Rate Quick Badge (Rectangular with curved corners) -->
        <div class="flex items-center gap-4 self-start lg:self-center shrink-0 bg-slate-50 px-4 py-2.5 rounded-lg border border-slate-200">
          <div class="flex flex-col text-right">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Elapsed Time</span>
            <span class="font-mono text-xs font-bold text-slate-800">{{ store.workloadProgress().elapsedFormatted }}</span>
          </div>
          <div class="h-8 w-[1px] bg-slate-200"></div>
          <div class="flex flex-col text-right">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Current Rate</span>
            <span class="font-mono text-xs font-bold text-blue-700">{{ store.workloadProgress().currentRateFormatted }}</span>
          </div>
        </div>
      </div>

      <!-- Zone 2: Dynamic M1–M7 Mode Metric Ribbon (Rectangular Cards with breathing room) -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-5 py-5 border-b border-slate-100">
        @for (metric of store.statusPulse().metrics; track metric.id) {
          <div class="bg-white hover:border-blue-200 border border-slate-200 rounded-xl p-4 flex flex-col justify-between transition-colors shadow-xs">
            <div class="flex items-center justify-between text-[11px] text-slate-500 font-medium mb-1">
              <span class="tracking-wider uppercase text-[10px] font-bold text-slate-400">{{ cleanText(metric.label) }}</span>
              <span [ngClass]="getMetricIndicatorDot(metric.status)" class="w-2 h-2 rounded-sm"></span>
            </div>
            <div class="flex items-baseline gap-1.5 my-1">
              <span class="font-mono text-base font-bold text-slate-900 tracking-tight">{{ cleanText(metric.value) }}</span>
              @if (metric.unit) {
                <span class="text-xs text-slate-500 font-medium">{{ metric.unit }}</span>
              }
            </div>
            @if (metric.sparkline && metric.sparkline.length > 1) {
              <div class="h-3.5 w-full my-1 overflow-hidden">
                <svg class="w-full h-full" viewBox="0 0 100 18" preserveAspectRatio="none">
                  <path
                    [attr.d]="getSparklineSvgPath(metric.sparkline)"
                    fill="none"
                    [attr.stroke]="getSparklineColor(metric.status)"
                    stroke-width="1.75"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
            }
            @if (metric.detail) {
              <div class="text-[11px] text-slate-400 mt-0.5 truncate" [title]="metric.detail">
                {{ cleanText(metric.detail) }}
              </div>
            }
          </div>
        }
      </div>

      <!-- Zone 3: Workload Progress Bar (Distinct from DAG stages) -->
      <div class="pt-5 flex flex-col gap-2.5">
        <div class="flex items-center justify-between text-xs">
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Workload Execution</span>
            <span class="text-slate-300">&middot;</span>
            <span class="text-slate-700 font-medium">{{ cleanText(store.workloadProgress().phaseDescription) }}</span>
          </div>

          <div class="flex items-center gap-3">
            @if (store.workloadProgress().isContinuous) {
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                <span class="w-2 h-2 rounded-sm bg-blue-500 animate-pulse"></span>
                <span>Continuous Stream</span>
              </span>
            } @else if (!store.workloadProgress().isUnknown) {
              <span class="font-mono font-semibold text-slate-800">
                {{ store.workloadProgress().processedFormatted }} / {{ store.workloadProgress().totalFormatted }}
                <span class="text-slate-400 font-normal">({{ store.workloadProgress().percentage.toFixed(1) }}%)</span>
              </span>
            }

            @if (store.workloadProgress().etaFormatted) {
              <span class="text-slate-300">&middot;</span>
              <span class="text-slate-500">
                ETA: <span class="font-mono font-semibold text-slate-800">{{ store.workloadProgress().etaFormatted }}</span>
              </span>
            }
          </div>
        </div>

        <!-- Visual Progress Track -->
        <div class="relative w-full h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200/60">
          @if (store.workloadProgress().isContinuous) {
            <div class="absolute inset-0 bg-gradient-to-r from-blue-400 via-blue-500 to-blue-400 animate-[shimmer_2s_infinite] w-full"></div>
          } @else if (store.workloadProgress().isUnknown) {
            <div class="absolute inset-0 bg-slate-300 animate-pulse w-full"></div>
          } @else {
            <div
              class="h-full bg-blue-600 transition-all duration-500 ease-out rounded-full"
              [style.width.%]="store.workloadProgress().percentage">
            </div>
          }
        </div>
      </div>
    </section>
  `
})
export class CockpitStatusPulseComponent {
  public store = inject(CockpitStoreService);

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }

  public getStatusIconBgClasses(): string {
    const state = this.store.identity().lifecycleState;
    switch (state) {
      case 'RUNNING': return 'bg-emerald-50 border-emerald-200';
      case 'PAUSED': return 'bg-amber-50 border-amber-200';
      case 'WAITING_FOR_APPROVAL': return 'bg-purple-50 border-purple-200';
      case 'RECOVERING': return 'bg-blue-50 border-blue-200';
      case 'FAILED': return 'bg-rose-50 border-rose-200';
      case 'COMPLETED': return 'bg-slate-50 border-slate-200';
      default: return 'bg-slate-50 border-slate-200';
    }
  }

  public getStatusIconColorClasses(): string {
    const state = this.store.identity().lifecycleState;
    switch (state) {
      case 'RUNNING': return 'text-emerald-600';
      case 'PAUSED': return 'text-amber-600';
      case 'WAITING_FOR_APPROVAL': return 'text-purple-600';
      case 'RECOVERING': return 'text-blue-600';
      case 'FAILED': return 'text-rose-600';
      case 'COMPLETED': return 'text-slate-600';
      default: return 'text-slate-500';
    }
  }

  public getStatusIconName(): string {
    const state = this.store.identity().lifecycleState;
    switch (state) {
      case 'RUNNING': return 'zap';
      case 'PAUSED': return 'pause';
      case 'WAITING_FOR_APPROVAL': return 'shield-alert';
      case 'RECOVERING': return 'rotate-ccw';
      case 'FAILED': return 'alert-octagon';
      case 'COMPLETED': return 'check';
      default: return 'activity';
    }
  }

  public getMetricIndicatorDot(status: OperationalPulseMetric['status']): string {
    switch (status) {
      case 'SUCCESS': return 'bg-emerald-500';
      case 'WARNING': return 'bg-amber-500';
      case 'CRITICAL': return 'bg-rose-500';
      case 'NORMAL': return 'bg-blue-500';
      default: return 'bg-slate-300';
    }
  }

  public getSparklineSvgPath(points: number[]): string {
    if (!points || points.length < 2) return '';
    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1;
    const width = 100;
    const height = 18;
    const step = width / (points.length - 1);
    
    return points.map((p, i) => {
      const x = (i * step).toFixed(1);
      const y = (height - ((p - min) / range) * (height - 4) - 2).toFixed(1);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  }

  public getSparklineColor(status: OperationalPulseMetric['status']): string {
    switch (status) {
      case 'SUCCESS': return '#10b981'; // emerald-500
      case 'WARNING': return '#f59e0b'; // amber-500
      case 'CRITICAL': return '#f43f5e'; // rose-500
      case 'NORMAL': return '#3b82f6'; // blue-500
      default: return '#94a3b8'; // slate-400
    }
  }
}
