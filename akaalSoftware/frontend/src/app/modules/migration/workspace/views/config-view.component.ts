import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';

@Component({
  selector: 'app-config-view',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150">
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider">Effective Resolved Configuration</h3>
        <div class="divide-y divide-slate-100 text-xs">
          @for (group of ms.wizardConfigDomains(); track group.id) {
            <div class="py-3 first:pt-0 flex flex-col gap-2">
              <span class="font-bold text-blue-700">Domain {{ group.id }} • {{ group.name }}</span>
              <div class="grid grid-cols-2 gap-2 text-slate-700">
                @for (f of group.fields; track f.id) {
                  <div class="flex justify-between p-2 rounded-lg bg-slate-50">
                    <span class="text-slate-500">{{ f.label }}:</span>
                    <span class="font-semibold text-slate-900">{{ f.effectiveValue }}</span>
                  </div>
                }
              </div>
            </div>
          }
        </div>
      </div>
    </div>
  `
})
export class ConfigViewComponent {
  public ms = inject(MigrationUiService);
}
