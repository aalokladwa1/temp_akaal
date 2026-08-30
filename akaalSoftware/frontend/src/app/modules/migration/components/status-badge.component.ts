import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TagModule } from 'primeng/tag';
import { BadgeModule } from 'primeng/badge';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import {
  MigrationLifecycleState,
  MigrationMode,
  ValidationSyncVerdict
} from '../../../core/models/migration-view.models';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule, TagModule, BadgeModule, LucideIconComponent],
  template: `
    @if (lifecycle) {
      @switch (lifecycle) {
        @case ('RUNNING') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200/80">
            <app-lucide-icon name="activity" [size]="12"></app-lucide-icon>
            <span>RUNNING</span>
          </span>
        }
        @case ('ACTIVE') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200/80">
            <app-lucide-icon name="play" [size]="12"></app-lucide-icon>
            <span>ACTIVE</span>
          </span>
        }
        @case ('ATTENTION') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200/80">
            <app-lucide-icon name="alert-triangle" [size]="12" class="text-amber-600"></app-lucide-icon>
            <span>ATTENTION</span>
          </span>
        }
        @case ('GOVERNANCE_PENDING') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200/80">
            <app-lucide-icon name="lock" [size]="12" class="text-amber-700"></app-lucide-icon>
            <span>APPROVAL REQUIRED</span>
          </span>
        }
        @case ('SCHEDULED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            <app-lucide-icon name="clock" [size]="12"></app-lucide-icon>
            <span>SCHEDULED</span>
          </span>
        }
        @case ('INITIALIZED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            <app-lucide-icon name="clock" [size]="12"></app-lucide-icon>
            <span>SCHEDULED</span>
          </span>
        }
        @case ('PAUSED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200/80">
            <app-lucide-icon name="pause" [size]="12"></app-lucide-icon>
            <span>PAUSED</span>
          </span>
        }
        @case ('COMPLETED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80">
            <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
            <span>COMPLETED</span>
          </span>
        }
        @case ('FAILED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200/80">
            <app-lucide-icon name="triangle-alert" [size]="12"></app-lucide-icon>
            <span>FAILED</span>
          </span>
        }
        @default {
          <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {{ lifecycle }}
          </span>
        }
      }
    }

    @if (mode) {
      <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">
        {{ getModeLabel(mode) }}
      </span>
    }

    @if (verdict) {
      @switch (verdict) {
        @case ('SYNCED_CERTIFIED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <app-lucide-icon name="shield-check" [size]="13" class="text-emerald-700"></app-lucide-icon>
            <span>SYNCED · CERTIFIED</span>
          </span>
        }
        @case ('SYNCED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <app-lucide-icon name="check" [size]="13" class="text-emerald-700"></app-lucide-icon>
            <span>SYNCED</span>
          </span>
        }
        @case ('NOT_SYNCED') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
            <app-lucide-icon name="shield-alert" [size]="13" class="text-rose-700"></app-lucide-icon>
            <span>NOT SYNCED</span>
          </span>
        }
        @case ('VALIDATING') {
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping"></span>
            <span>VALIDATING</span>
          </span>
        }
        @default {
          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {{ verdict }}
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

  public getModeLabel(m: string): string {
    const upper = (m || '').toUpperCase();
    switch (upper) {
      case 'BULK_ONLY':
      case 'M1_BULK':
        return 'Bulk Migration';
      case 'BULK_CDC':
      case 'M2_BULK_CDC':
        return 'Bulk + CDC';
      case 'CDC_ONLY':
      case 'M3_CDC':
        return 'CDC Streaming';
      case 'INCREMENTAL_QUERY':
      case 'M4_INCREMENTAL':
        return 'Incremental Query';
      case 'STATE_SYNC':
      case 'M5_STATE_SYNC':
        return 'State Sync';
      case 'SCHEMA_ONLY':
      case 'M6_SCHEMA_ONLY':
        return 'Schema Only';
      case 'DATA_ONLY':
      case 'M7_DATA_ONLY':
        return 'Data Only';
      default:
        return m;
    }
  }
}
