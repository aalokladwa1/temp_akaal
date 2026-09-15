/**
 * AKAAL Administration — 5.11 Create Notification Policy
 * Centered single-task form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { IntegrationsService } from '../../services/integrations.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-policy-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/integrations/notifications/policies"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">POLICIES</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">NEW POLICY</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Create Notification Policy</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Configure severity filtering thresholds, target channel destinations, and quiet hours.
          </p>
        </div>
      </div>

      <!-- Centered Form -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Policy Name</label>
          <input
            type="text"
            [(ngModel)]="name"
            placeholder="e.g. Critical Data Loss & CDC Lag Policy"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="flex flex-col gap-2">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Subscribed Severity Levels</label>
          <div class="flex items-center gap-4">
            <label class="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
              <input type="checkbox" [(ngModel)]="critical" class="rounded border-slate-300 text-blue-600" />
              <span class="font-semibold text-rose-700">CRITICAL</span>
            </label>
            <label class="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
              <input type="checkbox" [(ngModel)]="high" class="rounded border-slate-300 text-blue-600" />
              <span class="font-semibold text-amber-700">HIGH</span>
            </label>
            <label class="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
              <input type="checkbox" [(ngModel)]="medium" class="rounded border-slate-300 text-blue-600" />
              <span class="font-semibold text-blue-700">MEDIUM</span>
            </label>
            <label class="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
              <input type="checkbox" [(ngModel)]="low" class="rounded border-slate-300 text-blue-600" />
              <span class="font-semibold text-slate-600">LOW</span>
            </label>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Quiet Hours Start</label>
            <input
              type="text"
              [(ngModel)]="quietStart"
              placeholder="e.g. 22:00"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Quiet Hours End</label>
            <input
              type="text"
              [(ngModel)]="quietEnd"
              placeholder="e.g. 06:00"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Escalation Delay (Minutes)</label>
          <input
            type="number"
            [(ngModel)]="escalationDelay"
            min="0"
            max="120"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          <span class="text-[11px] text-slate-500">
            Set to 0 for immediate unthrottled broadcast across all target channels.
          </span>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/integrations/notifications/policies"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Create Policy
          </button>
        </div>

      </div>

    </div>
  `
})
export class PolicyCreateComponent {
  private integrationsService = inject(IntegrationsService);
  private router = inject(Router);

  public name = '';
  public critical = true;
  public high = true;
  public medium = false;
  public low = false;
  public quietStart = '';
  public quietEnd = '';
  public escalationDelay = 0;

  public isValid(): boolean {
    return this.name.trim().length > 0 && (this.critical || this.high || this.medium || this.low);
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    const severities: ('CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW')[] = [];
    if (this.critical) severities.push('CRITICAL');
    if (this.high) severities.push('HIGH');
    if (this.medium) severities.push('MEDIUM');
    if (this.low) severities.push('LOW');

    this.integrationsService.createPolicy({
      name: this.name.trim(),
      severityLevels: severities,
      channelIds: ['chan-email-01', 'chan-slack-01'],
      quietHoursStart: this.quietStart.trim() || undefined,
      quietHoursEnd: this.quietEnd.trim() || undefined,
      escalationDelayMinutes: this.escalationDelay || undefined
    });
    this.router.navigate(['/administration/integrations/notifications/policies']);
  }
}
