import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CockpitActivityEvent } from '../cockpit.models';

@Component({
  selector: 'app-cockpit-events-dock',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col overflow-hidden">
      
      <!-- Dock Header & Filter Bar -->
      <div class="px-6 py-4 bg-slate-50/70 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="terminal" [size]="18" class="text-blue-600" />
          <h3 class="text-base font-bold text-slate-900 tracking-tight font-heading">Activity &amp; Operational Audit Trail</h3>
          <span class="text-xs text-slate-400 font-mono">({{ store.filteredEvents().length }} events)</span>
        </div>

        <!-- Filter Categories (Enterprise Blue active, Blue-hover outline inactive) -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          @for (cat of categories; track cat) {
            <button
              (click)="store.setEventFilter(cat)"
              [ngClass]="store.eventFilterCategory() === cat 
                ? 'bg-blue-600 text-white font-bold shadow-xs' 
                : 'bg-white border border-slate-200 text-slate-700 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 font-semibold'"
              class="px-3 py-1.5 text-xs rounded-lg transition-all shrink-0 cursor-pointer">
              {{ cleanText(cat) }}
            </button>
          }
        </div>
      </div>

      <!-- Events List View with Generous Line Spacing -->
      <div class="max-h-[340px] overflow-y-auto p-5 flex flex-col gap-2.5 font-mono text-xs divide-y divide-slate-100">
        @for (ev of store.filteredEvents(); track ev.id) {
          <div class="pt-2.5 first:pt-0 flex items-start gap-3.5 hover:bg-blue-50/30 p-2 rounded-lg transition-colors">
            
            <!-- Timestamp -->
            <span class="text-slate-400 font-normal shrink-0 text-xs w-18 pt-0.5">
              {{ ev.timestamp }}
            </span>

            <!-- Category Badge (Rectangular with curved corners) -->
            <span [ngClass]="getCategoryBadgeClasses(ev.category)"
                  class="px-2 py-0.5 rounded-md text-[10px] font-sans font-bold uppercase tracking-wider border shrink-0">
              {{ cleanText(ev.category) }}
            </span>

            <!-- Severity Indicator -->
            <span [ngClass]="getSeverityDotClasses(ev.severity)"
                  class="w-2 h-2 rounded-sm shrink-0 mt-1.5"></span>

            <!-- Message Text with clean line height and zero underscores -->
            <div class="flex-1 flex flex-col font-sans">
              <span class="text-slate-800 text-xs leading-relaxed font-medium">
                {{ cleanText(ev.message) }}
              </span>
              @if (ev.sourceComponent) {
                <span class="text-[11px] text-slate-400 font-mono mt-1">
                  Source: {{ cleanText(ev.sourceComponent) }}
                </span>
              }
            </div>
          </div>
        }

        @if (store.filteredEvents().length === 0) {
          <div class="py-10 text-center text-slate-400 font-sans text-xs">
            No events match the selected filter category.
          </div>
        }
      </div>
    </section>
  `
})
export class CockpitEventsDockComponent {
  public store = inject(CockpitStoreService);

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }

  public categories: string[] = [
    'ALL',
    'LIFECYCLE',
    'STAGE',
    'WORKER',
    'CHECKPOINT',
    'CDC',
    'BARRIER',
    'HEALTH',
    'ERROR'
  ];

  public getCategoryBadgeClasses(cat: CockpitActivityEvent['category']): string {
    switch (cat) {
      case 'LIFECYCLE': return 'bg-slate-100 text-slate-700 border-slate-200';
      case 'STAGE': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'WORKER': return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'CHECKPOINT': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'CDC': return 'bg-cyan-50 text-cyan-700 border-cyan-200';
      case 'BARRIER': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'HEALTH': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'ERROR': return 'bg-rose-50 text-rose-700 border-rose-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getSeverityDotClasses(sev: CockpitActivityEvent['severity']): string {
    switch (sev) {
      case 'SUCCESS': return 'bg-emerald-500';
      case 'WARNING': return 'bg-amber-500';
      case 'ERROR': return 'bg-rose-500';
      default: return 'bg-slate-400';
    }
  }
}
