import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BrandLogoComponent } from '../../shared/components/brand-logo/brand-logo.component';
import { LifecycleService } from '../../core/lifecycle/lifecycle.service';

@Component({
  selector: 'app-splash',
  standalone: true,
  imports: [CommonModule, BrandLogoComponent],
  template: `
    <div class="w-full h-full flex flex-col items-center justify-center bg-app text-text-primary">
      <app-brand-logo [size]="120" />
      <h1 class="text-3xl font-heading font-bold mt-6 tracking-tight">AKAAL</h1>
      <p class="text-text-secondary text-sm mt-2 font-sans">Enterprise Database Migration Platform</p>
      <div class="w-48 h-1 bg-border-subtle rounded-full overflow-hidden mt-8">
        <div class="w-full h-full bg-accent animate-pulse"></div>
      </div>
    </div>
  `,
})
export class SplashComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly lifecycle = inject(LifecycleService);

  ngOnInit(): void {
    // Initial bootstrap check
    setTimeout(() => {
      this.lifecycle.completeSplash(false);
      this.router.navigate(['/setup']);
    }, 1500);
  }
}
