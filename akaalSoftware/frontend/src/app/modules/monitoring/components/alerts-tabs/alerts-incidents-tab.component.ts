/**
 * AKAAL Monitoring — Part 4 of 4: Incidents Tab Component
 * Operational incidents lifecycle management, advisory RCA, linked alerts,
 * audit timeline, and operator collaborative notes.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AlertsMonitoringService } from '../../services/alerts-monitoring.service';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { IncidentDTO, IncidentStatus } from '../../models/alerts-monitoring.models';

@Component({
  selector: 'app-alerts-incidents-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Incidents Header Summary & Filters -->
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        
        <!-- Search Input -->
        <div class="relative flex-1">
          <app-lucide-icon name="search" [size]="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
          <input
            type="text"
            [value]="ams.incidentSearchQuery()"
            (input)="onSearchInput($event)"
            placeholder="Search incidents by ID, title, summary, or affected scope..."
            class="w-full pl-9 pr-4 py-2 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 transition-all"
          />
        </div>

        <!-- Status Filter Dropdown -->
        <div class="w-full sm:w-56">
          <app-custom-select
            [options]="statusOptions"
            [value]="ams.incidentStatusFilter()"
            (valueChange)="ams.incidentStatusFilter.set($event)"
            placeholder="Filter Status">
          </app-custom-select>
        </div>

      </div>

      <!-- 2. Two-Column Workspace: Incident Roster + Deep Investigation Workbench -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        <!-- Left: Incident Roster (4 Cols) -->
        <div class="lg:col-span-4 flex flex-col gap-3">
          @if (ams.filteredIncidents().length === 0) {
            <div class="p-8 rounded-2xl bg-white border border-slate-200 shadow-2xs text-center flex flex-col items-center justify-center gap-2">
              <app-lucide-icon name="check-circle" [size]="28" class="text-emerald-500 mb-1"></app-lucide-icon>
              <h4 class="text-xs font-bold text-slate-800">No Incidents Found</h4>
              <p class="text-[11px] text-slate-500">No operational incidents match the current criteria.</p>
            </div>
          } @else {
            @for (incident of ams.filteredIncidents(); track incident.id) {
              <div
                (click)="ams.selectIncident(incident.id)"
                class="p-4 rounded-2xl bg-white border transition-all cursor-pointer shadow-2xs flex flex-col gap-2.5"
                [ngClass]="{
                  'border-blue-600 ring-1 ring-blue-600/30 bg-blue-50/10': ams.selectedIncident()?.id === incident.id,
                  'border-slate-200 hover:border-slate-300': ams.selectedIncident()?.id !== incident.id
                }">
                
                <!-- Incident Header -->
                <div class="flex items-start justify-between gap-2">
                  <span class="text-xs font-mono font-bold text-slate-900">{{ incident.id }}</span>
                  
                  <div class="flex items-center gap-1.5 shrink-0">
                    <!-- Severity badge -->
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-rose-50 text-rose-700 border border-rose-200': incident.severity === 'CRITICAL',
                        'bg-amber-50 text-amber-800 border border-amber-200': incident.severity === 'HIGH' || incident.severity === 'MEDIUM',
                        'bg-blue-50 text-blue-700 border border-blue-200': incident.severity === 'LOW'
                      }">
                      {{ incident.severity }}
                    </span>

                    <!-- Status badge -->
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-semibold"
                      [ngClass]="{
                        'bg-rose-100 text-rose-800': incident.status === 'INVESTIGATING',
                        'bg-amber-100 text-amber-800': incident.status === 'IDENTIFIED',
                        'bg-blue-100 text-blue-800': incident.status === 'MONITORING',
                        'bg-emerald-100 text-emerald-800': incident.status === 'RESOLVED'
                      }">
                      {{ incident.status }}
                    </span>
                  </div>
                </div>

                <!-- Title -->
                <h4 class="text-xs font-bold text-slate-800 leading-snug">{{ incident.title }}</h4>

                <!-- Scope & Alerts Count -->
                <div class="flex items-center justify-between gap-2 pt-2 border-t border-slate-100 text-[11px] text-slate-500">
                  <span class="truncate">{{ incident.affected_scope_label }}</span>
                  <span class="shrink-0 font-medium text-slate-700 font-mono">{{ incident.linked_alerts_count }} alerts</span>
                </div>

              </div>
            }
          }
        </div>

        <!-- Right: Selected Incident Workbench (8 Cols) -->
        <div class="lg:col-span-8 flex flex-col gap-6">
          @if (ams.selectedIncident(); as inc) {
            
            <!-- Workbench Header Card -->
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-5">
              
              <!-- Title & Status Actions -->
              <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-slate-100">
                <div class="flex flex-col gap-1.5">
                  <div class="flex items-center gap-2.5 flex-wrap">
                    <span class="text-xs font-mono font-bold text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200/60">
                      {{ inc.id }}
                    </span>
                    
                    <span 
                      class="px-2.5 py-0.5 rounded text-xs font-bold"
                      [ngClass]="{
                        'bg-rose-100 text-rose-800': inc.severity === 'CRITICAL',
                        'bg-amber-100 text-amber-800': inc.severity === 'HIGH' || inc.severity === 'MEDIUM',
                        'bg-blue-100 text-blue-800': inc.severity === 'LOW'
                      }">
                      {{ inc.severity }} SEVERITY
                    </span>

                    <span class="text-xs text-slate-400 font-mono">
                      Opened {{ inc.opened_at | date:'yyyy-MM-dd HH:mm:ss' }}
                    </span>
                  </div>

                  <h2 class="text-lg font-bold text-slate-900 tracking-tight">{{ inc.title }}</h2>
                </div>

                <!-- Incident Lifecycle Transitions -->
                <div class="flex flex-col items-end gap-1.5 shrink-0">
                  <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Lifecycle Transition</span>
                  <div class="flex items-center gap-1.5 flex-wrap">
                    @for (st of lifecycleStatuses; track st) {
                      <button
                        type="button"
                        (click)="ams.updateIncidentStatus(inc.id, st)"
                        class="h-7 px-2.5 rounded-md font-semibold text-xs cursor-pointer transition-colors shadow-2xs"
                        [ngClass]="{
                          'bg-blue-600 text-white': inc.status === st,
                          'bg-slate-100 hover:bg-slate-200 text-slate-700': inc.status !== st
                        }">
                        {{ st }}
                      </button>
                    }
                  </div>
                </div>
              </div>

              <!-- Incident Summary & Affected Scope Links -->
              <div class="flex flex-col gap-3">
                <p class="text-xs text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
                  {{ inc.summary }}
                </p>

                <!-- Affected Cross-Module Links -->
                <div class="flex items-center gap-2 flex-wrap">
                  @if (inc.affected_migration_id) {
                    <button
                      type="button"
                      (click)="navigateToMigration(inc.affected_migration_id)"
                      class="h-8 px-3 rounded-md bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                      <app-lucide-icon name="layers" [size]="13"></app-lucide-icon>
                      <span>Migration: {{ inc.affected_migration_name }}</span>
                    </button>
                  }

                  @if (inc.affected_platform_resource) {
                    <button
                      type="button"
                      (click)="navigateToPlatform('connectivity')"
                      class="h-8 px-3 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors">
                      <app-lucide-icon name="server" [size]="13"></app-lucide-icon>
                      <span>Platform: {{ inc.affected_platform_resource }}</span>
                    </button>
                  }
                </div>
              </div>

            </div>

            <!-- Advisory RCA Card -->
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
              <div class="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="compass" [size]="16" class="text-blue-600"></app-lucide-icon>
                  <h3 class="text-sm font-bold text-slate-900">Advisory Root Cause Analysis (RCA)</h3>
                </div>
                <span class="text-[11px] text-slate-500 font-mono">Statistical Inference Engine</span>
              </div>

              <div class="grid grid-cols-1 gap-3">
                @for (rca of inc.advisory_rca; track rca.hypothesis) {
                  <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-2.5">
                    
                    <div class="flex items-start justify-between gap-4">
                      <div class="flex flex-col gap-0.5">
                        <span class="text-xs font-bold text-slate-900">{{ rca.hypothesis }}</span>
                        <span class="text-[11px] font-semibold text-blue-700">{{ rca.epistemic_status }}</span>
                      </div>

                      <div class="flex items-center gap-2 shrink-0">
                        <div class="w-20 bg-slate-200 rounded-full h-2 overflow-hidden">
                          <div 
                            class="bg-blue-600 h-2 rounded-full" 
                            [style.width.%]="rca.confidence_pct">
                          </div>
                        </div>
                        <span class="text-xs font-mono font-bold text-slate-800">{{ rca.confidence_pct }}%</span>
                      </div>
                    </div>

                    <div class="text-xs text-slate-600 bg-white p-3 rounded-lg border border-slate-200 font-mono text-[11px] leading-relaxed">
                      <strong class="text-slate-800 font-sans">Evidence: </strong> {{ rca.evidence }}
                    </div>

                  </div>
                }
              </div>
            </div>

            <!-- Linked Active Alerts Section -->
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
              <div class="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="bell" [size]="16" class="text-amber-600"></app-lucide-icon>
                  <h3 class="text-sm font-bold text-slate-900">Correlated Triggering Alerts</h3>
                </div>
                <span class="text-xs font-mono font-bold text-slate-700">{{ inc.linked_alerts.length }} alerts</span>
              </div>

              <div class="flex flex-col gap-2">
                @for (alert of inc.linked_alerts; track alert.id) {
                  <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-4">
                    <div class="flex items-center gap-3">
                      <span 
                        class="w-2 h-2 rounded-full shrink-0"
                        [ngClass]="{
                          'bg-rose-500': alert.severity === 'CRITICAL',
                          'bg-amber-500': alert.severity === 'WARNING',
                          'bg-blue-500': alert.severity === 'INFO'
                        }">
                      </span>
                      <div class="flex flex-col gap-0.5">
                        <span class="text-xs font-bold text-slate-900">{{ alert.title }}</span>
                        <span class="text-[11px] font-mono text-slate-500">{{ alert.signal_name }} &bull; {{ alert.affected_entity_name }}</span>
                      </div>
                    </div>

                    <div class="flex items-center gap-2 shrink-0">
                      <span class="text-xs font-mono text-slate-700 font-semibold">{{ alert.details.observed_value }}</span>
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">{{ alert.state }}</span>
                    </div>
                  </div>
                }
              </div>
            </div>

            <!-- Incident Audit Timeline -->
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
              <div class="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="clock" [size]="16" class="text-slate-600"></app-lucide-icon>
                  <h3 class="text-sm font-bold text-slate-900">Incident Audit Timeline</h3>
                </div>
              </div>

              <div class="relative pl-6 border-l-2 border-slate-200 flex flex-col gap-4">
                @for (evt of inc.timeline; track evt.id) {
                  <div class="relative flex flex-col gap-1">
                    <!-- Timeline Node Circle -->
                    <span 
                      class="absolute -left-[31px] top-1 w-3 h-3 rounded-full border-2 border-white"
                      [ngClass]="{
                        'bg-rose-500': evt.severity === 'CRITICAL',
                        'bg-amber-500': evt.severity === 'WARNING',
                        'bg-blue-500': evt.severity === 'INFO'
                      }">
                    </span>

                    <div class="flex items-center gap-2 flex-wrap text-xs">
                      <span class="font-mono text-slate-400">{{ evt.timestamp | date:'HH:mm:ss' }}</span>
                      <span class="font-bold text-slate-800">{{ ams.formatText(evt.event_type) }}</span>
                      <span class="text-slate-400">&bull;</span>
                      <span class="text-slate-600 font-medium">{{ evt.actor }}</span>
                    </div>

                    <p class="text-xs text-slate-600">{{ evt.description }}</p>
                  </div>
                }
              </div>
            </div>

            <!-- Operational Notes & Operator Collaboration -->
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
              <div class="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="message-square" [size]="16" class="text-blue-600"></app-lucide-icon>
                  <h3 class="text-sm font-bold text-slate-900">Operator Collaboration Notes</h3>
                </div>
                <span class="text-xs text-slate-500 font-mono">{{ inc.operational_notes.length }} notes</span>
              </div>

              <!-- Note Composer -->
              <div class="flex flex-col gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
                <textarea
                  [(ngModel)]="newNoteContent"
                  placeholder="Add operational update, mitigation detail, or SRE note..."
                  rows="2"
                  class="w-full p-2.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 transition-all resize-none"
                ></textarea>

                <div class="flex justify-end">
                  <button
                    type="button"
                    (click)="submitNote(inc.id)"
                    [disabled]="!newNoteContent.trim()"
                    class="h-8 px-4 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs disabled:opacity-50">
                    <app-lucide-icon name="send" [size]="12"></app-lucide-icon>
                    <span>Post Note</span>
                  </button>
                </div>
              </div>

              <!-- Existing Notes Roster -->
              <div class="flex flex-col gap-3 pt-2">
                @for (note of inc.operational_notes; track note.id) {
                  <div class="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/80 flex flex-col gap-1.5">
                    <div class="flex items-center justify-between text-[11px] text-slate-500">
                      <span class="font-bold text-slate-800">{{ note.author }}</span>
                      <span class="font-mono">{{ note.timestamp | date:'yyyy-MM-dd HH:mm:ss' }}</span>
                    </div>
                    <p class="text-xs text-slate-700 leading-relaxed">{{ note.content }}</p>
                  </div>
                }
              </div>

            </div>

          } @else {
            <div class="p-12 rounded-2xl bg-white border border-slate-200 shadow-2xs text-center text-xs text-slate-500">
              Select an incident from the roster to inspect detailed root cause analysis.
            </div>
          }
        </div>

      </div>

    </div>
  `
})
export class AlertsIncidentsTabComponent {
  public ams = inject(AlertsMonitoringService);
  private router = inject(Router);

  public newNoteContent = '';

  public lifecycleStatuses: IncidentStatus[] = [
    'INVESTIGATING',
    'IDENTIFIED',
    'MONITORING',
    'RESOLVED'
  ];

  public statusOptions: SelectOption[] = [
    { label: 'All Incident States', value: 'ALL' },
    { label: 'Investigating', value: 'INVESTIGATING' },
    { label: 'Identified', value: 'IDENTIFIED' },
    { label: 'Monitoring', value: 'MONITORING' },
    { label: 'Resolved', value: 'RESOLVED' }
  ];

  public onSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.ams.incidentSearchQuery.set(target.value);
  }

  public submitNote(incidentId: string): void {
    if (!this.newNoteContent.trim()) return;
    this.ams.addIncidentNote(incidentId, this.newNoteContent);
    this.newNoteContent = '';
  }

  public navigateToMigration(migrationId: string): void {
    this.router.navigate(['/monitoring/migrations', migrationId]);
  }

  public navigateToPlatform(platformTab: string): void {
    this.router.navigate(['/monitoring/platform', platformTab]);
  }
}
