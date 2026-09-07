import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step8GovernanceStoreService } from '../../../../core/services/step8-governance-store.service';
import { GovernanceActivityEvent } from './step8-governance.models';

@Component({
  selector: 'app-step8-activity-drawer',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <!-- Overlay Backdrop (zero blur) -->
    <div
      class="fixed inset-0 z-40 bg-slate-900/40 animate-in fade-in duration-100"
      (click)="store.closeActivityDrawer()">
    </div>

    <!-- Slide-over Drawer Surface (Right-aligned, w-[480px], flat border) -->
    <aside
      role="dialog"
      aria-modal="true"
      aria-label="Governance Activity Audit Timeline"
      class="fixed right-0 top-0 bottom-0 z-50 w-[480px] bg-white border-l border-slate-200 flex flex-col justify-between font-sans text-xs select-none animate-in slide-in-from-right duration-150"
      (click)="$event.stopPropagation()">
      
      <!-- Drawer Header -->
      <header class="p-4 border-b border-slate-200 flex items-start justify-between gap-3 bg-slate-50 shrink-0">
        <div class="flex flex-col gap-1 min-w-0">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="history" [size]="16" class="text-slate-600"></app-lucide-icon>
            <span class="font-bold text-slate-900 text-sm">Governance Activity Timeline</span>
          </div>
          <span class="text-[11px] text-slate-500 font-medium">Immutable audit trail of evaluations &amp; approvals</span>
        </div>

        <button
          type="button"
          (click)="store.closeActivityDrawer()"
          class="w-7 h-7 rounded border border-slate-200 bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-900 flex items-center justify-center cursor-pointer transition-colors shrink-0"
          title="Close drawer">
          <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
        </button>
      </header>

      <!-- Drawer Scrollable Body -->
      <div class="p-5 flex-1 overflow-y-auto flex flex-col gap-4">
        
        <div class="flex flex-col gap-3 relative before:absolute before:left-3.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
          @for (event of store.activityEvents(); track event.id) {
            <div class="flex items-start gap-3 relative z-10">
              
              <!-- Timeline Dot -->
              <div class="w-7 h-7 rounded-full border flex items-center justify-center shrink-0 bg-white"
                [class.border-blue-300]="event.eventType === 'EVALUATION'"
                [class.text-blue-600]="event.eventType === 'EVALUATION'"
                [class.border-emerald-300]="event.eventType === 'APPROVAL'"
                [class.text-emerald-600]="event.eventType === 'APPROVAL'"
                [class.border-rose-300]="event.eventType === 'REJECTION'"
                [class.text-rose-600]="event.eventType === 'REJECTION'"
                [class.border-amber-300]="event.eventType === 'ACKNOWLEDGEMENT'"
                [class.text-amber-600]="event.eventType === 'ACKNOWLEDGEMENT'">
                <app-lucide-icon
                  [name]="event.eventType === 'APPROVAL' ? 'check' : (event.eventType === 'REJECTION' ? 'x' : (event.eventType === 'ACKNOWLEDGEMENT' ? 'alert-triangle' : 'activity'))"
                  [size]="13">
                </app-lucide-icon>
              </div>

              <!-- Event Card -->
              <div class="flex-1 bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-1.5">
                <div class="flex items-center justify-between gap-2 border-b border-slate-200/60 pb-1">
                  <span class="font-bold text-slate-900 text-xs">{{ event.summary }}</span>
                  <span class="text-[10px] text-slate-400 font-mono shrink-0">{{ formatTime(event.timestamp) }}</span>
                </div>

                <div class="flex items-center gap-2 text-[11px] text-slate-600">
                  <span class="font-semibold text-slate-800">{{ event.actorName }}</span>
                  <span class="text-slate-400">&bull;</span>
                  <span class="text-slate-500 font-mono text-[10.5px]">{{ event.actorRole }}</span>
                </div>

                @if (event.details) {
                  <p class="text-[11px] text-slate-600 m-0 leading-relaxed bg-white p-2 rounded border border-slate-200/70">
                    {{ event.details }}
                  </p>
                }
              </div>

            </div>
          }
        </div>

      </div>

      <!-- Drawer Footer Actions -->
      <footer class="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end shrink-0">
        <button
          type="button"
          (click)="store.closeActivityDrawer()"
          class="h-8 px-4 text-xs font-semibold text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-100 transition-colors cursor-pointer">
          Close
        </button>
      </footer>

    </aside>
  `
})
export class Step8ActivityDrawerComponent {
  public store = inject(Step8GovernanceStoreService);

  public formatTime(iso: string): string {
    try {
      return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return iso;
    }
  }
}
