/**
 * AKAAL Administration — 5.11 Add Notification Channel
 * Centered single-task form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { IntegrationsService } from '../../services/integrations.service';
import { ChannelType } from '../../models/integrations.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-channel-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/integrations/notifications/channels"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">CHANNELS</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">NEW DESTINATION</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Add Notification Channel</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Register a webhook endpoint, Slack broadcast target, or PagerDuty incident routing key.
          </p>
        </div>
      </div>

      <!-- Centered Form -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Channel Name</label>
          <input
            type="text"
            [(ngModel)]="name"
            placeholder="e.g. Production Data Migration Incidents Slack"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Channel Provider Type</label>
          <app-custom-select
            [options]="typeOptions"
            [value]="selectedType"
            (valueChange)="selectedType = $event">
          </app-custom-select>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Target Endpoint / URL / Email Address</label>
          <input
            type="text"
            [(ngModel)]="targetEndpoint"
            placeholder="e.g. https://hooks.slack.com/services/... or alerts@corp.com"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Vault Credential Reference (Optional)</label>
          <input
            type="text"
            [(ngModel)]="credentialRef"
            placeholder="vault://secret/notifications/auth-token"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          <span class="text-[11px] text-slate-500">
            Encapsulate secrets within Vault. Plaintext tokens or API keys are strictly prohibited in product UI.
          </span>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Description & Applicability</label>
          <textarea
            rows="3"
            [(ngModel)]="description"
            placeholder="Describe what severity of incidents should route to this endpoint..."
            class="p-3 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"></textarea>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/integrations/notifications/channels"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Add Channel
          </button>
        </div>

      </div>

    </div>
  `
})
export class ChannelCreateComponent {
  private integrationsService = inject(IntegrationsService);
  private router = inject(Router);

  public name = '';
  public selectedType: ChannelType = 'SLACK';
  public targetEndpoint = '';
  public credentialRef = '';
  public description = '';

  public typeOptions: SelectOption[] = [
    { label: 'Slack Webhook / Incoming App', value: 'SLACK' },
    { label: 'Corporate Email / SMTP Relay', value: 'EMAIL_SMTP' },
    { label: 'Microsoft Teams Webhook Connector', value: 'TEAMS' },
    { label: 'PagerDuty Events API v2', value: 'PAGERDUTY' },
    { label: 'Generic JSON HTTP Webhook', value: 'WEBHOOK' }
  ];

  public isValid(): boolean {
    return this.name.trim().length > 0 && this.targetEndpoint.trim().length > 0;
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    this.integrationsService.createChannel({
      name: this.name.trim(),
      channelType: this.selectedType,
      targetEndpointOrAddress: this.targetEndpoint.trim(),
      credentialRef: this.credentialRef.trim() || undefined,
      isEnabled: true,
      description: this.description.trim()
    });
    this.router.navigate(['/administration/integrations/notifications/channels']);
  }
}
