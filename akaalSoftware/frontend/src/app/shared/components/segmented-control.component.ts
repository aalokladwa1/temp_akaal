import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from './lucide-icon.component';

export interface SegmentedControlOption {
  label: string;
  value: any;
  icon?: string;
}

@Component({
  selector: 'app-segmented-control',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="inline-flex p-1 bg-slate-100/90 dark:bg-[#141517] border border-slate-200/60 dark:border-white/[0.08] rounded-xl items-center gap-1 select-none">
      @for (opt of options; track opt.value) {
        <button
          type="button"
          (click)="select(opt.value)"
          class="px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-2 cursor-pointer"
          [ngClass]="{
            'bg-white dark:bg-[#1e2024] font-bold text-slate-900 dark:text-slate-100 shadow-2xs': value === opt.value,
            'text-slate-600 dark:text-slate-400 font-medium hover:text-slate-900 dark:hover:text-slate-200': value !== opt.value
          }">
          @if (opt.icon) {
            <app-lucide-icon [name]="opt.icon" [size]="14" [class]="value === opt.value ? 'text-blue-600 dark:text-blue-400' : 'text-slate-500 dark:text-slate-400'"></app-lucide-icon>
          }
          <span>{{ opt.label }}</span>
        </button>
      }
    </div>
  `
})
export class SegmentedControlComponent {
  @Input() options: SegmentedControlOption[] = [];
  @Input() value: any;
  @Output() valueChange = new EventEmitter<any>();

  public select(val: any): void {
    if (this.value !== val) {
      this.value = val;
      this.valueChange.emit(val);
    }
  }
}
