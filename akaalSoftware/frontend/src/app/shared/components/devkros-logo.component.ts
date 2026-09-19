import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SettingsService } from '../../modules/settings/services/settings.service';

@Component({
  selector: 'app-devkros-logo',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div 
      class="inline-flex items-center justify-center shrink-0 select-none"
      [style.width.px]="numericSize"
      [style.height.px]="numericSize">
      @if (variant === 'dark') {
        <img 
          src="assets/images/devkros-logo-dark.png" 
          [style.width.px]="numericSize" 
          [style.height.px]="numericSize" 
          alt="DevKros Logo"
          class="object-contain" />
      } @else if (variant === 'light') {
        <img 
          src="assets/images/devkros-logo-light.png" 
          [style.width.px]="numericSize" 
          [style.height.px]="numericSize" 
          alt="DevKros Logo"
          class="object-contain" />
      } @else {
        <!-- Dark Mode: Pure White Logo, Light Mode: Black Logo -->
        @if (isDark()) {
          <img 
            src="assets/images/devkros-logo-light.png" 
            [style.width.px]="numericSize" 
            [style.height.px]="numericSize" 
            alt="DevKros Logo"
            class="object-contain brightness-200" />
        } @else {
          <img 
            src="assets/images/devkros-logo-dark.png" 
            [style.width.px]="numericSize" 
            [style.height.px]="numericSize" 
            alt="DevKros Logo"
            class="object-contain" />
        }
      }
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
