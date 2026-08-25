import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { LifecycleService } from '../../core/lifecycle/lifecycle.service';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full h-full flex items-center justify-center p-8 bg-app">
      <div class="glass-panel max-w-md w-full p-8 flex flex-col items-center text-center">
        <h2 class="text-2xl font-heading font-bold text-text-primary">Sign in to AKAAL</h2>
        <p class="text-text-secondary text-sm mt-2">Enter credentials or authenticate via Enterprise SSO.</p>
        <button (click)="signIn()" class="mt-8 w-full py-2.5 bg-accent hover:bg-accent-hover text-white rounded-md font-medium transition-colors">
          Sign In
        </button>
      </div>
    </div>
  `,
})
export class AuthComponent {
  private readonly router = inject(Router);
  private readonly lifecycle = inject(LifecycleService);

  signIn(): void {
    this.lifecycle.completeLogin();
    this.router.navigate(['/app']);
  }
}
