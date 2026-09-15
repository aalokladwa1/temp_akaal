import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-jit-access-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to People & Access
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Just-In-Time (JIT) Elevation</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Ephemeral, time-bounded privilege escalation requests with automated auto-expiry and dual-control sign-off.
          </p>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <a
            routerLink="/administration/people/jit-access/request"
            class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
            Request JIT Elevation
          </a>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Requester</th>
                <th class="py-3 px-4">Target Role</th>
                <th class="py-3 px-4">Scope</th>
                <th class="py-3 px-4">Duration</th>
                <th class="py-3 px-4">Justification</th>
                <th class="py-3 px-4">Status</th>
                <th class="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let j of peopleService.jitRequests()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900">{{ j.requesterName }}</span>
                    <span class="text-[11px] text-slate-500 font-mono">{{ j.requesterEmail }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 font-semibold text-amber-700">
                  {{ j.targetRoleName }}
                </td>
                <td class="py-3 px-4 text-slate-800">
                  {{ j.targetScopeName }}
                </td>
                <td class="py-3 px-4 font-bold text-slate-900">
                  {{ j.durationHours }} hrs
                </td>
                <td class="py-3 px-4 max-w-xs truncate text-slate-600">
                  {{ j.justification }}
                </td>
                <td class="py-3 px-4">
                  <span
                    class="rounded px-2 py-0.5 text-[11px] font-semibold"
                    [ngClass]="{
                      'bg-amber-50 text-amber-700': j.status === 'PENDING_APPROVAL',
                      'bg-emerald-50 text-emerald-700': j.status === 'ACTIVE_ELEVATED',
                      'bg-slate-100 text-slate-600': j.status === 'EXPIRED',
                      'bg-rose-50 text-rose-700': j.status === 'REJECTED'
                    }">
                    {{ j.status }}
                  </span>
                </td>
                <td class="py-3 px-4 text-right">
                  <a [routerLink]="['/administration/people/jit-access', j.id]" class="text-xs font-semibold text-blue-600 hover:text-blue-800">
                    Review
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class JitAccessListComponent {
  public peopleService = inject(PeopleService);
}