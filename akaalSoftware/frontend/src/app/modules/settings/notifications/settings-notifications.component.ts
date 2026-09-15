import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../shared/components/custom-select.component';
import { SettingsService } from '../services/settings.service';
import { IntegrationsService } from '../../admin/services/integrations.service';
import { NotificationSeverityLevel, NotificationDigestFrequency } from '../models/settings.models';

@Component({
  selector: 'app-settings-notifications',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="space-y-8">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div class="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider font-mono">Operational Defaults</div>
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">Notifications</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure alert dispatch thresholds, notification destinations, escalation policies, and quiet hours for platform events.
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
          <span class="font-bold text-slate-900 dark:text-slate-100">Workstation Notification Preferences:</span>
          Preferences configured here initialize default alert delivery channels and severity filters for new workflows on this workstation. Critical platform security and fatal cluster halts bypass quiet hours and always escalate in accordance with enterprise policy.
        </div>
      </div>

      <!-- 1. Email Notifications -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="mail" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">1. Email Notifications</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Direct SMTP alert dispatches, severity filtering, and digest delivery rollup.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('emailEnabled', !settings().emailEnabled)"
            [class.bg-blue-600]="settings().emailEnabled"
            [class.bg-slate-300]="!settings().emailEnabled"
            [class.dark:bg-slate-700]="!settings().emailEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().emailEnabled"
              [class.translate-x-0]="!settings().emailEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" [class.opacity-60]="!settings().emailEnabled">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Minimum Alert Severity
            </label>
            <app-custom-select
              [options]="severityOptions"
              [disabled]="!settings().emailEnabled"
              [ngModel]="settings().emailMinSeverity"
              (ngModelChange)="updateSetting('emailMinSeverity', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Events below this severity threshold will not generate email alerts.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Digest Delivery Frequency
            </label>
            <app-custom-select
              [options]="digestFrequencyOptions"
              [disabled]="!settings().emailEnabled"
              [ngModel]="settings().emailDigestFrequency"
              (ngModelChange)="updateSetting('emailDigestFrequency', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Batches non-critical warnings into periodic summaries to reduce inbox noise.</p>
          </div>

          <div class="md:col-span-2 space-y-3">
            <div class="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Subscribed Event Categories
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label class="flex items-center gap-2.5 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 cursor-pointer">
                <input
                  type="checkbox"
                  [disabled]="!settings().emailEnabled"
                  [ngModel]="settings().emailNotifyOnMigrationFailure"
                  (ngModelChange)="updateSetting('emailNotifyOnMigrationFailure', $event)"
                  class="rounded text-blue-600 focus:ring-blue-500 h-4 w-4 border-slate-300 dark:border-slate-600" />
                <span class="text-xs font-medium text-slate-700 dark:text-slate-300">Pipeline Failures</span>
              </label>

              <label class="flex items-center gap-2.5 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 cursor-pointer">
                <input
                  type="checkbox"
                  [disabled]="!settings().emailEnabled"
                  [ngModel]="settings().emailNotifyOnSecurityAlert"
                  (ngModelChange)="updateSetting('emailNotifyOnSecurityAlert', $event)"
                  class="rounded text-blue-600 focus:ring-blue-500 h-4 w-4 border-slate-300 dark:border-slate-600" />
                <span class="text-xs font-medium text-slate-700 dark:text-slate-300">Security &amp; Auth Alerts</span>
              </label>

              <label class="flex items-center gap-2.5 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 cursor-pointer">
                <input
                  type="checkbox"
                  [disabled]="!settings().emailEnabled"
                  [ngModel]="settings().emailNotifyOnGovernanceBarrier"
                  (ngModelChange)="updateSetting('emailNotifyOnGovernanceBarrier', $event)"
                  class="rounded text-blue-600 focus:ring-blue-500 h-4 w-4 border-slate-300 dark:border-slate-600" />
                <span class="text-xs font-medium text-slate-700 dark:text-slate-300">Governance Barriers</span>
              </label>
            </div>
          </div>

          <!-- Enterprise Endpoint Reference Card -->
          <div class="md:col-span-2 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <app-lucide-icon name="shield" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
                Enterprise SMTP Relay Endpoint
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Target: <span class="font-mono text-slate-700 dark:text-slate-300">{{ emailEndpoint() }}</span>
              </div>
            </div>
            <div class="text-xs font-bold text-slate-600 dark:text-slate-300 px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shrink-0">
              Channel: chan-email-01
            </div>
          </div>
        </div>
      </section>

      <!-- 2. Slack Notifications -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="message-square" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">2. Slack Notifications</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Incoming webhook integration for live team alerts and incident thread diagnostics.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('slackEnabled', !settings().slackEnabled)"
            [class.bg-blue-600]="settings().slackEnabled"
            [class.bg-slate-300]="!settings().slackEnabled"
            [class.dark:bg-slate-700]="!settings().slackEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().slackEnabled"
              [class.translate-x-0]="!settings().slackEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" [class.opacity-60]="!settings().slackEnabled">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Default Target Slack Channel
            </label>
            <app-custom-select
              [options]="slackChannelOptions()"
              [disabled]="!settings().slackEnabled"
              [ngModel]="settings().slackChannelId"
              (ngModelChange)="updateSetting('slackChannelId', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Dispatches to registered Slack integration channels from Administration.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Minimum Severity Threshold
            </label>
            <app-custom-select
              [options]="severityOptions"
              [disabled]="!settings().slackEnabled"
              [ngModel]="settings().slackMinSeverity"
              (ngModelChange)="updateSetting('slackMinSeverity', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Filters noise from high-frequency info notices.</p>
          </div>

          <div class="md:col-span-2 flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Incident Thread Diagnostics</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">Post detailed error codes, worker stack traces, and recovery links as replies under the main alert card.</div>
            </div>
            <button
              type="button"
              [disabled]="!settings().slackEnabled"
              (click)="updateSetting('slackThreadReplies', !settings().slackThreadReplies)"
              [class.bg-blue-600]="settings().slackThreadReplies"
              [class.bg-slate-300]="!settings().slackThreadReplies"
              [class.dark:bg-slate-700]="!settings().slackThreadReplies"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5 disabled:opacity-50 disabled:cursor-not-allowed">
              <span
                [class.translate-x-5]="settings().slackThreadReplies"
                [class.translate-x-0]="!settings().slackThreadReplies"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>
        </div>
      </section>

      <!-- 3. Microsoft Teams Notifications -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="users" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">3. Microsoft Teams</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Incoming webhook integration for Office 365 and Microsoft Teams channels.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('teamsEnabled', !settings().teamsEnabled)"
            [class.bg-blue-600]="settings().teamsEnabled"
            [class.bg-slate-300]="!settings().teamsEnabled"
            [class.dark:bg-slate-700]="!settings().teamsEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().teamsEnabled"
              [class.translate-x-0]="!settings().teamsEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="space-y-4" [class.opacity-60]="!settings().teamsEnabled">
          <div class="bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 rounded-lg p-4 flex items-start gap-3">
            <app-lucide-icon name="alert-circle" [size]="16" class="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="text-xs text-slate-700 dark:text-slate-300">
              <span class="font-bold text-slate-900 dark:text-slate-100">No Teams Channel Configured:</span>
              There is currently no Microsoft Teams incoming webhook registered in Administration. Enable this channel after adding an Office 365 connector in Administration (Integrations &amp; Notifications).
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Configured Channel Target
              </label>
              <input
                type="text"
                readonly
                value="Unconfigured in Workspace"
                class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-500 dark:text-slate-400 cursor-not-allowed" />
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Minimum Severity Level
              </label>
              <app-custom-select
                [options]="severityOptions"
                [disabled]="!settings().teamsEnabled"
                [ngModel]="settings().teamsMinSeverity"
                (ngModelChange)="updateSetting('teamsMinSeverity', $event)">
              </app-custom-select>
            </div>
          </div>
        </div>
      </section>

      <!-- 4. Webhooks -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="webhook" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">4. Webhooks</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Custom HTTP JSON POST callbacks for external automation, alerting, and SIEM forwarders.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('webhookEnabled', !settings().webhookEnabled)"
            [class.bg-blue-600]="settings().webhookEnabled"
            [class.bg-slate-300]="!settings().webhookEnabled"
            [class.dark:bg-slate-700]="!settings().webhookEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().webhookEnabled"
              [class.translate-x-0]="!settings().webhookEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" [class.opacity-60]="!settings().webhookEnabled">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Payload Schema Format
            </label>
            <app-custom-select
              [options]="webhookFormatOptions"
              [disabled]="!settings().webhookEnabled"
              [ngModel]="settings().webhookPayloadFormat"
              (ngModelChange)="updateSetting('webhookPayloadFormat', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Standard envelope complies with CloudEvents 1.0 specifications.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Cryptographic Header Signature
            </label>
            <input
              type="text"
              readonly
              value="HMAC SHA-256 (X-Akaal-Signature)"
              class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Every webhook delivery is signed with the cluster secret key.</p>
          </div>
        </div>
      </section>

      <!-- 5. Escalation Defaults -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="alert-triangle" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">5. Escalation Defaults</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">On-call escalation rules and operator acknowledgment deadlines.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('escalationEnabled', !settings().escalationEnabled)"
            [class.bg-blue-600]="settings().escalationEnabled"
            [class.bg-slate-300]="!settings().escalationEnabled"
            [class.dark:bg-slate-700]="!settings().escalationEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().escalationEnabled"
              [class.translate-x-0]="!settings().escalationEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" [class.opacity-60]="!settings().escalationEnabled">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Escalation Destination Service
            </label>
            <app-custom-select
              [options]="escalationChannelOptions()"
              [disabled]="!settings().escalationEnabled"
              [ngModel]="settings().escalationTargetChannelId"
              (ngModelChange)="updateSetting('escalationTargetChannelId', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Designated on-call dispatch channel registered in enterprise policy.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Personal Acknowledgment Window (minutes)
            </label>
            <app-custom-select
              [options]="ackWindowOptions"
              [disabled]="!settings().escalationEnabled"
              [ngModel]="settings().personalAckWindowMinutes"
              (ngModelChange)="updateSetting('personalAckWindowMinutes', +$event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Time before an unacknowledged incident triggers secondary on-call paging.</p>
          </div>

          <!-- Governed Mandatory Policy Notice -->
          <div class="md:col-span-2 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <app-lucide-icon name="shield" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
                Mandatory Critical Escalation Enforced
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Enterprise policy npol-01 mandates that unhandled CRITICAL events cannot be suppressed by workstation preferences.
              </div>
            </div>
            <div class="text-xs font-bold text-slate-600 dark:text-slate-300 px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shrink-0">
              Policy npol-01
            </div>
          </div>
        </div>
      </section>

      <!-- 6. Quiet Hours -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="moon" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">6. Quiet Hours</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Schedule automatic suppression for low and medium operational notifications.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('quietHoursEnabled', !settings().quietHoursEnabled)"
            [class.bg-blue-600]="settings().quietHoursEnabled"
            [class.bg-slate-300]="!settings().quietHoursEnabled"
            [class.dark:bg-slate-700]="!settings().quietHoursEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().quietHoursEnabled"
              [class.translate-x-0]="!settings().quietHoursEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" [class.opacity-60]="!settings().quietHoursEnabled">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Quiet Period Start (Local Time)
            </label>
            <input
              type="time"
              [disabled]="!settings().quietHoursEnabled"
              [ngModel]="settings().quietHoursStart"
              (ngModelChange)="updateSetting('quietHoursStart', $event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Routine operational dispatches pause at this time.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Quiet Period End (Local Time)
            </label>
            <input
              type="time"
              [disabled]="!settings().quietHoursEnabled"
              [ngModel]="settings().quietHoursEnd"
              (ngModelChange)="updateSetting('quietHoursEnd', $event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Batched digests deliver immediately following quiet period completion.</p>
          </div>

          <!-- Critical Bypass Safety Banner -->
          <div class="md:col-span-2 bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <app-lucide-icon name="alert-octagon" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
                Critical Alert Bypass Safety Guarantee
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Fatal migration halts and KMS key compromise alerts bypass quiet hours and ring immediately.
              </div>
            </div>
            <div class="text-xs font-bold text-blue-700 dark:text-blue-300 px-2.5 py-1 bg-blue-100/60 dark:bg-blue-900/40 border border-blue-200 dark:border-blue-800 rounded-md shrink-0">
              Enforced Safety Rule
            </div>
          </div>
        </div>
      </section>
    </div>
  `
})
export class SettingsNotificationsComponent {
  private settingsService = inject(SettingsService);
  private integrationsService = inject(IntegrationsService);

  public settings = this.settingsService.notificationSettings;

  public severityOptions: SelectOption[] = [
    { label: 'Low (All operational notices)', value: 'LOW' },
    { label: 'Medium (Warnings & errors)', value: 'MEDIUM' },
    { label: 'High (Errors & critical only)', value: 'HIGH' },
    { label: 'Critical (Fatal halts only)', value: 'CRITICAL' }
  ];

  public digestFrequencyOptions: SelectOption[] = [
    { label: 'Immediate (Real-time alert dispatch)', value: 'IMMEDIATE' },
    { label: 'Hourly Digest (Batched hourly summary)', value: 'HOURLY_DIGEST' },
    { label: 'Daily Digest (24-hour summary briefing)', value: 'DAILY_DIGEST' }
  ];

  public webhookFormatOptions: SelectOption[] = [
    { label: 'Standard Envelope (CloudEvents 1.0 JSON)', value: 'STANDARD_JSON' },
    { label: 'Expanded Envelope (Includes Stack Trace & Context)', value: 'EXPANDED_JSON' }
  ];

  public ackWindowOptions: SelectOption[] = [
    { label: '5 minutes', value: 5 },
    { label: '15 minutes (Standard)', value: 15 },
    { label: '30 minutes', value: 30 }
  ];

  // Dynamic channels from canonical IntegrationsService
  public emailEndpoint = computed<string>(() => {
    const ch = this.integrationsService.getChannelById('chan-email-01');
    return ch ? ch.targetEndpointOrAddress : 'secops-alerts@akaaltech.com';
  });

  public slackChannelOptions = computed<SelectOption[]>(() => {
    const list = this.integrationsService.channels().filter(c => c.channelType === 'SLACK');
    if (list.length === 0) {
      return [{ label: 'No Slack channels configured', value: '' }];
    }
    return list.map(c => ({
      label: `${c.name} (${c.id})`,
      value: c.id,
      desc: c.description
    }));
  });

  public escalationChannelOptions = computed<SelectOption[]>(() => {
    const list = this.integrationsService.channels().filter(c => c.channelType === 'PAGERDUTY' || c.channelType === 'EMAIL_SMTP');
    return list.map(c => ({
      label: `${c.name} (${c.id})`,
      value: c.id,
      desc: c.description
    }));
  });

  public updateSetting(key: string, value: any): void {
    this.settingsService.updateNotification({ [key]: value });
  }

  public resetDefaults(): void {
    this.settingsService.resetNotifications();
  }
}
