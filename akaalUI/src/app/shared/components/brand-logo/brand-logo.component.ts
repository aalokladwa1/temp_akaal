import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-brand-logo',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative flex items-center justify-center" [style.width.px]="size()" [style.height.px]="size()">
      <img src="assets/branding/akaal-logo.svg" alt="AKAAL 3-Ring Logo" class="w-full h-full object-contain" />
    </div>
  `,
})
export class BrandLogoComponent {
  public size = input<number>(64);
}
