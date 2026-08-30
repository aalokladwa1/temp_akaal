import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-history-view',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150">
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider">Execution Attempt Timeline</h3>
        
        <div class="divide-y divide-slate-100 text-xs">
          <div class="py-3 first:pt-0 flex items-start justify-between">
            <div class="flex flex-col gap-0.5">
              <span class="font-bold text-slate-900">Attempt #2 • Streaming Active</span>
              <span class="text-slate-500">Dispatched on cluster-worker-01 • Plan v2.1.0</span>
            </div>
            <span class="text-slate-400">Started today at 06:00 UTC</span>
          </div>

          <div class="py-3 flex items-start justify-between">
            <div class="flex flex-col gap-0.5">
              <span class="font-bold text-slate-700">Attempt #1 • Initial Snapshot Succeeded</span>
              <span class="text-slate-500">148.2M records bulk loaded • Plan v1.0.0</span>
            </div>
            <span class="text-slate-400">Completed yesterday at 22:30 UTC</span>
          </div>
        </div>
      </div>
    </div>
  `
})
export class HistoryViewComponent {
  public ms = inject(MigrationUiService);
}
