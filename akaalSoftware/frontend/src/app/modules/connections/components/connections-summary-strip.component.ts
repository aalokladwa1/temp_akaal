import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConnectionsService } from '../connections.service';

@Component({
  selector: 'app-connections-summary-strip',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 select-none">
      
      <!-- 1. Total Configured -->
      <div
        (click)="setFilter('ALL')"
        class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group shadow-2xs"
        [class.border-blue-600]="isFilterActive('ALL')"
        [class.ring-1]="isFilterActive('ALL')"
        [class.ring-blue-500]="isFilterActive('ALL')"
        [class.bg-blue-50]="isFilterActive('ALL')"
        [class.bg-white]="!isFilterActive('ALL')"
        [class.border-slate-200]="!isFilterActive('ALL')"
        [class.hover:border-slate-300]="!isFilterActive('ALL')"
        [class.hover:bg-slate-50]="!isFilterActive('ALL')">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-800 transition-colors">
            Total Inventory
          </span>
          <span class="text-[10px] font-mono text-slate-400">All Systems</span>
        </div>
        <div class="flex items-baseline justify-between gap-3">
          <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
            {{ cs.summaryCounters().total }}
          </span>
          <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
            configured profiles
          </span>
        </div>
      </div>

      <!-- 2. Verified Point-in-Time -->
      <div
        (click)="setFilter('VERIFIED')"
        class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group shadow-2xs"
        [class.border-emerald-600]="isFilterActive('VERIFIED')"
        [class.ring-1]="isFilterActive('VERIFIED')"
        [class.ring-emerald-500]="isFilterActive('VERIFIED')"
        [class.bg-emerald-50]="isFilterActive('VERIFIED')"
        [class.bg-white]="!isFilterActive('VERIFIED')"
        [class.border-slate-200]="!isFilterActive('VERIFIED')"
        [class.hover:border-slate-300]="!isFilterActive('VERIFIED')"
        [class.hover:bg-slate-50]="!isFilterActive('VERIFIED')">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">
            Verified (Point-in-Time)
          </span>
          <span class="w-2 h-2 rounded-xs bg-emerald-500"></span>
        </div>
        <div class="flex items-baseline justify-between gap-3">
          <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
            {{ cs.summaryCounters().verified }}
          </span>
          <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
            passed probe checks
          </span>
        </div>
      </div>

      <!-- 3. Needs Attention (Failed / Stale / Config Changed) -->
      <div
        (click)="setFilter('ATTENTION')"
        class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group shadow-2xs"
        [class.border-amber-600]="isFilterActive('ATTENTION')"
        [class.ring-1]="isFilterActive('ATTENTION')"
        [class.ring-amber-500]="isFilterActive('ATTENTION')"
        [class.bg-amber-50]="isFilterActive('ATTENTION')"
        [class.bg-white]="!isFilterActive('ATTENTION')"
        [class.border-slate-200]="!isFilterActive('ATTENTION')"
        [class.hover:border-slate-300]="!isFilterActive('ATTENTION')"
        [class.hover:bg-slate-50]="!isFilterActive('ATTENTION')">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-amber-700 uppercase tracking-wider">
            Needs Attention
          </span>
          <span class="w-2 h-2 rounded-xs bg-amber-500"></span>
        </div>
        <div class="flex items-baseline justify-between gap-3">
          <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
            {{ cs.summaryCounters().needsAttention }}
          </span>
          <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
            failed, stale, or mutated
          </span>
        </div>
      </div>

      <!-- 4. Unused Resources -->
      <div
        (click)="setFilter('UNUSED')"
        class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group shadow-2xs"
        [class.border-slate-600]="isFilterActive('UNUSED')"
        [class.ring-1]="isFilterActive('UNUSED')"
        [class.ring-slate-500]="isFilterActive('UNUSED')"
        [class.bg-slate-100]="isFilterActive('UNUSED')"
        [class.bg-white]="!isFilterActive('UNUSED')"
        [class.border-slate-200]="!isFilterActive('UNUSED')"
        [class.hover:border-slate-300]="!isFilterActive('UNUSED')"
        [class.hover:bg-slate-50]="!isFilterActive('UNUSED')">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
            Unused Resources
          </span>
          <span class="text-[10px] font-mono text-slate-400">Zero Workloads</span>
        </div>
        <div class="flex items-baseline justify-between gap-3">
          <span class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums">
            {{ cs.summaryCounters().unused }}
          </span>
          <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
            no active workloads
          </span>
        </div>
      </div>

    </div>
  `
})
export class ConnectionsSummaryStripComponent {
  public cs = inject(ConnectionsService);

  public isFilterActive(type: 'ALL' | 'VERIFIED' | 'ATTENTION' | 'UNUSED'): boolean {
    const f = this.cs.filters();
    if (type === 'ALL') {
      return f.verificationState === 'ALL' && f.usageFilter === 'ALL' && f.family === 'ALL';
    }
    if (type === 'VERIFIED') {
      return f.verificationState === 'VERIFIED_GROUP';
    }
    if (type === 'ATTENTION') {
      return f.verificationState === 'ATTENTION_GROUP';
    }
    if (type === 'UNUSED') {
      return f.usageFilter === 'UNUSED';
    }
    return false;
  }

  public setFilter(type: 'ALL' | 'VERIFIED' | 'ATTENTION' | 'UNUSED'): void {
    if (type === 'ALL') {
      this.cs.clearFilters();
    } else if (type === 'VERIFIED') {
      if (this.cs.filters().verificationState === 'VERIFIED_GROUP') {
        this.cs.setVerificationFilter('ALL');
      } else {
        this.cs.setVerificationFilter('VERIFIED_GROUP');
      }
    } else if (type === 'ATTENTION') {
      if (this.cs.filters().verificationState === 'ATTENTION_GROUP') {
        this.cs.setVerificationFilter('ALL');
      } else {
        this.cs.setVerificationFilter('ATTENTION_GROUP');
      }
    } else if (type === 'UNUSED') {
      if (this.cs.filters().usageFilter === 'UNUSED') {
        this.cs.setUsageFilter('ALL');
      } else {
        this.cs.setUsageFilter('UNUSED');
      }
    }
  }
}
