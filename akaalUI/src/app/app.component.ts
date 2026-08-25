import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ThemeService } from './core/theme/theme.service';
import { LifecycleService } from './core/lifecycle/lifecycle.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule],
  template: `
    <main class="w-screen h-screen overflow-hidden bg-app text-text-primary flex flex-col font-sans select-none">
      <router-outlet></router-outlet>
    </main>
  `,
})
export class AppComponent {
  private readonly themeService = inject(ThemeService);
  public readonly lifecycle = inject(LifecycleService);
}
