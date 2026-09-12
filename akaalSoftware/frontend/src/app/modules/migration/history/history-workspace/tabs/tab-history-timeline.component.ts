import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { TimelineEventItem, TimelineCategory, TimelineSeverity } from '../history-workspace.models';

@Component({
  selector: 'app-tab-history-timeline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-4">
      
      <!-- Filter & Search Toolbar -->
      <div class="bg-white border border-slate-200 rounded-lg p-3.5 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
        <!-- Search Input -->
        <div class="w-full md:w-72">
          <input
            type="text"
            [ngModel]="hws.timelineSearch()"
            (ngModelChange)="hws.timelineSearch.set($event)"
            placeholder="Search chronological events..."
            class="w-full h-8 px-3 text-xs bg-slate-50 border border-slate-300 rounded-md placeholder-slate-400 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors" />
        </div>

        <!-- Filter Dropdowns & Reset Action -->
        <div class="flex items-center gap-2 w-full md:w-auto justify-end flex-wrap">
          <!-- Category Selector -->
          <div class="flex items-center gap-1 text-xs text-slate-600">
            <span class="text-[11px] font-semibold text-slate-500">Category:</span>
            <select
              [ngModel]="hws.timelineCategory()"
              (ngModelChange)="hws.timelineCategory.set($event)"
              class="h-8 px-2.5 text-xs bg-white border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer">
              <option value="ALL">All Categories</option>
              <option value="PLANNING">Planning</option>
              <option value="GOVERNANCE">Governance</option>
              <option value="EXECUTION">Execution</option>
              <option value="VALIDATION">Validation</option>
              <option value="CONTINUITY">Continuity &amp; Cutover</option>
              <option value="RECOVERY">Recovery</option>
              <option value="SYSTEM">System</option>
              <option value="OPERATOR">Operator</option>
            </select>
          </div>

          <!-- Severity Selector -->
          <div class="flex items-center gap-1 text-xs text-slate-600">
            <span class="text-[11px] font-semibold text-slate-500">Severity:</span>
            <select
              [ngModel]="hws.timelineSeverity()"
              (ngModelChange)="hws.timelineSeverity.set($event)"
              class="h-8 px-2.5 text-xs bg-white border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer">
              <option value="ALL">All Severities</option>
              <option value="INFO">Info</option>
              <option value="SUCCESS">Success</option>
              <option value="WARNING">Warning</option>
              <option value="ERROR">Error</option>
            </select>
          </div>

          <!-- Text-Only Reset Button -->
          <button
            type="button"
            (click)="hws.resetTimelineFilters()"
            class="h-8 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors cursor-pointer">
            Reset
          </button>
        </div>
      </div>

      <!-- Chronological Event Stream -->
      <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
        @if (hws.filteredTimelineEvents().length > 0) {
          <div class="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            @for (event of hws.filteredTimelineEvents(); track event.id) {
              <div class="relative group">
                <!-- Timeline Dot Indicator -->
                <div class="absolute -left-6 mt-1 w-3 h-3 rounded-full border-2 border-white"
                  [ngClass]="getSeverityDotClass(event.severity)"></div>

                <!-- Event Header -->
                <div class="flex items-center justify-between gap-2 flex-wrap">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-bold text-slate-900">{{ event.title }}</span>
                    
                    <!-- Category Tag -->
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border"
                      [ngClass]="getCategoryBadgeClass(event.category)">
                      {{ event.category }}
                    </span>

                    <!-- Severity Badge -->
                    <span class="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-bold uppercase tracking-wider border"
                      [ngClass]="getSeverityBadgeClass(event.severity)">
                      {{ event.severity }}
                    </span>
                  </div>

                  <span class="text-[11px] font-mono text-slate-500">{{ formatTimestamp(event.timestamp) }}</span>
                </div>

                <!-- Event Body & Metadata -->
                <div class="mt-1 text-xs text-slate-600">
                  <p>{{ event.description }}</p>
                  
                  <div class="mt-1.5 flex items-center gap-4 text-[11px] text-slate-400 flex-wrap">
                    <span>Actor: <strong class="text-slate-600 font-medium">{{ event.actor }}</strong></span>
                    @if (event.correlationId) {
                      <span>Correlation ID: <strong class="text-slate-600 font-mono">{{ event.correlationId }}</strong></span>
                    }
                  </div>
                </div>
              </div>
            }
          </div>
        } @else {
          <!-- Empty State -->
          <div class="py-12 text-center text-xs text-slate-500">
            <p class="font-medium text-slate-700">No timeline events matched the filter criteria.</p>
            <p class="text-slate-400 mt-1">Try broadening your search term or resetting category filters.</p>
            <button
              type="button"
              (click)="hws.resetTimelineFilters()"
              class="mt-3 h-8 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors cursor-pointer">
              Reset Filters
            </button>
          </div>
        }
      </div>

    </div>
  `
})
export class TabHistoryTimelineComponent {
  public hws = inject(HistoryWorkspaceService);

  public getCategoryBadgeClass(cat: TimelineCategory): string {
    switch (cat) {
      case 'PLANNING': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'GOVERNANCE': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'EXECUTION': return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'VALIDATION': return 'bg-sky-50 text-sky-700 border-sky-200';
      case 'CONTINUITY': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'RECOVERY': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'SYSTEM': return 'bg-slate-100 text-slate-700 border-slate-200';
      case 'OPERATOR': return 'bg-teal-50 text-teal-800 border-teal-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  public getSeverityBadgeClass(sev: TimelineSeverity): string {
    switch (sev) {
      case 'SUCCESS': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'WARNING': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'ERROR': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'INFO':
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getSeverityDotClass(sev: TimelineSeverity): string {
    switch (sev) {
      case 'SUCCESS': return 'bg-emerald-500 ring-2 ring-emerald-100';
      case 'WARNING': return 'bg-amber-500 ring-2 ring-amber-100';
      case 'ERROR': return 'bg-rose-500 ring-2 ring-rose-100';
      case 'INFO':
      default: return 'bg-blue-500 ring-2 ring-blue-100';
    }
  }

  public formatTimestamp(ts: string): string {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  }
}
