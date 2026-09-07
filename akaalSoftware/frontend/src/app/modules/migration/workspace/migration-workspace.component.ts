import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitComponent } from '../cockpit/cockpit.component';

@Component({
  selector: 'app-migration-workspace',
  standalone: true,
  imports: [
    CommonModule,
    CockpitComponent
  ],
  template: `
    <app-cockpit></app-cockpit>
  `
})
export class MigrationWorkspaceComponent {}
