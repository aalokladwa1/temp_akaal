import { Component, inject, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { SelectedMigrationHeaderDTO } from '../models/migration-monitoring.models';
import { MigrationMonitoringService } from '../services/migration-monitoring.service';

@Component({
  selector: 'app-selected-migration-header',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    @if (header) {
      <div class="flex flex-col gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs select-none">
        
        <!-- Top Row: Back Navigation & Quick Actions -->
        <div class="flex items-center justify-between gap-4 flex-wrap">
          <div class="flex items-center gap-3">
            <button
              type="button"
              (click)="onBackToFleet()"
              class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back to Fleet</span>
            </button>

            <div class="flex items-center gap-2 text-xs text-slate-400">
              <span>Monitoring</span>
              <span>/</span>
              <span class="text-slate-600 font-medium">Migration Fleet</span>
              <span>/</span>
              <span class="text-slate-900 font-semibold truncate max-w-[280px]">{{ header.name }}</span>
            </div>
          </div>

          <!-- Deep Links & Telemetry Refresh -->
          <div class="flex items-center gap-2.5">
            <a
              [routerLink]="['/cockpit', header.id]"
              class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
              <app-lucide-icon name="activity" [size]="13" class="text-blue-600"></app-lucide-icon>
              <span>Live Cockpit</span>
            </a>

            <a
              [routerLink]="['/history', header.id]"
              class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
              <app-lucide-icon name="history" [size]="13" class="text-slate-600"></app-lucide-icon>
              <span>History</span>
            </a>

            <button
              type="button"
              (click)="mms.refresh()"
              [disabled]="mms.isRefreshing()"
              class="h-8 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs disabled:opacity-50">
              <app-lucide-icon 
                name="refresh-cw" 
                [size]="13" 
                [class.animate-spin]="mms.isRefreshing()">
              </app-lucide-icon>
              <span>{{ mms.isRefreshing() ? 'Refreshing' : 'Refresh' }}</span>
            </button>
          </div>
        </div>

        <!-- Middle Row: Migration Subject Details -->
        <div class="flex items-start justify-between gap-6 flex-wrap pt-1 border-t border-slate-100">
          <div class="flex flex-col gap-1.5">
            <div class="flex items-center gap-3 flex-wrap">
              <h2 class="text-xl font-bold text-slate-900 tracking-tight font-heading">{{ header.name }}</h2>
              
              <!-- Mode Badge (Rectangular, clean) -->
              <span class="px-2.5 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
                {{ mms.formatModeLabel(header.mode) }}
              </span>

              <!-- Operational State Badge -->
              <span 
                class="px-2.5 py-0.5 rounded text-xs font-semibold"
                [ngClass]="{
                  'bg-emerald-50 text-emerald-700 border border-emerald-200/60': header.operational_state === 'RUNNING' || header.operational_state === 'ACTIVE',
                  'bg-amber-50 text-amber-700 border border-amber-200/60': header.operational_state === 'ATTENTION' || header.operational_state === 'PAUSED',
                  'bg-rose-50 text-rose-700 border border-rose-200/60': header.operational_state === 'FAILED',
                  'bg-slate-100 text-slate-700 border border-slate-200': header.operational_state === 'COMPLETED' || header.operational_state === 'INITIALIZING'
                }">
                {{ mms.formatOperationalState(header.operational_state) }}
              </span>

              <!-- Health Indicator with Circular Dot -->
              <div class="flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
                <span 
                  class="w-2 h-2 rounded-full shrink-0"
                  [ngClass]="{
                    'bg-emerald-500': header.health === 'HEALTHY',
                    'bg-amber-500': header.health === 'DEGRADED',
                    'bg-rose-500': header.health === 'UNHEALTHY',
                    'bg-slate-400': header.health === 'UNKNOWN'
                  }">
                </span>
                <span>{{ mms.formatHealthLabel(header.health) }}</span>
              </div>
            </div>

            <!-- Project & Route Info -->
            <div class="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
              <span class="font-medium text-slate-700">{{ header.project_name }}</span>
              <span class="text-slate-300">•</span>
              <div class="flex items-center gap-1.5">
                <span class="font-semibold text-slate-700">{{ header.source_provider }}</span>
                <span class="text-slate-400">({{ header.source_instance }})</span>
                <span class="text-slate-400">→</span>
                <span class="font-semibold text-slate-700">{{ header.target_provider }}</span>
                <span class="text-slate-400">({{ header.target_instance }})</span>
              </div>
              <span class="text-slate-300">•</span>
              <span class="font-mono text-slate-500">{{ header.plan_version }}</span>
            </div>
          </div>

          <!-- Right Telemetry Freshness & Fingerprint -->
          <div class="flex flex-col items-end gap-1 text-right">
            <div class="flex items-center gap-1.5 text-xs text-slate-500">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Observed {{ header.observed_at | date:'HH:mm:ss' }}</span>
              <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 uppercase">
                {{ header.freshness_state }}
              </span>
            </div>
            <div class="text-[11px] font-mono text-slate-400 truncate max-w-[260px]" [title]="header.plan_fingerprint">
              {{ header.plan_fingerprint.substring(0, 24) }}...
            </div>
          </div>
        </div>

      </div>
    }
  `
})
export class SelectedMigrationHeaderComponent {
  @Input({ required: true }) header!: SelectedMigrationHeaderDTO;

  public mms = inject(MigrationMonitoringService);
  private router = inject(Router);

  public onBackToFleet(): void {
    this.mms.selectMigration(null);
    this.router.navigate(['/monitoring/migrations']);
  }
}
