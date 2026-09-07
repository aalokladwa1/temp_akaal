import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { AttentionItem } from '../validation-workstation.models';

@Component({
  selector: 'app-workstation-attention-panel',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
      
      <!-- Panel Header -->
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600" />
          <h2 class="text-sm font-bold text-slate-900 tracking-tight font-heading">
            Operational Attention &amp; Findings
          </h2>
        </div>
        <span class="text-[11px] font-mono font-medium text-slate-500">
          {{ store.state().attentionItems.length }} Item(s)
        </span>
      </div>

      <!-- Items List or Calm Empty State -->
      @if (store.state().attentionItems.length === 0) {
        <div class="p-6 rounded-xl bg-slate-50/50 border border-slate-200/80 flex items-center gap-3 text-slate-600 text-xs">
          <app-lucide-icon name="check-circle" [size]="18" class="text-emerald-600 shrink-0" />
          <div class="flex flex-col">
            <span class="font-bold text-slate-800">No active attention items detected</span>
            <span class="text-slate-500 text-[11px] mt-0.5">
              Target correspondence, schema alignment, and runtime baseline integrity are satisfied with zero outstanding blockers.
            </span>
          </div>
        </div>
      } @else {
        <div class="flex flex-col gap-3">
          @for (item of store.state().attentionItems; track item.id) {
            <div class="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                 [ngClass]="getItemBgClasses(item.severity)">
              
              <div class="flex items-start gap-3">
                <div [ngClass]="getSeverityIconBg(item.severity)"
                     class="w-7 h-7 rounded flex items-center justify-center shrink-0 border">
                  <app-lucide-icon [name]="getSeverityIcon(item.severity)" [size]="14" [class]="getSeverityIconColor(item.severity)" />
                </div>
                
                <div class="flex flex-col gap-0.5">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-xs font-bold text-slate-900">{{ item.title }}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border"
                          [ngClass]="getSeverityBadgeClasses(item.severity)">
                      {{ item.severity }}
                    </span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-white text-slate-600 border border-slate-200">
                      {{ formatCategory(item.category) }}
                    </span>
                  </div>
                  <p class="text-xs text-slate-600 mt-0.5">{{ item.description }}</p>
                  @if (item.location) {
                    <span class="font-mono text-[11px] text-slate-500 mt-1">Location: {{ item.location }}</span>
                  }
                </div>
              </div>

              <!-- Quick Action Link -->
              <button
                type="button"
                (click)="store.setActiveTab('discrepancies')"
                class="px-3 py-1.5 rounded text-xs font-semibold bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 shrink-0 self-start sm:self-center transition-colors cursor-pointer">
                View in Discrepancies
              </button>
            </div>
          }
        </div>
      }
    </section>
  `
})
export class WorkstationAttentionPanelComponent {
  readonly store = inject(ValidationWorkstationService);

  formatCategory(category: string): string {
    switch (category) {
      case 'difference': return 'Data Divergence';
      case 'missing_target': return 'Missing Records';
      case 'correspondence': return 'Schema Mapping';
      case 'baseline': return 'Baseline Drift';
      default: return category;
    }
  }

  getItemBgClasses(severity: string): string {
    switch (severity) {
      case 'blocker': return 'bg-rose-50/40 border-rose-200/80';
      case 'warning': return 'bg-amber-50/40 border-amber-200/80';
      case 'info': return 'bg-blue-50/40 border-blue-200/80';
      default: return 'bg-slate-50 border-slate-200';
    }
  }

  getSeverityIconBg(severity: string): string {
    switch (severity) {
      case 'blocker': return 'bg-rose-100 border-rose-200';
      case 'warning': return 'bg-amber-100 border-amber-200';
      case 'info': return 'bg-blue-100 border-blue-200';
      default: return 'bg-slate-100 border-slate-200';
    }
  }

  getSeverityIconColor(severity: string): string {
    switch (severity) {
      case 'blocker': return 'text-rose-700';
      case 'warning': return 'text-amber-700';
      case 'info': return 'text-blue-700';
      default: return 'text-slate-600';
    }
  }

  getSeverityIcon(severity: string): string {
    switch (severity) {
      case 'blocker': return 'shield-alert';
      case 'warning': return 'alert-triangle';
      case 'info': return 'info';
      default: return 'info';
    }
  }

  getSeverityBadgeClasses(severity: string): string {
    switch (severity) {
      case 'blocker': return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'warning': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'info': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  }
}
