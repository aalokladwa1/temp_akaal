import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { ReportsService } from '../services/reports.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-reports-evidence-activity',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-3 select-none">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            RECENT EVIDENCE ACTIVITY
          </span>
          @if (rs.hasEvidenceActivity()) {
            <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">
              {{ rs.evidenceActivity().length }}
            </span>
          }
        </div>

        <a
          routerLink="/reports/evidence"
          class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer">
          <span>Open Evidence Portal</span>
          <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
        </a>
      </div>

      <!-- State: LOADING -->
      @if (rs.evidenceState() === 'LOADING') {
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs animate-pulse h-24"></div>
      } @else if (rs.evidenceState() === 'UNAVAILABLE' || rs.evidenceState() === 'ERROR') {
        <!-- State: UNAVAILABLE / ERROR -->
        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 text-xs flex items-center justify-between">
          <span>Evidence activity is currently unavailable from the storage subsystem.</span>
          <a routerLink="/reports/evidence" class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs inline-flex items-center gap-1">Open Evidence Portal</a>
        </div>
      } @else if (!rs.hasEvidenceActivity()) {
        <!-- State: AVAILABLE_EMPTY -->
        <div class="p-6 rounded-xl bg-white border border-slate-200 text-center text-xs text-slate-500 shadow-2xs">
          No recent evidence manifests or verification activity recorded.
        </div>
      } @else {
        <!-- State: AVAILABLE_WITH_DATA (Clean Table matching standard AKAAL list) -->
        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Activity / Evidence</th>
                <th class="py-3 px-4">Subject</th>
                <th class="py-3 px-4 hidden md:table-cell">Occurred</th>
                <th class="py-3 px-4">Integrity State</th>
                <th class="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (item of rs.evidenceActivity(); track item.id) {
                <tr class="hover:bg-slate-50/80 transition-colors group cursor-pointer" (click)="openEvidence(item.id)">
                  
                  <td class="py-3.5 px-4">
                    <div class="flex items-center gap-2.5">
                      <div class="w-6 h-6 rounded-md bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
                        <app-lucide-icon [name]="getActivityIcon(item.activity_type)" [size]="13"></app-lucide-icon>
                      </div>
                      <div class="flex flex-col gap-0.5">
                        <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                          {{ rs.formatText(item.activity_type) }}
                        </span>
                        <span class="text-[11px] text-slate-500 font-medium">
                          {{ item.artifact_type }}
                        </span>
                      </div>
                    </div>
                  </td>

                  <td class="py-3.5 px-4 text-slate-700 font-medium">
                    {{ item.subject_name }}
                  </td>

                  <td class="py-3.5 px-4 text-slate-500 hidden md:table-cell font-mono text-[11px]">
                    {{ item.occurred_at | date:'yyyy-MM-dd HH:mm' }}
                  </td>

                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': item.verification_status === 'VERIFIED',
                        'bg-amber-50 text-amber-800 border border-amber-200': item.verification_status === 'PENDING',
                        'bg-slate-100 text-slate-700': item.verification_status === 'UNAVAILABLE' || item.verification_status === 'UNVERIFIED'
                      }">
                      {{ item.verification_status }}
                    </span>
                  </td>

                  <td class="py-3.5 px-4 text-right">
                    <button
                      type="button"
                      (click)="openEvidence(item.id); $event.stopPropagation()"
                      class="px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs border border-slate-200 transition-colors cursor-pointer">
                      Inspect Proof
                    </button>
                  </td>

                </tr>
              }
            </tbody>
          </table>
        </div>
      }

    </div>
  `
})
export class ReportsEvidenceActivityComponent {
  public rs = inject(ReportsService);
  private router = inject(Router);

  public getActivityIcon(activityType: string): string {
    switch (activityType) {
      case 'MANIFEST_GENERATED': return 'file-check';
      case 'INTEGRITY_VERIFIED': return 'shield-check';
      case 'DIGEST_VERIFIED': return 'lock';
      case 'ATTESTATION_RECORDED': return 'award';
      default: return 'package';
    }
  }

  public openEvidence(evidenceId: string): void {
    this.router.navigate(['/reports/evidence'], { queryParams: { evidenceId } });
  }
}
