/**
 * AKAAL Administration — 5.10 Schedule Maintenance Window
 * Centered single-task form.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { PlatformAdminService } from '../../services/platform-admin.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-maintenance-window-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/platform-admin/lifecycle/maintenance"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">MAINTENANCE</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">SCHEDULE WINDOW</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Schedule Maintenance Window</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Reserve planned maintenance downtime, configure worker drain durations, and define cluster scope.
          </p>
        </div>
      </div>

      <!-- Centered Form -->
      <div class="max-w-3xl mx-auto w-full bg-white border border-slate-200 rounded-xl p-8 shadow-2xs flex flex-col gap-6">
        
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Maintenance Window Title</label>
          <input
            type="text"
            [(ngModel)]="title"
            placeholder="e.g. Q2 Distributed Storage Upgrade & Kernel Roll"
            class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Start Time (UTC)</label>
            <input
              type="text"
              [(ngModel)]="startTime"
              placeholder="e.g. 2026-04-01 02:00 UTC"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">End Time (UTC)</label>
            <input
              type="text"
              [(ngModel)]="endTime"
              placeholder="e.g. 2026-04-01 06:00 UTC"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Maintenance Scope</label>
          <app-custom-select
            [options]="scopeOptions"
            [value]="selectedScope"
            (valueChange)="selectedScope = $event">
          </app-custom-select>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <input
            type="checkbox"
            id="allowJobDrain"
            [(ngModel)]="allowJobDrain"
            class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
          <label for="allowJobDrain" class="text-xs font-medium text-slate-700 cursor-pointer">
            Allow Graceful Pipeline Worker Drain (Prevents In-Flight Data Truncation)
          </label>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/platform-admin/lifecycle/maintenance"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors">
            Cancel
          </a>
          <button
            type="button"
            (click)="onSubmit()"
            [disabled]="!isValid()"
            class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
            Schedule Window
          </button>
        </div>

      </div>

    </div>
  `
})
export class MaintenanceWindowCreateComponent {
  private platformService = inject(PlatformAdminService);
  private router = inject(Router);

  public title = '';
  public startTime = '2026-04-01 02:00 UTC';
  public endTime = '2026-04-01 06:00 UTC';
  public selectedScope: 'CLUSTER_WIDE' | 'SPECIFIC_NODES' = 'CLUSTER_WIDE';
  public allowJobDrain = true;

  public scopeOptions: SelectOption[] = [
    { label: 'Cluster-Wide (All Compute Nodes & Daemons)', value: 'CLUSTER_WIDE' },
    { label: 'Specific Ingestion Nodes Only', value: 'SPECIFIC_NODES' }
  ];

  public isValid(): boolean {
    return this.title.trim().length > 0 && this.startTime.trim().length > 0 && this.endTime.trim().length > 0;
  }

  public onSubmit(): void {
    if (!this.isValid()) return;
    this.platformService.createMaintenanceWindow({
      title: this.title.trim(),
      scheduledStartTime: this.startTime.trim(),
      scheduledEndTime: this.endTime.trim(),
      scope: this.selectedScope,
      allowJobDrain: this.allowJobDrain
    });
    this.router.navigate(['/administration/platform-admin/lifecycle/maintenance']);
  }
}
