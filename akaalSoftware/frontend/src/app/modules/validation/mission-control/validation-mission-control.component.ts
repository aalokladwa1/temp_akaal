import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationComponent } from '../workstation/validation-workstation.component';

/**
 * Legacy wrapper forwarding to the canonical ValidationWorkstationComponent (Mandate 22).
 * Eliminates duplicate authorities and ensures consistent presentation.
 */
@Component({
  selector: 'app-validation-mission-control',
  standalone: true,
  imports: [CommonModule, ValidationWorkstationComponent],
  template: `<app-validation-workstation />`
})
export class ValidationMissionControlComponent {}
