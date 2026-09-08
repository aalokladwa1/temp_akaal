import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ConnectionsService } from './connections.service';
import { ConnectionsHeaderComponent } from './components/connections-header.component';
import { ConnectionsSummaryStripComponent } from './components/connections-summary-strip.component';
import { ConnectionsTableComponent } from './components/connections-table.component';
import { ConnectionsStatesComponent } from './components/connections-states.component';
import { ConnectionsInspectDrawerComponent } from './components/connections-inspect-drawer.component';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-connections-home',
  standalone: true,
  imports: [
    CommonModule,
    ConnectionsHeaderComponent,
    ConnectionsSummaryStripComponent,
    ConnectionsTableComponent,
    ConnectionsStatesComponent,
    ConnectionsInspectDrawerComponent,
    LucideIconComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- =============================================================== -->
      <!-- 1. HEADER (Sibling Grammar)                                     -->
      <!-- =============================================================== -->
      <app-connections-header></app-connections-header>

      <!-- Database / State Unavailable Notice (Sibling Pattern) -->
      @if (cs.availabilityState() === 'UNAVAILABLE' || cs.availabilityState() === 'ERROR') {
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold">{{ cs.errorMessage() || 'The connection registry or verification engine is currently unavailable.' }}</span>
          </div>
          <button
            type="button"
            (click)="cs.reload()"
            class="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs cursor-pointer">
            Retry Connection
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 2. FOUR KPI QUICK FILTERS (Exact Sibling Strip)                  -->
      <!-- =============================================================== -->
      <app-connections-summary-strip></app-connections-summary-strip>

      <!-- =============================================================== -->
      <!-- 3. INVENTORY CARD OR STATES                                     -->
      <!-- =============================================================== -->
      <div class="relative">
        <app-connections-table
          *ngIf="showTable()">
        </app-connections-table>

        <app-connections-states
          *ngIf="!showTable()"
          (createConnection)="onCreateConnection()">
        </app-connections-states>
      </div>

      <!-- Slide-over Inspect Drawer -->
      <app-connections-inspect-drawer></app-connections-inspect-drawer>
      
    </div>
  `
})
export class ConnectionsHomeComponent implements OnInit {
  public cs = inject(ConnectionsService);
  private router = inject(Router);

  ngOnInit(): void {
    if (this.cs.availabilityState() === 'LOADING') {
      setTimeout(() => {
        this.cs.availabilityState.set('READY');
      }, 100);
    }
  }

  showTable(): boolean {
    return (
      this.cs.availabilityState() === 'READY' &&
      this.cs.filteredConnections().length > 0
    );
  }

  onCreateConnection(): void {
    const isMigrationPrefix = this.router.url.startsWith('/migration');
    this.router.navigate([isMigrationPrefix ? '/migration/connections/new' : '/connections/new']);
  }
}
