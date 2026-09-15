import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-monitoring-landing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-8 text-center text-slate-500 text-sm font-medium">
      Monitoring Module (Ready for Reconstruction)
    </div>
  `
})
export class MonitoringLandingComponent {}

