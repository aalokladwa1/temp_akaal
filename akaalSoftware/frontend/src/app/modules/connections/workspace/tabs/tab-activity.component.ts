import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-tab-activity',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (ws.connection(); as conn) {
      <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
        
        <!-- Top Header & Filter Controls -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-3">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
              Activity &amp; Governance History
            </h2>
            <p class="text-xs text-slate-500 font-normal">
              Chronological log of configuration modifications, verification tests, secret rotations, and lifecycle actions.
            </p>
          </div>
        </div>

        <!-- Truthful Unavailable State (B-2.2-08) -->
        <div class="p-12 text-center bg-white border border-slate-200 rounded-xl flex flex-col items-center justify-center gap-3 shadow-2xs">
          <div class="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center mx-auto mb-1 text-slate-400">
            <app-lucide-icon name="history" [size]="22"></app-lucide-icon>
          </div>
          <span class="text-sm font-bold text-slate-900">Connection activity is currently unavailable.</span>
          <p class="text-xs text-slate-500 max-w-md mx-auto">
            Activity audit history and timeline tracking require an active connection service session.
          </p>
        </div>

      </div>
    }
  `
})
export class TabActivityComponent {
  public ws = inject(ConnectionWorkspaceService);
}
