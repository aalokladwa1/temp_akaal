import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { LucideIconComponent } from './lucide-icon.component';

@Component({
  selector: 'app-metric-surface',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div 
      (click)="navigate()"
      class="p-5 rounded-2xl border transition-all duration-200 flex flex-col justify-between h-32 cursor-pointer group select-none shadow-2xs hover:-translate-y-0.5 active:scale-[0.98]"
      [ngClass]="{
        'bg-white dark:bg-[#1a1b1e] border-slate-200 dark:border-[#26272b] hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-[#202226]': !isAccent && !isWarning,
        'bg-blue-50 dark:bg-blue-950/40 border-blue-300 dark:border-blue-700/50 hover:border-blue-500': isAccent,
        'bg-amber-50 dark:bg-amber-950/40 border-amber-300 dark:border-amber-700/50 hover:border-amber-400': isWarning && !isAccent
      }">
      
      <!-- Top Label & Status Dot -->
      <div class="flex items-center justify-between">
        <span 
          class="text-[11px] font-bold uppercase tracking-wider transition-colors"
          [ngClass]="{
            'text-slate-500 dark:text-slate-400 group-hover:text-slate-800 dark:group-hover:text-slate-200': !isAccent && !isWarning,
            'text-blue-700 dark:text-blue-400': isAccent,
            'text-amber-700 dark:text-amber-400': isWarning && !isAccent
          }">
          {{ label }}
        </span>
        @if (statusDot) {
          <app-lucide-icon
            name="circle-dot"
            [size]="10"
            [ngClass]="{
              'text-emerald-500': statusDot === 'EMERALD',
              'text-amber-500': statusDot === 'AMBER',
              'text-rose-500': statusDot === 'ROSE',
              'text-blue-500': statusDot === 'BLUE',
              'text-slate-400': statusDot === 'SLATE'
            }">
          </app-lucide-icon>
        }
      </div>

      <!-- Bottom Number & Subtext Aligned to Baseline -->
      <div class="flex items-baseline justify-between gap-3">
        <span 
          class="text-3xl font-bold tracking-tight tabular-nums"
          [ngClass]="{
            'text-slate-900 dark:text-slate-100': !isAccent && !isWarning,
            'text-blue-600 dark:text-blue-400': isAccent,
            'text-amber-600 dark:text-amber-400': isWarning && !isAccent
          }">
          {{ value }}
        </span>
        @if (subtext) {
          <span class="text-xs text-slate-500 dark:text-slate-400 font-medium tabular-nums text-right truncate">
            {{ subtext }}
          </span>
        }
      </div>

    </div>
  `
})
export class MetricSurfaceComponent {
  @Input() public label: string = '';
  @Input() public value: number | string = '—';
  @Input() public subtext?: string;
  @Input() public isAccent: boolean = false;
  @Input() public isWarning: boolean = false;
  @Input() public statusDot?: 'EMERALD' | 'AMBER' | 'ROSE' | 'BLUE' | 'SLATE';
  @Input() public targetRoute: string = '/migration';

  constructor(private router: Router) {}

  public navigate(): void {
    if (this.targetRoute) {
      this.router.navigate([this.targetRoute]);
    }
  }
}
