import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { TableProgressItem, WorkerTelemetryItem, ExecutionSiteItem, SchemaObjectExecutionItem } from '../cockpit.models';

@Component({
  selector: 'app-cockpit-workbench',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col overflow-hidden">
      
      <!-- Tab Header Bar -->
      <div class="px-6 pt-5 bg-slate-50/70 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="layout-grid" [size]="18" class="text-blue-600" />
          <h3 class="text-base font-bold text-slate-900 tracking-tight font-heading">Operational Workbench</h3>
        </div>

        <!-- Navigation Tabs (Blue accent active state) -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-0 scrollbar-none">
          @for (domain of store.workbenchData().availableDomains; track domain) {
            <button
              (click)="store.setActiveWorkbenchTab(domain)"
              [ngClass]="store.activeWorkbenchTab() === domain 
                ? 'border-blue-600 text-blue-700 font-bold bg-white shadow-2xs' 
                : 'border-transparent text-slate-600 hover:text-blue-700 hover:bg-blue-50/50 font-medium'"
              class="px-3.5 py-2 text-xs rounded-t-lg border-b-2 transition-all shrink-0 whitespace-nowrap cursor-pointer">
              {{ cleanText(formatDomainTabTitle(domain)) }}
            </button>
          }
        </div>
      </div>

      <!-- Tab Content Area with Generous Spacing -->
      <div class="p-6">

        <!-- DOMAIN 1: DATA MOVEMENT (M1, M2, M7) -->
        @if (store.activeWorkbenchTab() === 'data_movement' && store.workbenchData().dataMovement; as dm) {
          <div class="flex flex-col gap-5">
            <!-- Header Summary Row -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/80 border border-slate-200 rounded-lg p-4 text-xs">
              <div class="flex items-center gap-4">
                <span>Tables Completed: <strong class="font-mono text-slate-900 font-bold">{{ dm.completedTables }}/{{ dm.totalTables }}</strong></span>
                <span class="text-slate-300">&middot;</span>
                <span>Active Extractions: <strong class="font-mono text-blue-700 font-bold">{{ dm.activeTablesCount }}</strong></span>
              </div>
              <div class="flex items-center gap-4">
                <span>Aggregate Rate: <strong class="font-mono text-slate-900 font-bold">{{ dm.overallRowsSec | number }} rows/s</strong></span>
                <span class="text-slate-300">&middot;</span>
                <span>Throughput: <strong class="font-mono text-slate-900 font-bold">1.42 GB/s</strong></span>
              </div>
            </div>

            <!-- Table Progress Table -->
            <div class="border border-slate-200 rounded-lg overflow-hidden shadow-2xs">
              <table class="w-full text-left text-xs border-collapse">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                    <th class="py-3 px-4">Table Name</th>
                    <th class="py-3 px-4">Progress</th>
                    <th class="py-3 px-4 text-right">Rows Processed</th>
                    <th class="py-3 px-4 text-right">Throughput</th>
                    <th class="py-3 px-4 text-center">Workers</th>
                    <th class="py-3 px-4 text-right">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 font-sans">
                  @for (t of dm.tableProgressList; track t.tableName) {
                    <tr class="hover:bg-blue-50/30 transition-colors">
                      <td class="py-3 px-4 font-mono font-bold text-slate-900">
                        {{ cleanText(t.schemaName) }}.{{ cleanText(t.tableName) }}
                      </td>
                      <td class="py-3 px-4 min-w-[150px]">
                        <div class="flex items-center gap-2.5">
                          <div class="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200/60">
                            <div class="h-full bg-blue-600 rounded-full" [style.width.%]="t.percentComplete"></div>
                          </div>
                          <span class="font-mono text-xs font-semibold text-slate-700 w-11 text-right">{{ t.percentComplete }}%</span>
                        </div>
                      </td>
                      <td class="py-3 px-4 text-right font-mono text-slate-700 font-medium">
                        {{ t.rowsProcessed | number }} / {{ t.rowsTotal | number }}
                      </td>
                      <td class="py-3 px-4 text-right font-mono text-slate-900 font-semibold">
                        {{ t.throughputRowsSec | number }} r/s
                      </td>
                      <td class="py-3 px-4 text-center font-mono text-slate-700">
                        {{ t.activeWorkers }}
                      </td>
                      <td class="py-3 px-4 text-right">
                        <span [ngClass]="getTableStateBadgeClasses(t.state)"
                              class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border shadow-3xs">
                          {{ cleanText(t.state) }}
                        </span>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }

        <!-- DOMAIN 2: CDC & CONVERGENCE (M2, M3) -->
        @if (store.activeWorkbenchTab() === 'cdc_convergence' && store.workbenchData().cdcConvergence; as cdc) {
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            <div class="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Capture SCN / LSN</span>
              <div class="mt-2 font-mono text-sm font-bold text-slate-900 break-all">{{ cleanText(cdc.captureScn) }}</div>
              <div class="text-[11px] text-slate-500 mt-2">Source transaction stream position</div>
            </div>

            <div class="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Apply LSN Position</span>
              <div class="mt-2 font-mono text-sm font-bold text-slate-900 break-all">{{ cleanText(cdc.applyLsn) }}</div>
              <div class="text-[11px] text-slate-500 mt-2">Target engine commit boundary</div>
            </div>

            <div class="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Replication Lag</span>
              <div class="mt-2 flex items-baseline gap-1.5">
                <span class="font-mono text-xl font-bold text-emerald-600">{{ cdc.lagMs }}</span>
                <span class="text-xs text-slate-500 font-medium">ms</span>
              </div>
              <div class="text-[11px] text-emerald-700 font-semibold mt-2">Status: {{ cleanText(cdc.convergenceStatus) }}</div>
            </div>

            <div class="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Memory Spool Buffer</span>
              <div class="mt-2 flex items-baseline gap-1.5">
                <span class="font-mono text-base font-bold text-slate-900">{{ cdc.bufferUsedMb }} MB</span>
                <span class="text-xs text-slate-500 font-medium">/ {{ cdc.bufferCapacityMb }} MB</span>
              </div>
              <div class="text-[11px] text-slate-500 mt-2">DLQ Count: <strong class="font-mono text-slate-800">{{ cdc.dlqCount }}</strong></div>
            </div>
          </div>
        }

        <!-- DOMAIN 3: WORKERS POOL (Universal) -->
        @if (store.activeWorkbenchTab() === 'workers_pool' && store.workbenchData().workersPool; as wp) {
          <div class="flex flex-col gap-4">
            <div class="flex items-center justify-between text-xs text-slate-600 bg-slate-50/80 border border-slate-200 rounded-lg p-3.5">
              <span>Total Workers: <strong class="font-mono text-slate-900 font-bold">{{ wp.totalWorkers }}</strong></span>
              <span>Active: <strong class="font-mono text-blue-700 font-bold">{{ wp.activeWorkers }}</strong></span>
              <span>Idle: <strong class="font-mono text-slate-600 font-bold">{{ wp.idleWorkers }}</strong></span>
              <span>Unhealthy: <strong class="font-mono text-rose-700 font-bold">{{ wp.unhealthyWorkers }}</strong></span>
            </div>

            <div class="border border-slate-200 rounded-lg overflow-hidden shadow-2xs">
              <table class="w-full text-left text-xs border-collapse">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                    <th class="py-3 px-4">Worker ID</th>
                    <th class="py-3 px-4">Execution Site</th>
                    <th class="py-3 px-4">Assigned Entity</th>
                    <th class="py-3 px-4 text-right">Throughput</th>
                    <th class="py-3 px-4 text-right">Memory (MB)</th>
                    <th class="py-3 px-4 text-right">Heartbeat</th>
                    <th class="py-3 px-4 text-right">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 font-mono text-slate-700">
                  @for (w of wp.workersList; track w.workerId) {
                    <tr class="hover:bg-blue-50/30 transition-colors">
                      <td class="py-3 px-4 font-bold text-slate-900">{{ cleanText(w.workerId) }} (T-{{ w.threadId }})</td>
                      <td class="py-3 px-4 font-sans text-slate-600">{{ cleanText(w.siteName) }}</td>
                      <td class="py-3 px-4 text-slate-900 font-bold">{{ cleanText(w.assignedEntity) }}</td>
                      <td class="py-3 px-4 text-right font-bold text-slate-900">{{ w.throughputRowsSec | number }} r/s</td>
                      <td class="py-3 px-4 text-right font-medium">{{ w.memoryMb }}</td>
                      <td class="py-3 px-4 text-right text-slate-500 font-medium">{{ w.heartbeatAgeMs }} ms</td>
                      <td class="py-3 px-4 text-right font-sans">
                        <span [ngClass]="getWorkerStatusBadge(w.status)"
                              class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border shadow-3xs">
                          {{ cleanText(w.status) }}
                        </span>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }

        <!-- DOMAIN 4: EXECUTION SITES (Universal) -->
        @if (store.activeWorkbenchTab() === 'execution_sites' && store.workbenchData().executionSites; as es) {
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            @for (site of es.sitesList; track site.siteId) {
              <div class="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between gap-3.5 hover:border-blue-200 transition-colors shadow-xs">
                <div class="flex items-center justify-between">
                  <div class="flex flex-col">
                    <h4 class="text-xs font-bold text-slate-900 font-heading">{{ cleanText(site.siteName) }}</h4>
                    <span class="text-[11px] text-slate-500 font-medium mt-0.5">{{ cleanText(site.siteTypeDescriptor) }}</span>
                  </div>
                  <span [ngClass]="site.livenessState === 'ONLINE' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'"
                        class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border shadow-3xs">
                    {{ cleanText(site.livenessState) }}
                  </span>
                </div>

                <div class="flex items-center justify-between text-xs pt-2.5 border-t border-slate-200/60">
                  <span class="text-slate-500">Worker Allocation:</span>
                  <span class="font-mono font-bold text-slate-900">{{ site.workersAllocated }} / {{ site.workerCapacity }}</span>
                </div>

                <div class="flex items-center justify-between text-xs">
                  <span class="text-slate-500">Network Latency:</span>
                  <span class="font-mono font-bold text-slate-700">{{ site.latencyMs }} ms</span>
                </div>
              </div>
            }
          </div>
        }

        <!-- DOMAIN 5: CHECKPOINT & RECOVERY (Universal) -->
        @if (store.activeWorkbenchTab() === 'checkpoint_recovery' && store.workbenchData().checkpointRecovery; as cr) {
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Last Durable Checkpoint</span>
              <div class="mt-2 font-mono text-sm font-bold text-slate-900">{{ cleanText(cr.lastCheckpointScn) }}</div>
              <div class="text-[11px] text-slate-500 mt-2">Freshness: {{ cr.freshnessSeconds }}s ago</div>
            </div>

            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Resume Coordinate</span>
              <div class="mt-2 font-mono text-sm font-bold text-slate-900">{{ cleanText(cr.resumePosition) }}</div>
              <div class="text-[11px] text-slate-500 mt-2">Attempt #{{ cr.activeAttempt }}</div>
            </div>

            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Recovery Guarantee</span>
              <div class="mt-2 font-sans text-sm font-bold text-emerald-700">{{ cleanText(cr.recoveryStrategy) }}</div>
              <div class="text-[11px] text-slate-500 mt-2">State: {{ cr.isDurable ? 'Durable on WAL' : 'In Flight' }}</div>
            </div>
          </div>
        }

        <!-- DOMAIN 6: VALIDATION & INTEGRITY -->
        @if (store.activeWorkbenchTab() === 'validation_integrity' && store.workbenchData().validationIntegrity; as vi) {
          <div class="flex flex-col gap-4">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
                <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Row Count Match</span>
                <div class="mt-2 font-mono text-xl font-bold text-emerald-600">{{ vi.rowCountMatchRate }}%</div>
              </div>
              <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
                <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Checksum Match</span>
                <div class="mt-2 font-mono text-xl font-bold text-emerald-600">{{ vi.checksumMatchRate }}%</div>
              </div>
              <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
                <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Discrepancies</span>
                <div class="mt-2 font-mono text-xl font-bold text-slate-900">{{ vi.discrepanciesCount }}</div>
              </div>
            </div>
          </div>
        }

        <!-- DOMAIN 7: SCHEMA EXECUTION (M6 Schema Only) -->
        @if (store.activeWorkbenchTab() === 'schema_execution' && store.workbenchData().schemaExecution; as se) {
          <div class="flex flex-col gap-4">
            <div class="flex items-center justify-between text-xs text-slate-600 bg-slate-50/80 border border-slate-200 rounded-lg p-3.5">
              <span>Total Objects: <strong class="font-mono text-slate-900 font-bold">{{ se.totalObjects }}</strong></span>
              <span>Applied: <strong class="font-mono text-emerald-700 font-bold">{{ se.completedObjects }}</strong></span>
              <span>Failed: <strong class="font-mono text-rose-700 font-bold">{{ se.failedObjects }}</strong></span>
            </div>

            <div class="border border-slate-200 rounded-lg overflow-hidden shadow-2xs">
              <table class="w-full text-left text-xs border-collapse">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                    <th class="py-3 px-4">#</th>
                    <th class="py-3 px-4">Object Name</th>
                    <th class="py-3 px-4">Type</th>
                    <th class="py-3 px-4 text-right">Execution Time</th>
                    <th class="py-3 px-4 text-right">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 font-sans">
                  @for (obj of se.objectStream; track obj.objectName) {
                    <tr class="hover:bg-blue-50/30 transition-colors">
                      <td class="py-3 px-4 font-mono text-slate-400">{{ obj.order }}</td>
                      <td class="py-3 px-4 font-mono font-bold text-slate-900">{{ cleanText(obj.objectName) }}</td>
                      <td class="py-3 px-4 text-slate-600 font-medium">{{ cleanText(obj.objectType) }}</td>
                      <td class="py-3 px-4 text-right font-mono text-slate-600 font-medium">{{ obj.executionTimeMs || '--' }} ms</td>
                      <td class="py-3 px-4 text-right">
                        <span [ngClass]="getSchemaObjBadge(obj.status)"
                              class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border shadow-3xs">
                          {{ cleanText(obj.status) }}
                        </span>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }

        <!-- DOMAIN 8: INCREMENTAL POLLING (M4 Incremental) -->
        @if (store.activeWorkbenchTab() === 'incremental_polling' && store.workbenchData().incrementalPolling; as ip) {
          <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Watermark Coordinate</span>
              <div class="mt-2 font-mono text-sm font-bold text-slate-900">{{ cleanText(ip.watermarkColumn) }}: {{ cleanText(ip.currentWatermarkValue) }}</div>
              <div class="text-[11px] text-slate-500 mt-2">High-water boundary</div>
            </div>
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Polling Interval</span>
              <div class="mt-2 font-mono text-sm font-bold text-slate-900">{{ ip.pollIntervalSec }}s (Last: {{ ip.lastPollDurationMs }}ms)</div>
              <div class="text-[11px] text-slate-500 mt-2">Cycle State: {{ cleanText(ip.cycleState) }}</div>
            </div>
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Records Ingested Last Batch</span>
              <div class="mt-2 font-mono text-sm font-bold text-slate-900">{{ ip.recordsLastCycle | number }}</div>
              <div class="text-[11px] text-slate-500 mt-2">Next Poll: {{ cleanText(ip.nextPollScheduled) }}</div>
            </div>
          </div>
        }

        <!-- DOMAIN 9: STATE SYNCHRONIZATION (M5 State Sync) -->
        @if (store.activeWorkbenchTab() === 'state_sync' && store.workbenchData().stateSync; as ss) {
          <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Reconciliation Cycle</span>
              <div class="mt-2 font-mono text-base font-bold text-slate-900">Cycle #{{ ss.comparisonCycle }}</div>
              <div class="text-[11px] text-slate-500 mt-2">Last run: {{ cleanText(ss.lastReconciliationTimestamp) }}</div>
            </div>
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Active Divergence Count</span>
              <div class="mt-2 font-mono text-base font-bold text-amber-700">{{ ss.divergenceCount }} diffs</div>
              <div class="text-[11px] text-slate-500 mt-2">Trend: {{ cleanText(ss.convergenceTrend) }}</div>
            </div>
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-200 transition-colors">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Corrections Applied</span>
              <div class="mt-2 font-mono text-base font-bold text-emerald-700">{{ ss.correctionsApplied }}</div>
              <div class="text-[11px] text-slate-500 mt-2">Unresolved: {{ ss.unresolvedDiffs }}</div>
            </div>
          </div>
        }

      </div>
    </section>
  `
})
export class CockpitWorkbenchComponent {
  public store = inject(CockpitStoreService);

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }

  public formatDomainTabTitle(domainId: string): string {
    switch (domainId) {
      case 'data_movement': return 'Data Movement';
      case 'cdc_convergence': return 'CDC & Convergence';
      case 'workers_pool': return 'Workers Pool';
      case 'execution_sites': return 'Execution Sites';
      case 'checkpoint_recovery': return 'Checkpoint & Recovery';
      case 'validation_integrity': return 'Validation & Integrity';
      case 'schema_execution': return 'Schema Execution';
      case 'incremental_polling': return 'Incremental Polling';
      case 'state_sync': return 'State Synchronization';
      case 'retry_throttling': return 'Retry & Throttling';
      default: return this.cleanText(domainId);
    }
  }

  public getTableStateBadgeClasses(state: TableProgressItem['state']): string {
    switch (state) {
      case 'COMPLETED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'IN_PROGRESS': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'RETRYING': return 'bg-amber-50 text-amber-700 border-amber-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getWorkerStatusBadge(status: WorkerTelemetryItem['status']): string {
    switch (status) {
      case 'ACTIVE': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'IDLE': return 'bg-slate-100 text-slate-600 border-slate-200';
      case 'UNHEALTHY': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'DRAINING': return 'bg-amber-50 text-amber-700 border-amber-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getSchemaObjBadge(status: SchemaObjectExecutionItem['status']): string {
    switch (status) {
      case 'SUCCEEDED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'APPLYING': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'SKIPPED': return 'bg-slate-100 text-slate-400 border-slate-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }
}
