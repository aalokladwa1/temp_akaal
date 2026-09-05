import { Component, Input, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AttentionItem } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-attention-queue',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between gap-6 shadow-xs h-full flex-1">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="triangle-alert" [size]="20" class="text-amber-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Needs Your Attention</h2>
        </div>
        <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-xs font-bold select-none">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
          <span>{{ items.length }}</span>
        </span>
      </div>

      <!-- Attention Items List -->
      @if (items.length === 0) {
        <div class="py-10 flex flex-col items-center justify-center text-center gap-2 my-auto">
          <div class="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
            <app-lucide-icon name="circle-check" [size]="20"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800">Nothing needs your attention</span>
          <p class="text-[11px] text-slate-500 font-medium max-w-xs">No actionable migration conditions are currently reported.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-200/80">
          @for (item of items; track item.id) {
            <div class="py-3.5 first:pt-0 last:pb-0 flex flex-col gap-2">
              
              <div class="flex items-start justify-between gap-3">
                <div class="flex items-center gap-2">
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-200">
                    <span class="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                    <span>{{ item.severity }}</span>
                  </span>
                  <span class="text-xs font-bold text-slate-900">{{ item.title }}</span>
                </div>
                <span class="text-[11px] font-mono text-slate-400 font-medium shrink-0">{{ item.timestamp }}</span>
              </div>

              <p class="text-xs text-slate-600 leading-relaxed font-medium">
                {{ item.description }}
              </p>

              @if (item.actionLabel) {
                <div class="flex justify-end pt-1">
                  <button
                    type="button"
                    (click)="handleAction(item)"
                    class="h-8 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer flex items-center gap-1.5 select-none">
                    <span>{{ item.actionLabel }}</span>
                    <app-lucide-icon name="chevron-right" [size]="13"></app-lucide-icon>
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
  @HostBinding('class') public hostClass = 'flex flex-col h-full flex-1';
  @Input() public items: AttentionItem[] = [];

  constructor(private router: Router) {}

  public handleAction(item: AttentionItem): void {
    this.router.navigate(['/migration']);
  }
}
