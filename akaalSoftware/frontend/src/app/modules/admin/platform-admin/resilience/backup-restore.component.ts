/**
 * AKAAL Administration — 5.10 Backup & Restore
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PlatformAdminService } from '../../services/platform-admin.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-backup-restore',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/platform-admin"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">PLATFORM</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">RESILIENCE & RECOVERY</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Backup & Restore</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Control plane metadata snapshots, disaster recovery restore checkpoints, and cryptographic checksum verification.
          </p>
        </div>
      </div>

      <!-- Backup Catalog Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Snapshot Name</th>
              <th class="py-3.5 px-4">Backup Type</th>
              <th class="py-3.5 px-4">Storage Location Reference</th>
              <th class="py-3.5 px-4">Snapshot Size</th>
              <th class="py-3.5 px-4">SHA-256 Checksum</th>
              <th class="py-3.5 px-4">Created Timestamp</th>
              <th class="py-3.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (bak of platformService.backups(); track bak.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900 font-heading">{{ bak.backupName }}</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-700">{{ bak.backupType }}</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-blue-600 max-w-xs truncate" [title]="bak.locationRef">
                  {{ bak.locationRef }}
                </td>
                <td class="py-3.5 px-4 font-semibold text-slate-900">{{ (bak.sizeBytes / (1024 * 1024)).toFixed(1) }} MB</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-500 max-w-[120px] truncate" [title]="bak.sha256Checksum">
                  {{ bak.sha256Checksum }}
                </td>
                <td class="py-3.5 px-4 text-slate-600 whitespace-nowrap">{{ bak.createdAt }}</td>
                <td class="py-3.5 px-4 text-right">
                  <button
                    type="button"
                    (click)="onRestore(bak.id)"
                    class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
                    Initiate Restore
                  </button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class BackupRestoreComponent {
  public platformService = inject(PlatformAdminService);

  public onRestore(id: string): void {
    const ok = confirm(`Initiating control plane restore from backup ${id} will enter maintenance mode. Confirm restore action?`);
    if (ok) {
      alert(`Restore operation for ${id} dispatched to backend authority.`);
    }
  }
}
