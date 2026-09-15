import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../shared/components/custom-select.component';
import { SettingsService } from '../services/settings.service';
import { ClientLogLevel, EngineLogLevel, LogDestination } from '../models/settings.models';

@Component({
  selector: 'app-settings-logging',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="space-y-8">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div class="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider font-mono">System &amp; Intelligence</div>
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">Logging &amp; Diagnostics</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure log verbosity levels, crash diagnostic telemetry, W3C distributed tracing spans, and diagnostic support bundle parameters.
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
          <span class="font-bold text-slate-900 dark:text-slate-100">Workstation Diagnostic Preferences:</span>
          These settings configure local client log verbosity, engine diagnostics, and defaults for diagnostic package assembly.
          Support bundle generation, cryptographic signing, and export operations are governed under <span class="font-medium text-slate-900 dark:text-slate-100">Administration &gt; Diagnostics &amp; Maintenance</span>.
        </div>
      </div>

      <!-- Log Levels -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="file-text" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">Log Levels</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Adjust client application and runtime migration engine output verbosity.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Client Log Verbosity -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Client Log Verbosity</label>
            <app-custom-select
              [options]="clientLogLevelOptions"
              [value]="settings().clientLogLevel"
              (valueChange)="updateSetting('clientLogLevel', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400">Local UI and desktop shell event logging threshold.</p>
          </div>

          <!-- Runtime Engine Diagnostic Verbosity -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Runtime Engine Verbosity</label>
            <app-custom-select
              [options]="engineLogLevelOptions"
              [value]="settings().engineLogLevel"
              (valueChange)="updateSetting('engineLogLevel', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400">Core Go Wails data engine diagnostic verbosity level.</p>
          </div>

          <!-- Log Target Destination -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Log Target Destination</label>
            <app-custom-select
              [options]="logDestinationOptions"
              [value]="settings().logDestination"
              (valueChange)="updateSetting('logDestination', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400">Target output stream for workstation event records.</p>
          </div>

          <!-- Max Active Log Size -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Max Active Log Size (MB)</label>
            <input
              type="number"
              min="10"
              max="500"
              step="10"
              [ngModel]="settings().maxActiveLogSizeMb"
              (ngModelChange)="updateSetting('maxActiveLogSizeMb', +$event)"
              class="w-full px-3 py-2 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400">Active log file segment capacity before automatic local rotation.</p>
          </div>
        </div>
      </section>

      <!-- Diagnostics -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="activity" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">Diagnostics</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Unhandled panic instrumentation and local anomaly state snapshots.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Crash Diagnostic Capture Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Crash Diagnostic Capture</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Records unhandled panic traces locally to diagnostic storage for triage.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('crashDiagnosticCapture', !settings().crashDiagnosticCapture)"
              [class.bg-blue-600]="settings().crashDiagnosticCapture"
              [class.bg-slate-300]="!settings().crashDiagnosticCapture"
              [class.dark:bg-slate-700]="!settings().crashDiagnosticCapture"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().crashDiagnosticCapture"
                [class.translate-x-0]="!settings().crashDiagnosticCapture"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Engine State Snapshot Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Engine State Snapshot on Anomaly</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Captures runtime goroutine stacks and buffer states on fatal worker aborts.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('engineStateSnapshotOnAnomaly', !settings().engineStateSnapshotOnAnomaly)"
              [class.bg-blue-600]="settings().engineStateSnapshotOnAnomaly"
              [class.bg-slate-300]="!settings().engineStateSnapshotOnAnomaly"
              [class.dark:bg-slate-700]="!settings().engineStateSnapshotOnAnomaly"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().engineStateSnapshotOnAnomaly"
                [class.translate-x-0]="!settings().engineStateSnapshotOnAnomaly"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>
        </div>

        <!-- Anomaly Storage Location (Read-Only) -->
        <div class="space-y-1.5">
          <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Local Diagnostic Dump Location</label>
          <div class="flex items-center gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-mono text-slate-600 dark:text-slate-400">
            <app-lucide-icon name="hard-drive" [size]="14" class="text-slate-400 shrink-0"></app-lucide-icon>
            <span class="truncate">{{ settings().anomalyDumpDirectory }}</span>
            <span class="ml-auto text-[11px] font-sans font-medium text-slate-400 dark:text-slate-500 shrink-0">System Path</span>
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400">Workstation path where crash dumps, goroutine profiles, and ringbuffer dumps are retained.</p>
        </div>
      </section>

      <!-- Tracing -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="git-branch" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">Tracing</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Distributed tracing context and in-memory span buffering.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- W3C Trace Context Propagation Toggle -->
          <div class="md:col-span-3 flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">W3C Trace Context Propagation</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Injects and propagates standard traceparent headers across worker IPC and database connector calls.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('traceContextPropagation', !settings().traceContextPropagation)"
              [class.bg-blue-600]="settings().traceContextPropagation"
              [class.bg-slate-300]="!settings().traceContextPropagation"
              [class.dark:bg-slate-700]="!settings().traceContextPropagation"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().traceContextPropagation"
                [class.translate-x-0]="!settings().traceContextPropagation"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Local Span Buffer Limit -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Local Span Buffer Limit</label>
            <input
              type="number"
              min="1000"
              max="50000"
              step="1000"
              [ngModel]="settings().localSpanBufferLimit"
              (ngModelChange)="updateSetting('localSpanBufferLimit', +$event)"
              class="w-full px-3 py-2 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400">Maximum spans retained in volatile client ringbuffer before eviction.</p>
          </div>

          <!-- Tracing Sampling Rate -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Sampling Rate (%)</label>
            <input
              type="number"
              min="1"
              max="100"
              step="1"
              [ngModel]="settings().tracingSamplingRatePercent"
              (ngModelChange)="updateSetting('tracingSamplingRatePercent', +$event)"
              class="w-full px-3 py-2 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400">Percentage of migration operations producing distributed trace traces.</p>
          </div>
        </div>
      </section>

      <!-- Support Bundles -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="archive" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">Support Bundles</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Workstation defaults for diagnostic package assembly.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Include Sanitized Config -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Include Sanitized Configuration</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Packages non-sensitive runtime parameters, thread limits, and layout metadata.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('bundleIncludeSanitizedConfig', !settings().bundleIncludeSanitizedConfig)"
              [class.bg-blue-600]="settings().bundleIncludeSanitizedConfig"
              [class.bg-slate-300]="!settings().bundleIncludeSanitizedConfig"
              [class.dark:bg-slate-700]="!settings().bundleIncludeSanitizedConfig"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().bundleIncludeSanitizedConfig"
                [class.translate-x-0]="!settings().bundleIncludeSanitizedConfig"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Include Engine Status Snapshot -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Include Engine Status Snapshot</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Captures active worker counts, queue depth watermarks, and memory allocations.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('bundleIncludeEngineStatus', !settings().bundleIncludeEngineStatus)"
              [class.bg-blue-600]="settings().bundleIncludeEngineStatus"
              [class.bg-slate-300]="!settings().bundleIncludeEngineStatus"
              [class.dark:bg-slate-700]="!settings().bundleIncludeEngineStatus"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().bundleIncludeEngineStatus"
                [class.translate-x-0]="!settings().bundleIncludeEngineStatus"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Include Scrubbed Local Logs -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Include Scrubbed Local Logs</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Attaches recent event logs filtered through cryptographic secret masking patterns.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('bundleIncludeScrubbedLogs', !settings().bundleIncludeScrubbedLogs)"
              [class.bg-blue-600]="settings().bundleIncludeScrubbedLogs"
              [class.bg-slate-300]="!settings().bundleIncludeScrubbedLogs"
              [class.dark:bg-slate-700]="!settings().bundleIncludeScrubbedLogs"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().bundleIncludeScrubbedLogs"
                [class.translate-x-0]="!settings().bundleIncludeScrubbedLogs"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Mandatory Secret & PII Scrubbing (Locked) -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-emerald-50/40 dark:bg-emerald-950/20 rounded-lg border border-emerald-200/50 dark:border-emerald-900/40">
            <div class="pr-2">
              <div class="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                <app-lucide-icon name="shield-check" [size]="14" class="text-emerald-600 dark:text-emerald-400"></app-lucide-icon>
                <span>Scrub Secrets &amp; PII (Locked)</span>
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">All passwords, bearer tokens, connection URIs, and user keys are irrevocably masked.</div>
            </div>
            <div class="text-xs font-mono font-semibold px-2.5 py-1 bg-emerald-100/80 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300 rounded-md shrink-0">
              ENFORCED
            </div>
          </div>
        </div>

        <!-- Architectural Authority Notice -->
        <div class="p-3.5 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400 flex items-start gap-2.5">
          <app-lucide-icon name="info" [size]="15" class="text-slate-500 shrink-0 mt-0.5"></app-lucide-icon>
          <div>
            <span class="font-semibold text-slate-800 dark:text-slate-200">Administrative Boundary:</span>
            Actual compilation, digital signature generation, and bundle download routines operate exclusively under
            <span class="font-medium text-blue-600 dark:text-blue-400">Administration &gt; Diagnostics &amp; Maintenance</span>.
            Settings governs client preference templates only.
          </div>
        </div>
      </section>
    </div>
  `
})
export class SettingsLoggingComponent {
  private settingsService = inject(SettingsService);

  public settings = this.settingsService.loggingSettings;

  public clientLogLevelOptions: SelectOption[] = [
    { value: 'DEBUG', label: 'DEBUG (Detailed traces & events)' },
    { value: 'INFO', label: 'INFO (Standard operational events)' },
    { value: 'WARN', label: 'WARN (Warnings & degradation only)' },
    { value: 'ERROR', label: 'ERROR (Critical errors only)' }
  ];

  public engineLogLevelOptions: SelectOption[] = [
    { value: 'INFO', label: 'INFO (Standard engine metrics)' },
    { value: 'DEBUG', label: 'DEBUG (Goroutine & buffer telemetry)' }
  ];

  public logDestinationOptions: SelectOption[] = [
    { value: 'CONSOLE_AND_DISK', label: 'Console + Local Disk (Recommended)' },
    { value: 'DISK_ONLY', label: 'Local Disk Only' },
    { value: 'CONSOLE_ONLY', label: 'Console Only' }
  ];

  public updateSetting(key: string, value: any): void {
    this.settingsService.updateLogging({ [key]: value });
  }

  public resetDefaults(): void {
    this.settingsService.resetLogging();
  }
}
