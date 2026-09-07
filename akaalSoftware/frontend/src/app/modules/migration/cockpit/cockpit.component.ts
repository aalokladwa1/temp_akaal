import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { CockpitStoreService } from '../../../core/services/cockpit-store.service';
import { CockpitHeaderComponent } from './components/cockpit-header.component';
import { CockpitStatusPulseComponent } from './components/cockpit-status-pulse.component';
import { CockpitInterventionComponent } from './components/cockpit-intervention.component';
import { CockpitDagViewComponent } from './components/cockpit-dag-view.component';
import { CockpitCurrentActivityComponent } from './components/cockpit-current-activity.component';
import { CockpitEngineHealthComponent } from './components/cockpit-engine-health.component';
import { CockpitWorkbenchComponent } from './components/cockpit-workbench.component';
import { CockpitExecutionContextComponent } from './components/cockpit-execution-context.component';
import { CockpitEventsDockComponent } from './components/cockpit-events-dock.component';

@Component({
  selector: 'app-cockpit',
  standalone: true,
  imports: [
    CommonModule,
    CockpitHeaderComponent,
    CockpitStatusPulseComponent,
    CockpitInterventionComponent,
    CockpitDagViewComponent,
    CockpitCurrentActivityComponent,
    CockpitEngineHealthComponent,
    CockpitWorkbenchComponent,
    CockpitExecutionContextComponent,
    CockpitEventsDockComponent
  ],
  template: `
    <div class="min-h-screen bg-slate-50/50 flex flex-col font-sans text-slate-800 antialiased selection:bg-slate-900 selection:text-white pb-16">
      
      <!-- Sticky Navigation / Command Header -->
      <app-cockpit-header />

      <!-- Main Operational Surface -->
      <main class="max-w-[1600px] w-full mx-auto px-6 pt-6 flex flex-col gap-6">
        
        <!-- Zone 1: 5-Second Status Glance, Metric Ribbon & Workload Progress -->
        <app-cockpit-status-pulse />

        <!-- Zone 2: Operator Intervention Banner (Appears only on Barrier / Failure / Hold / Degraded) -->
        <app-cockpit-intervention />

        <!-- Zone 3: Page-Native Runtime DAG Visualizer -->
        <app-cockpit-dag-view />

        <!-- Zone 4: Active Physical Execution Snapshot -->
        <app-cockpit-current-activity />

        <!-- Zone 5: Dynamic Operational Domain Workbench (M1–M7 adaptive tabs) -->
        <app-cockpit-workbench />

        <!-- Zone 6: PREVIOUS ➔ NOW ➔ NEXT Execution Narrative -->
        <app-cockpit-execution-context />

        <!-- Zone 7: Explainable Engine Subsystem Health Grid -->
        <app-cockpit-engine-health />

        <!-- Zone 8: Chronological Audit Events & Diagnostic Dock -->
        <app-cockpit-events-dock />

      </main>
    </div>
  `
})
export class CockpitComponent implements OnInit {
  public store = inject(CockpitStoreService);
  private route = inject(ActivatedRoute);

  ngOnInit(): void {
    // Check for route param or query param migration ID
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id) {
        this.store.loadMigration(id);
      }
    });

    this.route.queryParamMap.subscribe(queryParams => {
      const id = queryParams.get('id');
      if (id) {
        this.store.loadMigration(id);
      }
    });
  }
}
