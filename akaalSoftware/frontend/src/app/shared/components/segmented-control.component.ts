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
    <div class="inline-flex p-1 bg-slate-100/90 border border-slate-200/60 rounded-xl items-center gap-1 select-none">
      @for (opt of options; track opt.value) {
        <button
          type="button"
          (click)="select(opt.value)"
          class="px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-2 cursor-pointer"
          [class.bg-white]="value === opt.value"
          [class.font-bold]="value === opt.value"
          [class.text-slate-900]="value === opt.value"
          [class.text-slate-600]="value !== opt.value"
          [class.font-medium]="value !== opt.value"
          [class.hover:text-slate-900]="value !== opt.value">
          @if (opt.icon) {
            <app-lucide-icon [name]="opt.icon" [size]="14" [class]="value === opt.value ? 'text-blue-600' : 'text-slate-500'"></app-lucide-icon>
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
