import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { SubsystemHealthEntry, EngineHealthState } from '../cockpit.models';

@Component({
  selector: 'app-cockpit-engine-health',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      <!-- Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="server" [size]="18" class="text-blue-600" />
          <h3 class="text-base font-bold text-slate-900 tracking-tight font-heading">Engine Subsystem Health &amp; Diagnostics</h3>
        </div>

        <div class="flex items-center gap-2">
          <span [ngClass]="getOverallStatusBadge(store.engineHealth().overallStatus)"
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider border shadow-3xs">
            <span class="w-2 h-2 rounded-sm" [ngClass]="getOverallDot(store.engineHealth().overallStatus)"></span>
            <span>{{ cleanText(store.engineHealth().statusLabel) }}</span>
          </span>
        </div>
      </div>

      <!-- Narrative summary -->
      <p class="text-xs text-slate-600 leading-relaxed -mt-1">
        {{ cleanText(store.engineHealth().summaryNarrative) }}
      </p>

      <!-- Primary Degraded Alert Box (If any causal failure exists) -->
      @if (store.engineHealth().overallStatus === 'DEGRADED' || store.engineHealth().overallStatus === 'CRITICAL') {
        <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3.5 shadow-2xs">
          <app-lucide-icon name="alert-triangle" [size]="20" class="text-amber-600 shrink-0 mt-0.5" />
          <div class="flex flex-col gap-1.5 text-xs">
            <span class="font-bold text-amber-900">
              Primary Bottleneck: {{ cleanText(store.engineHealth().primaryDegradedReason || 'Subsystem Latency Spike') }}
            </span>
            @if (store.engineHealth().primaryDegradedEvidence) {
              <span class="font-mono text-[11px] text-amber-900 bg-amber-100/70 px-2.5 py-1 rounded-md border border-amber-200 w-fit">
                Evidence: {{ cleanText(store.engineHealth().primaryDegradedEvidence) }}
              </span>
            }
          </div>
        </div>
      }

      <!-- Subsystems Collection Grid (Rectangular cards with generous spacing) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        @for (sub of store.engineHealth().subsystems; track sub.id) {
          <div [ngClass]="getSubsystemCardBorder(sub.status, sub.isCausal)"
               class="rounded-xl border p-5 bg-white flex flex-col justify-between min-h-[120px] transition-colors shadow-xs hover:border-blue-200">
            
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold text-slate-900 truncate font-heading" [title]="sub.name">{{ cleanText(sub.name) }}</span>
              <span [ngClass]="getSubsystemStatusBadge(sub.status)"
                    class="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border shrink-0">
                {{ cleanText(sub.status) }}
              </span>
            </div>

            <div class="flex flex-col gap-1.5 text-[11px] mt-auto">
              @if (sub.latencyMs !== undefined) {
                <div class="flex items-center justify-between text-slate-500">
                  <span>Latency</span>
                  <span class="font-mono font-bold text-slate-800">{{ sub.latencyMs }} ms</span>
                </div>
              }
              @if (sub.throughputMetrics) {
                <div class="flex items-center justify-between text-slate-500">
                  <span>{{ sub.latencyMs !== undefined ? 'Throughput' : 'State' }}</span>
                  <span class="font-mono font-bold text-slate-800">{{ cleanText(sub.throughputMetrics) }}</span>
                </div>
              }
              @if (sub.reason) {
                <div class="text-amber-800 font-semibold text-[10px] mt-1 line-clamp-1" [title]="sub.reason">
                  {{ cleanText(sub.reason) }}
                </div>
              }
            </div>
          </div>
        }
      </div>
    </section>
  `
})
export class CockpitEngineHealthComponent {
  public store = inject(CockpitStoreService);

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }

  public getOverallStatusBadge(status: EngineHealthState): string {
    switch (status) {
      case 'HEALTHY': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'DEGRADED': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'CRITICAL': return 'bg-rose-50 text-rose-700 border-rose-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getOverallDot(status: EngineHealthState): string {
    switch (status) {
      case 'HEALTHY': return 'bg-emerald-500';
      case 'DEGRADED': return 'bg-amber-500 animate-pulse';
      case 'CRITICAL': return 'bg-rose-500 animate-pulse';
      default: return 'bg-slate-400';
    }
  }

  public getSubsystemCardBorder(status: SubsystemHealthEntry['status'], isCausal: boolean): string {
    if (isCausal || status === 'CRITICAL') return 'border-rose-300 bg-rose-50/40';
    if (status === 'DEGRADED') return 'border-amber-300 bg-amber-50/40';
    return 'border-slate-200 bg-slate-50/60 hover:bg-slate-50';
  }

  public getSubsystemStatusBadge(status: SubsystemHealthEntry['status']): string {
    switch (status) {
      case 'HEALTHY': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'DEGRADED': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'CRITICAL': return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'NOT_APPLICABLE': return 'bg-slate-100 text-slate-400 border-slate-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }
}
