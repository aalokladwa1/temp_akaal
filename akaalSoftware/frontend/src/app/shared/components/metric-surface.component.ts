import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-metric-surface',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div 
      (click)="navigate()"
      class="p-5 rounded-2xl border transition-all duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none"
      [class.bg-white]="!isAccent && !isWarning"
      [class.border-slate-200]="!isAccent && !isWarning"
      [class.hover:border-slate-300]="!isAccent && !isWarning"
      [class.hover:bg-slate-50]="!isAccent && !isWarning"
      [class.border-blue-300]="isAccent"
      [class.bg-blue-50]="isAccent"
      [class.hover:border-blue-500]="isAccent"
      [class.border-amber-300]="isWarning && !isAccent"
      [class.bg-amber-50]="isWarning && !isAccent"
      [class.hover:border-amber-400]="isWarning && !isAccent">
      
      <!-- Top Label & Status Dot -->
      <div class="flex items-center justify-between">
        <span 
          class="text-[11px] font-bold text-slate-500 uppercase tracking-wider transition-colors"
          [class.group-hover:text-slate-800]="!isAccent && !isWarning"
          [class.text-blue-700]="isAccent"
          [class.text-amber-700]="isWarning && !isAccent">
          {{ label }}
        </span>
        @if (statusDot) {
          <span
            class="w-2 h-2 rounded-full"
            [class.bg-emerald-500]="statusDot === 'EMERALD'"
            [class.bg-amber-500]="statusDot === 'AMBER'"
            [class.bg-rose-500]="statusDot === 'ROSE'"
            [class.bg-blue-500]="statusDot === 'BLUE'"
            [class.bg-slate-400]="statusDot === 'SLATE'">
          </span>
        }
      </div>

      <!-- Bottom Number & Subtext Aligned to Baseline -->
      <div class="flex items-baseline justify-between gap-3">
        <span 
          class="text-3xl font-bold font-mono text-slate-900 tracking-tight tabular-nums"
          [class.text-blue-600]="isAccent"
          [class.text-amber-600]="isWarning && !isAccent">
          {{ value }}
        </span>
        @if (subtext) {
          <span class="text-xs text-slate-500 font-medium tabular-nums text-right truncate">
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
