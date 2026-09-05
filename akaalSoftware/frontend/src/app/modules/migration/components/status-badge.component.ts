import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (lifecycle) {
      @switch (lifecycle.toUpperCase()) {
        @case ('RUNNING') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
            <span>Running</span>
          </span>
        }
        @case ('ACTIVE') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
            <span>Active</span>
          </span>
        }
        @case ('ATTENTION') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span>Attention</span>
          </span>
        }
        @case ('GOVERNANCE_PENDING') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span>Approval Required</span>
          </span>
        }
        @case ('SCHEDULED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            <span>Scheduled</span>
          </span>
        }
        @case ('INITIALIZED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            <span>Scheduled</span>
          </span>
        }
        @case ('PAUSED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span>Paused</span>
          </span>
        }
        @case ('COMPLETED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Completed</span>
          </span>
        }
        @case ('FAILED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            <span>Failed</span>
          </span>
        }
        @default {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            <span>{{ lifecycle }}</span>
          </span>
        }
      }
    }

    @if (mode) {
      <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200 select-none">
        {{ getCanonicalModeLabel(mode) }}
      </span>
    }

    @if (verdict) {
      @switch (verdict.toUpperCase()) {
        @case ('SYNCED_CERTIFIED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Synced &middot; Certified</span>
          </span>
        }
        @case ('SYNCED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Synced</span>
          </span>
        }
        @case ('NOT_SYNCED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            <span>Not Synced</span>
          </span>
        }
        @case ('VALIDATING') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
            <span>Validating</span>
          </span>
        }
        @default {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 select-none">
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            <span>{{ verdict }}</span>
          </span>
        }
      }
    }
  `
})
export class StatusBadgeComponent {
  @Input() lifecycle?: any;
  @Input() mode?: any;
  @Input() verdict?: any;

  public getCanonicalModeLabel(m: string): string {
    const upper = (m || '').toUpperCase();
    switch (upper) {
      case 'BULK_ONLY':
      case 'M1_BULK':
      case 'M1':
        return 'M1: Bulk';
      case 'BULK_CDC':
      case 'M2_BULK_CDC':
      case 'M2':
        return 'M2: Bulk + CDC';
      case 'CDC_ONLY':
      case 'M3_CDC':
      case 'M3':
        return 'M3: CDC';
      case 'INCREMENTAL_QUERY':
      case 'M4_INCREMENTAL':
      case 'M4':
        return 'M4: Incremental';
      case 'STATE_SYNC':
      case 'M5_STATE_SYNC':
      case 'M5':
        return 'M5: State Sync';
      case 'SCHEMA_ONLY':
      case 'M6_SCHEMA_ONLY':
      case 'M6':
        return 'M6: Schema Only';
      case 'DATA_ONLY':
      case 'M7_DATA_ONLY':
      case 'M7':
        return 'M7: Data Only';
      case 'VALIDATION':
      case 'M8_VALIDATION':
      case 'M8':
        return 'M8: Validation';
      default:
        return m;
    }
  }
}
