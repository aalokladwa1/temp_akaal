import { Component, Input, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { PendingApproval } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-pending-approvals',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between gap-6 shadow-xs h-full flex-1">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="shield-check" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Pending Approvals</h2>
        </div>
        <span class="text-xs text-slate-500 font-medium">{{ approvals.length }} waiting</span>
      </div>

      <!-- Approvals List / Empty State -->
      @if (approvals.length === 0) {
        <div class="py-8 flex flex-col items-center justify-center text-center gap-2 my-auto">
          <div class="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
            <app-lucide-icon name="circle-check" [size]="18"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800">No approvals waiting</span>
          <p class="text-[11px] text-slate-500 font-medium max-w-xs">All four-eyes quorum barriers are currently satisfied.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-200/80">
          @for (app of approvals; track app.id) {
            <div class="py-3 first:pt-0 last:pb-0 flex items-center justify-between gap-4 flex-wrap">
              <div class="flex flex-col gap-0.5">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-slate-900">{{ app.migrationName }}</span>
                  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] bg-amber-50 text-amber-700 border border-amber-200 font-bold select-none">
                    <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                    <span>Quorum {{ app.quorum }}</span>
                  </span>
                </div>
                <span class="text-[11px] text-slate-500 font-medium">{{ app.operation }} &bull; By {{ app.requester }} ({{ app.requestedAt }})</span>
              </div>

              <button
                type="button"
                (click)="goToMigration()"
                class="h-8 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer inline-flex items-center gap-1.5 select-none">
                <span>Review</span>
              </button>
            </div>
          }
        </div>
      }

      <div class="pt-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 font-medium">
        <span>Governance: Four-Eyes Principle</span>
        <span class="text-slate-500 font-semibold">Enforced</span>
      </div>

    </div>
  `
})
export class PendingApprovalsComponent {
  @HostBinding('class') public hostClass = 'flex flex-col h-full flex-1';
  @Input() public approvals: PendingApproval[] = [];

  constructor(private router: Router) {}

  public goToMigration(): void {
    this.router.navigate(['/migration']);
  }
}
