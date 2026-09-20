import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ShellComponent } from './modules/shell/shell.component';
import { DevkrosLaunchSplashComponent } from './shared/components/devkros-launch-splash.component';
import { SettingsService } from './modules/settings/services/settings.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ShellComponent, DevkrosLaunchSplashComponent],
  template: `
    <app-devkros-launch-splash></app-devkros-launch-splash>
    <app-shell></app-shell>
  `
})
export class AppComponent {
  private settings = inject(SettingsService);
}
