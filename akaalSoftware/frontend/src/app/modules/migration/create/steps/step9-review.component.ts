// ============================================================================
// AKAAL CREATE MIGRATION — STEP 9: REVIEW, SCHEDULE & INITIALIZE
// ROOT STEP 9 COMPONENT (CANONICAL 7-SECTION SINGLE-COLUMN WORKSPACE)
// ============================================================================

import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step9ReviewStoreService } from '../../../../core/services/step9-review-store.service';
import { Step9TechnicalModalComponent } from './step9-technical-modal.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-step9-review',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    CustomSelectComponent,
    Step9TechnicalModalComponent
  ],
  template: `
    <div class="w-full max-w-6xl mx-auto flex flex-col gap-6 font-sans select-none animate-in fade-in duration-150 text-xs pb-10">
      
      <!-- ========================================================================= -->
      <!-- 1. PAGE INTRODUCTION                                                      -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-1 border-b border-slate-200/60 pb-2">
        <h1 class="text-base font-bold text-slate-900 tracking-tight">
          Review, Schedule &amp; Initialize
        </h1>
        <p class="text-xs text-slate-500 font-normal">
          Review the governed migration plan and choose when AKAAL should begin.
        </p>
      </div>

      <!-- ERROR BANNER (When IPC or initialization errors occur) -->
      @if (store.operationError(); as err) {
        <div class="rounded-xl bg-rose-50 border border-rose-200 p-4 flex items-start gap-3 text-xs text-rose-800 animate-in fade-in duration-100">
          <app-lucide-icon name="alert-triangle" [size]="16" class="text-rose-600 shrink-0 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-1 flex-1">
            <span class="font-bold text-rose-900">{{ err.title }}</span>
            <span class="leading-relaxed">{{ err.message }}</span>
            @if (err.recoveryGuidance) {
              <span class="text-[11px] text-rose-700 font-medium mt-0.5">{{ err.recoveryGuidance }}</span>
            }
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- 2. MIGRATION IDENTITY & ROUTE                                             -->
      <!-- ========================================================================= -->
      <section class="rounded-xl bg-white border border-slate-200 p-5 flex flex-col gap-4">
        
        <!-- Header: Migration Name + Environment Badge -->
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
              <app-lucide-icon name="layers" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col min-w-0">
              <h2 class="text-sm font-bold text-slate-900 truncate">
                {{ identity().migrationName }}
              </h2>
              <span class="text-[11px] text-slate-500 font-normal">
                {{ identity().modeTitle }}
              </span>
            </div>
          </div>

          <span
            class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border shrink-0"
            [ngClass]="getEnvironmentBadgeClass(identity().environment)">
            {{ identity().environment }}
          </span>
        </div>

        <!-- Route Visual Anchor: Source -> Target -->
        <div class="grid grid-cols-1 md:grid-cols-11 gap-3 items-center">
          
          <!-- Source Box -->
          <div class="md:col-span-5 rounded-lg bg-slate-50 border border-slate-200 p-3.5 flex flex-col gap-1">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Source Endpoint</span>
              <span class="text-[11px] font-semibold text-slate-700">{{ identity().source.provider }}</span>
            </div>
            <span class="text-xs font-bold text-slate-900 truncate">
              {{ identity().source.label }}
            </span>
          </div>

          <!-- Connecting Arrow -->
          <div class="md:col-span-1 flex items-center justify-center text-slate-400 py-1 md:py-0">
            <app-lucide-icon name="arrow-right" [size]="18" class="text-slate-400"></app-lucide-icon>
          </div>

          <!-- Target Box -->
          <div class="md:col-span-5 rounded-lg bg-slate-50 border border-slate-200 p-3.5 flex flex-col gap-1">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Target Endpoint</span>
              <span class="text-[11px] font-semibold text-slate-700">{{ identity().target.provider }}</span>
            </div>
            <span class="text-xs font-bold text-slate-900 truncate">
              {{ identity().target.label }}
            </span>
          </div>

        </div>

        <!-- Metadata Bar: Real Migration ID + Plan Revision -->
        <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-slate-500 text-[11px]">
          
          <!-- Canonical Migration ID with Copy Action -->
          <div class="flex items-center gap-1.5 font-mono">
            <span class="text-slate-400 font-sans font-medium">Migration ID:</span>
            <span class="font-bold text-slate-800">{{ identity().migrationId }}</span>
            <button
              type="button"
              (click)="copyMigrationId()"
              class="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors cursor-pointer"
              [title]="copiedMigrationId() ? 'Copied to clipboard' : 'Copy Migration ID'">
              <app-lucide-icon [name]="copiedMigrationId() ? 'check' : 'copy'" [size]="12" [class]="copiedMigrationId() ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
            </button>
          </div>

          <!-- Plan Revision -->
          <div class="flex items-center gap-1.5">
            <span class="text-slate-400">Governed Plan:</span>
            <span class="font-semibold text-slate-700">Revision v{{ identity().planRevision }}.0</span>
          </div>

        </div>

      </section>

      <!-- ========================================================================= -->
      <!-- 3. MIGRATION REVIEW (5 DOCUMENT GROUPS)                                   -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500 pb-0.5 border-b border-slate-200/60">
          Migration Review
        </h2>

        <div class="rounded-xl bg-white border border-slate-200 divide-y divide-slate-100 flex flex-col overflow-hidden">
          
          @for (group of reviewGroups(); track group.id) {
            <div class="p-4 lg:p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              
              <!-- Left: Group Info & Fields -->
              <div class="flex flex-col gap-2 flex-1 min-w-0">
                <div class="flex flex-col">
                  <span class="text-xs font-bold text-slate-900">{{ group.title }}</span>
                  <span class="text-[11px] text-slate-500 font-normal">{{ group.subtitle }}</span>
                </div>

                <!-- 2-Column Key-Value Rows -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  @for (field of group.fields; track field.label) {
                    <div class="flex flex-col gap-0.5">
                      <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        {{ field.label }}
                      </span>
                      <div class="flex items-center gap-2">
                        <span class="text-xs font-semibold text-slate-800">
                          {{ field.value }}
                        </span>
                        @if (field.badge) {
                          <span
                            class="px-1.5 py-0.2 text-[9px] font-bold font-mono rounded border uppercase"
                            [ngClass]="field.badgeColor || 'bg-slate-100 text-slate-700 border-slate-200'">
                            {{ field.badge }}
                          </span>
                        }
                      </div>
                      @if (field.detail) {
                        <span class="text-[10px] text-slate-500 font-normal leading-tight">
                          {{ field.detail }}
                        </span>
                      }
                    </div>
                  }
                </div>
              </div>

              <!-- Right: Restrained Upstream Navigation Action -->
              <div class="shrink-0 flex items-center md:self-center">
                <button
                  type="button"
                  (click)="store.routeToUpstreamStep(group.upstreamStep)"
                  class="h-7 px-2.5 text-xs font-medium text-slate-600 hover:text-blue-700 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 rounded-md transition-colors flex items-center gap-1 cursor-pointer"
                  [title]="'Jump back to Step ' + group.upstreamStep + ' to modify'">
                  <span>{{ group.upstreamStepLabel }}</span>
                </button>
              </div>

            </div>
          }

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 4. BEFORE YOU START (DECISION-QUALITY INTELLIGENCE)                        -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500 pb-0.5 border-b border-slate-200/60">
          Before You Start
        </h2>

        <div class="rounded-xl bg-white border border-slate-200 p-5 flex flex-col gap-4">
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            <!-- 1. Data Scale Summary -->
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Data Scale</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200">
                  {{ before().dataScale.evidenceClassification }}
                </span>
              </div>
              <span class="text-xs font-bold text-slate-900">
                {{ before().dataScale.volumeEstimateLabel }}
              </span>
              <span class="text-[11px] text-slate-500 font-normal leading-relaxed">
                {{ before().dataScale.evidenceExplanation }}
              </span>
            </div>

            <!-- 2. Estimated Duration & Confidence -->
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Estimated Duration</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-slate-200 text-slate-700 border border-slate-300">
                  {{ before().duration.confidenceLevel }} CONFIDENCE
                </span>
              </div>
              <span class="text-xs font-bold text-slate-900">
                {{ before().duration.rangeDisplay }}
              </span>
              <span class="text-[11px] text-slate-500 font-normal leading-relaxed">
                {{ before().duration.confidenceExplanation }}
              </span>
            </div>

            <!-- 3. Structural Risk & Residuals -->
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Structural Risk</span>
                <span
                  class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono border uppercase"
                  [ngClass]="getRiskBadgeClass(before().structuralRisk.level)">
                  {{ before().structuralRisk.level }} RISK
                </span>
              </div>
              <span class="text-xs font-semibold text-slate-800">
                {{ before().structuralRisk.summary }}
              </span>
              @if (before().structuralRisk.residualRisks.length > 0) {
                <div class="flex flex-col gap-0.5 mt-0.5">
                  @for (risk of before().structuralRisk.residualRisks; track risk) {
                    <span class="text-[10px] text-slate-500 leading-tight">&bull; {{ risk }}</span>
                  }
                </div>
              }
            </div>

            <!-- 4. Runtime Intervention & Reversibility -->
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Runtime Intervention &amp; Consequence</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-slate-200 text-slate-700 border border-slate-300">
                  {{ before().reversibility.classification }}
                </span>
              </div>
              <span class="text-xs font-semibold text-slate-800">
                {{ before().runtimeIntervention.description }}
              </span>
              <span class="text-[11px] text-slate-500 font-normal leading-relaxed">
                {{ before().reversibility.summary }}
              </span>
            </div>

          </div>

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 5. EXECUTION TIMING (PRIMARY INTERACTION AREA)                            -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <h2 class="text-xs font-bold text-slate-900">
            When should this migration begin?
          </h2>
          <span class="text-[11px] text-slate-400 font-normal">Execution Timing Choice</span>
        </div>

        <div class="rounded-xl bg-white border border-slate-200 p-5 flex flex-col gap-5">
          
          <!-- 2-Column Timing Selection Tiles (Matching Step 1 visual style) -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            
            <!-- Tile 1: Run Now -->
            <div
              (click)="store.setTimingChoice('RUN_NOW')"
              class="p-4 border rounded-xl cursor-pointer bg-white transition-colors flex flex-col justify-between gap-1 min-h-[64px]"
              [class.border-blue-600]="timing().choice === 'RUN_NOW'"
              [class.ring-1]="timing().choice === 'RUN_NOW'"
              [class.ring-blue-600]="timing().choice === 'RUN_NOW'"
              [class.bg-blue-50]="timing().choice === 'RUN_NOW'"
              [class.border-slate-200]="timing().choice !== 'RUN_NOW'"
              [class.hover:border-slate-300]="timing().choice !== 'RUN_NOW'"
              [class.hover:bg-slate-50]="timing().choice !== 'RUN_NOW'">
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="play" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-900">Run Now</span>
                </div>
                @if (timing().choice === 'RUN_NOW') {
                  <div class="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold shrink-0">
                    &check;
                  </div>
                }
              </div>

              <p class="text-[11px] text-slate-500 leading-normal font-normal">
                Initialize this governed plan and begin execution immediately.
              </p>
            </div>

            <!-- Tile 2: Schedule for Later -->
            <div
              (click)="store.setTimingChoice('SCHEDULE_LATER')"
              class="p-4 border rounded-xl cursor-pointer bg-white transition-colors flex flex-col justify-between gap-1 min-h-[64px]"
              [class.border-blue-600]="timing().choice === 'SCHEDULE_LATER'"
              [class.ring-1]="timing().choice === 'SCHEDULE_LATER'"
              [class.ring-blue-600]="timing().choice === 'SCHEDULE_LATER'"
              [class.bg-blue-50]="timing().choice === 'SCHEDULE_LATER'"
              [class.border-slate-200]="timing().choice !== 'SCHEDULE_LATER'"
              [class.hover:border-slate-300]="timing().choice !== 'SCHEDULE_LATER'"
              [class.hover:bg-slate-50]="timing().choice !== 'SCHEDULE_LATER'">
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="calendar" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-900">Schedule for Later</span>
                </div>
                @if (timing().choice === 'SCHEDULE_LATER') {
                  <div class="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold shrink-0">
                    &check;
                  </div>
                }
              </div>

              <p class="text-[11px] text-slate-500 leading-normal font-normal">
                Start automatically at a chosen date and time.
              </p>
            </div>

          </div>

          <!-- Inline Scheduling Controls (Revealed when Schedule for Later is selected) -->
          @if (timing().choice === 'SCHEDULE_LATER') {
            <div class="pt-3 border-t border-slate-100 flex flex-col gap-4 animate-in fade-in duration-100">
              
              <div class="grid grid-cols-1 sm:grid-cols-12 gap-3">
                
                <!-- Date Picker -->
                <div class="sm:col-span-4 flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <app-lucide-icon name="calendar" [size]="13" class="text-slate-400"></app-lucide-icon>
                    <span>Execution Date <span class="text-rose-500">*</span></span>
                  </label>
                  <input
                    type="date"
                    [ngModel]="timing().scheduledDate"
                    (ngModelChange)="store.setScheduledDate($event)"
                    class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-600 transition-colors" />
                </div>

                <!-- Time Picker -->
                <div class="sm:col-span-3 flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <app-lucide-icon name="clock" [size]="13" class="text-slate-400"></app-lucide-icon>
                    <span>Time <span class="text-rose-500">*</span></span>
                  </label>
                  <input
                    type="time"
                    [ngModel]="timing().scheduledTime"
                    (ngModelChange)="store.setScheduledTime($event)"
                    class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-600 transition-colors" />
                </div>

                <!-- Timezone Selector (GDS Custom Select) -->
                <div class="sm:col-span-5 flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <app-lucide-icon name="globe" [size]="13" class="text-slate-400"></app-lucide-icon>
                    <span>Timezone <span class="text-rose-500">*</span></span>
                  </label>
                  <app-custom-select
                    [options]="timezoneOptions"
                    [value]="timing().selectedTimezone"
                    [searchable]="true"
                    searchPlaceholder="Search timezone..."
                    (valueChange)="store.setTimezone($event)">
                  </app-custom-select>
                </div>

              </div>

              <!-- Resolved Timing Confirmation Box -->
              <div class="rounded-lg bg-slate-50 border border-slate-200 p-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs">
                <div class="flex items-center gap-2 text-slate-700">
                  <app-lucide-icon name="calendar-clock" [size]="15" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span><strong>Local Target Time:</strong> {{ timing().resolvedLocalDisplay }} ({{ timing().selectedTimezone }})</span>
                </div>
                <span class="text-[11px] font-mono text-slate-500">
                  UTC: {{ timing().resolvedUtcDisplay }}
                </span>
              </div>

              <!-- Progressive Recurrence Option (For non-continuous modes) -->
              @if (timing().isRecurrencePermittedForMode) {
                <div class="flex items-center justify-between pt-1">
                  <label class="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      [checked]="timing().isAdvancedRecurring"
                      (change)="store.toggleAdvancedRecurring()"
                      class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-4 w-4" />
                    <span>Advanced / Recurring Schedule</span>
                  </label>

                  @if (timing().isAdvancedRecurring) {
                    <div class="flex items-center gap-2 text-xs">
                      <span class="text-slate-500 font-medium">Frequency:</span>
                      <select
                        [ngModel]="timing().recurrenceFrequency"
                        (ngModelChange)="store.setRecurrenceFrequency($event)"
                        class="h-8 px-2.5 bg-white border border-slate-200 rounded-md text-xs text-slate-800 focus:outline-none focus:border-blue-600 font-medium">
                        <option value="DAILY">Daily</option>
                        <option value="WEEKLY">Weekly</option>
                        <option value="MONTHLY">Monthly</option>
                      </select>
                    </div>
                  }
                </div>
              }

            </div>
          }

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 6. WHAT HAPPENS NEXT (CONSEQUENCE EXPLAINER)                              -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500 pb-0.5 border-b border-slate-200/60">
          What Happens Next
        </h2>

        <div class="rounded-xl bg-slate-50 border border-slate-200 p-5 flex flex-col gap-3">
          
          <div class="flex items-center gap-2.5">
            <div class="w-6 h-6 rounded-md bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold shrink-0">
              i
            </div>
            <h3 class="text-xs font-bold text-slate-900">
              {{ consequence().title }}
            </h3>
          </div>

          <p class="text-xs text-slate-600 leading-relaxed font-normal">
            {{ consequence().primaryActionDescription }}
          </p>

          <ul class="flex flex-col gap-1.5 pt-1 text-[11px] text-slate-600 font-medium">
            @for (step of consequence().subsequentSteps; track step) {
              <li class="flex items-start gap-2">
                <span class="text-blue-600 font-bold">&bull;</span>
                <span class="leading-relaxed">{{ step }}</span>
              </li>
            }
          </ul>

          @if (consequence().productionNotice) {
            <div class="mt-2 p-3 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-2 text-xs text-amber-800">
              <app-lucide-icon name="shield-alert" [size]="15" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
              <div class="flex flex-col">
                <span class="font-bold text-amber-900">Production Notice</span>
                <span class="text-[11px] leading-relaxed">{{ consequence().productionNotice }}</span>
              </div>
            </div>
          }

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 7. TECHNICAL DETAILS TRIGGER                                              -->
      <!-- ========================================================================= -->
      <section class="rounded-xl bg-white border border-slate-200 p-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 flex items-center justify-center shrink-0">
            <app-lucide-icon name="file-text" [size]="15"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <span class="text-xs font-bold text-slate-900">Plan Technical Details</span>
            <span class="text-[11px] text-slate-500 font-normal">
              Revision v{{ identity().planRevision }}.0 &middot; Cryptographic fingerprint sealed
            </span>
          </div>
        </div>

        <button
          type="button"
          (click)="store.openTechnicalModal()"
          class="h-8 px-3.5 text-xs font-medium text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer">
          <span>View Details &rarr;</span>
        </button>
      </section>

      <!-- Modal Mount -->
      <app-step9-technical-modal></app-step9-technical-modal>

    </div>
  `
})
export class Step9ReviewComponent {
  public store = inject(Step9ReviewStoreService);

  public identity = this.store.migrationIdentity;
  public reviewGroups = this.store.reviewGroups;
  public before = this.store.beforeYouStart;
  public timing = this.store.timingState;
  public consequence = this.store.consequence;
  public copiedMigrationId = signal<boolean>(false);

  // Timezone options for GDS CustomSelect
  public timezoneOptions: CustomSelectOption[] = [
    { label: 'Asia/Kolkata (IST • UTC+05:30)', value: 'Asia/Kolkata', icon: 'globe' },
    { label: 'UTC (Coordinated Universal Time • UTC+00:00)', value: 'UTC', icon: 'globe' },
    { label: 'America/New_York (EST/EDT • UTC-05:00)', value: 'America/New_York', icon: 'globe' },
    { label: 'America/Chicago (CST/CDT • UTC-06:00)', value: 'America/Chicago', icon: 'globe' },
    { label: 'America/Los_Angeles (PST/PDT • UTC-08:00)', value: 'America/Los_Angeles', icon: 'globe' },
    { label: 'Europe/London (GMT/BST • UTC+00:00)', value: 'Europe/London', icon: 'globe' },
    { label: 'Europe/Frankfurt (CET/CEST • UTC+01:00)', value: 'Europe/Frankfurt', icon: 'globe' },
    { label: 'Asia/Singapore (SGT • UTC+08:00)', value: 'Asia/Singapore', icon: 'globe' },
    { label: 'Asia/Tokyo (JST • UTC+09:00)', value: 'Asia/Tokyo', icon: 'globe' },
    { label: 'Australia/Sydney (AEST/AEDT • UTC+10:00)', value: 'Australia/Sydney', icon: 'globe' }
  ];

  public copyMigrationId(): void {
    const id = this.identity().migrationId;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(id);
      this.copiedMigrationId.set(true);
      setTimeout(() => this.copiedMigrationId.set(false), 2000);
    }
  }

  public getEnvironmentBadgeClass(env: string): string {
    switch (env) {
      case 'Production':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'Staging':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      default:
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  }

  public getRiskBadgeClass(level: string): string {
    switch (level) {
      case 'CRITICAL':
      case 'HIGH':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  }
}
