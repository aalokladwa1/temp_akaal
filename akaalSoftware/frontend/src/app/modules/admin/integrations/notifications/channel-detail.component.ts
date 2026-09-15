/**
 * AKAAL Administration — 5.11 Notification Channel Detail View
 */

import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { IntegrationsService } from '../../services/integrations.service';
import { NotificationChannel } from '../../models/integrations.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-channel-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
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
              <span>Back to Channels</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">NOTIFICATION CHANNEL</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-mono font-bold text-blue-600">{{ channel()?.id || 'CHANNEL' }}</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">
            {{ channel()?.name || 'Channel Details' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            {{ channel()?.description }}
          </p>
        </div>
      </div>

      <!-- Detail Card -->
      @if (channel(); as ch) {
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-6">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Provider Protocol</span>
              <span class="text-xs font-mono font-semibold text-slate-900">{{ ch.channelType }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Target Endpoint</span>
              <span class="text-xs font-mono text-slate-900 truncate" [title]="ch.targetEndpointOrAddress">{{ ch.targetEndpointOrAddress }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Credential Reference</span>
              <span class="text-xs font-mono text-blue-600">{{ ch.credentialRef || 'None (Unauthenticated Webhook)' }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Delivery Status</span>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 w-fit">
                {{ ch.isEnabled ? 'Active' : 'Disabled' }}
              </span>
            </div>
          </div>

          <div class="border-t border-slate-200 pt-4 flex items-center justify-between text-xs text-slate-500">
            <span>Created on {{ ch.createdAt }}</span>
            <span>Live connectivity is proven upon actual notification dispatch</span>
          </div>
        </div>
      }
    </div>
  `
})
export class ChannelDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private integrationsService = inject(IntegrationsService);

  public channel = signal<NotificationChannel | undefined>(undefined);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.channel.set(this.integrationsService.getChannelById(id));
    }
  }
}
