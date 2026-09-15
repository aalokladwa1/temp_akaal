/**
 * AKAAL Monitoring — Part 4 of 4: Notification & Escalation Tab Component
 * Delivery attempts, channels, retry states, external proof status, and escalation policies.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AlertsMonitoringService } from '../../services/alerts-monitoring.service';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-alerts-notifications-tab',
  standalone: true,
  imports: [CommonModule, CustomSelectComponent, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. KPI Stat Strip -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        
        <!-- Total Deliveries -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Total Dispatches</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight">
              {{ ams.notifications().length }}
            </span>
            <span class="text-xs text-slate-400">notifications</span>
          </div>
          <span class="text-[11px] text-slate-500 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Multi-channel fanout
          </span>
        </div>

        <!-- Success Rate -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Delivery Success</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-emerald-600 font-mono tracking-tight">
              {{ ams.summary().notification_success_rate_pct }}%
            </span>
            <span class="text-xs text-slate-400">confirmed</span>
          </div>
          <span class="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Cryptographic delivery proof
          </span>
        </div>

        <!-- Failed Dispatches -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Failed / Retrying</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-rose-600 font-mono tracking-tight">
              {{ failedCount }}
            </span>
            <span class="text-xs text-slate-400">errors</span>
          </div>
          <span class="text-[11px] text-rose-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            Auto-retry policy active
          </span>
        </div>

        <!-- Active Channels -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Active Channels</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight">
              4
            </span>
            <span class="text-xs text-slate-400">configured</span>
          </div>
          <span class="text-[11px] text-blue-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Slack, PagerDuty, Webhook, Email
          </span>
        </div>

      </div>

      <!-- 2. Search & Filter Bar -->
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        
        <!-- Search input -->
        <div class="relative flex-1">
          <app-lucide-icon name="search" [size]="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
          <input
            type="text"
            [value]="ams.notificationSearchQuery()"
            (input)="onSearchInput($event)"
            placeholder="Search notifications by channel, endpoint, ID, or incident..."
            class="w-full pl-9 pr-4 py-2 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 transition-all"
          />
        </div>

        <!-- Status Filter Dropdown -->
        <div class="w-full sm:w-56">
          <app-custom-select
            [options]="statusOptions"
            [value]="ams.notificationStatusFilter()"
            (valueChange)="ams.notificationStatusFilter.set($event)"
            placeholder="Filter Delivery Status">
          </app-custom-select>
        </div>

      </div>

      <!-- 3. Notification Deliveries Table -->
      <div class="rounded-2xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3.5 px-4">Channel & Target</th>
                <th class="py-3.5 px-4">Linked Trigger</th>
                <th class="py-3.5 px-4">Status & Code</th>
                <th class="py-3.5 px-4">Latency & Retries</th>
                <th class="py-3.5 px-4">Escalation Policy</th>
                <th class="py-3.5 px-4">Delivery Proof</th>
                <th class="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (notif of ams.filteredNotifications(); track notif.id) {
                <tr class="hover:bg-slate-50/60 transition-colors">
                  
                  <!-- Channel & Target -->
                  <td class="py-3.5 px-4">
                    <div class="flex flex-col gap-0.5">
                      <div class="flex items-center gap-1.5">
                        <span class="font-bold text-slate-900">{{ notif.channel_name }}</span>
                        <span class="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-slate-100 text-slate-700">
                          {{ notif.channel_type }}
                        </span>
                      </div>
                      <span class="font-mono text-[11px] text-slate-500 truncate max-w-xs">{{ notif.target_endpoint }}</span>
                    </div>
                  </td>

                  <!-- Linked Trigger -->
                  <td class="py-3.5 px-4">
                    @if (notif.linked_incident_id) {
                      <span class="font-mono text-xs font-bold text-purple-700">{{ notif.linked_incident_id }}</span>
                    } @else if (notif.linked_alert_id) {
                      <span class="font-mono text-xs font-medium text-amber-700">{{ notif.linked_alert_id }}</span>
                    } @else {
                      <span class="text-slate-400 font-mono text-xs">System Heartbeat</span>
                    }
                  </td>

                  <!-- Status & HTTP Code -->
                  <td class="py-3.5 px-4">
                    <div class="flex items-center gap-2">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-emerald-100 text-emerald-800': notif.status === 'DELIVERED',
                          'bg-rose-100 text-rose-800': notif.status === 'FAILED',
                          'bg-amber-100 text-amber-800': notif.status === 'RETRYING'
                        }">
                        {{ notif.status }}
                      </span>
                      <span class="font-mono text-[11px] text-slate-600 font-semibold">HTTP {{ notif.response_code }}</span>
                    </div>
                  </td>

                  <!-- Latency & Retries -->
                  <td class="py-3.5 px-4">
                    <div class="flex flex-col gap-0.5">
                      <span class="font-mono text-xs text-slate-700 font-medium">{{ notif.latency_ms }} ms</span>
                      <span class="text-[10px] text-slate-400 font-mono">
                        {{ notif.retry_count }} / {{ notif.max_retries }} retries
                      </span>
                    </div>
                  </td>

                  <!-- Escalation Policy -->
                  <td class="py-3.5 px-4">
                    <div class="flex flex-col gap-0.5">
                      <span class="font-medium text-slate-800 text-[11px]">{{ notif.escalation_policy_ref }}</span>
                      <span class="text-[10px] text-slate-500">Tier {{ notif.escalation_step }}</span>
                    </div>
                  </td>

                  <!-- Delivery Proof -->
                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-semibold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': notif.external_proof_status === 'VERIFIED_DELIVERY',
                        'bg-blue-50 text-blue-700 border border-blue-200': notif.external_proof_status === 'MOCK_SANDBOX',
                        'bg-slate-50 text-slate-600 border border-slate-200': notif.external_proof_status === 'UNVERIFIED'
                      }">
                      {{ ams.formatText(notif.external_proof_status) }}
                    </span>
                  </td>

                  <!-- Actions -->
                  <td class="py-3.5 px-4 text-right">
                    @if (notif.status === 'FAILED' || notif.status === 'RETRYING') {
                      <button
                        type="button"
                        (click)="ams.retryNotification(notif.id)"
                        class="h-7 px-2.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center gap-1 cursor-pointer transition-colors shadow-2xs">
                        <app-lucide-icon name="rotate-cw" [size]="11"></app-lucide-icon>
                        <span>Retry</span>
                      </button>
                    } @else {
                      <span class="text-emerald-600 font-medium text-xs inline-flex items-center gap-1">
                        <app-lucide-icon name="check" [size]="13"></app-lucide-icon>
                        <span>Verified</span>
                      </span>
                    }
                  </td>

                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- 4. Escalation Policy Architecture Reference Card -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="shield-alert" [size]="16" class="text-blue-600"></app-lucide-icon>
            <h3 class="text-sm font-bold text-slate-900">Escalation Policy Flow Matrix</h3>
          </div>
          <span class="text-xs text-slate-400 font-mono">Policy: prod-critical-escalation</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Tier 1: Immediate Fanout</span>
              <span class="font-mono text-emerald-600 font-bold">0 min</span>
            </div>
            <p class="text-slate-600 text-[11px] leading-relaxed">
              Dispatches synchronous Webhook to Slack (<span class="font-mono">#war-room-critical</span>) and updates in-memory operational state.
            </p>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Tier 2: Primary On-Call</span>
              <span class="font-mono text-amber-600 font-bold">+5 min</span>
            </div>
            <p class="text-slate-600 text-[11px] leading-relaxed">
              Dispatches high-urgency PagerDuty incident trigger with dynamic runbook payload to primary on-call SRE.
            </p>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Tier 3: Executive Escalation</span>
              <span class="font-mono text-rose-600 font-bold">+15 min</span>
            </div>
            <p class="text-slate-600 text-[11px] leading-relaxed">
              Dispatches secondary notification batch to Lead Platform Architect and Engineering Management if unacknowledged.
            </p>
          </div>
        </div>
      </div>

    </div>
  `
})
export class AlertsNotificationsTabComponent {
  public ams = inject(AlertsMonitoringService);

  public statusOptions: SelectOption[] = [
    { label: 'All Delivery Statuses', value: 'ALL' },
    { label: 'Delivered', value: 'DELIVERED' },
    { label: 'Failed', value: 'FAILED' },
    { label: 'Retrying', value: 'RETRYING' }
  ];

  public get failedCount(): number {
    return this.ams.notifications().filter(n => n.status === 'FAILED' || n.status === 'RETRYING').length;
  }

  public onSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.ams.notificationSearchQuery.set(target.value);
  }
}
