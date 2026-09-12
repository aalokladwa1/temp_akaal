import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SettingsService } from '../services/settings.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import {
  ThemeOption,
  AccessibilityPaletteOption,
  ContrastOption
} from '../models/settings.models';

@Component({
  selector: 'app-settings-appearance',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 animate-in fade-in duration-150 max-w-4xl pb-16">
      
      <!-- Section Top Header & Actions -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold text-blue-600 tracking-wider uppercase font-mono">
              WORKSTATION PREFERENCES
            </span>
          </div>
          <h2 class="text-xl font-bold text-slate-900 tracking-tight">
            Appearance &amp; Accessibility
          </h2>
          <p class="text-xs text-slate-500 max-w-2xl mt-0.5">
            Customize workstation visual themes, color-blindness accessible palettes, high-contrast borders, and motion reduction.
          </p>
        </div>

        <div class="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            (click)="resetAppearance()"
            class="h-9 px-3.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer shadow-2xs">
            <app-lucide-icon name="rotate-ccw" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span>Reset Appearance</span>
          </button>
        </div>
      </div>

      <!-- Live Notification Banner -->
      @if (statusMessage()) {
        <div class="p-3 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-between animate-in fade-in duration-150">
          <div class="flex items-center gap-2 text-xs font-medium text-blue-800">
            <app-lucide-icon name="check" [size]="14" class="text-blue-600"></app-lucide-icon>
            <span>{{ statusMessage() }}</span>
          </div>
          <button type="button" (click)="statusMessage.set(null)" class="text-blue-500 hover:text-blue-700 cursor-pointer">
            <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 1. WORKSPACE THEME (3 RECTANGULAR TILES)                        -->
      <!-- =============================================================== -->
      <section aria-labelledby="theme-heading" class="flex flex-col gap-3">
        <div class="flex flex-col">
          <h3 id="theme-heading" class="text-sm font-bold text-slate-900">Workspace Theme</h3>
          <p class="text-xs text-slate-500">
            Choose the baseline visual appearance for all workstation views and controls.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          
          <!-- Option 1: Enterprise Blue -->
          <div
            (click)="setTheme('enterprise-blue')"
            role="radio"
            [attr.aria-checked]="settings.appearanceSettings().theme === 'enterprise-blue'"
            tabindex="0"
            (keydown.enter)="setTheme('enterprise-blue')"
            (keydown.space)="setTheme('enterprise-blue')"
            class="p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between gap-3 select-none relative group shadow-2xs"
            [class.border-blue-600]="settings.appearanceSettings().theme === 'enterprise-blue'"
            [class.ring-2]="settings.appearanceSettings().theme === 'enterprise-blue'"
            [class.bg-blue-50]="settings.appearanceSettings().theme === 'enterprise-blue'"
            [class.border-slate-200]="settings.appearanceSettings().theme !== 'enterprise-blue'"
            [class.bg-white]="settings.appearanceSettings().theme !== 'enterprise-blue'"
            [class.hover:border-slate-300]="settings.appearanceSettings().theme !== 'enterprise-blue'">
            
            <!-- Miniature Graphical Preview -->
            <div class="w-full h-24 rounded-lg bg-slate-100 border border-slate-200 p-2 flex flex-col gap-1.5 overflow-hidden">
              <div class="h-4 bg-white rounded border border-slate-200 flex items-center px-2 justify-between">
                <div class="w-8 h-1.5 bg-blue-600 rounded-xs"></div>
                <div class="w-4 h-1.5 bg-slate-300 rounded-xs"></div>
              </div>
              <div class="flex-1 flex gap-1.5">
                <div class="w-10 bg-white rounded border border-slate-200 flex flex-col gap-1 p-1">
                  <div class="w-6 h-1 bg-slate-300 rounded-xs"></div>
                  <div class="w-7 h-1 bg-blue-600 rounded-xs"></div>
                  <div class="w-5 h-1 bg-slate-200 rounded-xs"></div>
                </div>
                <div class="flex-1 bg-white rounded border border-slate-200 p-1.5 flex flex-col gap-1">
                  <div class="w-12 h-1.5 bg-slate-800 rounded-xs"></div>
                  <div class="w-full h-4 bg-slate-50 rounded border border-slate-100"></div>
                </div>
              </div>
            </div>

            <!-- Details -->
            <div class="flex flex-col gap-1">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-900">Enterprise Blue</span>
                @if (settings.appearanceSettings().theme === 'enterprise-blue') {
                  <app-lucide-icon name="circle-check" [size]="16" class="text-blue-600"></app-lucide-icon>
                }
              </div>
              <span class="text-[10px] font-semibold text-blue-600 uppercase font-mono tracking-wider">Default Light</span>
              <p class="text-[11px] text-slate-500 leading-snug">
                Clean slate surfaces, crisp 1px borders, and high-contrast blue primary accents for enterprise daylight operations.
              </p>
            </div>
          </div>

          <!-- Option 2: Dark Mode -->
          <div
            (click)="setTheme('dark')"
            role="radio"
            [attr.aria-checked]="settings.appearanceSettings().theme === 'dark'"
            tabindex="0"
            (keydown.enter)="setTheme('dark')"
            (keydown.space)="setTheme('dark')"
            class="p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between gap-3 select-none relative group shadow-2xs"
            [class.border-blue-600]="settings.appearanceSettings().theme === 'dark'"
            [class.ring-2]="settings.appearanceSettings().theme === 'dark'"
            [class.bg-blue-50]="settings.appearanceSettings().theme === 'dark'"
            [class.border-slate-200]="settings.appearanceSettings().theme !== 'dark'"
            [class.bg-white]="settings.appearanceSettings().theme !== 'dark'"
            [class.hover:border-slate-300]="settings.appearanceSettings().theme !== 'dark'">
            
            <!-- Miniature Graphical Preview -->
            <div class="w-full h-24 rounded-lg bg-slate-950 border border-slate-800 p-2 flex flex-col gap-1.5 overflow-hidden">
              <div class="h-4 bg-slate-900 rounded border border-slate-800 flex items-center px-2 justify-between">
                <div class="w-8 h-1.5 bg-blue-500 rounded-xs"></div>
                <div class="w-4 h-1.5 bg-slate-700 rounded-xs"></div>
              </div>
              <div class="flex-1 flex gap-1.5">
                <div class="w-10 bg-slate-900 rounded border border-slate-800 flex flex-col gap-1 p-1">
                  <div class="w-6 h-1 bg-slate-700 rounded-xs"></div>
                  <div class="w-7 h-1 bg-blue-500 rounded-xs"></div>
                  <div class="w-5 h-1 bg-slate-800 rounded-xs"></div>
                </div>
                <div class="flex-1 bg-slate-900 rounded border border-slate-800 p-1.5 flex flex-col gap-1">
                  <div class="w-12 h-1.5 bg-slate-200 rounded-xs"></div>
                  <div class="w-full h-4 bg-slate-950 rounded border border-slate-800"></div>
                </div>
              </div>
            </div>

            <!-- Details -->
            <div class="flex flex-col gap-1">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-900">Dark Mode</span>
                @if (settings.appearanceSettings().theme === 'dark') {
                  <app-lucide-icon name="circle-check" [size]="16" class="text-blue-600"></app-lucide-icon>
                }
              </div>
              <span class="text-[10px] font-semibold text-slate-500 uppercase font-mono tracking-wider">Low-Glare Dark</span>
              <p class="text-[11px] text-slate-500 leading-snug">
                Deep obsidian and slate surfaces engineered for 24/7 mission-control rooms and low-light NOC monitoring.
              </p>
            </div>
          </div>

          <!-- Option 3: System Follow -->
          <div
            (click)="setTheme('system')"
            role="radio"
            [attr.aria-checked]="settings.appearanceSettings().theme === 'system'"
            tabindex="0"
            (keydown.enter)="setTheme('system')"
            (keydown.space)="setTheme('system')"
            class="p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between gap-3 select-none relative group shadow-2xs"
            [class.border-blue-600]="settings.appearanceSettings().theme === 'system'"
            [class.ring-2]="settings.appearanceSettings().theme === 'system'"
            [class.bg-blue-50]="settings.appearanceSettings().theme === 'system'"
            [class.border-slate-200]="settings.appearanceSettings().theme !== 'system'"
            [class.bg-white]="settings.appearanceSettings().theme !== 'system'"
            [class.hover:border-slate-300]="settings.appearanceSettings().theme !== 'system'">
            
            <!-- Miniature Graphical Preview (Split Light/Dark) -->
            <div class="w-full h-24 rounded-lg border border-slate-300 flex overflow-hidden">
              <!-- Left: Light half -->
              <div class="flex-1 bg-slate-100 p-2 flex flex-col gap-1.5 border-r border-slate-300">
                <div class="h-4 bg-white rounded border border-slate-200 flex items-center px-1">
                  <div class="w-6 h-1.5 bg-blue-600 rounded-xs"></div>
                </div>
                <div class="flex-1 bg-white rounded border border-slate-200 p-1 flex flex-col gap-1">
                  <div class="w-8 h-1 bg-slate-800 rounded-xs"></div>
                  <div class="w-full h-3 bg-slate-50 rounded"></div>
                </div>
              </div>
              <!-- Right: Dark half -->
              <div class="flex-1 bg-slate-950 p-2 flex flex-col gap-1.5">
                <div class="h-4 bg-slate-900 rounded border border-slate-800 flex items-center px-1">
                  <div class="w-6 h-1.5 bg-blue-500 rounded-xs"></div>
                </div>
                <div class="flex-1 bg-slate-900 rounded border border-slate-800 p-1 flex flex-col gap-1">
                  <div class="w-8 h-1 bg-slate-200 rounded-xs"></div>
                  <div class="w-full h-3 bg-slate-950 rounded"></div>
                </div>
              </div>
            </div>

            <!-- Details -->
            <div class="flex flex-col gap-1">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-900">Follow System</span>
                @if (settings.appearanceSettings().theme === 'system') {
                  <app-lucide-icon name="circle-check" [size]="16" class="text-blue-600"></app-lucide-icon>
                }
              </div>
              <span class="text-[10px] font-semibold text-indigo-600 uppercase font-mono tracking-wider">
                Dynamic OS ({{ settings.systemPrefersDark() ? 'Dark Detected' : 'Light Detected' }})
              </span>
              <p class="text-[11px] text-slate-500 leading-snug">
                Dynamically matches the host operating system's dark/light preferences via native system media queries.
              </p>
            </div>
          </div>

        </div>
      </section>

      <!-- =============================================================== -->
      <!-- 2. ACCESSIBILITY PALETTE (2 RECTANGULAR TILES)                  -->
      <!-- =============================================================== -->
      <section aria-labelledby="palette-heading" class="flex flex-col gap-3">
        <div class="flex flex-col">
          <h3 id="palette-heading" class="text-sm font-bold text-slate-900">Accessibility Palette</h3>
          <p class="text-xs text-slate-500">
            Optimize status indicators, badges, and alerts for color vision deficiencies.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          
          <!-- Standard Palette -->
          <div
            (click)="setPalette('standard')"
            role="radio"
            [attr.aria-checked]="settings.appearanceSettings().palette === 'standard'"
            tabindex="0"
            (keydown.enter)="setPalette('standard')"
            (keydown.space)="setPalette('standard')"
            class="p-4 rounded-xl border transition-all cursor-pointer flex flex-col gap-3 select-none relative group shadow-2xs"
            [class.border-blue-600]="settings.appearanceSettings().palette === 'standard'"
            [class.ring-2]="settings.appearanceSettings().palette === 'standard'"
            [class.bg-blue-50]="settings.appearanceSettings().palette === 'standard'"
            [class.border-slate-200]="settings.appearanceSettings().palette !== 'standard'"
            [class.bg-white]="settings.appearanceSettings().palette !== 'standard'"
            [class.hover:border-slate-300]="settings.appearanceSettings().palette !== 'standard'">
            
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-slate-900">Standard Enterprise</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-slate-100 text-slate-600">DEFAULT</span>
              </div>
              @if (settings.appearanceSettings().palette === 'standard') {
                <app-lucide-icon name="circle-check" [size]="16" class="text-blue-600"></app-lucide-icon>
              }
            </div>

            <!-- Color Swatches Strip -->
            <div class="flex items-center gap-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
              <div class="flex items-center gap-1.5 flex-1">
                <span class="w-4 h-4 rounded bg-blue-600 border border-blue-700/30 shrink-0" title="Primary Blue"></span>
                <span class="text-[10px] font-semibold text-slate-700">Primary</span>
              </div>
              <div class="flex items-center gap-1.5 flex-1">
                <span class="w-4 h-4 rounded bg-emerald-600 border border-emerald-700/30 shrink-0" title="Success Green"></span>
                <span class="text-[10px] font-semibold text-slate-700">Success</span>
              </div>
              <div class="flex items-center gap-1.5 flex-1">
                <span class="w-4 h-4 rounded bg-amber-500 border border-amber-600/30 shrink-0" title="Warning Amber"></span>
                <span class="text-[10px] font-semibold text-slate-700">Warning</span>
              </div>
              <div class="flex items-center gap-1.5 flex-1">
                <span class="w-4 h-4 rounded bg-red-600 border border-red-700/30 shrink-0" title="Critical Red"></span>
                <span class="text-[10px] font-semibold text-slate-700">Critical</span>
              </div>
            </div>

            <p class="text-[11px] text-slate-500 leading-snug">
              Standard corporate color allocations for nominal throughput, warnings, and critical error states.
            </p>
          </div>

          <!-- Color Vision Safe Palette -->
          <div
            (click)="setPalette('color-vision-safe')"
            role="radio"
            [attr.aria-checked]="settings.appearanceSettings().palette === 'color-vision-safe'"
            tabindex="0"
            (keydown.enter)="setPalette('color-vision-safe')"
            (keydown.space)="setPalette('color-vision-safe')"
            class="p-4 rounded-xl border transition-all cursor-pointer flex flex-col gap-3 select-none relative group shadow-2xs"
            [class.border-blue-600]="settings.appearanceSettings().palette === 'color-vision-safe'"
            [class.ring-2]="settings.appearanceSettings().palette === 'color-vision-safe'"
            [class.bg-blue-50]="settings.appearanceSettings().palette === 'color-vision-safe'"
            [class.border-slate-200]="settings.appearanceSettings().palette !== 'color-vision-safe'"
            [class.bg-white]="settings.appearanceSettings().palette !== 'color-vision-safe'"
            [class.hover:border-slate-300]="settings.appearanceSettings().palette !== 'color-vision-safe'">
            
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-slate-900">Color Vision Safe (Okabe-Ito)</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-blue-100 text-blue-800">ACCESSIBLE</span>
              </div>
              @if (settings.appearanceSettings().palette === 'color-vision-safe') {
                <app-lucide-icon name="circle-check" [size]="16" class="text-blue-600"></app-lucide-icon>
              }
            </div>

            <!-- Color Swatches Strip (Okabe-Ito) -->
            <div class="flex items-center gap-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
              <div class="flex items-center gap-1.5 flex-1">
                <span class="w-4 h-4 rounded bg-[#0072b2] border border-blue-900/30 shrink-0" title="Safe Blue"></span>
                <span class="text-[10px] font-semibold text-slate-700">Primary</span>
              </div>
              <div class="flex items-center gap-1.5 flex-1">
                <span class="w-4 h-4 rounded bg-[#009e73] border border-emerald-900/30 shrink-0" title="Safe Teal/Green"></span>
                <span class="text-[10px] font-semibold text-slate-700">Success</span>
              </div>
              <div class="flex items-center gap-1.5 flex-1">
                <span class="w-4 h-4 rounded bg-[#e69f00] border border-amber-800/30 shrink-0" title="Safe Amber"></span>
                <span class="text-[10px] font-semibold text-slate-700">Warning</span>
              </div>
              <div class="flex items-center gap-1.5 flex-1">
                <span class="w-4 h-4 rounded bg-[#d55e00] border border-orange-900/30 shrink-0" title="Safe Vermilion"></span>
                <span class="text-[10px] font-semibold text-slate-700">Critical</span>
              </div>
            </div>

            <p class="text-[11px] text-slate-500 leading-snug">
              High-luminance-differentiation Okabe-Ito scale engineered for deuteranopia, protanopia, and tritanopia color blindness.
            </p>
          </div>

        </div>
      </section>

      <!-- =============================================================== -->
      <!-- 3. CONTRAST MODE (2 RECTANGULAR TILES)                          -->
      <!-- =============================================================== -->
      <section aria-labelledby="contrast-heading" class="flex flex-col gap-3">
        <div class="flex flex-col">
          <h3 id="contrast-heading" class="text-sm font-bold text-slate-900">Contrast Calibration</h3>
          <p class="text-xs text-slate-500">
            Select contrast thresholds to guarantee legibility under harsh ambient lighting or high ambient glare.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          
          <!-- Standard Contrast -->
          <div
            (click)="setContrast('standard')"
            role="radio"
            [attr.aria-checked]="settings.appearanceSettings().contrast === 'standard'"
            tabindex="0"
            (keydown.enter)="setContrast('standard')"
            (keydown.space)="setContrast('standard')"
            class="p-4 rounded-xl border transition-all cursor-pointer flex flex-col gap-2.5 select-none relative group shadow-2xs"
            [class.border-blue-600]="settings.appearanceSettings().contrast === 'standard'"
            [class.ring-2]="settings.appearanceSettings().contrast === 'standard'"
            [class.bg-blue-50]="settings.appearanceSettings().contrast === 'standard'"
            [class.border-slate-200]="settings.appearanceSettings().contrast !== 'standard'"
            [class.bg-white]="settings.appearanceSettings().contrast !== 'standard'"
            [class.hover:border-slate-300]="settings.appearanceSettings().contrast !== 'standard'">
            
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-slate-900">Standard Contrast</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-slate-100 text-slate-600">WCAG AA</span>
              </div>
              @if (settings.appearanceSettings().contrast === 'standard') {
                <app-lucide-icon name="circle-check" [size]="16" class="text-blue-600"></app-lucide-icon>
              }
            </div>

            <p class="text-[11px] text-slate-500 leading-snug">
              Balanced 4.5:1 minimum text luminance ratio with soft borders and neutral background elevation layering.
            </p>
          </div>

          <!-- High Contrast Mode -->
          <div
            (click)="setContrast('high-contrast')"
            role="radio"
            [attr.aria-checked]="settings.appearanceSettings().contrast === 'high-contrast'"
            tabindex="0"
            (keydown.enter)="setContrast('high-contrast')"
            (keydown.space)="setContrast('high-contrast')"
            class="p-4 rounded-xl border transition-all cursor-pointer flex flex-col gap-2.5 select-none relative group shadow-2xs"
            [class.border-blue-600]="settings.appearanceSettings().contrast === 'high-contrast'"
            [class.ring-2]="settings.appearanceSettings().contrast === 'high-contrast'"
            [class.bg-blue-50]="settings.appearanceSettings().contrast === 'high-contrast'"
            [class.border-slate-200]="settings.appearanceSettings().contrast !== 'high-contrast'"
            [class.bg-white]="settings.appearanceSettings().contrast !== 'high-contrast'"
            [class.hover:border-slate-300]="settings.appearanceSettings().contrast !== 'high-contrast'">
            
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-slate-900">High Contrast</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-indigo-100 text-indigo-800">WCAG AAA</span>
              </div>
              @if (settings.appearanceSettings().contrast === 'high-contrast') {
                <app-lucide-icon name="circle-check" [size]="16" class="text-blue-600"></app-lucide-icon>
              }
            </div>

            <p class="text-[11px] text-slate-500 leading-snug">
              Strict 7:1+ luminance ratio with prominent 1.5px high-contrast structural borders and absolute dark/light canvases.
            </p>
          </div>

        </div>
      </section>

      <!-- =============================================================== -->
      <!-- 4. MOTION & FOCUS TOGGLES                                       -->
      <!-- =============================================================== -->
      <section aria-labelledby="motion-focus-heading" class="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex flex-col">
          <h3 id="motion-focus-heading" class="text-sm font-bold text-slate-900">Motion &amp; Keyboard Focus Control</h3>
          <p class="text-xs text-slate-500">
            Orthogonal accessibility enhancements that apply across all themes and views.
          </p>
        </div>

        <div class="flex flex-col divide-y divide-slate-100 pt-1">
          
          <!-- Reduce Motion -->
          <div class="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
                <app-lucide-icon name="zap" [size]="16"></app-lucide-icon>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-xs font-bold text-slate-900">Reduce Motion &amp; Disable Transitions</span>
                <p class="text-[11px] text-slate-500">
                  Suppresses non-essential CSS transitions, modal zoom scales, and animated status spinners for vestibular comfort.
                </p>
              </div>
            </div>

            <label class="flex items-center gap-2 cursor-pointer shrink-0">
              <input
                type="checkbox"
                [checked]="settings.appearanceSettings().reduceMotion"
                (change)="toggleReduceMotion($event)"
                class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500">
              <span class="text-xs font-semibold text-slate-700">
                {{ settings.appearanceSettings().reduceMotion ? 'Reduced' : 'Standard' }}
              </span>
            </label>
          </div>

          <!-- Enhanced Focus Visibility -->
          <div class="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
                <app-lucide-icon name="focus" [size]="16"></app-lucide-icon>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-xs font-bold text-slate-900">Enhanced Focus Visibility</span>
                <p class="text-[11px] text-slate-500">
                  Renders high-visibility 3px accented focus rings with offset spacing around all interactive controls during keyboard navigation.
                </p>
              </div>
            </div>

            <label class="flex items-center gap-2 cursor-pointer shrink-0">
              <input
                type="checkbox"
                [checked]="settings.appearanceSettings().enhancedFocus"
                (change)="toggleEnhancedFocus($event)"
                class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500">
              <span class="text-xs font-semibold text-slate-700">
                {{ settings.appearanceSettings().enhancedFocus ? 'Enhanced (3px)' : 'Standard (1px)' }}
              </span>
            </label>
          </div>

        </div>
      </section>

      <!-- =============================================================== -->
      <!-- 5. LIVE COMPONENT COMPOSITION INSPECTION SANDBOX                -->
      <!-- =============================================================== -->
      <section aria-labelledby="sandbox-heading" class="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between">
          <div class="flex flex-col">
            <h3 id="sandbox-heading" class="text-sm font-bold text-slate-900">Live Appearance Inspection Sandbox</h3>
            <p class="text-xs text-slate-500">
              Verify how the composite layers (Theme: <strong>{{ settings.effectiveTheme() }}</strong>, Palette: <strong>{{ settings.appearanceSettings().palette }}</strong>, Contrast: <strong>{{ settings.appearanceSettings().contrast }}</strong>) render on standard UI widgets.
            </p>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600">LIVE RENDER</span>
        </div>

        <div class="p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-wrap items-center gap-3">
          <!-- Primary Button -->
          <button type="button" class="h-8 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium cursor-pointer shadow-xs">
            Primary Action
          </button>

          <!-- Secondary Button -->
          <button type="button" class="h-8 px-3 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium cursor-pointer shadow-2xs">
            Secondary Button
          </button>

          <!-- Danger Button -->
          <button type="button" class="h-8 px-3 rounded-lg bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 text-xs font-medium cursor-pointer">
            Destructive
          </button>

          <!-- Success Badge -->
          <span class="px-2 py-1 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Operational
          </span>

          <!-- Warning Badge -->
          <span class="px-2 py-1 rounded text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            Caution Threshold
          </span>

          <!-- Sample Text Input -->
          <input
            type="text"
            readonly
            value="Focus test keyboard input"
            class="h-8 px-3 rounded-md bg-white border border-slate-200 text-xs text-slate-800">
        </div>
      </section>

    </div>
  `
})
export class SettingsAppearanceComponent {
  public settings = inject(SettingsService);
  public statusMessage = signal<string | null>(null);

  public setTheme(theme: ThemeOption): void {
    this.settings.updateAppearance({ theme });
    this.flash(`Workspace theme updated to ${theme}`);
  }

  public setPalette(palette: AccessibilityPaletteOption): void {
    this.settings.updateAppearance({ palette });
    this.flash(`Accessibility palette updated to ${palette}`);
  }

  public setContrast(contrast: ContrastOption): void {
    this.settings.updateAppearance({ contrast });
    this.flash(`Contrast mode updated to ${contrast}`);
  }

  public toggleReduceMotion(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.settings.updateAppearance({ reduceMotion: checked });
    this.flash(checked ? 'Reduced motion enabled globally' : 'Standard motion restored');
  }

  public toggleEnhancedFocus(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.settings.updateAppearance({ enhancedFocus: checked });
    this.flash(checked ? 'Enhanced 3px focus visibility active' : 'Standard focus restored');
  }

  public resetAppearance(): void {
    this.settings.resetAppearance();
    this.flash('Appearance preferences restored to default Enterprise Blue');
  }

  private flash(msg: string): void {
    this.statusMessage.set(msg);
  }
}
