import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../shared/components/custom-select.component';
import { SettingsService } from '../services/settings.service';
import { TLSEnforcementMode, CursorPaginationStrategy } from '../models/settings.models';

@Component({
  selector: 'app-settings-connectors',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="space-y-8">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div class="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider font-mono">Operational Defaults</div>
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">Connector Defaults</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Configure reusable connection timeouts, TCP keep-alive probes, streaming fetch buffers, and enterprise TLS security baselines.</p>
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
          <span class="font-bold text-slate-900 dark:text-slate-100">Connection Pre-Population:</span>
          Parameters configured here pre-populate new connection registrations and migration source/target configurations. Active database pools and established endpoints are not mutated. Connector drivers and plugins are managed in Domain 5.6 Connector Center.
        </div>
      </div>

      <!-- Section 1: Connection Behavior & Timeouts -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="clock" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">1. Connection Behavior &amp; Timeouts</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Default transport and session timeout boundaries applied to new database endpoints.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Connection Timeout (ms)
            </label>
            <input
              type="number"
              min="1000"
              max="60000"
              step="1000"
              [ngModel]="settings().connectTimeoutMs"
              (ngModelChange)="updateSetting('connectTimeoutMs', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Socket TCP handshake deadline (default 15,000 ms).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Socket / Read Timeout (ms)
            </label>
            <input
              type="number"
              min="5000"
              max="120000"
              step="5000"
              [ngModel]="settings().socketTimeoutMs"
              (ngModelChange)="updateSetting('socketTimeoutMs', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Maximum read inactivity window before transport reset (default 30,000 ms).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              DNS Resolution Timeout (ms)
            </label>
            <input
              type="number"
              min="1000"
              max="15000"
              step="500"
              [ngModel]="settings().dnsTimeoutMs"
              (ngModelChange)="updateSetting('dnsTimeoutMs', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Hostname lookup deadline with Happy Eyeballs fallback (default 5,000 ms).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Statement Timeout (ms)
            </label>
            <input
              type="number"
              min="5000"
              max="300000"
              step="5000"
              [ngModel]="settings().statementTimeoutMs"
              (ngModelChange)="updateSetting('statementTimeoutMs', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Individual SQL query execution deadline (default 60,000 ms).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Lock Acquisition Timeout (ms)
            </label>
            <input
              type="number"
              min="1000"
              max="60000"
              step="1000"
              [ngModel]="settings().lockTimeoutMs"
              (ngModelChange)="updateSetting('lockTimeoutMs', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Maximum wait duration for table/row lock acquisition (default 10,000 ms).</p>
          </div>
        </div>
      </section>

      <!-- Section 2: Keep-Alive & Network Probes -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="activity" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">2. Keep-Alive &amp; Network Probes</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Transport-level heartbeat probes to detect dead sockets and prevent middlebox dropouts.</p>
          </div>
        </div>

        <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
          <div>
            <div class="text-xs font-bold text-slate-800 dark:text-slate-200">TCP Keep-Alive Probing</div>
            <div class="text-xs text-slate-500 dark:text-slate-400">Sends background probe packets across idle database connections to prevent stateful NAT/firewall drops.</div>
          </div>
          <button
            type="button"
            (click)="updateSetting('keepaliveEnabled', !settings().keepaliveEnabled)"
            [class.bg-blue-600]="settings().keepaliveEnabled"
            [class.bg-slate-300]="!settings().keepaliveEnabled"
            [class.dark:bg-slate-700]="!settings().keepaliveEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().keepaliveEnabled"
              [class.translate-x-0]="!settings().keepaliveEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Keep-Alive Idle Time (seconds)
            </label>
            <input
              type="number"
              min="10"
              max="300"
              [ngModel]="settings().keepaliveIdleSeconds"
              (ngModelChange)="updateSetting('keepaliveIdleSeconds', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Inactivity duration before the initial probe is dispatched (default 60s).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Probe Interval (seconds)
            </label>
            <input
              type="number"
              min="5"
              max="60"
              [ngModel]="settings().keepaliveIntervalSeconds"
              (ngModelChange)="updateSetting('keepaliveIntervalSeconds', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Cadence between consecutive unanswered probes (default 15s).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Probe Count (retries)
            </label>
            <input
              type="number"
              min="2"
              max="10"
              [ngModel]="settings().keepaliveProbesCount"
              (ngModelChange)="updateSetting('keepaliveProbesCount', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Failed probe count before socket is declared severed (default 5).</p>
          </div>
        </div>
      </section>

      <!-- Section 3: Fetch & Transfer Behavior -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="layers" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">3. Fetch &amp; Transfer Behavior</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Cursor fetch chunk sizes, memory limits, and pagination streaming models.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Default Cursor Fetch Size (rows)
            </label>
            <input
              type="number"
              min="500"
              max="10000"
              step="500"
              [ngModel]="settings().defaultFetchSize"
              (ngModelChange)="updateSetting('defaultFetchSize', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Row chunk quantity retrieved per network roundtrip (default 2,000).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Max Row Read Buffer (MiB)
            </label>
            <input
              type="number"
              min="4"
              max="64"
              step="4"
              [ngModel]="settings().maxReadBufferMb"
              (ngModelChange)="updateSetting('maxReadBufferMb', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Driver buffer ceiling for incoming unmarshaled records (default 16 MiB).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Streaming Pagination Strategy
            </label>
            <app-custom-select
              [options]="paginationOptions"
              [ngModel]="settings().paginationStrategy"
              (ngModelChange)="updateSetting('paginationStrategy', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Keyset cursors prevent offset degradation on large-volume tables.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Character Encoding Fallback
            </label>
            <input
              type="text"
              readonly
              value="UTF-8 (Strict)"
              class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Enforces strict UTF-8 validation with zero silent byte loss.</p>
          </div>
        </div>
      </section>

      <!-- Section 4: Security Baseline -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="shield-check" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">4. Security Baseline</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Transport encryption enforcement and zero-trust credential reference protocol.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Minimum TLS Protocol Version
            </label>
            <input
              type="text"
              readonly
              value="TLSv1.2 (TLSv1.3 Preferred)"
              class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Legacy SSLv3, TLS 1.0, and TLS 1.1 are strictly rejected by platform policy.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Default TLS Mode
            </label>
            <app-custom-select
              [options]="tlsModeOptions"
              [ngModel]="settings().tlsMode"
              (ngModelChange)="updateSetting('tlsMode', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">VERIFY_FULL enforces certificate authority chain and hostname validation.</p>
          </div>
        </div>

        <!-- Governed Security Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3.5">
            <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Permissive Self-Signed Certificates</div>
            <div class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 flex items-center gap-1.5">
              <app-lucide-icon name="lock" [size]="14" class="text-blue-600"></app-lucide-icon>
              Strictly Disabled (Enforced by Policy)
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Production connectors require valid CA signatures or pinned X.509 certificates managed in Domain 5.4 Identity &amp; Security.
            </div>
          </div>

          <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3.5">
            <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Credential Custody Protocol</div>
            <div class="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1 flex items-center gap-1.5">
              <app-lucide-icon name="shield" [size]="14" class="text-blue-600"></app-lucide-icon>
              vault:// Encapsulated References
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Zero plaintext credentials. All database passwords and keys are resolved ephemerally via enterprise KMS and HashiCorp Vault.
            </div>
          </div>
        </div>
      </section>
    </div>
  `
})
export class SettingsConnectorsComponent {
  private settingsService = inject(SettingsService);

  public settings = this.settingsService.connectorSettings;

  public paginationOptions: SelectOption[] = [
    { label: 'Keyset Cursor (Recommended for High Scale)', value: 'KEYSET_CURSOR' },
    { label: 'Limit / Offset Windowing', value: 'LIMIT_OFFSET' },
    { label: 'Streaming Resultset (Driver Managed)', value: 'STREAMING_RESULTSET' }
  ];

  public tlsModeOptions: SelectOption[] = [
    { label: 'VERIFY_FULL: Chain & Hostname Validation (Recommended)', value: 'VERIFY_FULL' },
    { label: 'VERIFY_CA: Certificate Authority Chain Only', value: 'VERIFY_CA' },
    { label: 'REQUIRED: Encrypted Transit (No Chain Verification)', value: 'REQUIRED' },
    { label: 'PREFERRED: Opportunistic TLS', value: 'PREFERRED' }
  ];

  public updateSetting(key: string, value: any): void {
    this.settingsService.updateConnector({ [key]: value });
  }

  public resetDefaults(): void {
    this.settingsService.resetConnector();
  }
}
