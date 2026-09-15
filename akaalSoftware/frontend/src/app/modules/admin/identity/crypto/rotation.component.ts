/**
 * AKAAL Administration — Secret Rotation & Auditing
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-rotation',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity/crypto" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Cryptography & Secrets
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Automated Secret Rotation</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Zero-downtime rotation policies for database credentials, service account tokens, and KMS wrapping keys.
            </p>
          </div>
        </div>
      </div>

      <!-- Rotation Rules Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Rotation Rule Name</th>
              <th class="py-3 px-4">Target Type</th>
              <th class="py-3 px-4">Target Resource</th>
              <th class="py-3 px-4">Frequency</th>
              <th class="py-3 px-4">Last Rotated</th>
              <th class="py-3 px-4">Next Rotation</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let r of identity.rotationRules()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4 font-bold text-slate-900">{{ r.name }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ r.targetType }}
                </span>
              </td>
              <td class="py-3 px-4 font-mono font-medium text-slate-800">{{ r.targetResourceName }}</td>
              <td class="py-3 px-4 font-semibold text-slate-700">Every {{ r.rotationFrequencyDays }} days</td>
              <td class="py-3 px-4 text-slate-600 text-[11px]">{{ r.lastRotationTimestamp }}</td>
              <td class="py-3 px-4 text-slate-600 font-mono text-[11px]">{{ r.nextRotationTimestamp }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ r.lastRotationStatus }}
                </span>
              </td>
              <td class="py-3 px-4 text-right">
                <button
                  (click)="identity.triggerSecretRotation(r.id)"
                  class="px-2.5 py-1 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs cursor-pointer">
                  Rotate Now
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class RotationComponent {
  public identity = inject(IdentityService);
}
