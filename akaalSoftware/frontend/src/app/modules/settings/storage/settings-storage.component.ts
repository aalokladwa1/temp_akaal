import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { SettingsService } from '../services/settings.service';

@Component({
  selector: 'app-settings-storage',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="space-y-8">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div class="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider font-mono">Operational Defaults</div>
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">Storage &amp; Retention</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure checkpoint persistence cadences, CDC buffer spill storage, diagnostic log rotation budgets, and retention policy baselines.
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
          <span class="font-bold text-slate-900 dark:text-slate-100">Storage &amp; Durability Invariant:</span>
          Settings configures local presentation preferences and subordinate operational defaults. Settings does not own destructive purge execution, legal hold overrides, or audit log erasure. All compliance retention is governed authoritatively by Domain 5.9 Audit.
        </div>
      </div>

      <!-- Section 1: Checkpoints -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="check-circle" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">1. Checkpoints</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">State snapshot cadences and durability journal configuration.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Checkpoint Row Interval
            </label>
            <input
              type="number"
              min="100"
              max="10000"
              step="100"
              [ngModel]="settings().checkpointIntervalRows"
              (ngModelChange)="updateSetting('checkpointIntervalRows', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Rows processed between durability checkpoint commits (default 1,000).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Checkpoint Time Interval (seconds)
            </label>
            <input
              type="number"
              min="5"
              max="300"
              step="5"
              [ngModel]="settings().checkpointIntervalSeconds"
              (ngModelChange)="updateSetting('checkpointIntervalSeconds', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Maximum elapsed time between checkpoints during low-throughput windows (default 30s).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Retained Checkpoints per Job
            </label>
            <input
              type="number"
              min="3"
              max="50"
              [ngModel]="settings().retainedCheckpointsCount"
              (ngModelChange)="updateSetting('retainedCheckpointsCount', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Number of historical recovery points preserved before rotating (default 10).</p>
          </div>
        </div>

        <!-- Governed Durability Policy -->
        <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <app-lucide-icon name="shield" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
              Mandatory Checkpoint Durability: Enforced Active
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Storage Engine: SQLite WAL Journal with Monotonic Epochs. Disabling checkpoints is prohibited to guarantee zero data loss.
            </div>
          </div>
          <div class="text-xs font-bold text-slate-600 dark:text-slate-300 px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shrink-0">
            Enforced Read-Only
          </div>
        </div>
      </section>

      <!-- Section 2: CDC Buffers -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="hard-drive" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">2. CDC Buffers &amp; Spill Storage</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">In-memory buffer quotas, scratch disk spill locations, and source log retention monitoring.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Buffer Memory Allocation per Stream (MiB)
            </label>
            <input
              type="number"
              min="32"
              max="512"
              step="32"
              [ngModel]="settings().cdcStreamBufferMb"
              (ngModelChange)="updateSetting('cdcStreamBufferMb', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Fast in-memory ring buffer before writing spill frames (default 64 MiB).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Source Log Retention Warning Threshold (%)
            </label>
            <input
              type="number"
              min="5"
              max="30"
              [ngModel]="settings().sourceRetentionWarningPercent"
              (ngModelChange)="updateSetting('sourceRetentionWarningPercent', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Emits warning when source WAL/binlog capacity drops below this margin (default 15%).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Spill Storage Location
            </label>
            <input
              type="text"
              readonly
              value="Local Encrypted Durability Scratch"
              class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Dedicated disk partition managed with AES-256 local scratch encryption.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Governed Spill Storage Budget
            </label>
            <input
              type="text"
              readonly
              value="100 GiB (Managed by Platform Quota)"
              class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Enforced by StorageQuotaMonitor in Authority #5 Durability.</p>
          </div>
        </div>
      </section>

      <!-- Section 3: Reports / Evidence -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="file-text" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">3. Reports / Evidence</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Default operational report retention preferences and cryptographic attestation digests.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Default Operational Report Retention (days)
            </label>
            <input
              type="number"
              min="30"
              max="365"
              step="30"
              [ngModel]="settings().defaultReportRetentionDays"
              (ngModelChange)="updateSetting('defaultReportRetentionDays', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Workstation default display window for operational and validation summaries.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Export Packages Enabled
            </label>
            <input
              type="text"
              readonly
              value="JSON, CSV, Audit Bundle (ZIP with SHA-256)"
              class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Export package formats available for audit investigations.</p>
          </div>
        </div>

        <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3.5">
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Cryptographic Compliance Evidence</div>
          <div class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 flex items-center gap-1.5">
            <app-lucide-icon name="shield-check" [size]="14" class="text-blue-600"></app-lucide-icon>
            SHA-256 Merkle Root Attestation (Mandatory Active)
          </div>
          <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Formal compliance certificates are signed and immutable. Settings preferences cannot weaken or delete regulatory evidence.
          </div>
        </div>
      </section>

      <!-- Section 4: Logs (Storage & Retention) -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="archive" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">4. Logs (Storage &amp; Retention)</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Disk budgets, segment rotation size, and archival compression for diagnostic log files.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Diagnostic Log Budget (GiB)
            </label>
            <input
              type="number"
              min="2"
              max="50"
              [ngModel]="settings().diagnosticLogBudgetGb"
              (ngModelChange)="updateSetting('diagnosticLogBudgetGb', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Total local disk capacity allocated for engine and pipeline log files (default 10 GiB).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Log Segment Size (MiB)
            </label>
            <input
              type="number"
              min="20"
              max="250"
              step="10"
              [ngModel]="settings().logSegmentSizeMb"
              (ngModelChange)="updateSetting('logSegmentSizeMb', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Threshold at which active log file rolls over into a compressed segment (default 100 MiB).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Max Retained Log Segments
            </label>
            <input
              type="number"
              min="5"
              max="100"
              step="5"
              [ngModel]="settings().maxRetainedLogSegments"
              (ngModelChange)="updateSetting('maxRetainedLogSegments', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Maximum rotated segments retained before oldest archive is purged (default 20).</p>
          </div>
        </div>

        <div class="text-xs text-slate-500 dark:text-slate-400 italic">
          Note: This section configures local disk storage and rotation. Diagnostic verbosity and tracing filters are configured in Logging &amp; Diagnostics.
        </div>
      </section>

      <!-- Section 5: Retention Policies -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="shield" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">5. Retention Policies</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Subordinate operational lifecycle defaults and legal hold protection visibility.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Default Operational History Retention (days)
            </label>
            <input
              type="number"
              min="30"
              max="180"
              [ngModel]="settings().defaultJobHistoryRetentionDays"
              (ngModelChange)="updateSetting('defaultJobHistoryRetentionDays', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Workstation preference for completed migration run histories (default 30 days).</p>
          </div>

          <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3.5">
            <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Enterprise Minimum Retention</div>
            <div class="text-base font-bold text-slate-900 dark:text-slate-100 mt-1">30 Days Minimum Required</div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-1">
              <app-lucide-icon name="shield" [size]="12" class="text-blue-600"></app-lucide-icon>
              Enforced by Enterprise Governance Policy
            </div>
          </div>
        </div>

        <!-- Legal Hold Protection Card -->
        <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <app-lucide-icon name="lock" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
              Active Legal Hold Exemption Status: Protected
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Active legal preservation orders in Domain 5.9 Audit override all local retention policies and suspend automated purges.
            </div>
          </div>
          <div class="text-xs font-bold text-blue-700 dark:text-blue-400 px-2.5 py-1 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-md shrink-0">
            Litigation Hold Protected
          </div>
        </div>

        <!-- Destructive Purge Protection Notice -->
        <div class="text-xs text-slate-500 dark:text-slate-400 italic">
          Destructive Action Safety: Settings does not contain purge controls. Historical checkpoint deletion and log purging require privileged authorization in Domain 5.9 Audit &amp; Retention.
        </div>
      </section>
    </div>
  `
})
export class SettingsStorageComponent {
  private settingsService = inject(SettingsService);

  public settings = this.settingsService.storageRetentionSettings;

  public updateSetting(key: string, value: any): void {
    this.settingsService.updateStorageRetention({ [key]: value });
  }

  public resetDefaults(): void {
    this.settingsService.resetStorageRetention();
  }
}
