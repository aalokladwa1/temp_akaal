import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { CreateConnectionService } from './create-connection.service';
import { CreateConnectionStepItem } from './create-connection.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

// Step Components
import { Step1ProviderComponent } from './steps/step1-provider.component';
import { Step2ConnectionComponent } from './steps/step2-connection.component';
import { Step3SecurityComponent } from './steps/step3-security.component';
import { Step4CapabilitiesComponent } from './steps/step4-capabilities.component';
import { Step5ReviewComponent } from './steps/step5-review.component';

@Component({
  selector: 'app-create-connection-wizard',
  standalone: true,
  imports: [
    CommonModule,
    LucideIconComponent,
    Step1ProviderComponent,
    Step2ConnectionComponent,
    Step3SecurityComponent,
    Step4CapabilitiesComponent,
    Step5ReviewComponent
  ],
  template: `
    <!-- Fluid Shell Content Wrapper (Consistent with Migration & Validation Wizards) -->
    <div class="flex flex-col h-[calc(100vh-theme(spacing.16))] -m-6 lg:-m-9 bg-slate-50 overflow-hidden select-none font-sans text-xs">
      
      <!-- ========================================================================= -->
      <!-- ZONE 1: TOP SHELL BAR                                                     -->
      <!-- ========================================================================= -->
      <header class="h-[52px] bg-white border-b border-slate-200 shrink-0 z-30 px-6 lg:px-8 flex items-center justify-between">
        
        <!-- Left: Exit Button + Breadcrumb -->
        <div class="flex items-center gap-3.5 min-w-0">
          <button
            type="button"
            (click)="cs.cancel()"
            class="h-8 px-2.5 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer transition-colors shrink-0"
            title="Exit Create Connection">
            <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
            <span>Exit</span>
          </button>

          <span class="h-4 w-[1px] bg-slate-200 shrink-0"></span>

          <h1 class="text-[10px] font-bold tracking-wider uppercase text-slate-500 shrink-0 m-0 leading-none">
            CREATE CONNECTION &middot; STEP {{ cs.currentStep() }} OF 5
          </h1>
        </div>

        <!-- Right: Status Pill -->
        <div class="flex items-center gap-3 shrink-0">
          <div class="h-8 px-3 rounded-lg border border-slate-200 bg-white flex items-center gap-2 text-xs font-medium text-slate-700 shadow-2xs">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>
            <span>Draft Active</span>
            @if (cs.selectedProvider(); as p) {
              <span class="text-slate-400 font-normal">&middot; {{ p.name }}</span>
            }
          </div>
        </div>

      </header>

      <!-- ========================================================================= -->
      <!-- ZONE 2: LOW-PROFILE 5-STEP PROCESS STEPPER                                -->
      <!-- ========================================================================= -->
      <nav aria-label="Create Connection Steps" class="h-12 bg-white border-b border-slate-200 px-6 lg:px-8 flex items-center shrink-0 relative z-20">
        <div class="w-full max-w-5xl mx-auto flex items-center justify-between gap-2 overflow-x-hidden">
          @for (step of steps; track step.index) {
            
            <!-- Case 1: Active Step -->
            @if (step.index === cs.currentStep()) {
              <div 
                class="flex items-center gap-2 text-slate-900 font-bold text-xs shrink-0 select-none"
                aria-current="step">
                <span class="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </div>
            }

            <!-- Case 2: Completed Step (Clickable Backward) -->
            @else if (step.index < cs.currentStep()) {
              <button
                type="button"
                (click)="cs.goToStep(step.index)"
                class="flex items-center gap-2 text-slate-600 hover:text-slate-900 text-xs font-medium shrink-0 cursor-pointer transition-colors group"
                title="Jump backward to Step {{ step.index }}: {{ step.label }}">
                <span class="w-5 h-5 rounded-full bg-slate-100 group-hover:bg-slate-200 text-slate-600 text-[10px] font-bold flex items-center justify-center shrink-0 border border-slate-200">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </button>
            }

            <!-- Case 3: Future Step -->
            @else {
              <div
                class="flex items-center gap-2 text-slate-400 text-xs font-normal shrink-0 cursor-not-allowed"
                aria-disabled="true"
                [title]="'Complete Step ' + cs.currentStep() + ' before continuing to Step ' + step.index">
                <span class="w-5 h-5 rounded-full bg-slate-100 border border-slate-200 text-slate-400 text-[10px] font-medium flex items-center justify-center shrink-0">
                  {{ step.index }}
                </span>
                <span class="tracking-tight">{{ step.label }}</span>
              </div>
            }

          }
        </div>
      </nav>

      <!-- ========================================================================= -->
      <!-- ZONE 3: ACTIVE STEP WORKSPACE CANVAS                                      -->
      <!-- ========================================================================= -->
      <section
        aria-label="Active Step Workspace"
        class="flex-1 min-h-0 overflow-y-auto px-6 lg:px-8 py-5 select-none">
        
        <div class="w-full max-w-5xl mx-auto">
          @switch (cs.currentStep()) {
            @case (1) { <app-step1-provider></app-step1-provider> }
            @case (2) { <app-step2-connection></app-step2-connection> }
            @case (3) { <app-step3-security></app-step3-security> }
            @case (4) { <app-step4-capabilities></app-step4-capabilities> }
            @case (5) { <app-step5-review></app-step5-review> }
          }
        </div>

      </section>

      <!-- ========================================================================= -->
      <!-- ZONE 4: FIXED FOOTER (Strict Text-Led Actions, No Icons Inside Buttons)    -->
      <!-- ========================================================================= -->
      <footer class="h-14 border-t border-slate-200 bg-white px-6 lg:px-8 flex items-center justify-between shrink-0 z-30">
        
        <!-- Left Slot: Back / Cancel -->
        <div class="flex items-center gap-2.5">
          @if (cs.currentStep() > 1) {
            <button
              type="button"
              (click)="cs.prevStep()"
              class="h-8 px-3.5 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors cursor-pointer">
              Back
            </button>
          } @else {
            <button
              type="button"
              (click)="cs.cancel()"
              class="h-8 px-3.5 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors cursor-pointer">
              Cancel
            </button>
          }
        </div>

        <!-- Right Slot: Continue / Create Connection -->
        <div class="flex items-center gap-3">
          @if (cs.currentStep() < 5) {
            <button
              type="button"
              (click)="cs.nextStep()"
              [disabled]="!cs.canProceed()"
              class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:pointer-events-none rounded-md transition-colors cursor-pointer shadow-2xs">
              Continue
            </button>
          } @else {
            <button
              type="button"
              (click)="cs.createConnection()"
              class="h-8 px-5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors cursor-pointer shadow-xs">
              Create Connection
            </button>
          }
        </div>

      </footer>

    </div>
  `
})
export class CreateConnectionWizardComponent implements OnInit {
  public cs = inject(CreateConnectionService);
  private router = inject(Router);

  public steps: CreateConnectionStepItem[] = [
    { index: 1, label: 'Provider', sublabel: 'System & Category', description: 'Select physical provider or managed cloud resolver' },
    { index: 2, label: 'Connection', sublabel: 'Identity & Addressing', description: 'Configure host, port, database, and extensions' },
    { index: 3, label: 'Security & Network', sublabel: 'Auth, TLS, & Routes', description: 'Configure credentials, encryption, and tunnels' },
    { index: 4, label: 'Capabilities & Validation', sublabel: 'Point-in-Time Probe', description: 'Test connectivity facts, permissions, and CDC' },
    { index: 5, label: 'Review & Create', sublabel: 'Summary & Provisioning', description: 'Confirm parameters and create connection resource' }
  ];

  ngOnInit(): void {
    // Start at Step 1
  }
}
