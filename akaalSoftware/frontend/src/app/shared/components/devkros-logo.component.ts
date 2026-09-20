import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SettingsService } from '../../modules/settings/services/settings.service';

@Component({
  selector: 'app-devkros-logo',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div 
      class="inline-flex items-center justify-center shrink-0 select-none overflow-visible"
      [style.width.px]="numericSize"
      [style.height.px]="numericHeight"
      [style.color]="logoColor">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 861 810"
        [attr.width]="numericSize"
        [attr.height]="numericHeight"
        fill="currentColor"
        class="w-full h-full object-contain overflow-visible"
        preserveAspectRatio="xMidYMid meet">
        <path
          fill-rule="evenodd"
          d="M 4 4 L 4 269 L 147 415 L 4 550 L 3 804 L 269 803 L 632 487 L 748 599 L 747 713 L 627 714 L 526 623 L 453 687 L 572 804 L 856 803 L 855 555 L 709 412 L 857 268 L 856 3 L 587 3 L 229 346 L 111 228 L 111 111 L 231 109 L 329 207 L 407 133 L 275 3 Z M 750 111 L 749 229 L 639 335 L 539 237 L 460 312 L 558 413 L 225 714 L 111 713 L 111 590 L 225 486 L 322 582 L 402 508 L 306 413 L 631 110 Z" />
      </svg>
    </div>
  `
})
export class DevkrosLogoComponent {
  public settings = inject(SettingsService, { optional: true });
  @Input() size: number | string = 24;
  @Input() variant: 'auto' | 'dark' | 'light' = 'auto';

  get numericSize(): number {
    if (typeof this.size === 'number') return this.size;
    const parsed = parseInt(this.size, 10);
    return isNaN(parsed) ? 24 : parsed;
  }

  get numericHeight(): number {
    return Math.round(this.numericSize * (810 / 861));
  }

  get logoColor(): string {
    if (this.variant === 'light') return '#ffffff';
    if (this.variant === 'dark') return '#0f172a';
    return this.isDark() ? '#ffffff' : '#0f172a';
  }

  isDark(): boolean {
    if (this.settings) {
      return this.settings.effectiveTheme() === 'dark';
    }
    if (typeof document !== 'undefined') {
      return document.documentElement.classList.contains('dark') ||
             document.documentElement.getAttribute('data-theme') === 'dark';
    }
    return false;
  }
}
