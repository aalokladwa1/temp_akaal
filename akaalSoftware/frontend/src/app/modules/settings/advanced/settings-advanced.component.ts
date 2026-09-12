import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { SettingsService } from '../services/settings.service';

@Component({
  selector: 'app-settings-advanced',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="space-y-8">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div class="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider font-mono">System &amp; Intelligence</div>
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">Advanced</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Low-level engine capability tuning, developer instrumentation flags, and local storage diagnostic health.
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

      <!-- Enterprise Safety Boundary Banner -->
      <div class="bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-xl p-4 flex items-start gap-3">
        <div class="w-7 h-7 rounded-lg bg-blue-100/80 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
          <app-lucide-icon name="shield" [size]="16"></app-lucide-icon>
        </div>
        <div class="text-xs leading-relaxed text-slate-700 dark:text-slate-300">
          <span class="font-bold text-slate-900 dark:text-slate-100">Enterprise Safety Boundary (Fail-Closed):</span>
          Workstation advanced controls configure client performance tuning and diagnostics.
          Under no circumstances can local client preferences bypass platform security gates, tenant isolation, KMS encryption, or governance approval workflows.
        </div>
      </div>

      <!-- Capability Controls -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="sliders" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">Capability Controls</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Workstation memory allocations, schema inspection concurrency, and timeout ceilings.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Client Memory Cache Limit -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Client Memory Cache Limit (MB)</label>
            <input
              type="number"
              min="128"
              max="4096"
              step="128"
              [ngModel]="settings().clientMemoryCacheLimitMb"
              (ngModelChange)="updateSetting('clientMemoryCacheLimitMb', +$event)"
              class="w-full px-3 py-2 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400">Max in-memory metadata and record preview cache before eviction.</p>
          </div>

          <!-- Parallel Schema Inspection Threads -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Parallel Schema Inspection Threads</label>
            <input
              type="number"
              min="1"
              max="16"
              step="1"
              [ngModel]="settings().parallelSchemaInspectionThreads"
              (ngModelChange)="updateSetting('parallelSchemaInspectionThreads', +$event)"
              class="w-full px-3 py-2 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400">Concurrent workers for table metadata discovery during route authoring.</p>
          </div>

          <!-- IPC Response Timeout -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">IPC Response Timeout (Seconds)</label>
            <input
              type="number"
              min="5"
              max="120"
              step="5"
              [ngModel]="settings().ipcResponseTimeoutSeconds"
              (ngModelChange)="updateSetting('ipcResponseTimeoutSeconds', +$event)"
              class="w-full px-3 py-2 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400">Maximum duration before desktop UI flags IPC communication timeout.</p>
          </div>

          <!-- Local Disk I/O Throttle -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">Local Disk I/O Throttle (MB/s)</label>
            <input
              type="number"
              min="0"
              max="500"
              step="10"
              [ngModel]="settings().localDiskIoThrottleMb"
              (ngModelChange)="updateSetting('localDiskIoThrottleMb', +$event)"
              class="w-full px-3 py-2 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400">Disk throughput cap for scratch buffer writes (0 = Unlimited).</p>
          </div>
        </div>
      </section>

      <!-- Experimental Capabilities -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-4">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="sparkles" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">Experimental Capabilities</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Pre-release features and algorithmic previews.</p>
            </div>
          </div>
        </div>

        <!-- Truthful GA State Display -->
        <div class="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-800 flex items-start gap-3">
          <div class="w-7 h-7 rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 flex items-center justify-center shrink-0 mt-0.5">
            <app-lucide-icon name="shield-check" [size]="16"></app-lucide-icon>
          </div>
          <div>
            <div class="text-xs font-bold text-slate-800 dark:text-slate-200">No Experimental Flags Active in Current Release</div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
              This deployment runs strictly on certified General Availability (GA) engine baselines.
              Experimental engine switches and beta protocols are disabled on production builds to ensure deterministic pipeline state and audit reproducibility.
            </div>
          </div>
        </div>
      </section>

      <!-- Developer Options -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="code" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">Developer Options</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Workstation instrumentation, IPC tracing, and layout inspection controls.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- IPC Debug Logging Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">IPC Debug Logging</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Logs JSON-RPC calls between UI and Go engine.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('ipcDebugLogging', !settings().ipcDebugLogging)"
              [class.bg-blue-600]="settings().ipcDebugLogging"
              [class.bg-slate-300]="!settings().ipcDebugLogging"
              [class.dark:bg-slate-700]="!settings().ipcDebugLogging"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().ipcDebugLogging"
                [class.translate-x-0]="!settings().ipcDebugLogging"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- UI Bounding Box Inspection Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Bounding Inspection</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Overlays layout bounding boxes for testing.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('uiBoundingBoxInspection', !settings().uiBoundingBoxInspection)"
              [class.bg-blue-600]="settings().uiBoundingBoxInspection"
              [class.bg-slate-300]="!settings().uiBoundingBoxInspection"
              [class.dark:bg-slate-700]="!settings().uiBoundingBoxInspection"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().uiBoundingBoxInspection"
                [class.translate-x-0]="!settings().uiBoundingBoxInspection"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Extended Error Stack Traces Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Extended Stack Traces</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Includes full client error stacks in toasts.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('extendedErrorStackTraces', !settings().extendedErrorStackTraces)"
              [class.bg-blue-600]="settings().extendedErrorStackTraces"
              [class.bg-slate-300]="!settings().extendedErrorStackTraces"
              [class.dark:bg-slate-700]="!settings().extendedErrorStackTraces"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().extendedErrorStackTraces"
                [class.translate-x-0]="!settings().extendedErrorStackTraces"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>
        </div>
      </section>

      <!-- Internal Diagnostics -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="hard-drive" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">Internal Diagnostics</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Local SQLite WAL journal integrity and block validation parameters.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- SQLite WAL Diagnostic Journaling Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">SQLite WAL Journal Telemetry</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Emits write-ahead-log sync metrics to local diagnostic storage.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('sqliteWalDiagnosticJournaling', !settings().sqliteWalDiagnosticJournaling)"
              [class.bg-blue-600]="settings().sqliteWalDiagnosticJournaling"
              [class.bg-slate-300]="!settings().sqliteWalDiagnosticJournaling"
              [class.dark:bg-slate-700]="!settings().sqliteWalDiagnosticJournaling"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().sqliteWalDiagnosticJournaling"
                [class.translate-x-0]="!settings().sqliteWalDiagnosticJournaling"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Corrupt Block Self-Check on Startup Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Corrupt Block Self-Check on Startup</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Performs quick checksum validation across internal catalogs on launch.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('corruptBlockSelfCheckOnStartup', !settings().corruptBlockSelfCheckOnStartup)"
              [class.bg-blue-600]="settings().corruptBlockSelfCheckOnStartup"
              [class.bg-slate-300]="!settings().corruptBlockSelfCheckOnStartup"
              [class.dark:bg-slate-700]="!settings().corruptBlockSelfCheckOnStartup"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().corruptBlockSelfCheckOnStartup"
                [class.translate-x-0]="!settings().corruptBlockSelfCheckOnStartup"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>
        </div>

        <!-- Fail-Closed Governance Law (Locked) -->
        <div class="flex items-center justify-between gap-4 p-3.5 bg-emerald-50/40 dark:bg-emerald-950/20 rounded-lg border border-emerald-200/50 dark:border-emerald-900/40">
          <div class="pr-2">
            <div class="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
              <app-lucide-icon name="shield-check" [size]="14" class="text-emerald-600 dark:text-emerald-400"></app-lucide-icon>
              <span>Fail-Closed Governance (Locked Invariant)</span>
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Workstation aborts pipeline execution immediately upon corrupt block detection or security tamper.</div>
          </div>
          <div class="text-xs font-mono font-semibold px-2.5 py-1 bg-emerald-100/80 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300 rounded-md shrink-0">
            ENFORCED
          </div>
        </div>
      </section>
    </div>
  `
})
export class SettingsAdvancedComponent {
  private settingsService = inject(SettingsService);

  public settings = this.settingsService.advancedSettings;

  public updateSetting(key: string, value: any): void {
    this.settingsService.updateAdvanced({ [key]: value });
  }

  public resetDefaults(): void {
    this.settingsService.resetAdvanced();
  }
}
