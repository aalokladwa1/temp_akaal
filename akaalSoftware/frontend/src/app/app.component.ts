import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ShellComponent } from './modules/shell/shell.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ShellComponent],
  template: `<app-shell></app-shell>`
})
export class AppComponent {}
