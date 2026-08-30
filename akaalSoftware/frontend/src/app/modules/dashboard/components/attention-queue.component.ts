import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AttentionItem } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-attention-queue',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200/90 flex flex-col gap-6 shadow-xs h-full">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="triangle-alert" [size]="20" class="text-amber-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Needs Your Attention</h2>
        </div>
        <span class="px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60 text-xs font-bold">
          {{ items.length }}
        </span>
      </div>

      <!-- Attention Items List -->
      @if (items.length === 0) {
        <div class="py-14 flex flex-col items-center justify-center text-center gap-3">
          <div class="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <app-lucide-icon name="circle-check" [size]="24"></app-lucide-icon>
          </div>
          <span class="text-sm font-bold text-slate-900">Nothing needs your attention</span>
          <p class="text-xs text-slate-600 font-medium max-w-xs">No actionable migration conditions are currently reported.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-100">
          @for (item of items; track item.id) {
            <div class="py-4 first:pt-0 last:pb-0 flex flex-col gap-2.5">
              
              <div class="flex items-start justify-between gap-3">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800">
                    {{ item.severity }}
                  </span>
                  <span class="text-xs font-bold text-slate-900">{{ item.title }}</span>
                </div>
                <span class="text-[11px] text-slate-500 font-medium shrink-0">{{ item.timestamp }}</span>
              </div>

              <p class="text-xs text-slate-700 leading-relaxed font-medium">
                {{ item.description }}
              </p>

              @if (item.actionLabel) {
                <div class="flex justify-end pt-1">
                  <button
                    type="button"
                    (click)="handleAction(item)"
                    class="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-2xs transition-colors cursor-pointer flex items-center gap-1.5">
                    <span>{{ item.actionLabel }}</span>
                    <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
                  </button>
                </div>
              }

            </div>
          }
        </div>
      }

    </div>
  `
})
export class AttentionQueueComponent {
  @Input() public items: AttentionItem[] = [];

  constructor(private router: Router) {}

  public handleAction(item: AttentionItem): void {
    this.router.navigate(['/migration']);
  }
}
