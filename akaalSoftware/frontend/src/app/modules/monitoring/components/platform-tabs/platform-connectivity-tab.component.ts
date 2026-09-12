/**
 * AKAAL Monitoring — Part 3 of 4: Platform Connectivity & Endpoints Tab Component
 * Real-time operational health of data-path connectors, driver/auth status,
 * connection pools, RTT latencies, and external dependencies.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { PlatformMonitoringService } from '../../services/platform-monitoring.service';

@Component({
  selector: 'app-platform-connectivity-tab',
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
            [ngModel]="pms.connectorSearchQuery()"
            (ngModelChange)="pms.setConnectorSearch($event)"
            placeholder="Search data-path connectors by provider name or target endpoint..."
            class="w-full h-9 pl-9 pr-3.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 focus:bg-white text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors">
        </div>

        <!-- Family Filter with CustomSelect -->
        <div class="w-44">
          <app-custom-select
            [options]="familyOptions"
            [value]="pms.connectorFamilyFilter()"
            (valueChange)="pms.setConnectorFamilyFilter($event)"
            [placeholder]="'All Families'"
            [size]="'sm'">
          </app-custom-select>
        </div>

      </div>

      <!-- 1. Data-Path Connectors Table -->
      <div class="rounded-2xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
        <div class="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Data-Path Connectors &amp; Endpoints</h3>
          <span class="text-xs text-slate-500 font-medium">
            Showing {{ pms.filteredConnectors().length }} of {{ pms.data().connectors.length }} connectors
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75 select-none">
                <th class="py-3 px-4 min-w-[220px]">Provider / Engine</th>
                <th class="py-3 px-4 min-w-[200px]">Endpoint Target</th>
                <th class="py-3 px-4 min-w-[120px]">Driver &amp; Auth</th>
                <th class="py-3 px-4 min-w-[110px]">Connection Pool</th>
                <th class="py-3 px-4 min-w-[100px]">Network RTT</th>
                <th class="py-3 px-4 text-right min-w-[120px]">Health &amp; State</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (conn of pms.filteredConnectors(); track conn.id) {
                <tr class="hover:bg-slate-50/75 transition-colors">
                  
                  <!-- Provider Name & Family -->
                  <td class="py-3.5 px-4">
                    <div class="font-bold text-slate-900">
                      {{ conn.provider }}
                    </div>
                    <div class="text-[11px] font-medium text-slate-500">
                      {{ pms.formatText(conn.family) }}
                    </div>
                  </td>

                  <!-- Endpoint Target -->
                  <td class="py-3.5 px-4 font-mono text-slate-700 truncate max-w-[240px]" [title]="conn.endpoint_target">
                    {{ conn.endpoint_target }}
                  </td>

                  <!-- Driver & Auth -->
                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2 py-0.5 rounded text-[11px] font-semibold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700': conn.driver_status === 'AUTHENTICATED',
                        'bg-rose-50 text-rose-700': conn.driver_status === 'UNAUTHORIZED',
                        'bg-amber-50 text-amber-700': conn.driver_status === 'UNAVAILABLE',
                        'bg-slate-100 text-slate-600': conn.driver_status === 'NOT_CONFIGURED'
                      }">
                      {{ pms.formatText(conn.driver_status) }}
                    </span>
                  </td>

                  <!-- Pool Active / Max -->
                  <td class="py-3.5 px-4 font-mono">
                    <span class="font-semibold text-slate-800">{{ conn.active_connections }}</span>
                    <span class="text-slate-400"> / {{ conn.pool_max }}</span>
                  </td>

                  <!-- RTT Latency -->
                  <td class="py-3.5 px-4 font-mono font-semibold" [ngClass]="conn.rtt_latency_ms < 10 ? 'text-emerald-700' : 'text-amber-700'">
                    {{ conn.rtt_latency_ms }} ms
                  </td>

                  <!-- Health & State (Circular Dot Indicator) -->
                  <td class="py-3.5 px-4 whitespace-nowrap text-right">
                    <div class="inline-flex items-center gap-2">
                      <span 
                        class="w-2.5 h-2.5 rounded-full shrink-0"
                        [ngClass]="{
                          'bg-emerald-500': conn.health === 'HEALTHY',
                          'bg-amber-500': conn.health === 'DEGRADED',
                          'bg-rose-500': conn.health === 'UNHEALTHY',
                          'bg-slate-400': conn.health === 'UNKNOWN'
                        }">
                      </span>
                      <span class="font-medium text-slate-800">{{ pms.formatText(conn.reachability) }}</span>
                    </div>
                  </td>

                </tr>
              }

              @if (pms.filteredConnectors().length === 0) {
                <tr>
                  <td colspan="6" class="py-12 text-center text-slate-400 text-xs">
                    No data-path connectors match the search or filter criteria.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- 2. External Infrastructure Dependencies -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">External Infrastructure Dependencies</h3>
          <span class="text-xs text-slate-500 font-medium">{{ pms.data().external_dependencies.length }} dependencies</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          @for (dep of pms.data().external_dependencies; track dep.id) {
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between gap-3 text-xs">
              <div class="flex flex-col gap-1">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-slate-900">{{ dep.name }}</span>
                  <span class="flex items-center gap-1.5 text-slate-700 font-medium">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    {{ pms.formatText(dep.health) }}
                  </span>
                </div>
                <div class="text-[11px] font-medium text-slate-500">{{ pms.formatText(dep.category) }}</div>
                <p class="text-slate-600 pt-1 border-t border-slate-100">{{ dep.summary }}</p>
              </div>

              <div class="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-200/60">
                <span>Latency: <strong class="text-emerald-700">{{ dep.latency_ms }} ms</strong></span>
                <span class="text-slate-600">{{ dep.reachability }}</span>
              </div>
            </div>
          }
        </div>
      </div>

    </div>
  `
})
export class PlatformConnectivityTabComponent {
  public pms = inject(PlatformMonitoringService);

  public familyOptions: CustomSelectOption[] = [
    { label: 'All Families', value: 'ALL', desc: 'All supported engine families' },
    { label: 'Relational', value: 'RELATIONAL', desc: 'Oracle, PostgreSQL, MySQL, SQL Server' },
    { label: 'Warehouse / Lakehouse', value: 'WAREHOUSE', desc: 'Snowflake, BigQuery, Redshift, Databricks' },
    { label: 'NoSQL / Document', value: 'NOSQL', desc: 'MongoDB, Cassandra, DynamoDB, Redis' },
    { label: 'Streaming', value: 'STREAMING', desc: 'Kafka, Event Hubs, Kinesis, Pulsar' },
    { label: 'Object Storage', value: 'OBJECT_STORAGE', desc: 'S3, GCS, Azure Blob, MinIO' }
  ];
}
