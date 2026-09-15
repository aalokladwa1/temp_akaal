import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TemplatesHomeComponent } from './templates-home.component';

@Component({
  selector: 'app-template-browser',
  standalone: true,
  imports: [CommonModule, TemplatesHomeComponent],
  template: `<app-templates-home></app-templates-home>`
})
export class TemplateBrowserComponent {}
