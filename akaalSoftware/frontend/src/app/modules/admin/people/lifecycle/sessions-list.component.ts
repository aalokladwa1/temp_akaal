import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-sessions-list',
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
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Active Principal Sessions</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Live interactive and programmatic session states with real-time remote termination capabilities.
          </p>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Principal</th>
                <th class="py-3 px-4">IP Address</th>
                <th class="py-3 px-4">Device / Client</th>
                <th class="py-3 px-4">Location</th>
                <th class="py-3 px-4">Last Activity</th>
                <th class="py-3 px-4">Status</th>
                <th class="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let s of peopleService.sessions()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900">{{ s.principalName }}</span>
                    <span class="text-[11px] text-slate-500 font-mono">{{ s.principalEmail }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 font-mono text-slate-800">
                  {{ s.ipAddress }}
                </td>
                <td class="py-3 px-4 text-slate-700">
                  {{ s.deviceInfo }}
                </td>
                <td class="py-3 px-4 text-slate-700">
                  {{ s.location }}
                </td>
                <td class="py-3 px-4 text-slate-600">
                  {{ s.lastActivityAt }}
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold" [ngClass]="s.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'">
                    {{ s.status }}
                  </span>
                </td>
                <td class="py-3 px-4 text-right">
                  <button *ngIf="s.status === 'ACTIVE'" (click)="terminate(s.id)" class="text-xs font-semibold text-rose-600 hover:text-rose-800 cursor-pointer">
                    Terminate Session
                  </button>
                  <span *ngIf="s.status !== 'ACTIVE'" class="text-xs text-slate-400">Terminated</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class SessionsListComponent {
  public peopleService = inject(PeopleService);

  public terminate(id: string): void {
    this.peopleService.terminateSession(id);
  }
}