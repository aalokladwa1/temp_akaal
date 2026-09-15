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
    <div class="min-h-screen bg-slate-50/50 flex flex-col font-sans text-slate-800 antialiased selection:bg-blue-100 selection:text-blue-900 pb-16">
      
      <!-- Sticky Navigation / Command Header -->
      <app-cockpit-header />

      <!-- Main Operational Surface -->
      <main class="max-w-[1600px] w-full mx-auto px-6 pt-6 flex flex-col gap-6">
        
        <!-- Top Status Ribbon & Workload Progress Glance -->
        <app-cockpit-status-pulse />

        <!-- High-Priority Operator Intervention Banner (when holds/barriers active) -->
        <app-cockpit-intervention />

        <!-- 2-Column Operational Cockpit Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          <!-- Left Column (lg:col-span-7): Primary Live Execution Topology & Activity -->
          <div class="lg:col-span-7 flex flex-col gap-6">
            <!-- Zone 3: Page-Native Runtime DAG Visualizer -->
            <app-cockpit-dag-view />

            <!-- Zone 4: Active Physical Execution Snapshot -->
            <app-cockpit-current-activity />

            <!-- Zone 6: PREVIOUS ➔ NOW ➔ NEXT Execution Narrative -->
            <app-cockpit-execution-context />
          </div>

          <!-- Right Column (lg:col-span-5): Dynamic Workbench, Health & Diagnostic Dock -->
          <div class="lg:col-span-5 flex flex-col gap-6">
            <!-- Zone 5: Dynamic Operational Domain Workbench (M1–M7 adaptive tabs) -->
            <app-cockpit-workbench />

            <!-- Zone 7: Explainable Engine Subsystem Health Grid -->
            <app-cockpit-engine-health />

            <!-- Zone 8: Chronological Audit Events & Diagnostic Dock -->
            <app-cockpit-events-dock />
          </div>

        </div>

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
      const id = params.get('migrationId') || params.get('id');
      if (id) {
        this.store.loadMigration(id);
      }
    });

    this.route.queryParamMap.subscribe(queryParams => {
      const id = queryParams.get('migrationId') || queryParams.get('id');
      if (id) {
        this.store.loadMigration(id);
      }
    });
  }
}
