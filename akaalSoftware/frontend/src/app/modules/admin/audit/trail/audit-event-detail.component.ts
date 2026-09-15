/**
 * AKAAL Administration — 5.9 Audit Event Detail View
 */

import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { AdministrativeAuditEvent } from '../../models/audit.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-audit-event-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/audit/trail"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back to Trail</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">AUDIT RECORD</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-mono font-bold text-blue-600">{{ event()?.id || 'EVENT' }}</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2 font-mono">
            {{ event()?.action || 'Event Details' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Recorded at {{ event()?.timestamp }} by {{ event()?.actor }} (IP: {{ event()?.ipAddress }}).
          </p>
        </div>
      </div>

      <!-- Properties Grid -->
      @if (event(); as evt) {
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-6">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Actor Principal</span>
              <span class="text-xs font-bold text-slate-900">{{ evt.actor }}</span>
              <span class="text-[11px] font-mono text-slate-500">{{ evt.actorRole }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Target Resource</span>
              <span class="text-xs font-mono font-bold text-blue-600">{{ evt.resourceType }}: {{ evt.resourceId }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Correlation ID</span>
              <span class="text-xs font-mono text-slate-700 select-all">{{ evt.correlationId }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Operational Outcome</span>
              <span 
                class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border w-fit"
                [ngClass]="{
                  'bg-emerald-50 text-emerald-700 border-emerald-200': evt.outcome === 'SUCCESS',
                  'bg-rose-50 text-rose-700 border-rose-200': evt.outcome === 'FAILURE',
                  'bg-amber-50 text-amber-700 border-amber-200': evt.outcome === 'DENIED'
                }">
                {{ evt.outcome }}
              </span>
            </div>
          </div>

          <div class="border-t border-slate-200 pt-5 flex flex-col gap-2">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Event Details & Mutation Payload</span>
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 leading-relaxed">
              {{ evt.details }}
            </div>
          </div>
        </div>
      }
    </div>
  `
})
export class AuditEventDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private auditService = inject(AuditService);

  public event = signal<AdministrativeAuditEvent | undefined>(undefined);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.event.set(this.auditService.getEventById(id));
    }
  }
}
