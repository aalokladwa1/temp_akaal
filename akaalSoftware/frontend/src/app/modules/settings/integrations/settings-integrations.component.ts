import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../shared/components/custom-select.component';
import { SettingsService } from '../services/settings.service';
import { IntegrationsService } from '../../admin/services/integrations.service';
import { TelemetryExportTarget, CatalogFormatType } from '../models/settings.models';

interface InstalledIntegrationItem {
  id: string;
  name: string;
  category: 'SIEM' | 'ITSM' | 'CHANNEL';
  provider: string;
  endpoint: string;
  status: string;
}

@Component({
  selector: 'app-settings-integrations',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="space-y-8">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div class="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider font-mono">Operational Defaults</div>
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">Integrations</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure observability export targets, default notification routing channels, catalog lineage publishing, and enterprise connection suppression.
          </p>
        </div>
        <div class="flex items-center gap-3">
          <button
            type="button"
            (click)="resetDefaults()"
            class="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-2">
            <app-lucide-icon name="rotate-ccw" [size]="14"></app-lucide-icon>
            Reset Defaults
          </button>
        </div>
      </div>

      <!-- Scope Notice Banner -->
      <div class="bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-xl p-4 flex items-start gap-3">
        <div class="w-7 h-7 rounded-lg bg-blue-100/80 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
          <app-lucide-icon name="info" [size]="16"></app-lucide-icon>
        </div>
        <div class="text-xs leading-relaxed text-slate-700 dark:text-slate-300">
          <span class="font-bold text-slate-900 dark:text-slate-100">Workspace Integration Preferences:</span>
          Configure workstation defaults for telemetry streaming and external metadata publishing. Integrations, credentials, and API tokens are managed authoritatively in Domain 5.11 Administration.
        </div>
      </div>

      <!-- 1. Observability Integrations -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="activity" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">1. Observability Integrations</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Stream runtime execution metrics, OpenTelemetry spans, and structured logs to external collectors.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('observabilityExportEnabled', !settings().observabilityExportEnabled)"
            [class.bg-blue-600]="settings().observabilityExportEnabled"
            [class.bg-slate-300]="!settings().observabilityExportEnabled"
            [class.dark:bg-slate-700]="!settings().observabilityExportEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().observabilityExportEnabled"
              [class.translate-x-0]="!settings().observabilityExportEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" [class.opacity-60]="!settings().observabilityExportEnabled">
          <div class="md:col-span-2">
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Primary Telemetry Destination
            </label>
            <app-custom-select
              [options]="telemetryDestinationOptions"
              [disabled]="!settings().observabilityExportEnabled"
              [ngModel]="settings().telemetryDestination"
              (ngModelChange)="updateSetting('telemetryDestination', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Active SIEM collector configured in Administration.</p>
          </div>

          <!-- W3C Trace Context Toggle -->
          <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Propagate W3C Trace Context</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">Inject standard traceparent and tracestate headers into outbound connector sessions.</div>
            </div>
            <button
              type="button"
              [disabled]="!settings().observabilityExportEnabled"
              (click)="updateSetting('propagateTraceContext', !settings().propagateTraceContext)"
              [class.bg-blue-600]="settings().propagateTraceContext"
              [class.bg-slate-300]="!settings().propagateTraceContext"
              [class.dark:bg-slate-700]="!settings().propagateTraceContext"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5 disabled:opacity-50 disabled:cursor-not-allowed">
              <span
                [class.translate-x-5]="settings().propagateTraceContext"
                [class.translate-x-0]="!settings().propagateTraceContext"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Auto-Export Crash Diagnostics Toggle -->
          <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Auto-Export Crash Diagnostics</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">Transmit sanitized stack traces and worker panic dumps to SIEM on fatal error.</div>
            </div>
            <button
              type="button"
              [disabled]="!settings().observabilityExportEnabled"
              (click)="updateSetting('autoExportCrashDiagnostics', !settings().autoExportCrashDiagnostics)"
              [class.bg-blue-600]="settings().autoExportCrashDiagnostics"
              [class.bg-slate-300]="!settings().autoExportCrashDiagnostics"
              [class.dark:bg-slate-700]="!settings().autoExportCrashDiagnostics"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5 disabled:opacity-50 disabled:cursor-not-allowed">
              <span
                [class.translate-x-5]="settings().autoExportCrashDiagnostics"
                [class.translate-x-0]="!settings().autoExportCrashDiagnostics"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>
        </div>
      </section>

      <!-- 2. Notification Integrations -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="bell" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">2. Notification Routing Defaults</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Default dispatch channel and multi-channel fan-out rules for platform events.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Default Broadcast Channel
            </label>
            <app-custom-select
              [options]="channelOptions()"
              [ngModel]="settings().defaultNotificationChannelId"
              (ngModelChange)="updateSetting('defaultNotificationChannelId', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Primary notification endpoint initialized for new pipelines.</p>
          </div>

          <!-- Multi-Channel Fan-Out Toggle -->
          <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Fan-Out Critical Failures</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">Simultaneously dispatch fatal alerts across all active enterprise policy channels.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('fanOutCriticalFailures', !settings().fanOutCriticalFailures)"
              [class.bg-blue-600]="settings().fanOutCriticalFailures"
              [class.bg-slate-300]="!settings().fanOutCriticalFailures"
              [class.dark:bg-slate-700]="!settings().fanOutCriticalFailures"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().fanOutCriticalFailures"
                [class.translate-x-0]="!settings().fanOutCriticalFailures"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>
        </div>
      </section>

      <!-- 3. Catalog / Lineage Integrations -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="git-branch" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">3. Catalog &amp; Lineage Integrations</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Publish table schemas, column transformations, and run lineage to enterprise governance catalogs.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('lineagePublishingEnabled', !settings().lineagePublishingEnabled)"
            [class.bg-blue-600]="settings().lineagePublishingEnabled"
            [class.bg-slate-300]="!settings().lineagePublishingEnabled"
            [class.dark:bg-slate-700]="!settings().lineagePublishingEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().lineagePublishingEnabled"
              [class.translate-x-0]="!settings().lineagePublishingEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="space-y-4" [class.opacity-60]="!settings().lineagePublishingEnabled">
          <!-- Truthful Unconfigured State Banner (Zero-Fake Guarantee) -->
          <div class="bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 rounded-xl p-4 flex items-start gap-3">
            <app-lucide-icon name="alert-circle" [size]="16" class="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
              <div class="font-bold text-slate-900 dark:text-slate-100 mb-0.5">Unconfigured in Workspace / Missing Backend Semantics</div>
              There is currently no external catalog endpoint (OpenLineage, Collibra, or Apache Atlas) registered in this workspace environment. If lineage publishing is enabled, lineage graphs will be buffered locally in audit logs until a catalog integration is registered in Administration (Integrations &amp; Notifications).
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Lineage Metadata Specification
              </label>
              <app-custom-select
                [options]="catalogFormatOptions"
                [disabled]="!settings().lineagePublishingEnabled"
                [ngModel]="settings().catalogFormat"
                (ngModelChange)="updateSetting('catalogFormat', $event)">
              </app-custom-select>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Standard schema format for emitting run facets and input/output datasets.</p>
            </div>

            <!-- Auto-Export Lineage on Execution Toggle -->
            <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
              <div>
                <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Auto-Export on Execution</div>
                <div class="text-xs text-slate-500 dark:text-slate-400">Transmit lineage event graphs automatically on migration completion.</div>
              </div>
              <button
                type="button"
                [disabled]="!settings().lineagePublishingEnabled"
                (click)="updateSetting('autoExportLineageOnExecution', !settings().autoExportLineageOnExecution)"
                [class.bg-blue-600]="settings().autoExportLineageOnExecution"
                [class.bg-slate-300]="!settings().autoExportLineageOnExecution"
                [class.dark:bg-slate-700]="!settings().autoExportLineageOnExecution"
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5 disabled:opacity-50 disabled:cursor-not-allowed">
                <span
                  [class.translate-x-5]="settings().autoExportLineageOnExecution"
                  [class.translate-x-0]="!settings().autoExportLineageOnExecution"
                  class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 4. Installed Enterprise Integrations -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="plug" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">4. Installed Enterprise Integrations</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Configured enterprise adapters from Administration. Toggle local workstation suppression during test executions.</p>
            </div>
          </div>
          <span class="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 px-2.5 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
            {{ installedIntegrations().length }} Active Adapters
          </span>
        </div>

        <div class="space-y-3">
          @for (item of installedIntegrations(); track item.id) {
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-slate-200/70 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
              <div class="flex items-start sm:items-center gap-3.5">
                <div class="w-9 h-9 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center shrink-0 text-slate-700 dark:text-slate-300 shadow-sm">
                  @if (item.category === 'SIEM') {
                    <app-lucide-icon name="shield-alert" [size]="18"></app-lucide-icon>
                  } @else if (item.category === 'ITSM') {
                    <app-lucide-icon name="check-square" [size]="18"></app-lucide-icon>
                  } @else {
                    <app-lucide-icon name="radio" [size]="18"></app-lucide-icon>
                  }
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-bold text-slate-900 dark:text-slate-100">{{ item.name }}</span>
                    <span class="text-[10px] font-mono px-2 py-0.5 rounded-md font-semibold bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                      {{ item.provider }}
                    </span>
                  </div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-2">
                    <span class="font-mono">{{ item.id }}</span>
                    <span>&bull;</span>
                    <span class="truncate max-w-xs">{{ item.endpoint }}</span>
                  </div>
                </div>
              </div>

              <div class="flex items-center justify-between sm:justify-end gap-4 shrink-0">
                <div class="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                  <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                  Configured
                </div>

                <div class="flex items-center gap-2 pl-4 border-l border-slate-200 dark:border-slate-700">
                  <span class="text-xs text-slate-500 dark:text-slate-400">
                    {{ isSuppressed(item.id) ? 'Suppressed' : 'Active' }}
                  </span>
                  <button
                    type="button"
                    (click)="toggleSuppression(item.id)"
                    [class.bg-amber-500]="isSuppressed(item.id)"
                    [class.bg-slate-300]="!isSuppressed(item.id)"
                    [class.dark:bg-slate-700]="!isSuppressed(item.id)"
                    title="Toggle local workstation suppression"
                    class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
                    <span
                      [class.translate-x-4]="isSuppressed(item.id)"
                      [class.translate-x-0]="!isSuppressed(item.id)"
                      class="inline-block h-4 w-4 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
                  </button>
                </div>
              </div>
            </div>
          }
        </div>
      </section>
    </div>
  `
})
export class SettingsIntegrationsComponent {
  private settingsService = inject(SettingsService);
  private integrationsService = inject(IntegrationsService);

  public settings = this.settingsService.integrationSettings;

  public telemetryDestinationOptions: SelectOption[] = [
    {
      label: 'Corporate Splunk Enterprise Cloud HEC (siem-01)',
      value: 'SPLUNK_HEC',
      desc: 'https://http-inputs-akaal.splunkcloud.com:8088'
    },
    {
      label: 'On-Prem Datadog Agent Syslog Forwarder (siem-02)',
      value: 'DATADOG_AGENT',
      desc: 'datadog-intake.internal:10516'
    },
    {
      label: 'Local Diagnostic Console (Offline / Testing)',
      value: 'LOCAL_CONSOLE',
      desc: 'Directs telemetry to local logs without network dispatch'
    }
  ];

  public catalogFormatOptions: SelectOption[] = [
    { label: 'OpenLineage 1.0 (Standard Spec)', value: 'OPEN_LINEAGE' },
    { label: 'Apache Atlas Entity Model', value: 'APACHE_ATLAS' },
    { label: 'Custom Enterprise Catalog Schema', value: 'CUSTOM_CATALOG' }
  ];

  public channelOptions = computed<SelectOption[]>(() => {
    return this.integrationsService.channels().map(c => ({
      label: `${c.name} (${c.id})`,
      value: c.id,
      desc: c.description
    }));
  });

  public installedIntegrations = computed<InstalledIntegrationItem[]>(() => {
    const list: InstalledIntegrationItem[] = [];

    // SIEMs
    for (const s of this.integrationsService.siemIntegrations()) {
      list.push({
        id: s.id,
        name: s.name,
        category: 'SIEM',
        provider: s.siemType,
        endpoint: s.endpointUrl,
        status: s.status
      });
    }

    // ITSM
    for (const it of this.integrationsService.itsmIntegrations()) {
      list.push({
        id: it.id,
        name: it.name,
        category: 'ITSM',
        provider: it.provider,
        endpoint: it.instanceUrl,
        status: it.status
      });
    }

    // Channels
    for (const ch of this.integrationsService.channels()) {
      list.push({
        id: ch.id,
        name: ch.name,
        category: 'CHANNEL',
        provider: ch.channelType,
        endpoint: ch.targetEndpointOrAddress,
        status: ch.isEnabled ? 'CONFIGURED' : 'DISABLED'
      });
    }

    return list;
  });

  public isSuppressed(id: string): boolean {
    return !!this.settings().suppressedIntegrations?.[id];
  }

  public toggleSuppression(id: string): void {
    const current = { ...this.settings().suppressedIntegrations };
    current[id] = !current[id];
    this.settingsService.updateIntegration({ suppressedIntegrations: current });
  }

  public updateSetting(key: string, value: any): void {
    this.settingsService.updateIntegration({ [key]: value });
  }

  public resetDefaults(): void {
    this.settingsService.resetIntegrations();
  }
}
