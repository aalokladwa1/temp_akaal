/**
 * AKAAL Administration — 5.9 Audit Policy Detail View
 */

import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { AuditPolicy } from '../../models/audit.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-audit-policy-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/audit/policies"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back to Policies</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">AUDIT POLICY</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-mono font-bold text-blue-600">{{ policy()?.id || 'POLICY' }}</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">
            {{ policy()?.name || 'Policy Details' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            {{ policy()?.description }}
          </p>
        </div>
      </div>

      <!-- Properties Grid -->
      @if (policy(); as p) {
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs grid grid-cols-1 md:grid-cols-4 gap-6">
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Event Category</span>
            <span class="text-xs font-mono font-semibold text-slate-900">{{ p.category }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Severity Filter</span>
            <span class="text-xs font-semibold text-slate-900">{{ p.severityFilter.replace('_', ' ') }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Retention Window</span>
            <span class="text-xs font-semibold text-slate-900">{{ p.retentionDays }} Days ({{ (p.retentionDays / 365).toFixed(1) }} Years)</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Status</span>
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 w-fit">
              {{ p.status }}
            </span>
          </div>
        </div>

        <!-- Target Destinations Section -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Configured Target Destinations</h2>
            <a
              routerLink="/administration/audit/destinations"
              class="text-xs font-semibold text-blue-600 hover:underline">
              Manage Destinations
            </a>
          </div>

          <div class="flex flex-wrap gap-2">
            @for (destId of p.destinations; track destId) {
              <span class="inline-flex items-center px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700">
                {{ destId }}
              </span>
            }
          </div>
        </div>
      }
    </div>
  `
})
export class AuditPolicyDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private auditService = inject(AuditService);

  public policy = signal<AuditPolicy | undefined>(undefined);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.policy.set(this.auditService.getPolicyById(id));
    }
  }
}
