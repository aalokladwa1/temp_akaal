import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../shared/components/custom-select.component';
import { SettingsService } from '../services/settings.service';
import { AssistanceProactivityMode, RecommendationConfidenceLevel } from '../models/settings.models';

@Component({
  selector: 'app-settings-ai-intelligence',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="space-y-8">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div class="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider font-mono">Operational Defaults</div>
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">AI &amp; Intelligence</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure operator assistance modes, plan synthesis advisors, automated tuning heuristics, root cause diagnostics, and recommendation policies.
          </p>
        </div>
        <div class="flex items-center gap-3">
          <button
            type="button"
            (click)="resetDefaults()"
            class="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-2">
            <app-lucide-icon name="rotate-ccw" [size]="14"></app-lucide-icon>
            Reset Defaults
          </button>
        </div>
      </div>

      <!-- Scope Notice Banner -->
      <div class="bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-xl p-4 flex items-start gap-3">
        <div class="w-7 h-7 rounded-lg bg-blue-100/80 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
          <app-lucide-icon name="info" [size]="16"></app-lucide-icon>
        </div>
        <div class="text-xs leading-relaxed text-slate-700 dark:text-slate-300">
          <span class="font-bold text-slate-900 dark:text-slate-100">Governed Intelligence Baseline:</span>
          AKAAL AI and intelligence features act exclusively as an advisory co-pilot. In accordance with platform governance, the assistant cannot execute destructive schema migrations, drop tables, or mutate production data autonomously. All generated suggestions require explicit operator confirmation.
        </div>
      </div>

      <!-- 1. Assistant Configuration -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="sparkles" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">1. Assistant Configuration</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Baseline operator assistance mode, token budget allocation, and endpoint security controls.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('assistantEnabled', !settings().assistantEnabled)"
            [class.bg-blue-600]="settings().assistantEnabled"
            [class.bg-slate-300]="!settings().assistantEnabled"
            [class.dark:bg-slate-700]="!settings().assistantEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().assistantEnabled"
              [class.translate-x-0]="!settings().assistantEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6" [class.opacity-60]="!settings().assistantEnabled">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Assistance Proactivity Mode
            </label>
            <app-custom-select
              [options]="proactivityModeOptions"
              [disabled]="!settings().assistantEnabled"
              [ngModel]="settings().proactivityMode"
              (ngModelChange)="updateSetting('proactivityMode', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Determines when the assistant surfaces contextual insights during authoring.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Request Token Budget (tokens/turn)
            </label>
            <input
              type="number"
              min="500"
              max="16000"
              step="500"
              [disabled]="!settings().assistantEnabled"
              [ngModel]="settings().defaultRequestTokenBudget"
              (ngModelChange)="updateSetting('defaultRequestTokenBudget', +$event)"
              class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Maximum context and response token allocation per interaction (default 4,000).</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Governed Model Endpoint Provider
            </label>
            <input
              type="text"
              readonly
              [value]="settings().governedProviderDisplay"
              class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Model gateway managed centrally by platform policy.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Workspace Monthly Cost Cap
            </label>
            <input
              type="text"
              readonly
              [value]="settings().workspaceMonthlyCostCapDisplay"
              class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Enforced token expenditure limit for current workspace tenant.</p>
          </div>

          <!-- Credential Sanitization Banner -->
          <div class="md:col-span-2 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <app-lucide-icon name="shield-check" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
                Strict Secret &amp; Credential Sanitization Enforced
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Database passwords, API tokens, and private URIs are automatically stripped before model prompts are constructed.
              </div>
            </div>
            <div class="text-xs font-bold text-slate-600 dark:text-slate-300 px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shrink-0">
              Enforced Read-Only
            </div>
          </div>
        </div>
      </section>

      <!-- 2. Planning Assistance -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="file-text" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">2. Planning Assistance</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Automated DAG structure synthesis and table partition strategy advisories.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Plan Synthesis Assistance Toggle -->
          <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Plan Synthesis Assistance</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">Suggests table dependency ordering and parallel execution phases for new plans.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('planSynthesisAssistance', !settings().planSynthesisAssistance)"
              [class.bg-blue-600]="settings().planSynthesisAssistance"
              [class.bg-slate-300]="!settings().planSynthesisAssistance"
              [class.dark:bg-slate-700]="!settings().planSynthesisAssistance"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().planSynthesisAssistance"
                [class.translate-x-0]="!settings().planSynthesisAssistance"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Partition Strategy Recommendation Toggle -->
          <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Partition Strategy Recommendations</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">Recommends keyset vs modulo range partitioning based on table statistics.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('partitionStrategyRecommendation', !settings().partitionStrategyRecommendation)"
              [class.bg-blue-600]="settings().partitionStrategyRecommendation"
              [class.bg-slate-300]="!settings().partitionStrategyRecommendation"
              [class.dark:bg-slate-700]="!settings().partitionStrategyRecommendation"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().partitionStrategyRecommendation"
                [class.translate-x-0]="!settings().partitionStrategyRecommendation"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Mandatory Approval Notice -->
          <div class="md:col-span-2 bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <app-lucide-icon name="user-check" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
                Human Confirmation Required for All Generated Plans
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                AI cannot directly trigger pipeline execution. Generated steps must be inspected and confirmed in the Migration Cockpit.
              </div>
            </div>
            <div class="text-xs font-bold text-blue-700 dark:text-blue-300 px-2.5 py-1 bg-blue-100/60 dark:bg-blue-900/40 border border-blue-200 dark:border-blue-800 rounded-md shrink-0">
              Enforced Policy
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Optimization & Auto-Tuning -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="sliders" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">3. Optimization &amp; Auto-Tuning</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Heuristic recommendations for transaction batch sizing and worker concurrency tuning.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Workload Auto-Tuning Suggestions Toggle -->
          <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Workload Auto-Tuning Suggestions</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">Surfaces batch size and fetch buffer optimizations based on live target lock latency.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('workloadAutoTuningSuggestions', !settings().workloadAutoTuningSuggestions)"
              [class.bg-blue-600]="settings().workloadAutoTuningSuggestions"
              [class.bg-slate-300]="!settings().workloadAutoTuningSuggestions"
              [class.dark:bg-slate-700]="!settings().workloadAutoTuningSuggestions"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().workloadAutoTuningSuggestions"
                [class.translate-x-0]="!settings().workloadAutoTuningSuggestions"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Concurrency Recommendation Advisory Toggle -->
          <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div>
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Concurrency Scaling Advisory</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">Recommends worker pool scale-up/scale-down bounds when CPU headroom allows.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('concurrencyRecommendationAdvisory', !settings().concurrencyRecommendationAdvisory)"
              [class.bg-blue-600]="settings().concurrencyRecommendationAdvisory"
              [class.bg-slate-300]="!settings().concurrencyRecommendationAdvisory"
              [class.dark:bg-slate-700]="!settings().concurrencyRecommendationAdvisory"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().concurrencyRecommendationAdvisory"
                [class.translate-x-0]="!settings().concurrencyRecommendationAdvisory"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>
        </div>
      </section>

      <!-- 4. RCA & Diagnostics -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <app-lucide-icon name="search" [size]="18"></app-lucide-icon>
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">4. RCA &amp; Diagnostics</h3>
              <p class="text-xs text-slate-500 dark:text-slate-400">Natural-language root cause explanations and suggested remediation commands for worker aborts.</p>
            </div>
          </div>
          <button
            type="button"
            (click)="updateSetting('failureRcaEnabled', !settings().failureRcaEnabled)"
            [class.bg-blue-600]="settings().failureRcaEnabled"
            [class.bg-slate-300]="!settings().failureRcaEnabled"
            [class.dark:bg-slate-700]="!settings().failureRcaEnabled"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
            <span
              [class.translate-x-5]="settings().failureRcaEnabled"
              [class.translate-x-0]="!settings().failureRcaEnabled"
              class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
          </button>
        </div>

        <div class="space-y-4" [class.opacity-60]="!settings().failureRcaEnabled">
          <div class="text-xs text-slate-600 dark:text-slate-300">
            When a pipeline task halts with an exception, the assistant aggregates connector log snippets, engine state codes, and schema definitions to synthesize a diagnostic summary and recommended action.
          </div>

          <!-- Sensitive Data Redaction Notice -->
          <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <app-lucide-icon name="lock" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
                Trace Scrubbing Active
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Table values, customer identifiers, and query literal binds are masked before analysis.
              </div>
            </div>
            <div class="text-xs font-bold text-slate-600 dark:text-slate-300 px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shrink-0">
              Enforced Safety Rule
            </div>
          </div>
        </div>
      </section>

      <!-- 5. Recommendation Policies -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="shield-check" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">5. Recommendation Policies</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Confidence gating thresholds and enterprise human-in-the-loop validation enforcement.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Confidence Filter Threshold
            </label>
            <app-custom-select
              [options]="confidenceLevelOptions"
              [ngModel]="settings().recommendationConfidenceLevel"
              (ngModelChange)="updateSetting('recommendationConfidenceLevel', $event)">
            </app-custom-select>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">High Confidence filters out ambiguous or speculative tuning proposals.</p>
          </div>

          <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col justify-between">
            <div>
              <div class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <app-lucide-icon name="slash" [size]="14" class="text-red-500"></app-lucide-icon>
                Autonomous Execution Permanently Disabled
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Zero autonomous changes are permitted on target databases. Every suggested optimization requires explicit operator dispatch.
              </div>
            </div>
            <div class="text-[11px] font-mono font-bold text-slate-600 dark:text-slate-400 mt-2">
              Status: Enforced by Platform Policy
            </div>
          </div>
        </div>
      </section>

      <!-- 6. Predictive Operations -->
      <section class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
        <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
            <app-lucide-icon name="trending-up" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">6. Predictive Operations</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">Deterministic statistical velocity heuristics for buffer spill risks and throughput stalls.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- CDC Buffer Saturation Prediction Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">CDC Buffer Saturation Warning</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Emits pre-emptive alerts when replication inflow velocity<br/>exceeds drain rate towards 80% watermark.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('cdcBufferSaturationPrediction', !settings().cdcBufferSaturationPrediction)"
              [class.bg-blue-600]="settings().cdcBufferSaturationPrediction"
              [class.bg-slate-300]="!settings().cdcBufferSaturationPrediction"
              [class.dark:bg-slate-700]="!settings().cdcBufferSaturationPrediction"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().cdcBufferSaturationPrediction"
                [class.translate-x-0]="!settings().cdcBufferSaturationPrediction"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>

          <!-- Throughput Anomaly Detection Toggle -->
          <div class="flex items-center justify-between gap-4 p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
            <div class="pr-2">
              <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Throughput Anomaly Detection</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Flags unexpected drops in record transfer velocity against running rolling averages.</div>
            </div>
            <button
              type="button"
              (click)="updateSetting('throughputAnomalyDetection', !settings().throughputAnomalyDetection)"
              [class.bg-blue-600]="settings().throughputAnomalyDetection"
              [class.bg-slate-300]="!settings().throughputAnomalyDetection"
              [class.dark:bg-slate-700]="!settings().throughputAnomalyDetection"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
              <span
                [class.translate-x-5]="settings().throughputAnomalyDetection"
                [class.translate-x-0]="!settings().throughputAnomalyDetection"
                class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
            </button>
          </div>
        </div>

        <div class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/60 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400">
          <span class="font-semibold text-slate-700 dark:text-slate-300">Statistical Engine:</span>
          Predictive alerts evaluate moving 60-second window regressions computed locally by akaalEngine. No telemetry or query metrics are transmitted to third-party services.
        </div>
      </section>
    </div>
  `
})
export class SettingsAiIntelligenceComponent {
  private settingsService = inject(SettingsService);

  public settings = this.settingsService.aiIntelligenceSettings;

  public proactivityModeOptions: SelectOption[] = [
    { label: 'Advisory (Ambient suggestions & risk warnings)', value: 'ADVISORY' },
    { label: 'On-Demand (Invoked only on explicit operator request)', value: 'ON_DEMAND' }
  ];

  public confidenceLevelOptions: SelectOption[] = [
    { label: 'High Confidence Only (Suppresses ambiguous proposals)', value: 'HIGH' },
    { label: 'Standard Confidence (Displays all validated recommendations)', value: 'STANDARD' }
  ];

  public updateSetting(key: string, value: any): void {
    this.settingsService.updateAiIntelligence({ [key]: value });
  }

  public resetDefaults(): void {
    this.settingsService.resetAiIntelligence();
  }
}
