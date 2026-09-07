import {
  Component,
  inject,
  signal,
  computed,
  ViewChild,
  ElementRef,
  AfterViewInit,
  OnDestroy,
  HostListener
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import {
  AssuranceLevel,
  TemporalCadence,
  CoveragePolicy,
  CapabilityStatus,
  AssuranceTierCard,
  AssuranceExceptionGroup,
  AdvancedCoverageConfig,
  ContextualIntelligenceFinding,
  TemporalOption,
  ExceptionScopeType
} from './step6-strategy.models';

@Component({
  selector: 'app-step6-strategy',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent
  ],
  template: `
    <div class="max-w-5xl mx-auto w-full space-y-6 select-none text-xs font-sans pb-12">
      
      <!-- ========================================================================= -->
      <!-- 0. HEADER & RESTRAINED CONTEXT AREA                                       -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-3 border-b border-slate-200/60 pb-3">
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div class="flex flex-col gap-0.5">
            <h1 class="text-base font-bold text-slate-900 tracking-tight">Validation Strategy &amp; Assurance</h1>
            <p class="text-xs text-slate-500 font-normal">
              Choose how strongly AKAAL must prove equivalence within the selected scope and comparison baseline.
            </p>
          </div>

          <!-- Restrained Inherited Context Bar (Steps 2-5 Truth) -->
          <div class="flex items-center gap-3 px-3.5 py-1.5 bg-white border border-slate-200 rounded-lg shadow-2xs text-xs">
            
            <!-- Source -> Target -->
            <div class="flex items-center gap-2 text-slate-700">
              <app-lucide-icon [name]="getProviderIcon(sourceProvider())" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span class="font-bold text-slate-900">{{ sourceProvider() }}</span>
              <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
              <app-lucide-icon [name]="getProviderIcon(targetProvider())" [size]="14" class="text-emerald-600"></app-lucide-icon>
              <span class="font-bold text-slate-900">{{ targetProvider() }}</span>
            </div>

            <span class="text-slate-300">&middot;</span>

            <!-- Scoped Entities Count (Step 4) -->
            <div class="flex items-center gap-1.5 text-slate-600">
              <app-lucide-icon name="layers" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span class="font-semibold text-slate-900">{{ scopedEntitiesCount() }}</span>
              <span class="text-slate-500">scoped objects</span>
            </div>

            <span class="text-slate-300">&middot;</span>

            <!-- Comparison Baseline (Step 5) -->
            <div class="flex items-center gap-1.5 text-slate-600">
              <app-lucide-icon name="crosshair" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span class="text-slate-700 font-medium truncate max-w-[180px]">{{ baselineSummaryLabel() }}</span>
            </div>

          </div>
        </div>
      </div>

      <!-- ========================================================================= -->
      <!-- CONTEXTUAL INTELLIGENCE CALLOUT (Collapses to 0 height when null)           -->
      <!-- ========================================================================= -->
      @if (contextualFinding(); as finding) {
        @if (!finding.isDismissed) {
          <section
            aria-label="Contextual Intelligence Recommendation"
            class="rounded-xl border p-4 transition-all animate-in fade-in duration-150"
            [ngClass]="{
              'bg-blue-50/50 border-blue-200 text-blue-900': finding.severity === 'ADVISORY' || finding.severity === 'INFO',
              'bg-amber-50/60 border-amber-200 text-amber-900': finding.severity === 'WARNING'
            }">
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  [ngClass]="finding.severity === 'WARNING' ? 'bg-amber-100 text-amber-700 border border-amber-200' : 'bg-blue-100 text-blue-700 border border-blue-200'">
                  <app-lucide-icon [name]="finding.severity === 'WARNING' ? 'alert-triangle' : 'sparkles'" [size]="16"></app-lucide-icon>
                </div>
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <h3 class="text-xs font-bold text-slate-900">{{ finding.title }}</h3>
                    <span class="px-2 py-0.5 rounded-md text-[10px] font-bold border"
                      [ngClass]="finding.severity === 'WARNING' ? 'bg-amber-100 text-amber-800 border-amber-300' : 'bg-blue-100 text-blue-800 border-blue-300'">
                      Contextual Advisory
                    </span>
                  </div>
                  <p class="text-xs text-slate-600 leading-relaxed font-normal">
                    {{ finding.body }}
                  </p>
                </div>
              </div>

              <!-- Recommendation Actions: Accept or Dismiss -->
              <div class="flex items-center gap-2 shrink-0">
                @if (finding.recommendedAssuranceLevel && selectedLevel() !== finding.recommendedAssuranceLevel) {
                  <button
                    type="button"
                    (click)="applyContextualRecommendation(finding)"
                    class="h-7 px-3 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs">
                    <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                    <span>Apply Recommendation</span>
                  </button>
                }
                <button
                  type="button"
                  (click)="dismissContextualFinding()"
                  class="h-7 px-2.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50 rounded-md transition-colors cursor-pointer">
                  <span>Dismiss</span>
                </button>
              </div>
            </div>
          </section>
        }
      }

      <!-- ========================================================================= -->
      <!-- 1. PRIMARY SECTION: PROGRESSIVE ASSURANCE LADDER (SPACIOUS STACKED ROWS) -->
      <!-- ========================================================================= -->
      <section aria-label="Assurance Requirement" class="space-y-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <div class="flex items-center gap-2">
            <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Assurance Requirement <span class="text-rose-500">*</span>
            </h2>
            <span class="text-slate-300 font-light">&middot;</span>
            <span class="text-xs text-slate-400 font-normal">
              Select the level of mathematical and logical proof required to certify equivalence.
            </span>
          </div>
          <span class="text-[11px] text-slate-400 font-normal">Additive Proof Obligations</span>
        </div>

        <!-- Spacious Stacked Rectangular Surfaces -->
        <div class="space-y-3">
          @for (card of assuranceTiers; track card.level) {
            <div
              (click)="selectAssuranceLevel(card.level)"
              class="border rounded-xl transition-all select-none text-left"
              [ngClass]="{
                'cursor-pointer': card.capability !== 'UNAVAILABLE',
                'cursor-not-allowed opacity-60 bg-slate-50': card.capability === 'UNAVAILABLE',
                'bg-blue-50/20 border-blue-600 ring-1 ring-blue-600/30': selectedLevel() === card.level && card.capability !== 'UNAVAILABLE',
                'bg-white border-slate-200 hover:border-slate-300': selectedLevel() !== card.level && card.capability !== 'UNAVAILABLE'
              }">
              
              <!-- Card Header & Summary Row -->
              <div class="p-4 flex items-start justify-between gap-4">
                <div class="flex items-start gap-3.5 min-w-0">
                  <!-- Step number badge (curved corner rectangle) -->
                  <span class="w-7 h-7 rounded-md text-[10px] font-bold flex items-center justify-center font-mono border shrink-0 mt-0.5"
                    [ngClass]="selectedLevel() === card.level ? 'bg-blue-600 text-white border-blue-600' : 'bg-slate-100 text-slate-600 border-slate-200'">
                    {{ card.stepNumber }}
                  </span>

                  <!-- Tier icon (curved corner rectangle) -->
                  <div class="w-7 h-7 rounded-md flex items-center justify-center shrink-0 mt-0.5"
                    [ngClass]="selectedLevel() === card.level ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'">
                    <app-lucide-icon [name]="getTierIcon(card.level)" [size]="14"></app-lucide-icon>
                  </div>

                  <div class="space-y-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <h3 class="text-xs font-bold text-slate-900 leading-none">
                        {{ card.title }}
                      </h3>
                      <span class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                        {{ card.progressionLabel }}
                      </span>
                      @if (card.level === 'PARTITION_FINGERPRINT') {
                        <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                          Mission Default
                        </span>
                      }
                    </div>
                    <p class="text-xs text-slate-500 font-normal leading-relaxed">
                      {{ card.subtitle }}
                    </p>
                  </div>
                </div>

                <!-- Right Side: Status Badge & Selection Indicator -->
                <div class="flex items-center gap-3 shrink-0 pt-0.5">
                  @if (isTierSubsumed(card.level)) {
                    <span class="text-emerald-700 font-medium text-xs flex items-center gap-1">
                      <app-lucide-icon name="check-circle-2" [size]="12" class="text-emerald-600"></app-lucide-icon>
                      <span class="hidden sm:inline">Subsumed by higher tier</span>
                    </span>
                  } @else {
                    <span class="text-slate-400 font-medium text-xs hidden sm:inline">
                      {{ card.capability === 'AVAILABLE' ? 'Available' : card.capability === 'AVAILABLE_WITH_LIMITATIONS' ? 'Available with limitations' : 'Unavailable' }}
                    </span>
                  }

                  <!-- Curved Corner Rectangle Radio Indicator -->
                  <div class="w-4 h-4 rounded-md border flex items-center justify-center transition-colors shrink-0"
                    [ngClass]="selectedLevel() === card.level ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                    @if (selectedLevel() === card.level) {
                      <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                    }
                  </div>
                </div>
              </div>

              <!-- Integrated Contract Breakdown (Appears Inside Selected Tier) -->
              @if (selectedLevel() === card.level) {
                <div class="px-4 pb-4 pt-2 border-t border-blue-100/80 mt-1 animate-in fade-in duration-150 space-y-3">
                  
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <!-- Column 1: Establishes -->
                    <div class="p-3.5 rounded-lg bg-white border border-slate-200/80 space-y-2">
                      <div class="flex items-center gap-1.5 text-emerald-700 font-bold text-[11px] uppercase tracking-wider">
                        <app-lucide-icon name="check-circle" [size]="13" class="text-emerald-600"></app-lucide-icon>
                        <span>What this establishes</span>
                      </div>
                      <ul class="space-y-1.5 text-slate-700 font-normal leading-relaxed">
                        @for (item of card.establishes; track item) {
                          <li class="flex items-start gap-2">
                            <app-lucide-icon name="check" [size]="12" class="text-emerald-600 shrink-0 mt-0.5"></app-lucide-icon>
                            <span>{{ item }}</span>
                          </li>
                        }
                      </ul>
                    </div>

                    <!-- Column 2: Does not establish -->
                    <div class="p-3.5 rounded-lg bg-white border border-slate-200/80 space-y-2">
                      <div class="flex items-center gap-1.5 text-rose-700 font-bold text-[11px] uppercase tracking-wider">
                        <app-lucide-icon name="x-circle" [size]="13" class="text-rose-600"></app-lucide-icon>
                        <span>What this does not establish</span>
                      </div>
                      <ul class="space-y-1.5 text-slate-700 font-normal leading-relaxed">
                        @for (item of card.doesNotEstablish; track item) {
                          <li class="flex items-start gap-2">
                            <app-lucide-icon name="x" [size]="12" class="text-rose-600 shrink-0 mt-0.5"></app-lucide-icon>
                            <span>{{ item }}</span>
                          </li>
                        }
                      </ul>
                    </div>
                  </div>

                  <!-- Limitations & Semantics Note -->
                  <div class="px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-200 text-slate-600 text-xs flex items-start gap-2">
                    <app-lucide-icon name="info" [size]="13" class="text-slate-400 shrink-0 mt-0.5"></app-lucide-icon>
                    <div class="space-y-0.5 leading-relaxed">
                      <span class="font-semibold text-slate-800">Semantics &amp; Limitations:</span>
                      <span class="text-slate-600"> {{ card.limitations.join(' · ') }}</span>
                    </div>
                  </div>

                </div>
              }

            </div>
          }
        </div>

        <!-- Subsumption Law Helper Banner -->
        <div class="px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between text-xs text-slate-600">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="info" [size]="13" class="text-slate-500 shrink-0"></app-lucide-icon>
            <span>
              <strong>Additive Assurance Law:</strong> Selecting a higher tier automatically establishes and validates all prerequisite obligations below it.
            </span>
          </div>
          <span class="text-slate-400 hidden sm:inline text-[11px]">Subsumption is mathematically enforced</span>
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 2. TEMPORAL BEHAVIOR                                                      -->
      <!-- ========================================================================= -->
      <section aria-label="Temporal Validation Behavior" class="space-y-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <div class="flex items-center gap-2">
            <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Temporal Behavior <span class="text-rose-500">*</span>
            </h2>
            <span class="text-slate-300 font-light">&middot;</span>
            <span class="text-xs text-slate-400 font-normal">Specify when and how often equivalence is evaluated.</span>
          </div>
          <span class="text-[11px] text-slate-400 font-normal">Snapshot vs Continuous CDC</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          @for (temp of temporalOptions; track temp.id) {
            <div
              (click)="selectTemporalCadence(temp.id)"
              class="rounded-xl border p-4 transition-all relative flex flex-col justify-between gap-3 text-left shadow-2xs select-none"
              [ngClass]="{
                'cursor-pointer': temp.capability !== 'UNAVAILABLE',
                'cursor-not-allowed opacity-70 bg-slate-50': temp.capability === 'UNAVAILABLE',
                'bg-blue-50/30 border-blue-500 ring-1 ring-blue-500/20': selectedCadence() === temp.id && temp.capability !== 'UNAVAILABLE',
                'bg-white border-slate-200 hover:border-slate-300': selectedCadence() !== temp.id && temp.capability !== 'UNAVAILABLE'
              }">
              
              <div class="space-y-2">
                <div class="flex items-start justify-between gap-3">
                  <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                    [ngClass]="selectedCadence() === temp.id && temp.capability !== 'UNAVAILABLE' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'">
                    <app-lucide-icon [name]="temp.icon" [size]="16"></app-lucide-icon>
                  </div>

                  <!-- Selection Indicator (Curved Corner Rectangle) -->
                  <div class="w-4 h-4 rounded-md border flex items-center justify-center transition-colors shrink-0 mt-1"
                    [ngClass]="selectedCadence() === temp.id ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                    @if (selectedCadence() === temp.id) {
                      <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                    }
                  </div>
                </div>

                <div class="space-y-1">
                  <h3 class="text-xs font-bold text-slate-900">
                    {{ temp.title }}
                  </h3>
                  <p class="text-xs text-slate-500 font-normal leading-relaxed">
                    {{ temp.description }}
                  </p>
                </div>
              </div>

              <!-- Capability Notice for Unavailable Continuous Mode -->
              @if (temp.capability === 'UNAVAILABLE') {
                <div class="mt-2 px-2.5 py-2 rounded-md bg-slate-100 border border-slate-200 text-[11px] text-slate-600 flex items-start gap-2">
                  <app-lucide-icon name="info" [size]="13" class="text-slate-500 shrink-0 mt-0.5"></app-lucide-icon>
                  <div class="space-y-0.5">
                    <span class="font-semibold text-slate-800">Capability Unavailable</span>
                    <p class="text-slate-500 leading-normal">{{ temp.capabilityNotice }}</p>
                  </div>
                </div>
              }

            </div>
          }
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 3. ASSURANCE EXCEPTIONS (Mission Default + Scoped Overrides)               -->
      <!-- ========================================================================= -->
      <section aria-label="Assurance Exceptions" class="space-y-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <div class="flex items-center gap-2">
            <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Assurance Exceptions
            </h2>
            <span class="text-slate-300 font-light">&middot;</span>
            <span class="text-xs text-slate-400 font-normal">
              Apply stronger or lighter proof contracts to specific scoped subsets without configuring objects individually.
            </span>
          </div>

          <button
            type="button"
            (click)="openAddExceptionModal()"
            class="h-7 px-3 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs">
            <app-lucide-icon name="plus" [size]="12"></app-lucide-icon>
            <span>Add Exception</span>
          </button>
        </div>

        @if (exceptionGroups().length > 0) {
          <!-- High-Level Policy Breakdown -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            
            <!-- Default Group -->
            <div class="p-3 rounded-lg bg-white border border-slate-200 space-y-1">
              <div class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <app-lucide-icon name="shield" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                <span>Mission Default</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-900">{{ activeTier().title }}</span>
                <span class="text-xs font-mono font-semibold text-slate-600">{{ defaultObjectsCount() }} obj</span>
              </div>
              <p class="text-[11px] text-slate-500 font-normal">Base proof level applied across estate</p>
            </div>

            <!-- Escalated Scope -->
            <div class="p-3 rounded-lg bg-white border border-slate-200 space-y-1">
              <div class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-blue-600">
                <app-lucide-icon name="arrow-up-right" [size]="12" class="text-blue-600 shrink-0"></app-lucide-icon>
                <span>Escalated Scope</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-900">Complete Attribute</span>
                <span class="text-xs font-mono font-semibold text-blue-700">{{ escalatedObjectsCount() }} obj</span>
              </div>
              <p class="text-[11px] text-slate-500 font-normal">Critical entities requiring exhaustive logical proof</p>
            </div>

            <!-- Reduced Assurance Scope -->
            <div class="p-3 rounded-lg bg-white border border-slate-200 space-y-1">
              <div class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-amber-600">
                <app-lucide-icon name="arrow-down-right" [size]="12" class="text-amber-600 shrink-0"></app-lucide-icon>
                <span>Reduced Assurance</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-900">Cardinality / Structural</span>
                <span class="text-xs font-mono font-semibold text-amber-700">{{ reducedObjectsCount() }} obj</span>
              </div>
              <p class="text-[11px] text-slate-500 font-normal">Logging / archive tables exempt from deep inspection</p>
            </div>

          </div>

          <!-- Exception Cards List -->
          <div class="space-y-2 pt-1">
            @for (exc of exceptionGroups(); track exc.id) {
              <div class="p-3.5 rounded-xl border bg-white flex items-center justify-between gap-4 transition-all hover:border-slate-300"
                [ngClass]="exc.type === 'ESCALATED' ? 'border-blue-200 bg-blue-50/10' : 'border-amber-200 bg-amber-50/10'">
                <div class="flex items-start gap-3 min-w-0">
                  <div class="w-7 h-7 rounded-md flex items-center justify-center shrink-0 mt-0.5"
                    [ngClass]="exc.type === 'ESCALATED' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'">
                    <app-lucide-icon [name]="exc.type === 'ESCALATED' ? 'arrow-up-right' : 'arrow-down-right'" [size]="14"></app-lucide-icon>
                  </div>

                  <div class="space-y-0.5 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-bold text-slate-900">{{ getTierTitle(exc.targetAssuranceLevel) }}</span>
                      <span class="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase"
                        [ngClass]="exc.type === 'ESCALATED' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'">
                        {{ exc.type }} ({{ exc.objectIds.length }} {{ exc.objectIds.length === 1 ? 'Object' : 'Objects' }})
                      </span>
                    </div>
                    <p class="text-[11px] text-slate-600 truncate font-normal">
                      <strong>Reason:</strong> {{ exc.reason }}
                    </p>
                    <div class="text-[10px] text-slate-400 font-mono truncate">
                      Objects: {{ exc.objectNames.slice(0, 4).join(', ') }}{{ exc.objectNames.length > 4 ? ' + ' + (exc.objectNames.length - 4) + ' more' : '' }}
                    </div>
                  </div>
                </div>

                <!-- Actions -->
                <div class="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    (click)="removeExceptionGroup(exc.id)"
                    class="h-7 px-2 text-xs font-medium text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors cursor-pointer"
                    title="Remove exception">
                    <app-lucide-icon name="trash-2" [size]="12"></app-lucide-icon>
                  </button>
                </div>
              </div>
            }
          </div>
        } @else {
          <div class="p-4 text-center border border-dashed border-slate-200 rounded-xl bg-white flex flex-col items-center justify-center gap-1.5 py-6">
            <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400">
              <app-lucide-icon name="shield" [size]="16"></app-lucide-icon>
            </div>
            <span class="text-xs font-semibold text-slate-700">
              Mission default applies uniformly across all {{ scopedEntitiesCount() }} scoped entities.
            </span>
            <p class="text-[11px] text-slate-400 max-w-md font-normal">
              No exceptions configured. The selected assurance level applies across all scoped objects.
            </p>
          </div>
        }

      </section>

      <!-- ========================================================================= -->
      <!-- 4. ADVANCED COVERAGE (Progressively Disclosed)                            -->
      <!-- ========================================================================= -->
      <section aria-label="Advanced Coverage" class="pt-1">
        <button
          type="button"
          (click)="toggleAdvancedCoverage()"
          class="flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-900 cursor-pointer transition-colors select-none">
          <app-lucide-icon [name]="isAdvancedCoverageOpen() ? 'chevron-down' : 'chevron-right'" [size]="14" class="text-slate-400"></app-lucide-icon>
          <span>{{ isAdvancedCoverageOpen() ? 'Hide Advanced Coverage & Sampling' : 'Advanced Coverage & Sampling' }}</span>
        </button>

        @if (isAdvancedCoverageOpen()) {
          <div class="mt-3 rounded-xl bg-white border border-slate-200 p-5 animate-in fade-in duration-100 space-y-4">
            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
              <span class="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <app-lucide-icon name="pie-chart" [size]="14" class="text-slate-500"></app-lucide-icon>
                <span>Coverage Policy</span>
              </span>
              <span class="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 text-[10px] font-medium text-slate-600">
                Default: 100% Exhaustive Inspection
              </span>
            </div>

            <p class="text-xs text-slate-600 font-normal leading-relaxed">
              AKAAL inspects 100% of included records and attributes across all partitions by default. For rapid smoke testing on non-production estates, statistical sampling may be configured.
            </p>

            <!-- Permanent Non-Masquerade Law Warning -->
            <div class="p-3.5 bg-amber-50/70 border border-amber-200/80 rounded-lg text-xs text-amber-900 flex items-start gap-2.5">
              <app-lucide-icon name="alert-triangle" [size]="15" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
              <div class="space-y-1 leading-relaxed">
                <span class="font-bold text-slate-900">Statistical Sampling Law</span>
                <p class="text-slate-700 text-[11px]">
                  Sampled validation proves <strong>only the inspected subset</strong>. A passing sample does not establish complete equivalence, cannot prove zero data loss, and <strong>will not satisfy the cutover certification gate</strong>.
                </p>
              </div>
            </div>

            <!-- Sampling Option Radio Toggle -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div
                (click)="selectCoverageMode('EXHAUSTIVE')"
                class="p-3 rounded-lg border bg-white cursor-pointer transition-all flex items-start gap-2.5"
                [ngClass]="coverageMode() === 'EXHAUSTIVE' ? 'border-blue-500 ring-1 ring-blue-500' : 'border-slate-200'">
                <div class="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 mt-0.5"
                  [ngClass]="coverageMode() === 'EXHAUSTIVE' ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                  @if (coverageMode() === 'EXHAUSTIVE') {
                    <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                  }
                </div>
                <div class="space-y-0.5">
                  <div class="flex items-center gap-1.5 text-xs font-semibold text-slate-900">
                    <app-lucide-icon name="check-check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                    <span>100% Exhaustive Coverage</span>
                  </div>
                  <p class="text-[11px] text-slate-500 font-normal">All partitions, records, and mapped attributes validated.</p>
                </div>
              </div>

              <div
                (click)="selectCoverageMode('STATISTICAL_SAMPLE')"
                class="p-3 rounded-lg border bg-white cursor-pointer transition-all flex items-start gap-2.5"
                [ngClass]="coverageMode() === 'STATISTICAL_SAMPLE' ? 'border-blue-500 ring-1 ring-blue-500' : 'border-slate-200'">
                <div class="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 mt-0.5"
                  [ngClass]="coverageMode() === 'STATISTICAL_SAMPLE' ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                  @if (coverageMode() === 'STATISTICAL_SAMPLE') {
                    <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                  }
                </div>
                <div class="space-y-0.5">
                  <div class="flex items-center gap-1.5 text-xs font-semibold text-slate-900">
                    <app-lucide-icon name="percent" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                    <span>Deterministic Hash Modulo Sample</span>
                  </div>
                  <p class="text-[11px] text-slate-500 font-normal">Deterministic subset based on PK hash modulo (Seed: 42).</p>
                </div>
              </div>
            </div>

            <!-- Sample Percentage Slider if Sample Selected -->
            @if (coverageMode() === 'STATISTICAL_SAMPLE') {
              <div class="p-3.5 rounded-lg bg-white border border-slate-200 space-y-2">
                <div class="flex items-center justify-between">
                  <label class="text-xs font-semibold text-slate-800">Sample Percentage</label>
                  <span class="text-xs font-mono font-bold text-blue-600">{{ samplePercentage() }}% of records</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="50"
                  [ngModel]="samplePercentage()"
                  (ngModelChange)="onSamplePercentageChange($event)"
                  class="w-full accent-blue-600 cursor-pointer" />
                <div class="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>1% (Quick Smoke)</span>
                  <span>10% (Diagnostic)</span>
                  <span>50% (Upper Sample Bound)</span>
                </div>
              </div>
            }

          </div>
        }
      </section>

    </div>

    <!-- ========================================================================= -->
    <!-- MODAL: ADD ASSURANCE EXCEPTION (TELEPORTED TO DOCUMENT.BODY)              -->
    <!-- ========================================================================= -->
    <div
      #exceptionModalEl
      [style.display]="showExceptionModal() ? 'flex' : 'none'"
      role="dialog"
      aria-modal="true"
      class="fixed inset-0 z-[99999] items-center justify-center bg-slate-900/40 p-4 select-none duration-150"
      (click)="closeExceptionModal()">
      <div
        class="w-full max-w-xl rounded-2xl bg-white border border-slate-200 p-6 flex flex-col gap-4 shadow-2xl select-none"
        (click)="$event.stopPropagation()">
        
        <div class="flex items-center justify-between border-b border-slate-100 pb-3.5">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
              <app-lucide-icon name="plus" [size]="16"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-sm font-bold text-slate-900">Add Assurance Exception</h3>
              <span class="text-[11px] text-slate-500 font-normal">Apply specialized proof depth to a subset of scoped entities</span>
            </div>
          </div>

          <button
            type="button"
            (click)="closeExceptionModal()"
            class="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 flex items-center justify-center cursor-pointer transition-colors"
            title="Close dialog (Esc)">
            <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
          </button>
        </div>

        <!-- Exception Type: Escalated vs Reduced -->
        <div class="space-y-1.5">
          <label class="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
            <app-lucide-icon name="arrow-left-right" [size]="13" class="text-slate-400 shrink-0"></app-lucide-icon>
            <span>Exception Direction</span>
          </label>
          <div class="grid grid-cols-2 gap-3">
            <button
              type="button"
              (click)="draftExceptionType.set('ESCALATED')"
              class="p-3 rounded-xl border text-left flex items-center gap-2.5 cursor-pointer transition-all"
              [ngClass]="draftExceptionType() === 'ESCALATED' ? 'bg-blue-50/70 border-blue-500 text-blue-900 font-semibold ring-1 ring-blue-500/30' : 'bg-white border-slate-200 hover:border-slate-300 text-slate-700'">
              <div class="w-7 h-7 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                <app-lucide-icon name="arrow-up-right" [size]="14"></app-lucide-icon>
              </div>
              <div>
                <div class="text-xs font-bold">Escalate Assurance</div>
                <div class="text-[10px] text-slate-500 font-normal">Require deeper proof</div>
              </div>
            </button>

            <button
              type="button"
              (click)="draftExceptionType.set('REDUCED')"
              class="p-3 rounded-xl border text-left flex items-center gap-2.5 cursor-pointer transition-all"
              [ngClass]="draftExceptionType() === 'REDUCED' ? 'bg-amber-50/70 border-amber-500 text-amber-900 font-semibold ring-1 ring-amber-500/30' : 'bg-white border-slate-200 hover:border-slate-300 text-slate-700'">
              <div class="w-7 h-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
                <app-lucide-icon name="arrow-down-right" [size]="14"></app-lucide-icon>
              </div>
              <div>
                <div class="text-xs font-bold">Reduce Assurance</div>
                <div class="text-[10px] text-slate-500 font-normal">Exempt from heavy inspection</div>
              </div>
            </button>
          </div>
        </div>

        <!-- Target Assurance Level Dropdown -->
        <div class="space-y-1.5">
          <label class="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
            <app-lucide-icon name="file-badge" [size]="13" class="text-slate-400 shrink-0"></app-lucide-icon>
            <span>Target Assurance Level</span>
          </label>
          <select
            [(ngModel)]="draftTargetLevel"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs">
            <option value="STRUCTURAL">Structural Assurance (Schema Only)</option>
            <option value="CARDINALITY">Cardinality Assurance (Record Counts)</option>
            <option value="PARTITION_FINGERPRINT">Partition Fingerprint (Cryptographic XOR)</option>
            <option value="COMPLETE_ATTRIBUTE">Complete Attribute Assurance (Exhaustive Logical Values)</option>
          </select>
        </div>

        <!-- Mandatory Reason -->
        <div class="space-y-1.5">
          <label class="text-xs font-semibold text-slate-700 flex items-center justify-between">
            <span class="flex items-center gap-1.5">
              <app-lucide-icon name="file-text" [size]="13" class="text-slate-400 shrink-0"></app-lucide-icon>
              <span>Reason / Rationale <span class="text-rose-500">*</span></span>
            </span>
            <span class="text-[10px] text-slate-400">Required for audit trail</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draftReason"
            placeholder="e.g. Financial critical GL ledger tables requiring complete logical proof"
            class="w-full h-9 px-3 text-xs bg-white border rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 placeholder:text-slate-400 shadow-2xs"
            [class.border-rose-400]="isDraftReasonInvalid()"
            [class.bg-rose-50]="isDraftReasonInvalid()" />
          @if (isDraftReasonInvalid()) {
            <span class="text-[10px] text-rose-600 font-medium flex items-center gap-1">
              <app-lucide-icon name="alert-circle" [size]="11" class="text-rose-600 shrink-0"></app-lucide-icon>
              <span>Please enter a reason for this assurance exception.</span>
            </span>
          }
        </div>

        <!-- Scoped Object Selector (Search + Multi-Select) -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
              <app-lucide-icon name="layers" [size]="13" class="text-slate-400 shrink-0"></app-lucide-icon>
              <span>Select Scoped Entities ({{ draftSelectedObjectIds().length }} selected)</span>
            </label>
            <button
              type="button"
              (click)="selectAllFilteredObjects()"
              class="text-[11px] text-blue-600 hover:text-blue-800 font-semibold cursor-pointer">
              Select All
            </button>
          </div>

          <!-- Filter Search with Icon (Centered with Clean Left Padding) -->
          <div class="relative flex items-center">
            <input
              type="text"
              [(ngModel)]="objectSearchQuery"
              placeholder="Search scoped objects by name or namespace..."
              class="w-full h-9 pl-11 pr-3.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 transition-colors" />
            <app-lucide-icon name="search" [size]="14" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
          </div>

          <!-- Object List Box -->
          <div class="h-36 overflow-y-auto border border-slate-200 rounded-lg p-2 space-y-1 bg-slate-50/50">
            @for (obj of filteredScopedObjects(); track obj.id) {
              <div
                (click)="toggleObjectSelection(obj.id)"
                class="px-2.5 py-1.5 rounded-md text-xs flex items-center justify-between cursor-pointer transition-colors hover:bg-white"
                [ngClass]="isObjectSelected(obj.id) ? 'bg-white border border-blue-200 text-blue-900 font-semibold shadow-2xs' : 'text-slate-700'">
                <div class="flex items-center gap-2 truncate">
                  <app-lucide-icon name="table-2" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                  <span class="truncate font-mono">{{ obj.name }}</span>
                </div>
                @if (isObjectSelected(obj.id)) {
                  <app-lucide-icon name="check" [size]="12" class="text-blue-600 shrink-0"></app-lucide-icon>
                }
              </div>
            }
            @if (filteredScopedObjects().length === 0) {
              <div class="py-6 text-center text-slate-400 text-xs">No matching scoped objects found</div>
            }
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="flex items-center justify-end gap-2.5 pt-3.5 border-t border-slate-100">
          <button
            type="button"
            (click)="closeExceptionModal()"
            class="h-8 px-3.5 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 transition-colors cursor-pointer shadow-2xs">
            Cancel
          </button>
          <button
            type="button"
            (click)="saveExceptionGroup()"
            [disabled]="isDraftReasonInvalid() || draftSelectedObjectIds().length === 0"
            class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:pointer-events-none rounded-md transition-colors cursor-pointer shadow-2xs">
            Add Exception
          </button>
        </div>

      </div>
    </div>
  `
})
export class Step6StrategyComponent implements AfterViewInit, OnDestroy {
  @ViewChild('exceptionModalEl') exceptionModalEl?: ElementRef<HTMLElement>;
  private modalAttachedToBody = false;
  public vs: ValidationUiService;

  // Progressive disclosure for advanced coverage
  public isAdvancedCoverageOpen = signal<boolean>(false);

  // Modal state for adding scoped assurance exceptions
  public showExceptionModal = signal<boolean>(false);
  public draftExceptionType = signal<ExceptionScopeType>('ESCALATED');
  public draftTargetLevel = signal<AssuranceLevel>('COMPLETE_ATTRIBUTE');
  public draftReason = signal<string>('');
  public draftSelectedObjectIds = signal<string[]>([]);
  public objectSearchQuery = signal<string>('');

  // P7C Contextual Intelligence Finding (null by default; collapses to 0 height)
  public contextualFinding = signal<ContextualIntelligenceFinding | null>(null);

  // 4 Progressive Assurance Tiers
  public readonly assuranceTiers: AssuranceTierCard[] = [
    {
      level: 'STRUCTURAL',
      stepNumber: '01',
      title: 'Structural Assurance',
      subtitle: 'Schema equivalence, datatypes, and key relationships within selected scope.',
      progressionLabel: 'Structure',
      capability: 'AVAILABLE',
      establishes: [
        'Target table & mapped column existence',
        'Approved datatype widening rules',
        'Nullability compatibility (widening safe)',
        'Primary key structure composition'
      ],
      doesNotEstablish: [
        'Record presence or count parity',
        'Row or attribute value equality',
        'Check constraints or trigger equivalence'
      ],
      limitations: [
        'Evaluates DDL metadata only',
        'An empty target table passes structural validation'
      ]
    },
    {
      level: 'CARDINALITY',
      stepNumber: '02',
      title: 'Cardinality Assurance',
      subtitle: 'Inherits Structural + Record quantity equivalence across applicable scope.',
      progressionLabel: '+ Record Quantity',
      capability: 'AVAILABLE',
      establishes: [
        'All structural compatibility obligations',
        'Total record quantity parity (Source == Target)',
        'Filtered record count correspondence'
      ],
      doesNotEstablish: [
        'Record content or attribute values',
        'Row identity or field mapping correctness',
        'Protection against equal-count total corruption'
      ],
      limitations: [
        'Does not inspect record values',
        'Compensating errors (dropped rows + duplicate loads) can pass count parity'
      ]
    },
    {
      level: 'PARTITION_FINGERPRINT',
      stepNumber: '03',
      title: 'Partition Fingerprint',
      subtitle: 'Inherits Cardinality + Partition cryptographic content comparison using canonical row hashes.',
      progressionLabel: '+ Content Comparison',
      capability: 'AVAILABLE',
      establishes: [
        'All structural and cardinality parity obligations',
        'Bit-level row content comparison via SHA-256 partition XOR accumulators',
        'Deterministic partition divergence localization'
      ],
      doesNotEstablish: [
        'Exhaustive attribute-by-attribute proof on matching partitions',
        'Cryptographic Merkle tree structures (uses XOR accumulator)'
      ],
      limitations: [
        'Matching fingerprints provide strong partition comparison evidence but do not constitute exhaustive attribute proof',
        'Symmetric duplicate rows evaluate to zero in XOR accumulator'
      ]
    },
    {
      level: 'COMPLETE_ATTRIBUTE',
      stepNumber: '04',
      title: 'Complete Attribute',
      subtitle: 'Exhaustive canonical logical-value equivalence across all included records and mapped attributes.',
      progressionLabel: '+ Exhaustive Logical Values',
      capability: 'AVAILABLE',
      establishes: [
        'All structural, cardinality, and content obligations',
        'Exhaustive attribute-by-attribute comparison of every mapped field',
        'Disambiguation between NULL and missing document fields',
        'Pinpointed record and column divergence diffing'
      ],
      doesNotEstablish: [
        'Physical raw byte identity across heterogeneous database engines'
      ],
      limitations: [
        'Evaluates canonical logical value equivalence, not raw engine bytes',
        'Irreversible masked columns must be excluded from attribute comparison'
      ]
    }
  ];

  // 2 Temporal Options
  public readonly temporalOptions: TemporalOption[] = [
    {
      id: 'CONSISTENT_STATE',
      title: 'Consistent-State Validation',
      description: 'Validate equivalence against the comparison baseline established in Step 5 for this mission.',
      icon: 'clock',
      capability: 'AVAILABLE'
    },
    {
      id: 'CONTINUOUS',
      title: 'Continuous Validation',
      description: 'Continuously evaluate equivalence across changing data streams using CDC integration.',
      icon: 'refresh-cw',
      capability: 'UNAVAILABLE',
      capabilityNotice: 'Continuous streaming validation requires change data capture stream integration. This capability is not currently available.'
    }
  ];

  // Computed state from Service Draft
  public selectedLevel = computed<AssuranceLevel>(() => {
    return this.vs.newValidationDraft().assuranceLevel || 'PARTITION_FINGERPRINT';
  });

  public selectedCadence = computed<TemporalCadence>(() => {
    return this.vs.newValidationDraft().temporalCadence || 'CONSISTENT_STATE';
  });

  public coverageMode = computed<'EXHAUSTIVE' | 'STATISTICAL_SAMPLE'>(() => {
    return this.vs.newValidationDraft().advancedCoverage?.mode || 'EXHAUSTIVE';
  });

  public samplePercentage = computed<number>(() => {
    return this.vs.newValidationDraft().advancedCoverage?.samplePercentage || 5;
  });

  public exceptionGroups = computed<AssuranceExceptionGroup[]>(() => {
    return this.vs.newValidationDraft().assuranceExceptions || [];
  });

  public activeTier = computed<AssuranceTierCard>(() => {
    const lvl = this.selectedLevel();
    return this.assuranceTiers.find(t => t.level === lvl) || this.assuranceTiers[2];
  });

  public sourceProvider = computed<string>(() => {
    return this.vs.newValidationDraft().sourceProvider || 'Oracle';
  });

  public targetProvider = computed<string>(() => {
    return this.vs.newValidationDraft().targetProvider || 'PostgreSQL';
  });

  public scopedEntitiesCount = computed<number>(() => {
    const draft = this.vs.newValidationDraft();
    const units = draft.comparisonUnits || draft.scopedPairs || [];
    const included = units.filter(u => u.disposition !== 'EXCLUDED');
    return included.length > 0 ? included.length : 303; // Sensible default matching standard mission
  });

  public baselineSummaryLabel = computed<string>(() => {
    const draft = this.vs.newValidationDraft();
    if (draft.validationContext === 'EXISTING_PROJECT') {
      return 'Inherited Migration Baseline';
    }
    const intent = draft.baselineIntent;
    switch (intent) {
      case 'CURRENT_OPERATIONAL': return 'Operational Baseline';
      case 'MAINTENANCE_COORDINATED': return 'Coordinated Baseline';
      case 'STATIC_IMMUTABLE': return 'Static Baseline';
      case 'EXTERNAL_REPLICATION': return 'External Replication';
      default: return 'Comparison Baseline';
    }
  });

  // Scoped entities available for exception picking
  public availableScopedEntities = computed<{ id: string; name: string; namespace: string }[]>(() => {
    const draft = this.vs.newValidationDraft();
    const units = draft.comparisonUnits || draft.scopedPairs || [];
    const included = units.filter(u => u.disposition !== 'EXCLUDED');
    if (included.length > 0) {
      return included.map(u => ({
        id: u.sourceId || u.sourceName,
        name: u.sourceName,
        namespace: u.sourceNamespace || 'PUBLIC'
      }));
    }
    // Fallback standard scoped sample entities
    return [
      { id: 'tbl_gl_balances', name: 'GL_BALANCES', namespace: 'FINANCE' },
      { id: 'tbl_payments', name: 'PAYMENTS', namespace: 'FINANCE' },
      { id: 'tbl_accounts', name: 'ACCOUNTS', namespace: 'BANKING' },
      { id: 'tbl_audit_logs', name: 'AUDIT_LOGS', namespace: 'AUDIT' },
      { id: 'tbl_transactions', name: 'TRANSACTIONS', namespace: 'FINANCE' },
      { id: 'tbl_users', name: 'USERS', namespace: 'CORE' },
      { id: 'tbl_sessions', name: 'SESSIONS_ARCHIVE', namespace: 'LOGGING' }
    ];
  });

  public filteredScopedObjects = computed(() => {
    const q = this.objectSearchQuery().trim().toLowerCase();
    const list = this.availableScopedEntities();
    if (!q) return list;
    return list.filter(o => o.name.toLowerCase().includes(q) || o.namespace.toLowerCase().includes(q));
  });

  public escalatedObjectsCount = computed<number>(() => {
    return this.exceptionGroups()
      .filter(g => g.type === 'ESCALATED')
      .reduce((sum, g) => sum + g.objectIds.length, 0);
  });

  public reducedObjectsCount = computed<number>(() => {
    return this.exceptionGroups()
      .filter(g => g.type === 'REDUCED')
      .reduce((sum, g) => sum + g.objectIds.length, 0);
  });

  public defaultObjectsCount = computed<number>(() => {
    const total = this.scopedEntitiesCount();
    const totalExceptions = this.escalatedObjectsCount() + this.reducedObjectsCount();
    return Math.max(0, total - totalExceptions);
  });

  constructor(vs?: ValidationUiService) {
    this.vs = vs || inject(ValidationUiService);
  }

  public selectAssuranceLevel(level: AssuranceLevel): void {
    const tier = this.assuranceTiers.find(t => t.level === level);
    if (tier && tier.capability === 'UNAVAILABLE') return;

    this.vs.updateDraft({ assuranceLevel: level });
  }

  public selectTemporalCadence(cadence: TemporalCadence): void {
    const opt = this.temporalOptions.find(t => t.id === cadence);
    if (opt && opt.capability === 'UNAVAILABLE') {
      // In unavailable state, update draft to reflect operator selection so unavailable warning is rendered
      this.vs.updateDraft({ temporalCadence: cadence });
      return;
    }
    this.vs.updateDraft({ temporalCadence: cadence });
  }

  public toggleAdvancedCoverage(): void {
    this.isAdvancedCoverageOpen.update(v => !v);
  }

  public selectCoverageMode(mode: 'EXHAUSTIVE' | 'STATISTICAL_SAMPLE'): void {
    this.vs.updateDraft({
      coveragePolicy: mode === 'EXHAUSTIVE' ? 'EXHAUSTIVE' : 'LIMITED_SAMPLE',
      advancedCoverage: {
        mode,
        samplePercentage: mode === 'STATISTICAL_SAMPLE' ? this.samplePercentage() : undefined,
        deterministicSeed: 42,
        disclaimer: 'Limited or sampled coverage proves only the inspected subset and does not constitute exhaustive validation.'
      }
    });
  }

  public onSamplePercentageChange(pct: number): void {
    this.vs.updateDraft({
      advancedCoverage: {
        mode: 'STATISTICAL_SAMPLE',
        samplePercentage: Number(pct),
        deterministicSeed: 42,
        disclaimer: 'Limited or sampled coverage proves only the inspected subset and does not constitute exhaustive validation.'
      }
    });
  }

  public isTierSubsumed(level: AssuranceLevel): boolean {
    const currentLevel = this.selectedLevel();
    const rank: Record<AssuranceLevel, number> = {
      'STRUCTURAL': 1,
      'CARDINALITY': 2,
      'PARTITION_FINGERPRINT': 3,
      'COMPLETE_ATTRIBUTE': 4
    };
    return rank[currentLevel] > rank[level];
  }

  public getTierTitle(level: AssuranceLevel): string {
    const tier = this.assuranceTiers.find(t => t.level === level);
    return tier ? tier.title : level;
  }

  @HostListener('document:keydown.escape')
  public handleEscapeKey(): void {
    if (this.showExceptionModal()) {
      this.closeExceptionModal();
    }
  }

  public ngAfterViewInit(): void {
    this.attachModalToBody();
  }

  public ngOnDestroy(): void {
    this.detachModalFromBody();
  }

  public attachModalToBody(): void {
    if (this.exceptionModalEl?.nativeElement && !this.modalAttachedToBody) {
      document.body.appendChild(this.exceptionModalEl.nativeElement);
      this.modalAttachedToBody = true;
    }
  }

  private detachModalFromBody(): void {
    if (this.modalAttachedToBody && this.exceptionModalEl?.nativeElement) {
      if (this.exceptionModalEl.nativeElement.parentNode === document.body) {
        document.body.removeChild(this.exceptionModalEl.nativeElement);
      }
      this.modalAttachedToBody = false;
    }
  }

  public openAddExceptionModal(): void {
    this.draftExceptionType.set('ESCALATED');
    this.draftTargetLevel.set('COMPLETE_ATTRIBUTE');
    this.draftReason.set('');
    this.draftSelectedObjectIds.set([]);
    this.objectSearchQuery.set('');
    this.showExceptionModal.set(true);
    setTimeout(() => this.attachModalToBody(), 0);
  }

  public closeExceptionModal(): void {
    this.showExceptionModal.set(false);
  }

  public isDraftReasonInvalid(): boolean {
    return this.draftReason().trim().length === 0;
  }

  public isObjectSelected(id: string): boolean {
    return this.draftSelectedObjectIds().includes(id);
  }

  public toggleObjectSelection(id: string): void {
    this.draftSelectedObjectIds.update(current => {
      if (current.includes(id)) {
        return current.filter(item => item !== id);
      } else {
        return [...current, id];
      }
    });
  }

  public selectAllFilteredObjects(): void {
    const ids = this.filteredScopedObjects().map(o => o.id);
    this.draftSelectedObjectIds.update(current => {
      const merged = new Set([...current, ...ids]);
      return Array.from(merged);
    });
  }

  public saveExceptionGroup(): void {
    if (this.isDraftReasonInvalid() || this.draftSelectedObjectIds().length === 0) {
      return;
    }

    const selectedIds = this.draftSelectedObjectIds();
    const allEntities = this.availableScopedEntities();
    const selectedNames = allEntities
      .filter(e => selectedIds.includes(e.id))
      .map(e => e.name);

    const newGroup: AssuranceExceptionGroup = {
      id: 'exc-' + Date.now().toString(36),
      type: this.draftExceptionType(),
      targetAssuranceLevel: this.draftTargetLevel(),
      reason: this.draftReason().trim(),
      objectIds: selectedIds,
      objectNames: selectedNames
    };

    const currentGroups = this.exceptionGroups();
    this.vs.updateDraft({
      assuranceExceptions: [...currentGroups, newGroup]
    });

    this.closeExceptionModal();
  }

  public removeExceptionGroup(id: string): void {
    const updated = this.exceptionGroups().filter(g => g.id !== id);
    this.vs.updateDraft({
      assuranceExceptions: updated
    });
  }

  public applyContextualRecommendation(finding: ContextualIntelligenceFinding): void {
    if (finding.recommendedAssuranceLevel) {
      this.selectAssuranceLevel(finding.recommendedAssuranceLevel);
      finding.isAccepted = true;
    }
  }

  public dismissContextualFinding(): void {
    this.contextualFinding.update(f => f ? { ...f, isDismissed: true } : null);
  }

  public getTierIcon(level: AssuranceLevel): string {
    switch (level) {
      case 'STRUCTURAL':
        return 'layers';
      case 'CARDINALITY':
        return 'hash';
      case 'PARTITION_FINGERPRINT':
        return 'fingerprint';
      case 'COMPLETE_ATTRIBUTE':
        return 'shield-check';
      default:
        return 'layers';
    }
  }

  public getProviderIcon(provider?: string): string {
    switch (provider) {
      case 'Oracle':
      case 'PostgreSQL':
      case 'MySQL':
      case 'SQL Server':
        return 'database';
      case 'Snowflake':
        return 'snowflake';
      case 'MongoDB':
        return 'leaf';
      default:
        return 'database';
    }
  }
}
