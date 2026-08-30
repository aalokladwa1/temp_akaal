import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { PendingApproval } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-pending-approvals',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200/90 flex flex-col gap-6 shadow-xs h-full">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="shield-check" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Pending Approvals</h2>
        </div>
        <span class="text-xs text-slate-600 font-semibold">{{ approvals.length }} waiting</span>
      </div>

      <!-- Approvals List -->
      @if (approvals.length === 0) {
        <div class="py-12 flex flex-col items-center justify-center text-center gap-2">
          <div class="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center text-slate-500">
            <app-lucide-icon name="check" [size]="20"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800">No approvals waiting</span>
          <p class="text-[11px] text-slate-600 font-medium">All four-eyes quorum barriers are currently satisfied.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-100">
          @for (app of approvals; track app.id) {
            <div class="py-3.5 first:pt-0 last:pb-0 flex items-center justify-between gap-4 flex-wrap">
              <div class="flex flex-col gap-1">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-slate-900">{{ app.migrationName }}</span>
                  <span class="px-2 py-0.5 rounded text-[10px] bg-amber-50 text-amber-700 border border-amber-200/60 font-bold">
                    {{ app.quorum }}
                  </span>
                </div>
                <span class="text-xs text-slate-600 font-medium">{{ app.operation }} &bull; By {{ app.requester }} ({{ app.requestedAt }})</span>
              </div>

              <button
                type="button"
                (click)="goToMigration()"
                class="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-2xs transition-colors cursor-pointer">
                Review
              </button>
            </div>
          }
        </div>
      }

    </div>
  `
})
export class PendingApprovalsComponent {
  @Input() public approvals: PendingApproval[] = [];

  constructor(private router: Router) {}

  public goToMigration(): void {
    this.router.navigate(['/migration']);
  }
}
