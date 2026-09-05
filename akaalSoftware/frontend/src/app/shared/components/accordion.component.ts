import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from './lucide-icon.component';

@Component({
  selector: 'app-accordion',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="border border-slate-200 rounded-lg overflow-visible bg-slate-50/40 select-none">
      <button
        type="button"
        (click)="toggle()"
        class="w-full px-3.5 py-2.5 flex items-center justify-between text-xs font-semibold text-slate-800 hover:bg-slate-100/60 cursor-pointer transition-colors">
        <div class="flex items-center gap-2">
          <app-lucide-icon
            name="chevron-down"
            [size]="14"
            class="text-slate-500 transition-transform duration-150"
            [class.-rotate-90]="!isOpen"></app-lucide-icon>
          @if (icon) {
            <app-lucide-icon [name]="icon" [size]="14" class="text-slate-500"></app-lucide-icon>
          }
          <span>{{ title }}</span>
          @if (badge) {
            <span class="px-1.5 py-0.2 text-[9px] font-mono font-bold bg-slate-100 text-slate-600 rounded">
              {{ badge }}
            </span>
          }
        </div>
        @if (subtitle) {
          <span class="text-[11px] text-slate-400 font-normal">{{ subtitle }}</span>
        }
      </button>

      @if (isOpen) {
        <div class="p-3.5 border-t border-slate-200 bg-white flex flex-col gap-3 animate-in fade-in duration-100 overflow-visible">
          <ng-content></ng-content>
        </div>
      }
    </div>
  `
})
export class AccordionComponent {
  @Input() title: string = '';
  @Input() subtitle?: string;
  @Input() icon?: string;
  @Input() badge?: string;
  @Input() isOpen: boolean = false;
  @Output() isOpenChange = new EventEmitter<boolean>();

  public toggle(): void {
    this.isOpen = !this.isOpen;
    this.isOpenChange.emit(this.isOpen);
  }
}
