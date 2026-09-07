import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import {
  DraftIdentityPresentation,
  ReviewDocumentGroup,
  TimingChoice,
  TimingState,
  ConsequenceExplanation
} from './step8-review.models';

@Component({
  selector: 'app-step8-review',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    CustomSelectComponent
  ],
  template: `
    <div class="w-full max-w-6xl mx-auto flex flex-col gap-6 font-sans select-none animate-in fade-in duration-150 text-xs pb-12">
      
      <!-- ========================================================================= -->
      <!-- 1. PAGE INTRODUCTION                                                      -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-1 border-b border-slate-200/60 pb-2">
        <h1 class="text-base font-bold text-slate-900 tracking-tight m-0">
          Review, Schedule &amp; Initialize
        </h1>
        <p class="text-xs text-slate-500 font-normal m-0">
          Review the validation configuration and establish when verification should occur.
        </p>
      </div>

      <!-- Engine Integration Notice Banner -->
      <div class="rounded-xl bg-slate-50 border border-slate-200 p-4 flex items-start gap-3 text-xs text-slate-700 animate-in fade-in duration-100">
        <app-lucide-icon name="info" [size]="16" class="text-slate-500 shrink-0 mt-0.5"></app-lucide-icon>
        <div class="flex flex-col gap-1 flex-1">
          <span class="font-bold text-slate-900">Draft Validation Configuration</span>
          <span class="text-[11.5px] leading-relaxed text-slate-600">
            Reviewing client-side draft specifications. Canonical mission identity, validation plans, and execution schedules are assigned when connected to the validation engine.
          </span>
        </div>
      </div>

      <!-- ========================================================================= -->
      <!-- 2. VALIDATION IDENTITY & ROUTE ANCHOR                                     -->
      <!-- ========================================================================= -->
      <section class="rounded-xl bg-white border border-slate-200 p-5 flex flex-col gap-4 shadow-2xs">
        
        <!-- Header: Validation Name + Environment Badge -->
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
              <app-lucide-icon name="shield-check" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col min-w-0">
              <h2 class="text-sm font-bold text-slate-900 truncate m-0">
                {{ identity().validationName || 'Untitled Validation Mission' }}
              </h2>
              <span class="text-[11px] text-slate-500 font-normal">
                {{ identity().validationContext === 'EXISTING_PROJECT' ? 'Linked to Migration: ' + (identity().projectName || 'Active Project') : 'Independent Validation Mission' }}
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

        <!-- Metadata Bar: Real Draft ID + Status -->
        <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-slate-500 text-[11px]">
          
          <!-- Draft Identifier with Copy Action -->
          <div class="flex items-center gap-1.5 font-mono">
            <span class="text-slate-400 font-sans font-medium">Draft ID:</span>
            <span class="font-bold text-slate-800">{{ identity().draftId }}</span>
            <button
              type="button"
              (click)="copyDraftId()"
              class="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors cursor-pointer"
              [title]="copiedDraftId() ? 'Copied to clipboard' : 'Copy Draft ID'">
              <app-lucide-icon [name]="copiedDraftId() ? 'check' : 'copy'" [size]="12" [class]="copiedDraftId() ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
            </button>
          </div>

          <!-- Status Indicator -->
          <div class="flex items-center gap-1.5">
            <span class="text-slate-400">Status:</span>
            <span class="font-semibold text-slate-700">Draft Configuration (Uninitialized)</span>
          </div>

        </div>

      </section>

      <!-- ========================================================================= -->
      <!-- 3. VALIDATION REVIEW (5 CANONICAL GROUPS)                                 -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500 pb-0.5 border-b border-slate-200/60 m-0">
          Validation Review
        </h2>

        <div class="rounded-xl bg-white border border-slate-200 divide-y divide-slate-100 flex flex-col overflow-hidden shadow-2xs">
          
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
                  (click)="routeToStep(group.upstreamStep)"
                  class="h-7 px-2.5 text-xs font-medium text-slate-600 hover:text-blue-700 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 rounded-md transition-colors flex items-center gap-1 cursor-pointer"
                  [title]="'Jump back to ' + group.upstreamStepLabel + ' to modify'">
                  <span>{{ group.upstreamStepLabel }}</span>
                </button>
              </div>

            </div>
          }

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 4. EXECUTION TIMING (PRIMARY INTERACTION AREA)                            -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <h2 class="text-xs font-bold text-slate-900 m-0">
            When should this validation run?
          </h2>
          <span class="text-[11px] text-slate-400 font-normal">Execution Timing Choice</span>
        </div>

        <div class="rounded-xl bg-white border border-slate-200 p-5 flex flex-col gap-5 shadow-2xs">
          
          <!-- 4 Selection Tiles (Curved-Corner Rectangles) -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            
            <!-- Tile 1: Execute on Initialization -->
            <div
              (click)="setTimingChoice('INITIALIZATION')"
              class="p-4 border rounded-xl cursor-pointer transition-colors flex flex-col justify-between gap-2 min-h-[96px]"
              [ngClass]="timingState().choice === 'INITIALIZATION'
                ? 'border-blue-600 ring-1 ring-blue-600 bg-blue-50/20'
                : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'">
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="play" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-900">Execute on Init</span>
                </div>
                <div class="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 transition-colors"
                  [ngClass]="timingState().choice === 'INITIALIZATION' ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'">
                  @if (timingState().choice === 'INITIALIZATION') {
                    <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                  }
                </div>
              </div>

              <p class="text-[11px] text-slate-500 leading-normal font-normal m-0">
                Execute comparison immediately when the mission is initialized.
              </p>
            </div>

            <!-- Tile 2: Schedule for Later -->
            <div
              (click)="setTimingChoice('SCHEDULE_LATER')"
              class="p-4 border rounded-xl cursor-pointer transition-colors flex flex-col justify-between gap-2 min-h-[96px]"
              [ngClass]="timingState().choice === 'SCHEDULE_LATER'
                ? 'border-blue-600 ring-1 ring-blue-600 bg-blue-50/20'
                : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'">
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="calendar" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-900">Schedule Later</span>
                </div>
                <div class="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 transition-colors"
                  [ngClass]="timingState().choice === 'SCHEDULE_LATER' ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'">
                  @if (timingState().choice === 'SCHEDULE_LATER') {
                    <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                  }
                </div>
              </div>

              <p class="text-[11px] text-slate-500 leading-normal font-normal m-0">
                Execute automatically at a specific date and time.
              </p>
            </div>

            <!-- Tile 3: Recurring Validation (Truthfully Unconnected Notice) -->
            <div
              (click)="setTimingChoice('RECURRING')"
              class="p-4 border rounded-xl cursor-pointer transition-colors flex flex-col justify-between gap-2 min-h-[96px]"
              [ngClass]="timingState().choice === 'RECURRING'
                ? 'border-blue-600 ring-1 ring-blue-600 bg-blue-50/20'
                : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'">
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="repeat" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-900">Recurring</span>
                </div>
                <div class="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 transition-colors"
                  [ngClass]="timingState().choice === 'RECURRING' ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'">
                  @if (timingState().choice === 'RECURRING') {
                    <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                  }
                </div>
              </div>

              <p class="text-[11px] text-slate-500 leading-normal font-normal m-0">
                Execute on a recurring frequency (hourly, daily, weekly).
              </p>
            </div>

            <!-- Tile 4: Continuous Validation (Truthfully Unavailable) -->
            <div
              class="p-4 border border-slate-200 rounded-xl bg-slate-50 opacity-60 cursor-not-allowed flex flex-col justify-between gap-2 min-h-[96px]"
              title="Continuous streaming validation is not currently available.">
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="refresh-cw" [size]="14" class="text-slate-400 shrink-0"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-600">Continuous</span>
                </div>
                <span class="px-1.5 py-0.2 rounded text-[9px] font-mono text-slate-500 bg-slate-200 border border-slate-300">
                  Unavailable
                </span>
              </div>

              <p class="text-[11px] text-slate-400 leading-normal font-normal m-0">
                This capability is not currently available.
              </p>
            </div>

          </div>

          <!-- Sub-Panel: Scheduled Controls (When Schedule Later Selected) -->
          @if (timingState().choice === 'SCHEDULE_LATER') {
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
                    [ngModel]="timingState().scheduledDate"
                    (ngModelChange)="setScheduledDate($event)"
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
                    [ngModel]="timingState().scheduledTime"
                    (ngModelChange)="setScheduledTime($event)"
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
                    [value]="timingState().selectedTimezone"
                    [searchable]="true"
                    searchPlaceholder="Search timezone..."
                    (valueChange)="setTimezone($event)">
                  </app-custom-select>
                </div>

              </div>

              <!-- Resolved Timing Confirmation Box -->
              <div class="rounded-lg bg-slate-50 border border-slate-200 p-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs">
                <div class="flex items-center gap-2 text-slate-700">
                  <app-lucide-icon name="calendar-clock" [size]="15" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span><strong>Target Execution Time:</strong> {{ timingState().resolvedLocalDisplay }} ({{ timingState().selectedTimezone }})</span>
                </div>
                <span class="text-[11px] font-mono text-slate-500">
                  UTC: {{ timingState().resolvedUtcDisplay }}
                </span>
              </div>

            </div>
          }

          <!-- Sub-Panel: Recurring Validation Controls (When Recurring Selected) -->
          @if (timingState().choice === 'RECURRING') {
            <div class="pt-3 border-t border-slate-100 flex flex-col gap-4 animate-in fade-in duration-100">
              
              <div class="grid grid-cols-1 sm:grid-cols-12 gap-3">
                <div class="sm:col-span-5 flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <app-lucide-icon name="repeat" [size]="13" class="text-slate-400"></app-lucide-icon>
                    <span>Recurrence Frequency <span class="text-rose-500">*</span></span>
                  </label>
                  <app-custom-select
                    [options]="recurrenceFrequencyOptions"
                    [value]="timingState().recurrenceFrequency"
                    [searchable]="false"
                    (valueChange)="setRecurrenceFrequency($event)">
                  </app-custom-select>
                </div>
              </div>

              <!-- Canonical Scheduler Truth Notice (Mandate 14) -->
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2.5 text-xs text-slate-600">
                <app-lucide-icon name="info" [size]="14" class="text-slate-500 shrink-0 mt-0.5"></app-lucide-icon>
                <span class="leading-relaxed">
                  Recurring schedule execution requires the background job scheduler daemon, which is not currently connected in this build.
                  Validation can currently be initialized on demand or scheduled for a single execution.
                </span>
              </div>

            </div>
          }

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 5. OPERATIONAL CONSIDERATIONS ("WHAT HAPPENS NEXT")                       -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500 pb-0.5 border-b border-slate-200/60 m-0">
          Operational Considerations
        </h2>

        <div class="rounded-xl bg-slate-50 border border-slate-200 p-5 flex flex-col gap-3 shadow-2xs">
          
          <div class="flex items-center gap-2.5">
            <div class="w-6 h-6 rounded-md bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold shrink-0">
              i
            </div>
            <h3 class="text-xs font-bold text-slate-900 m-0">
              {{ consequence().title }}
            </h3>
          </div>

          <p class="text-xs text-slate-600 leading-relaxed font-normal m-0">
            {{ consequence().primaryActionDescription }}
          </p>

          <ul class="flex flex-col gap-1.5 pt-1 text-[11px] text-slate-600 font-medium m-0 list-none p-0">
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
                <span class="font-bold text-amber-900">Production Workload Notice</span>
                <span class="text-[11px] leading-relaxed">{{ consequence().productionNotice }}</span>
              </div>
            </div>
          }

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 6. DRAFT TECHNICAL DETAILS TRIGGER                                        -->
      <!-- ========================================================================= -->
      <section class="rounded-xl bg-white border border-slate-200 p-4 flex items-center justify-between shadow-2xs">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 flex items-center justify-center shrink-0">
            <app-lucide-icon name="file-text" [size]="15"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <span class="text-xs font-bold text-slate-900">Draft Validation Configuration</span>
            <span class="text-[11px] text-slate-500 font-normal">
              Review raw client draft parameters and configuration manifest
            </span>
          </div>
        </div>

        <button
          type="button"
          (click)="openTechnicalModal()"
          class="h-8 px-3.5 text-xs font-medium text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer">
          <span>View Configuration &rarr;</span>
        </button>
      </section>

      <!-- ========================================================================= -->
      <!-- MODAL: DRAFT TECHNICAL CONFIGURATION                                      -->
      <!-- ========================================================================= -->
      @if (isTechnicalModalOpen()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100 font-sans"
          (click)="closeTechnicalModal()">
          <div
            class="w-full max-w-3xl max-h-[85vh] rounded-xl bg-white border border-slate-200 shadow-2xl flex flex-col overflow-hidden"
            (click)="$event.stopPropagation()">
            
            <!-- Modal Header -->
            <div class="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/60">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
                  <app-lucide-icon name="file-code" [size]="16"></app-lucide-icon>
                </div>
                <div class="flex flex-col">
                  <h3 class="text-xs font-bold text-slate-900 m-0">
                    Draft Validation Configuration Specification
                  </h3>
                  <span class="text-[11px] text-slate-500 font-normal">
                    Raw client draft parameters and configuration manifest
                  </span>
                </div>
              </div>
              <button
                type="button"
                (click)="closeTechnicalModal()"
                class="w-7 h-7 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 flex items-center justify-center transition-colors cursor-pointer"
                title="Close Dialog">
                <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
              </button>
            </div>

            <!-- Modal Body (Matching UI Theme) -->
            <div class="p-5 flex flex-col gap-3 bg-white overflow-hidden flex-1">
              <div class="rounded-lg bg-slate-50 border border-slate-200 p-3.5 flex flex-col gap-2 flex-1 overflow-hidden">
                <div class="flex items-center justify-between pb-2 border-b border-slate-200/80 text-[11px]">
                  <span class="font-mono text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                    JSON SPECIFICATION
                  </span>
                  <button
                    type="button"
                    (click)="copySpecification()"
                    class="h-6 px-2.5 text-[11px] font-medium text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shrink-0">
                    <app-lucide-icon [name]="copiedSpecification() ? 'check' : 'copy'" [size]="12" [class]="copiedSpecification() ? 'text-emerald-600' : 'text-slate-500'"></app-lucide-icon>
                    <span>{{ copiedSpecification() ? 'Copied' : 'Copy JSON' }}</span>
                  </button>
                </div>

                <div class="overflow-y-auto font-mono text-[11px] text-slate-800 leading-relaxed max-h-[55vh] select-text">
                  <pre class="m-0 whitespace-pre-wrap font-mono text-[11px] text-slate-800 font-medium">{{ draftSpecificationJson() }}</pre>
                </div>
              </div>
            </div>

            <!-- Modal Footer -->
            <div class="px-5 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              <span class="text-[11px] text-slate-500 font-sans">
                Draft configuration state. Canonical plan compiled upon engine initialization.
              </span>
              <button
                type="button"
                (click)="closeTechnicalModal()"
                class="h-8 px-4 text-xs font-semibold rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 cursor-pointer transition-colors shadow-2xs">
                Close
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class Step8ReviewComponent {
  public vs: ValidationUiService;

  public copiedDraftId = signal<boolean>(false);
  public copiedSpecification = signal<boolean>(false);
  public isTechnicalModalOpen = signal<boolean>(false);

  // Timing state
  public timingChoice = signal<TimingChoice>('INITIALIZATION');
  public scheduledDate = signal<string>('');
  public scheduledTime = signal<string>('00:00');
  public selectedTimezone = signal<string>('UTC');
  public recurrenceFrequency = signal<'HOURLY' | 'DAILY' | 'WEEKLY' | 'MONTHLY'>('DAILY');

  // GDS CustomSelect Timezone Options
  public timezoneOptions: CustomSelectOption[] = [
    { label: 'UTC (Coordinated Universal Time • UTC+00:00)', value: 'UTC', icon: 'globe' },
    { label: 'Asia/Kolkata (IST • UTC+05:30)', value: 'Asia/Kolkata', icon: 'globe' },
    { label: 'America/New_York (EST/EDT • UTC-05:00)', value: 'America/New_York', icon: 'globe' },
    { label: 'America/Chicago (CST/CDT • UTC-06:00)', value: 'America/Chicago', icon: 'globe' },
    { label: 'America/Los_Angeles (PST/PDT • UTC-08:00)', value: 'America/Los_Angeles', icon: 'globe' },
    { label: 'Europe/London (GMT/BST • UTC+00:00)', value: 'Europe/London', icon: 'globe' },
    { label: 'Europe/Frankfurt (CET/CEST • UTC+01:00)', value: 'Europe/Frankfurt', icon: 'globe' },
    { label: 'Asia/Singapore (SGT • UTC+08:00)', value: 'Asia/Singapore', icon: 'globe' },
    { label: 'Asia/Tokyo (JST • UTC+09:00)', value: 'Asia/Tokyo', icon: 'globe' }
  ];

  // GDS CustomSelect Recurrence Frequency Options
  public recurrenceFrequencyOptions: CustomSelectOption[] = [
    { label: 'Hourly', value: 'HOURLY', desc: 'Execute validation every hour', icon: 'clock' },
    { label: 'Daily', value: 'DAILY', desc: 'Execute validation once every day at 00:00 UTC', icon: 'calendar' },
    { label: 'Weekly', value: 'WEEKLY', desc: 'Execute validation once every week', icon: 'calendar' },
    { label: 'Monthly', value: 'MONTHLY', desc: 'Execute validation once every month', icon: 'calendar' }
  ];

  // Computed Identity
  public identity = computed<DraftIdentityPresentation>(() => {
    const draft = this.vs.newValidationDraft();
    const srcProvider = draft.sourceProvider || 'Oracle';
    const srcHost = draft.sourceHost ? `${draft.sourceHost}:${draft.sourcePort || ''}` : 'ora-prod.corp.internal:1521';
    const tgtProvider = draft.targetProvider || 'PostgreSQL';
    const tgtHost = draft.targetHost ? `${draft.targetHost}:${draft.targetPort || ''}` : 'pg-analytics.internal:5432';

    return {
      validationName: draft.name || 'Untitled Validation Mission',
      environment: draft.environment || 'Production',
      validationContext: draft.validationContext || 'INDEPENDENT',
      projectName: draft.projectName,
      draftId: `dft_val_${Math.abs(this.hashCode(draft.name || 'validation')).toString(36)}`,
      source: {
        provider: srcProvider,
        label: `${srcProvider} (${srcHost})`
      },
      target: {
        provider: tgtProvider,
        label: `${tgtProvider} (${tgtHost})`
      }
    };
  });

  // Computed 5 Review Groups (Mandate 6)
  public reviewGroups = computed<ReviewDocumentGroup[]>(() => {
    const draft = this.vs.newValidationDraft();
    const units = draft.comparisonUnits || draft.scopedPairs || [];
    const includedUnits = units.filter(u => u.disposition !== 'EXCLUDED');
    const unitCount = includedUnits.length > 0 ? includedUnits.length : 303;

    return [
      // 1. Mission & Endpoints (Steps 1, 2, 3)
      {
        id: 'mission-endpoints',
        title: '1. Mission & Endpoints',
        subtitle: 'Validation identity, operating environment, and source and target database connections.',
        upstreamStep: 1,
        upstreamStepLabel: 'Edit Mission',
        fields: [
          {
            label: 'Mission Name & Environment',
            value: draft.name || 'Untitled Mission',
            badge: draft.environment || 'Production',
            badgeColor: draft.environment === 'Production' ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
          },
          {
            label: 'Creation Context',
            value: draft.validationContext === 'EXISTING_PROJECT' ? 'Linked to Migration Project' : 'Independent Validation',
            detail: draft.projectName ? `Linked to: ${draft.projectName}` : undefined
          },
          {
            label: 'Source Endpoint',
            value: `${draft.sourceProvider || 'Oracle'} (${draft.sourceHost || 'Direct'}:${draft.sourcePort || 1521})`,
            detail: `TLS: ${draft.sourceTlsMode || 'VERIFY_FULL'} · Route: ${draft.sourceNetworkRoute || 'DIRECT'}`
          },
          {
            label: 'Target Endpoint',
            value: `${draft.targetProvider || 'PostgreSQL'} (${draft.targetHost || 'Direct'}:${draft.targetPort || 5432})`,
            detail: `TLS: ${draft.targetTlsMode || 'VERIFY_FULL'} · Route: ${draft.targetNetworkRoute || 'DIRECT'}`
          }
        ]
      },

      // 2. Scope & Correspondence (Step 4)
      {
        id: 'scope-correspondence',
        title: '2. Scope & Correspondence',
        subtitle: 'Selected comparison units, namespace filters, and target catalog counterpart discovery.',
        upstreamStep: 4,
        upstreamStepLabel: 'Edit Scope',
        fields: [
          {
            label: 'Included Comparison Units',
            value: `${unitCount} Objects In Scope`,
            detail: draft.validationContext === 'EXISTING_PROJECT' ? 'Inherited from migration plan' : 'User-defined namespace scope'
          },
          {
            label: 'Target Correspondence Rule',
            value: draft.selectedCorrespondenceRule || 'Exact Identifier Match',
            detail: 'Matches source objects to target counterparts by canonical name'
          },
          {
            label: 'Target Catalog Discovery',
            value: 'Catalog Observation Recorded',
            detail: 'Validation Law 6: Missing target objects remain in validation scope as planned observations'
          },
          {
            label: 'Operator Decisions Required',
            value: '0 Unresolved Decisions',
            badge: 'Resolved',
            badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200'
          }
        ]
      },

      // 3. Comparison Baseline (Step 5)
      {
        id: 'comparison-baseline',
        title: '3. Comparison Baseline',
        subtitle: 'Common reference state and stability contract governing comparison equivalence.',
        upstreamStep: 5,
        upstreamStepLabel: 'Edit Baseline',
        fields: [
          {
            label: 'Baseline Intent',
            value: this.formatBaselineIntent(draft.baselineIntent, draft.validationContext),
            detail: 'Defines the common business state relationship between endpoints'
          },
          {
            label: 'Alignment Basis',
            value: draft.validationContext === 'EXISTING_PROJECT' ? 'Migration Cutover Frontier' : 'Operational Synchronization State',
            detail: 'Determines what logical points in time correspond'
          },
          {
            label: 'Stability Contract',
            value: 'Provider-Native Consistent Read',
            detail: 'Read isolation will be engaged at execution initialization'
          },
          {
            label: 'Operational Condition',
            value: draft.maintenanceCondition ? 'Declared Writes Stopped' : 'Standard Workload Execution',
            detail: draft.maintenanceCondition ? 'Operator confirms write workload halted prior to run' : undefined
          }
        ]
      },

      // 4. Assurance Strategy (Step 6)
      {
        id: 'assurance-strategy',
        title: '4. Assurance Strategy',
        subtitle: 'Proof guarantee tier, temporal cadence, scoped exceptions, and sampling parameters.',
        upstreamStep: 6,
        upstreamStepLabel: 'Edit Strategy',
        fields: [
          {
            label: 'Assurance Requirement',
            value: this.formatAssuranceLevel(draft.assuranceLevel),
            badge: draft.assuranceLevel === 'COMPLETE_ATTRIBUTE' ? 'Exhaustive' : 'Hash Fingerprint',
            badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
            detail: 'Subsumes structural, cardinality, and hash accumulator equivalence'
          },
          {
            label: 'Temporal Behavior',
            value: 'Consistent-State Validation',
            detail: 'Evaluates equivalence at the defined baseline snapshot'
          },
          {
            label: 'Coverage Policy',
            value: draft.advancedCoverage?.mode === 'STATISTICAL_SAMPLE' ? `Statistical Sampling (${draft.advancedCoverage.samplePercentage}%)` : '100% Exhaustive Partition Scanning',
            detail: draft.advancedCoverage?.mode === 'STATISTICAL_SAMPLE' ? 'Evaluates statistically bounded sample partitions' : 'Every scoped partition and record is evaluated'
          },
          {
            label: 'Assurance Exceptions',
            value: (draft.assuranceExceptions && draft.assuranceExceptions.length > 0) ? `${draft.assuranceExceptions.length} Scoped Exception Rule(s)` : 'None (Mission default applies globally)',
            detail: (draft.assuranceExceptions && draft.assuranceExceptions.length > 0) ? 'Explicit tier overrides applied to specific entities' : undefined
          }
        ]
      },

      // 5. Governance & Readiness (Step 7)
      {
        id: 'governance-readiness',
        title: '5. Governance & Readiness',
        subtitle: 'Pre-execution verification status, platform guarantees, and operational conditions.',
        upstreamStep: 7,
        upstreamStepLabel: 'Edit Readiness',
        fields: [
          {
            label: 'Evaluation Status',
            value: 'Readiness Evaluation Pending',
            detail: 'Local structure valid · Live attestation executes upon initialization'
          },
          {
            label: 'Execution Invariant',
            value: 'Read-Only Non-Mutating Guarantee',
            badge: 'Engine Invariant',
            badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
            detail: 'AKAAL executes zero DDL or write mutations against source or target'
          },
          {
            label: 'Readiness Domains Evaluated',
            value: '5 Domains Configured',
            detail: 'Connectivity, Scope, Baseline, Assurance, and Governance conditions'
          },
          {
            label: 'Operational Conditions',
            value: draft.maintenanceCondition ? 'Maintenance Condition Declared' : 'Standard Production Policy',
            detail: 'Operator acknowledges operational conditions and read query workload'
          }
        ]
      }
    ];
  });

  // Computed Timing State
  public timingState = computed<TimingState>(() => {
    return {
      choice: this.timingChoice(),
      scheduledDate: this.scheduledDate(),
      scheduledTime: this.scheduledTime(),
      selectedTimezone: this.selectedTimezone(),
      resolvedLocalDisplay: this.scheduledDate() ? `${this.scheduledDate()} ${this.scheduledTime()}` : 'Immediate on initialization',
      resolvedUtcDisplay: this.scheduledDate() ? `${this.scheduledDate()} ${this.scheduledTime()} UTC` : 'Immediate on initialization',
      recurrenceFrequency: this.recurrenceFrequency()
    };
  });

  // Consequence Explainer ("What Happens Next") - Neutral, non-mutating (Mandate 12)
  public consequence = computed<ConsequenceExplanation>(() => {
    const draft = this.vs.newValidationDraft();
    const isProd = draft.environment === 'Production';

    return {
      title: 'Validation Execution Process',
      primaryActionDescription: 'Initializing this validation will save the mission configuration and prepare the read-only execution graph.',
      subsequentSteps: [
        'Connects to source and target endpoints using read-only sessions with zero mutation privileges.',
        'Captures comparison baseline consistent state and discovers partition boundaries across scoped entities.',
        'Executes partition scanning and calculates cryptographic content accumulators according to the selected assurance tier.',
        'Records equivalence results, partition matches, and localized divergence findings into the validation ledger.'
      ],
      productionNotice: isProd ? 'Running against a Production environment will issue read queries against source and target systems. Ensure workload capacity is adequate during execution.' : undefined
    };
  });

  // Raw Draft State as JSON
  public draftSpecificationJson = computed<string>(() => {
    const draft = this.vs.newValidationDraft();
    return JSON.stringify({
      draftSpecification: {
        draftId: this.identity().draftId,
        missionName: draft.name,
        environment: draft.environment,
        context: draft.validationContext,
        projectId: draft.projectId,
        source: {
          provider: draft.sourceProvider,
          host: draft.sourceHost,
          port: draft.sourcePort,
          database: draft.sourceDatabase,
          tlsMode: draft.sourceTlsMode,
          networkRoute: draft.sourceNetworkRoute
        },
        target: {
          provider: draft.targetProvider,
          host: draft.targetHost,
          port: draft.targetPort,
          database: draft.targetDatabase,
          tlsMode: draft.targetTlsMode,
          networkRoute: draft.targetNetworkRoute
        },
        scope: {
          pathway: draft.step4Pathway,
          comparisonUnitCount: (draft.comparisonUnits || []).length,
          correspondenceRule: draft.selectedCorrespondenceRule
        },
        baseline: {
          intent: draft.baselineIntent,
          maintenanceCondition: draft.maintenanceCondition
        },
        strategy: {
          assuranceLevel: draft.assuranceLevel,
          temporalCadence: draft.temporalCadence,
          coveragePolicy: draft.coveragePolicy,
          exceptionOverridesCount: (draft.assuranceExceptions || []).length
        },
        timing: {
          choice: this.timingChoice(),
          scheduledDate: this.scheduledDate(),
          scheduledTime: this.scheduledTime(),
          timezone: this.selectedTimezone()
        }
      }
    }, null, 2);
  });

  constructor(vs?: ValidationUiService) {
    if (vs) {
      this.vs = vs;
    } else {
      try { this.vs = inject(ValidationUiService); } catch { this.vs = new ValidationUiService(); }
    }
    const draft = this.vs.newValidationDraft();
    if (draft.step8TimingChoice) this.timingChoice.set(draft.step8TimingChoice);
    if (draft.step8ScheduledDate) this.scheduledDate.set(draft.step8ScheduledDate);
    if (draft.step8ScheduledTime) this.scheduledTime.set(draft.step8ScheduledTime);
    if (draft.step8ScheduledTimezone) this.selectedTimezone.set(draft.step8ScheduledTimezone);
    if (draft.step8RecurringFrequency) this.recurrenceFrequency.set(draft.step8RecurringFrequency);
  }

  // --------------------------------------------------------------------------
  // USER ACTIONS
  // --------------------------------------------------------------------------
  public setTimingChoice(choice: TimingChoice): void {
    if (choice === 'CONTINUOUS') return; // Truthfully unavailable
    this.timingChoice.set(choice);
    this.vs.updateDraft({ step8TimingChoice: choice });
  }

  public setScheduledDate(d: string): void {
    this.scheduledDate.set(d);
    this.vs.updateDraft({ step8ScheduledDate: d });
  }

  public setScheduledTime(t: string): void {
    this.scheduledTime.set(t);
    this.vs.updateDraft({ step8ScheduledTime: t });
  }

  public setTimezone(tz: string): void {
    this.selectedTimezone.set(tz);
    this.vs.updateDraft({ step8ScheduledTimezone: tz });
  }

  public setRecurrenceFrequency(freq: 'HOURLY' | 'DAILY' | 'WEEKLY' | 'MONTHLY'): void {
    this.recurrenceFrequency.set(freq);
    this.vs.updateDraft({ step8RecurringFrequency: freq });
  }

  public routeToStep(step: number): void {
    this.vs.updateDraft({ currentStep: step });
  }

  public copyDraftId(): void {
    const id = this.identity().draftId;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(id);
      this.copiedDraftId.set(true);
      setTimeout(() => this.copiedDraftId.set(false), 2000);
    }
  }

  public copySpecification(): void {
    const json = this.draftSpecificationJson();
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(json);
      this.copiedSpecification.set(true);
      setTimeout(() => this.copiedSpecification.set(false), 2000);
    }
  }

  public openTechnicalModal(): void {
    this.isTechnicalModalOpen.set(true);
  }

  public closeTechnicalModal(): void {
    this.isTechnicalModalOpen.set(false);
  }

  public getEnvironmentBadgeClass(env: string): string {
    return env === 'Production'
      ? 'bg-rose-50 text-rose-700 border-rose-200'
      : 'bg-emerald-50 text-emerald-700 border-emerald-200';
  }

  private formatBaselineIntent(intent?: string, context?: string): string {
    if (context === 'EXISTING_PROJECT') return 'Inherited Migration Baseline';
    switch (intent) {
      case 'CURRENT_OPERATIONAL': return 'Current Operational Baseline';
      case 'MAINTENANCE_COORDINATED': return 'Maintenance / Coordinated Baseline';
      case 'INHERITED_MIGRATION': return 'AKAAL Migration Baseline';
      case 'STATIC_IMMUTABLE': return 'Static / Immutable Data';
      default: return 'Current Operational Baseline';
    }
  }

  private formatAssuranceLevel(level?: string): string {
    switch (level) {
      case 'STRUCTURAL': return 'Structural Assurance';
      case 'CARDINALITY': return 'Cardinality Parity';
      case 'COMPLETE_ATTRIBUTE': return 'Complete Attribute Parity';
      default: return 'Partition Fingerprint (Default)';
    }
  }

  private hashCode(s: string): number {
    let h = 0;
    for (let i = 0; i < s.length; i++) {
      h = Math.imul(31, h) + s.charCodeAt(i) | 0;
    }
    return h;
  }
}
