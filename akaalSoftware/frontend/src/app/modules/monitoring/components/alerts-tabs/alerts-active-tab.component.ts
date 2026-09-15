/**
 * AKAAL Monitoring — Part 4 of 4: Active Alerts Tab Component
 * Real-time operational alerts currently firing across the platform and migration fleet.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AlertsMonitoringService } from '../../services/alerts-monitoring.service';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ActiveAlertDTO } from '../../models/alerts-monitoring.models';

@Component({
  selector: 'app-alerts-active-tab',
  standalone: true,
  imports: [CommonModule, CustomSelectComponent, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. KPI Summary Cards -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        
        <!-- Total Active Alerts -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Active Alerts</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight">
              {{ ams.alerts().length }}
            </span>
            <span class="text-xs text-slate-400">total firing</span>
          </div>
          <span class="text-[11px] text-slate-500 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Real-time evaluator stream
          </span>
        </div>

        <!-- Critical Alerts -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Critical Alerts</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-rose-600 font-mono tracking-tight">
              {{ ams.summary().critical_alerts_count }}
            </span>
            <span class="text-xs text-slate-400">require immediate action</span>
          </div>
          <span class="text-[11px] text-rose-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            Elevated operational impact
          </span>
        </div>

        <!-- Warning Alerts -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Warning Alerts</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-amber-600 font-mono tracking-tight">
              {{ ams.summary().warning_alerts_count }}
            </span>
            <span class="text-xs text-slate-400">threshold breaches</span>
          </div>
          <span class="text-[11px] text-amber-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            Trending toward boundary
          </span>
        </div>

        <!-- Linked to Incidents -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Linked to Incidents</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-purple-600 font-mono tracking-tight">
              {{ linkedAlertsCount }}
            </span>
            <span class="text-xs text-slate-400">correlated</span>
          </div>
          <span class="text-[11px] text-purple-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
            Associated with active incident
          </span>
        </div>

      </div>

      <!-- 2. Search and Custom Select Filter Controls -->
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        
        <!-- Search input -->
        <div class="relative flex-1">
          <app-lucide-icon name="search" [size]="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
          <input
            type="text"
            [value]="ams.alertSearchQuery()"
            (input)="onSearchInput($event)"
            placeholder="Search alerts by title, signal name, or affected entity..."
            class="w-full pl-9 pr-4 py-2 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 transition-all"
          />
        </div>

        <!-- Severity Filter Dropdown -->
        <div class="w-full sm:w-48">
          <app-custom-select
            [options]="severityOptions"
            [value]="ams.alertSeverityFilter()"
            (valueChange)="ams.alertSeverityFilter.set($event)"
            placeholder="Filter Severity">
          </app-custom-select>
        </div>

        <!-- State Filter Dropdown -->
        <div class="w-full sm:w-48">
          <app-custom-select
            [options]="stateOptions"
            [value]="ams.alertStateFilter()"
            (valueChange)="ams.alertStateFilter.set($event)"
            placeholder="Filter Lifecycle">
          </app-custom-select>
        </div>

      </div>

      <!-- 3. Two-Column Workspace: Alerts List + Detail Inspector -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        <!-- Left / Master: Alerts List (7 Cols) -->
        <div class="lg:col-span-7 flex flex-col gap-3">
          @if (ams.filteredAlerts().length === 0) {
            <div class="p-10 rounded-2xl bg-white border border-slate-200 shadow-2xs text-center flex flex-col items-center justify-center gap-2">
              <app-lucide-icon name="check-circle" [size]="32" class="text-emerald-500 mb-1"></app-lucide-icon>
              <h3 class="text-sm font-bold text-slate-800">No Alerts Match Your Filters</h3>
              <p class="text-xs text-slate-500 max-w-sm">All evaluated telemetry streams are operating within defined acceptable operational boundaries.</p>
            </div>
          } @else {
            @for (alert of ams.filteredAlerts(); track alert.id) {
              <div 
                (click)="ams.selectAlert(alert.id)"
                class="p-4 rounded-2xl bg-white border transition-all cursor-pointer shadow-2xs flex flex-col gap-3"
                [ngClass]="{
                  'border-blue-600 ring-1 ring-blue-600/30 bg-blue-50/10': ams.selectedAlert()?.id === alert.id,
                  'border-slate-200 hover:border-slate-300': ams.selectedAlert()?.id !== alert.id
                }">
                
                <!-- Card Header -->
                <div class="flex items-start justify-between gap-3">
                  <div class="flex items-start gap-2.5">
                    <!-- Severity indicator dot -->
                    <span 
                      class="w-2.5 h-2.5 rounded-full shrink-0 mt-1"
                      [ngClass]="{
                        'bg-rose-500 ring-4 ring-rose-100': alert.severity === 'CRITICAL',
                        'bg-amber-500 ring-4 ring-amber-100': alert.severity === 'WARNING',
                        'bg-blue-500 ring-4 ring-blue-100': alert.severity === 'INFO'
                      }">
                    </span>

                    <div class="flex flex-col gap-0.5">
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-xs font-bold text-slate-900 leading-snug">{{ alert.title }}</span>
                      </div>
                      <span class="text-[11px] font-mono text-slate-500">{{ alert.signal_name }}</span>
                    </div>
                  </div>

                  <!-- Severity and State Badges -->
                  <div class="flex items-center gap-1.5 shrink-0">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-rose-50 text-rose-700 border border-rose-200': alert.severity === 'CRITICAL',
                        'bg-amber-50 text-amber-800 border border-amber-200': alert.severity === 'WARNING',
                        'bg-blue-50 text-blue-700 border border-blue-200': alert.severity === 'INFO'
                      }">
                      {{ alert.severity }}
                    </span>

                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-semibold"
                      [ngClass]="{
                        'bg-rose-100 text-rose-800': alert.state === 'FIRING',
                        'bg-blue-100 text-blue-800': alert.state === 'ACKNOWLEDGED',
                        'bg-slate-100 text-slate-700': alert.state === 'SUPPRESSED',
                        'bg-emerald-100 text-emerald-800': alert.state === 'RESOLVED'
                      }">
                      {{ alert.state }}
                    </span>
                  </div>
                </div>

                <!-- Entity Scope and Recurrence -->
                <div class="flex items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs text-slate-500 flex-wrap">
                  <div class="flex items-center gap-1.5">
                    <span class="font-semibold text-slate-700">{{ ams.formatText(alert.affected_entity_type) }}:</span>
                    <span class="text-slate-900 font-medium">{{ alert.affected_entity_name }}</span>
                  </div>

                  <div class="flex items-center gap-3 text-[11px]">
                    <span>Seen: <strong class="text-slate-700 font-mono">{{ alert.recurrence_count }}x</strong></span>
                    <span>Last: <strong class="text-slate-700 font-mono">{{ alert.last_seen_at | date:'HH:mm:ss' }}</strong></span>
                  </div>
                </div>

                <!-- Linked incident ribbon if present -->
                @if (alert.linked_incident_id) {
                  <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-50/60 border border-purple-200/60 text-xs text-purple-900">
                    <app-lucide-icon name="alert-triangle" [size]="13" class="text-purple-600 shrink-0"></app-lucide-icon>
                    <span class="font-medium truncate">Linked: <strong class="font-bold">{{ alert.linked_incident_id }}</strong> - {{ alert.linked_incident_title }}</span>
                  </div>
                }

              </div>
            }
          }
        </div>

        <!-- Right / Detail: Selected Alert Inspector (5 Cols) -->
        <div class="lg:col-span-5 sticky top-4">
          @if (ams.selectedAlert(); as sel) {
            <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-5">
              
              <!-- Inspector Header -->
              <div class="flex items-start justify-between gap-3 pb-3 border-b border-slate-100">
                <div class="flex flex-col gap-1">
                  <div class="flex items-center gap-2">
                    <span class="text-[11px] font-mono font-bold text-slate-400 uppercase tracking-wider">{{ sel.id }}</span>
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-rose-100 text-rose-800': sel.severity === 'CRITICAL',
                        'bg-amber-100 text-amber-800': sel.severity === 'WARNING',
                        'bg-blue-100 text-blue-800': sel.severity === 'INFO'
                      }">
                      {{ sel.severity }}
                    </span>
                  </div>
                  <h3 class="text-base font-bold text-slate-900 leading-snug">{{ sel.title }}</h3>
                </div>

                <!-- Quick Action Buttons -->
                <div class="flex items-center gap-1.5 shrink-0">
                  @if (sel.state === 'FIRING') {
                    <button
                      type="button"
                      (click)="ams.acknowledgeAlert(sel.id)"
                      class="h-7 px-2.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center gap-1 cursor-pointer transition-colors shadow-2xs">
                      <span>Ack</span>
                    </button>
                    <button
                      type="button"
                      (click)="ams.suppressAlert(sel.id)"
                      class="h-7 px-2.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs inline-flex items-center gap-1 cursor-pointer transition-colors">
                      <span>Suppress</span>
                    </button>
                  } @else if (sel.state === 'ACKNOWLEDGED') {
                    <button
                      type="button"
                      (click)="ams.resolveAlert(sel.id)"
                      class="h-7 px-2.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs inline-flex items-center gap-1 cursor-pointer transition-colors shadow-2xs">
                      <span>Resolve</span>
                    </button>
                  } @else {
                    <button
                      type="button"
                      (click)="ams.acknowledgeAlert(sel.id)"
                      class="h-7 px-2.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs inline-flex items-center gap-1 cursor-pointer transition-colors">
                      <span>Re-open</span>
                    </button>
                  }
                </div>
              </div>

              <!-- Observed Telemetry & Threshold Comparison -->
              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-3">
                <span class="text-xs font-bold text-slate-700 tracking-wide uppercase">Evaluator Threshold Rule</span>
                
                <div class="p-2.5 rounded-lg bg-white border border-slate-200 font-mono text-xs text-slate-800 break-all">
                  {{ sel.details.rule_expression }}
                </div>

                <div class="grid grid-cols-2 gap-3 pt-1">
                  <div class="flex flex-col gap-0.5">
                    <span class="text-[11px] text-slate-500">Observed Value:</span>
                    <span class="text-xs font-bold text-rose-600 font-mono">{{ sel.details.observed_value }}</span>
                  </div>
                  <div class="flex flex-col gap-0.5">
                    <span class="text-[11px] text-slate-500">Threshold Boundary:</span>
                    <span class="text-xs font-bold text-slate-700 font-mono">{{ sel.details.threshold_value }}</span>
                  </div>
                </div>
              </div>

              <!-- Context Notes -->
              <div class="flex flex-col gap-1.5">
                <span class="text-xs font-bold text-slate-700">Diagnostic Context</span>
                <p class="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-200">
                  {{ sel.details.notes }}
                </p>
              </div>

              <!-- Affected Entity & Metadata Table -->
              <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
                <div class="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                  <span class="text-slate-500">Entity Scope:</span>
                  <span class="font-semibold text-slate-800">{{ ams.formatText(sel.affected_entity_type) }}</span>
                </div>
                <div class="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                  <span class="text-slate-500">Entity Name:</span>
                  <span class="font-mono text-slate-800 font-medium">{{ sel.affected_entity_name }}</span>
                </div>
                <div class="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                  <span class="text-slate-500">First Observed:</span>
                  <span class="font-mono text-slate-800">{{ sel.first_seen_at | date:'yyyy-MM-dd HH:mm:ss' }}</span>
                </div>
                <div class="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                  <span class="text-slate-500">Recurrence:</span>
                  <span class="font-mono text-slate-800 font-bold">{{ sel.recurrence_count }} evaluations</span>
                </div>
                <div class="flex items-center justify-between text-xs py-1">
                  <span class="text-slate-500">Dedupe Fingerprint:</span>
                  <span class="font-mono text-[11px] text-slate-600">{{ sel.dedupe_fingerprint }}</span>
                </div>
              </div>

              <!-- Cross-Module Deep Link Actions -->
              <div class="flex flex-col gap-2 pt-3 border-t border-slate-100">
                <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Cross-Module Drilldown</span>
                <div class="flex items-center gap-2 flex-wrap">
                  @if (sel.linked_incident_id) {
                    <button
                      type="button"
                      (click)="navigateToIncident(sel.linked_incident_id)"
                      class="h-8 px-3 rounded-md bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                      <app-lucide-icon name="alert-circle" [size]="13"></app-lucide-icon>
                      <span>Investigate Incident</span>
                    </button>
                  }

                  @if (sel.deep_link_migration_id) {
                    <button
                      type="button"
                      (click)="navigateToMigration(sel.deep_link_migration_id)"
                      class="h-8 px-3 rounded-md bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                      <app-lucide-icon name="layers" [size]="13"></app-lucide-icon>
                      <span>View Migration</span>
                    </button>
                  }

                  @if (sel.deep_link_platform_tab) {
                    <button
                      type="button"
                      (click)="navigateToPlatform(sel.deep_link_platform_tab)"
                      class="h-8 px-3 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors">
                      <app-lucide-icon name="server" [size]="13"></app-lucide-icon>
                      <span>Platform {{ ams.formatText(sel.deep_link_platform_tab) }}</span>
                    </button>
                  }
                </div>
              </div>

            </div>
          } @else {
            <div class="p-8 rounded-2xl bg-white border border-slate-200 shadow-2xs text-center text-xs text-slate-500">
              Select an alert from the roster to inspect root cause telemetry.
            </div>
          }
        </div>

      </div>

    </div>
  `
})
export class AlertsActiveTabComponent {
  public ams = inject(AlertsMonitoringService);
  private router = inject(Router);

  public severityOptions: SelectOption[] = [
    { label: 'All Severities', value: 'ALL' },
    { label: 'Critical Only', value: 'CRITICAL' },
    { label: 'Warning Only', value: 'WARNING' },
    { label: 'Info Only', value: 'INFO' }
  ];

  public stateOptions: SelectOption[] = [
    { label: 'All Lifecycle States', value: 'ALL' },
    { label: 'Firing Only', value: 'FIRING' },
    { label: 'Acknowledged', value: 'ACKNOWLEDGED' },
    { label: 'Suppressed', value: 'SUPPRESSED' },
    { label: 'Resolved', value: 'RESOLVED' }
  ];

  public get linkedAlertsCount(): number {
    return this.ams.alerts().filter(a => !!a.linked_incident_id).length;
  }

  public onSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.ams.alertSearchQuery.set(target.value);
  }

  public navigateToIncident(incidentId: string): void {
    this.ams.selectIncident(incidentId);
    this.ams.selectTab('incidents');
    this.router.navigate(['/monitoring/alerts', 'incidents']);
  }

  public navigateToMigration(migrationId: string): void {
    this.router.navigate(['/monitoring/migrations', migrationId]);
  }

  public navigateToPlatform(platformTab: string): void {
    this.router.navigate(['/monitoring/platform', platformTab]);
  }
}
