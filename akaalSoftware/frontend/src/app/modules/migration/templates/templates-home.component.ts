import { Component, inject, Optional, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { TemplatesService } from './templates.service';
import { TemplatesHeaderComponent } from './components/templates-header.component';
import { TemplatesTableComponent } from './components/templates-table.component';
import { TemplatesStatesComponent } from './components/templates-states.component';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-templates-home',
  standalone: true,
  imports: [
    CommonModule,
    TemplatesHeaderComponent,
    TemplatesTableComponent,
    TemplatesStatesComponent,
    LucideIconComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- =============================================================== -->
      <!-- 1. HEADER (Sibling Grammar)                                     -->
      <!-- =============================================================== -->
      <app-templates-header></app-templates-header>

      <!-- Database / State Unavailable Notice (Sibling Pattern) -->
      @if (ts.availabilityState() === 'UNAVAILABLE' || ts.availabilityState() === 'ERROR') {
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold">{{ ts.errorMessage() || 'The template repository or migration configuration service is currently unreachable.' }}</span>
          </div>
          <button
            type="button"
            (click)="ts.reload()"
            class="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs cursor-pointer">
            Retry
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 2. INVENTORY CARD OR STATES                                     -->
      <!-- =============================================================== -->
      <div class="relative">
        <app-templates-table
          *ngIf="showTable()">
        </app-templates-table>

        <app-templates-states
          *ngIf="!showTable()"
          (createNewTemplate)="onCreateNewTemplate()">
        </app-templates-states>
      </div>

    </div>
  `
})
export class TemplatesHomeComponent implements OnInit {
  public ts: TemplatesService;
  private router: Router | null;

  constructor(
    @Optional() ts?: TemplatesService,
    @Optional() router?: Router
  ) {
    if (ts) {
      this.ts = ts;
    } else {
      try {
        this.ts = inject(TemplatesService);
      } catch {
        this.ts = new TemplatesService();
      }
    }

    if (router) {
      this.router = router;
    } else {
      try {
        this.router = inject(Router);
      } catch {
        this.router = null;
      }
    }
  }

  ngOnInit(): void {
    if (this.ts.availabilityState() === 'LOADING') {
      setTimeout(() => {
        this.ts.availabilityState.set('READY');
      }, 100);
    }
  }

  showTable(): boolean {
    return (
      this.ts.availabilityState() === 'READY' &&
      this.ts.filteredTemplates().length > 0
    );
  }

  onCreateNewTemplate(): void {
    const isMigrationPrefix = this.router ? this.router.url.startsWith('/migration') : true;
    this.router?.navigate([isMigrationPrefix ? '/migration/templates/new' : '/templates/new']);
  }
}
