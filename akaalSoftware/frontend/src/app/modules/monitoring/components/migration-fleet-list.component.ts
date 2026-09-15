import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../shared/components/custom-select.component';
import { MigrationMonitoringService } from '../services/migration-monitoring.service';
import { CanonicalMigrationMode } from '../models/migration-monitoring.models';

@Component({
  selector: 'app-migration-fleet-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- =============================================================== -->
      <!-- 1. FLEET SUMMARY STRIP                                          -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        
        <!-- Total Fleet -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Total Fleet</span>
          <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight">{{ mms.fleetCountSummary().total }}</span>
          <span class="text-[11px] text-slate-400 font-medium">Configured migrations</span>
        </div>

        <!-- Running / Active -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Active / Running</span>
          <span class="text-2xl font-bold text-blue-600 font-mono tracking-tight">{{ mms.fleetCountSummary().running }}</span>
          <span class="text-[11px] text-emerald-600 font-medium">Processing pipelines</span>
        </div>

        <!-- Needs Attention -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Needs Attention</span>
          <span class="text-2xl font-bold font-mono tracking-tight" [ngClass]="mms.fleetCountSummary().attention > 0 ? 'text-amber-600' : 'text-slate-900'">
            {{ mms.fleetCountSummary().attention }}
          </span>
          <span class="text-[11px] text-slate-400 font-medium">Attention items</span>
        </div>

        <!-- Healthy Migrations -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Healthy</span>
          <span class="text-2xl font-bold text-emerald-600 font-mono tracking-tight">{{ mms.fleetCountSummary().healthy }}</span>
          <span class="text-[11px] text-emerald-600 font-medium">Nominal SLA</span>
        </div>

        <!-- Fleet Aggregated Throughput -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1 col-span-2 sm:col-span-1 lg:col-span-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-slate-500">Fleet Throughput</span>
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          </div>
          <span class="text-xl font-bold text-slate-900 font-mono tracking-tight truncate">
            {{ mms.summary()?.aggregated_throughput_label || '90,170 ops/s across fleet' }}
          </span>
          <div class="flex items-center gap-1.5 text-[11px] text-slate-400">
            <span>Observed {{ mms.lastObservedAt() | date:'HH:mm:ss' }}</span>
            <span>•</span>
            <span class="font-semibold text-emerald-600 uppercase">{{ mms.telemetryConfidence() }}</span>
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 2. FILTER TOOLBAR (Mode M1-M7 only, Search, Health, State)       -->
      <!-- =============================================================== -->
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        
        <!-- Search Query Input -->
        <div class="relative flex-1 min-w-[240px]">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </div>
          <input
            type="text"
            [ngModel]="mms.searchQuery()"
            (ngModelChange)="mms.setSearchQuery($event)"
            placeholder="Search by migration name, project, database, or stage..."
            class="w-full h-9 pl-9 pr-3.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 focus:bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors">
        </div>

        <!-- Filter Selectors with Global Custom Select Design System -->
        <div class="flex items-center gap-2.5 flex-wrap">
          
          <!-- Mode Filter (Strictly M1-M7 Canonical Modes, NO M8!) -->
          <div class="w-44">
            <app-custom-select
              [options]="modeOptions"
              [value]="mms.modeFilter()"
              (valueChange)="mms.setModeFilter($event)"
              [placeholder]="'All Modes'"
              [size]="'sm'">
            </app-custom-select>
          </div>

          <!-- Health Filter -->
          <div class="w-36">
            <app-custom-select
              [options]="healthOptions"
              [value]="mms.healthFilter()"
              (valueChange)="mms.setHealthFilter($event)"
              [placeholder]="'All Health'"
              [size]="'sm'">
            </app-custom-select>
          </div>

          <!-- State Filter -->
          <div class="w-40">
            <app-custom-select
              [options]="stateOptions"
              [value]="mms.stateFilter()"
              (valueChange)="mms.setStateFilter($event)"
              [placeholder]="'All States'"
              [size]="'sm'">
            </app-custom-select>
          </div>

          <!-- Reset Filters Button -->
          @if (mms.searchQuery() || mms.modeFilter() !== 'ALL' || mms.healthFilter() !== 'ALL' || mms.stateFilter() !== 'ALL') {
            <button
              type="button"
              (click)="mms.resetFilters()"
              class="h-8 px-3 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 font-medium text-xs cursor-pointer transition-colors">
              Reset
            </button>
          }

        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 3. MIGRATION FLEET TABLE (Clean, Spacious, Balanced Spacing)    -->
      <!-- =============================================================== -->
      <div class="rounded-2xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
        <div class="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Active Migrations</h3>
          <span class="text-xs text-slate-500 font-medium">
            Showing {{ mms.filteredFleet().length }} of {{ mms.fleetList().length }} migrations
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75 select-none">
                <th class="py-3 px-4 min-w-[200px]">Migration Name</th>
                <th class="py-3 px-4 min-w-[170px]">Current Stage</th>
                <th class="py-3 px-4 min-w-[220px]">Source → Target</th>
                <th class="py-3 px-4 min-w-[120px]">Mode</th>
                <th class="py-3 px-4 min-w-[130px]">Health &amp; State</th>
                <th class="py-3 px-4 min-w-[140px]">Progress</th>
                <th class="py-3 px-4 text-right min-w-[100px]">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (item of mms.filteredFleet(); track item.id) {
                <tr 
                  (click)="onOpenMigration(item.id)"
                  class="hover:bg-slate-50/75 transition-colors cursor-pointer group">
                  
                  <!-- 1. Migration Name & Project -->
                  <td class="py-3.5 px-4">
                    <div class="font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                      {{ item.name }}
                    </div>
                    <div class="text-[11px] text-slate-500 font-medium">
                      {{ item.project_name }}
                    </div>
                  </td>

                  <!-- 2. Current Stage -->
                  <td class="py-3.5 px-4">
                    <span class="font-medium text-slate-800">{{ item.current_stage }}</span>
                  </td>

                  <!-- 3. Source -> Target -->
                  <td class="py-3.5 px-4">
                    <div class="flex items-center gap-1.5 flex-wrap">
                      <span class="font-semibold text-slate-800">{{ item.source_provider }}</span>
                      <span class="text-slate-400">→</span>
                      <span class="font-semibold text-slate-800">{{ item.target_provider }}</span>
                    </div>
                  </td>

                  <!-- 4. Mode (Clean Name Only) -->
                  <td class="py-3.5 px-4 whitespace-nowrap">
                    <span class="px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
                      {{ mms.formatModeLabel(item.mode) }}
                    </span>
                  </td>

                  <!-- 5. Health & State (Circular Dot Indicator) -->
                  <td class="py-3.5 px-4 whitespace-nowrap">
                    <div class="flex items-center gap-2">
                      <span 
                        class="w-2.5 h-2.5 rounded-full shrink-0"
                        [ngClass]="{
                          'bg-emerald-500': item.health === 'HEALTHY',
                          'bg-amber-500': item.health === 'DEGRADED',
                          'bg-rose-500': item.health === 'UNHEALTHY',
                          'bg-slate-400': item.health === 'UNKNOWN'
                        }">
                      </span>
                      <span class="font-medium text-slate-800">{{ mms.formatHealthLabel(item.health) }}</span>
                    </div>
                  </td>

                  <!-- 6. Progress (X% or Continuous / Unknown Total) -->
                  <td class="py-3.5 px-4 whitespace-nowrap">
                    @if (item.progress_percent !== null && item.progress_percent !== undefined) {
                      <div class="flex items-center gap-2">
                        <div class="w-16 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                          <div 
                            class="bg-blue-600 h-full rounded-full transition-all"
                            [style.width.%]="item.progress_percent">
                          </div>
                        </div>
                        <span class="font-mono font-semibold text-slate-800">{{ item.progress_percent }}%</span>
                      </div>
                    } @else {
                      <span class="font-mono text-slate-500 text-[11px]">Continuous</span>
                    }
                  </td>

                  <!-- 7. Action -->
                  <td class="py-3.5 px-4 whitespace-nowrap text-right">
                    <button
                      type="button"
                      (click)="onOpenMigration(item.id); $event.stopPropagation()"
                      class="h-7 px-2.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs cursor-pointer shadow-2xs transition-colors">
                      Investigate
                    </button>
                  </td>

                </tr>
              }

              @if (mms.filteredFleet().length === 0) {
                <tr>
                  <td colspan="7" class="py-12 text-center text-slate-500 text-xs">
                    No migrations match the selected search or filter criteria.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class MigrationFleetListComponent {
  public mms = inject(MigrationMonitoringService);
  private router = inject(Router);

  public modeOptions: CustomSelectOption[] = [
    { label: 'All Modes', value: 'ALL', desc: 'All M1-M7 canonical migration modes' },
    { label: 'Bulk Snapshot (M1)', value: 'M1_BULK', desc: 'Point-in-time full table snapshot' },
    { label: 'Bulk + CDC (M2)', value: 'M2_BULK_CDC', desc: 'Bulk snapshot + continuous change-stream catchup' },
    { label: 'Continuous CDC (M3)', value: 'M3_CDC', desc: 'Continuous change-data-capture stream replication' },
    { label: 'Incremental Polling (M4)', value: 'M4_INCREMENTAL', desc: 'High-watermark polling synchronization' },
    { label: 'State-Based Sync (M5)', value: 'M5_STATE_SYNC', desc: 'Periodic state hash scan & drift resolution' },
    { label: 'Schema Only (M6)', value: 'M6_SCHEMA_ONLY', desc: 'DDL compilation and constraint validation' },
    { label: 'Data Only (M7)', value: 'M7_DATA_ONLY', desc: 'Raw table/file chunk export & ingest' }
  ];

  public healthOptions: CustomSelectOption[] = [
    { label: 'All Health', value: 'ALL', desc: 'Show all migrations regardless of health' },
    { label: 'Healthy', value: 'HEALTHY', desc: 'All telemetry metrics nominal' },
    { label: 'Degraded', value: 'DEGRADED', desc: 'Performance degradation or latency spike' },
    { label: 'Unhealthy', value: 'UNHEALTHY', desc: 'Critical errors or stalled pipeline' }
  ];

  public stateOptions: CustomSelectOption[] = [
    { label: 'All States', value: 'ALL', desc: 'Show all operational states' },
    { label: 'Running', value: 'RUNNING', desc: 'Actively processing pipeline stages' },
    { label: 'Active', value: 'ACTIVE', desc: 'Pipeline ready and polling' },
    { label: 'Needs Attention', value: 'ATTENTION', desc: 'Requires operator review or approval' },
    { label: 'Paused', value: 'PAUSED', desc: 'Operator or governance paused' }
  ];

  public onOpenMigration(id: string): void {
    this.mms.selectMigration(id);
    this.router.navigate(['/monitoring/migrations', id, 'overview']);
  }
}
