import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { LifecycleService } from '../../core/lifecycle/lifecycle.service';

@Component({
  selector: 'app-first-admin',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full h-full flex items-center justify-center p-8 bg-app">
      <div class="glass-panel max-w-xl w-full p-8 flex flex-col">
        <h2 class="text-2xl font-heading font-bold text-text-primary">Create Root Administrator</h2>
        <p class="text-text-secondary text-sm mt-2">Configure primary administrator account and generate emergency recovery keys.</p>
        <button (click)="proceed()" class="mt-8 px-6 py-2.5 bg-accent hover:bg-accent-hover text-white rounded-md font-medium self-end transition-colors">
          Initialize System & Sign In
        </button>
      </div>
    </div>
  `,
})
export class FirstAdminComponent {
  private readonly router = inject(Router);
  private readonly lifecycle = inject(LifecycleService);

  proceed(): void {
    this.lifecycle.completeFirstAdmin();
    this.router.navigate(['/login']);
  }
}
