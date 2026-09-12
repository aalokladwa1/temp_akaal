/**
 * AKAAL Monitoring — Part 3 of 4: Platform Runtime & Services Tab Component
 * Observability into internal runtime daemons, coordinator, execution engine,
 * checkpoint durability, and IPC dispatcher with selected service drill-down.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { PlatformMonitoringService } from '../../services/platform-monitoring.service';
import { RuntimeServiceDTO } from '../../models/platform-monitoring.models';

@Component({
  selector: 'app-platform-runtime-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- Filter Toolbar -->
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        
        <!-- Search Input -->
        <div class="relative flex-1 min-w-[240px]">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </div>
          <input
            type="text"
            [ngModel]="pms.serviceSearchQuery()"
            (ngModelChange)="pms.setServiceSearch($event)"
            placeholder="Search internal runtime services, subsystems, or roles..."
            class="w-full h-9 pl-9 pr-3.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 focus:bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors">
        </div>

        <!-- Status Filter with CustomSelect -->
        <div class="w-40">
          <app-custom-select
            [options]="statusOptions"
            [value]="pms.serviceStatusFilter()"
            (valueChange)="pms.setServiceStatusFilter($event)"
            [placeholder]="'All Status'"
            [size]="'sm'">
          </app-custom-select>
        </div>

      </div>

      <!-- Services Inventory Table -->
      <div class="rounded-2xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
        <div class="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Internal Runtime Services &amp; Daemons</h3>
          <span class="text-xs text-slate-500 font-medium">
            Showing {{ pms.filteredServices().length }} of {{ pms.data().runtime_services.length }} services
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75 select-none">
                <th class="py-3 px-4 min-w-[220px]">Service / Subsystem</th>
                <th class="py-3 px-4 min-w-[100px]">Version</th>
                <th class="py-3 px-4 min-w-[110px]">Availability</th>
                <th class="py-3 px-4 min-w-[110px]">P95 Latency</th>
                <th class="py-3 px-4 min-w-[90px]">Errors (24h)</th>
                <th class="py-3 px-4 min-w-[120px]">Health &amp; State</th>
                <th class="py-3 px-4 text-right min-w-[90px]">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (svc of pms.filteredServices(); track svc.id) {
                <tr 
                  (click)="pms.selectService(svc.id)"
                  class="hover:bg-slate-50/75 transition-colors cursor-pointer group"
                  [ngClass]="{'bg-blue-50/30': pms.selectedServiceId() === svc.id}">
                  
                  <!-- Service Name & Subsystem -->
                  <td class="py-3.5 px-4">
                    <div class="font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                      {{ svc.name }}
                    </div>
                    <div class="text-[11px] font-mono text-slate-500">
                      {{ svc.subsystem }}
                    </div>
                  </td>

                  <!-- Version -->
                  <td class="py-3.5 px-4 font-mono text-slate-700">
                    {{ svc.version }}
                  </td>

                  <!-- Availability -->
                  <td class="py-3.5 px-4 font-mono font-semibold text-emerald-700">
                    {{ svc.availability_pct }}%
                  </td>

                  <!-- Latency -->
                  <td class="py-3.5 px-4 font-mono text-slate-800 font-semibold">
                    {{ svc.p95_latency_ms }} ms
                  </td>

                  <!-- Errors -->
                  <td class="py-3.5 px-4 font-mono" [ngClass]="svc.error_count_24h > 0 ? 'text-amber-700 font-bold' : 'text-slate-500'">
                    {{ svc.error_count_24h }}
                  </td>

                  <!-- Health & Status -->
                  <td class="py-3.5 px-4 whitespace-nowrap">
                    <div class="flex items-center gap-2">
                      <span 
                        class="w-2.5 h-2.5 rounded-full shrink-0"
                        [ngClass]="{
                          'bg-emerald-500': svc.health === 'HEALTHY',
                          'bg-amber-500': svc.health === 'DEGRADED',
                          'bg-rose-500': svc.health === 'UNHEALTHY',
                          'bg-slate-400': svc.health === 'UNKNOWN'
                        }">
                      </span>
                      <span class="font-medium text-slate-800">{{ pms.formatText(svc.status) }}</span>
                    </div>
                  </td>

                  <!-- Action -->
                  <td class="py-3.5 px-4 whitespace-nowrap text-right">
                    <button
                      type="button"
                      (click)="pms.selectService(svc.id); $event.stopPropagation()"
                      class="h-7 px-2.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs cursor-pointer shadow-2xs transition-colors">
                      Inspect
                    </button>
                  </td>

                </tr>
              }

              @if (pms.filteredServices().length === 0) {
                <tr>
                  <td colspan="7" class="py-12 text-center text-slate-400 text-xs">
                    No runtime services match search or filter criteria.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Selected Service Detail Card (Lazy Drill-Down) -->
      @if (pms.selectedService(); as svc) {
        <div class="p-5 rounded-2xl bg-white border border-blue-200 shadow-sm flex flex-col gap-4 animate-in fade-in duration-100">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
              <div>
                <h3 class="text-base font-bold text-slate-900 tracking-tight font-heading">{{ svc.name }}</h3>
                <span class="text-xs font-mono text-slate-500">{{ svc.subsystem }}</span>
              </div>
            </div>
            
            <button
              type="button"
              (click)="pms.selectService(null)"
              class="h-7 px-2.5 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-medium cursor-pointer">
              Close Detail ✕
            </button>
          </div>

          <p class="text-xs text-slate-700 leading-relaxed">{{ svc.description }}</p>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Memory Allocated</span>
              <span class="font-mono font-bold text-slate-900 text-sm">{{ svc.memory_allocated_mb }} MB</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Threads / Routines</span>
              <span class="font-mono font-bold text-slate-900 text-sm">{{ svc.goroutines_or_threads }}</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Liveness &amp; Readiness</span>
              <span class="font-semibold text-emerald-700 text-sm">Pass / Pass</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Dependencies</span>
              <span class="font-mono text-slate-700 text-xs truncate" [title]="svc.dependencies_summary">{{ svc.dependencies_summary }}</span>
            </div>
          </div>
        </div>
      }

    </div>
  `
})
export class PlatformRuntimeTabComponent {
  public pms = inject(PlatformMonitoringService);

  public statusOptions: CustomSelectOption[] = [
    { label: 'All Status', value: 'ALL', desc: 'Show all internal runtime services' },
    { label: 'Active', value: 'ACTIVE', desc: 'Running and dispatching requests' },
    { label: 'Standby', value: 'STANDBY', desc: 'Warm replica in standby quorum' },
    { label: 'Degraded', value: 'DEGRADED', desc: 'Operating with latency or retry backpressure' },
    { label: 'Failed', value: 'FAILED', desc: 'Service halted or unrecoverable' }
  ];
}
