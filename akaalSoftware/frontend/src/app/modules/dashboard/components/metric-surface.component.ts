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
      class="p-6 rounded-2xl bg-white border-2 border-slate-200/90 hover:border-blue-600 transition-colors duration-150 flex flex-col justify-between h-32 cursor-pointer group select-none"
      [class.border-blue-600]="isAccent">
      <div class="flex items-center justify-between">
        <span class="text-xs font-bold text-slate-600 uppercase tracking-wider group-hover:text-blue-600 transition-colors">{{ label }}</span>
      </div>
      <div class="flex items-baseline justify-between gap-2">
        <span class="text-3xl font-bold font-heading text-slate-900 tracking-tight" [class.text-blue-600]="isAccent" [class.text-amber-600]="isWarning">
          {{ value }}
        </span>
        @if (subtext) {
          <span class="text-xs text-slate-600 font-medium">{{ subtext }}</span>
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
  @Input() public targetRoute: string = '/migration';

  constructor(private router: Router) {}

  public navigate(): void {
    this.router.navigate([this.targetRoute]);
  }
}
