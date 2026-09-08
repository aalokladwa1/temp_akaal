import { Component, inject, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConnectionsService } from '../connections.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-connections-states',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <!-- 1. LOADING SKELETON STATE -->
    <div *ngIf="cs.availabilityState() === 'LOADING'" class="w-full bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-2xs">
      <div class="h-6 bg-slate-100 rounded-md w-1/4 animate-pulse"></div>
      <div class="space-y-3 pt-2">
        <div class="h-12 bg-slate-50 rounded-lg animate-pulse border border-slate-100"></div>
        <div class="h-12 bg-slate-50 rounded-lg animate-pulse border border-slate-100"></div>
        <div class="h-12 bg-slate-50 rounded-lg animate-pulse border border-slate-100"></div>
        <div class="h-12 bg-slate-50 rounded-lg animate-pulse border border-slate-100"></div>
      </div>
    </div>

    <!-- 2. ERROR / UNAVAILABLE STATE -->
    <div
      *ngIf="cs.availabilityState() === 'ERROR' || cs.availabilityState() === 'UNAVAILABLE'"
      class="w-full bg-white border border-rose-200 rounded-xl p-12 text-center shadow-2xs">
      <div class="w-12 h-12 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto mb-4 text-rose-600">
        <app-lucide-icon name="alert-triangle" [size]="24"></app-lucide-icon>
      </div>
      <h3 class="text-base font-bold text-slate-900 mb-1">
        Connection Inventory Unavailable
      </h3>
      <p class="text-xs text-slate-500 max-w-md mx-auto mb-6">
        {{ cs.errorMessage() || 'The connection registry or verification engine could not be contacted. Please verify local agent connectivity and try again.' }}
      </p>
      <button
        type="button"
        (click)="onRetry()"
        class="h-9 px-4 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-md transition-colors cursor-pointer shadow-2xs focus:outline-hidden focus:ring-2 focus:ring-slate-400">
        Retry Connection
      </button>
    </div>

    <!-- 3. TRUE EMPTY STATE (No connections in system) -->
    <div
      *ngIf="cs.availabilityState() === 'EMPTY' || (cs.availabilityState() === 'READY' && cs.connections().length === 0)"
      class="w-full bg-white border border-slate-200 rounded-xl p-12 text-center shadow-2xs">
      <div class="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center mx-auto mb-4 text-slate-400">
        <app-lucide-icon name="database" [size]="24"></app-lucide-icon>
      </div>
      <h3 class="text-base font-bold text-slate-900 mb-1">
        No Connections Configured
      </h3>
      <p class="text-xs text-slate-500 max-w-md mx-auto mb-6">
        Connect your enterprise databases, warehouse lakes, object stores, and event streams to initiate migrations and validations.
      </p>
      <button
        type="button"
        (click)="onCreate()"
        class="h-9 px-4 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors cursor-pointer shadow-2xs focus:outline-hidden focus:ring-2 focus:ring-blue-500">
        Create Connection
      </button>
    </div>

    <!-- 4. FILTERED EMPTY STATE (Inventory exists, but query matched 0) -->
    <div
      *ngIf="cs.availabilityState() === 'READY' && cs.connections().length > 0 && cs.filteredConnections().length === 0"
      class="w-full bg-white border border-slate-200 rounded-xl p-12 text-center shadow-2xs">
      <div class="w-12 h-12 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center mx-auto mb-4 text-slate-400">
        <app-lucide-icon name="search" [size]="24"></app-lucide-icon>
      </div>
      <h3 class="text-base font-bold text-slate-900 mb-1">
        No matching connections found
      </h3>
      <p class="text-xs text-slate-500 max-w-md mx-auto mb-6">
        No connection profiles match your current search terms or active filters. Clear or adjust your filter parameters to view the inventory.
      </p>
      <button
        type="button"
        (click)="onClearFilters()"
        class="h-9 px-4 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-md transition-colors cursor-pointer shadow-2xs focus:outline-hidden focus:ring-2 focus:ring-slate-400">
        Clear all filters
      </button>
    </div>
  `
})
export class ConnectionsStatesComponent {
  public cs = inject(ConnectionsService);

  @Output() createConnection = new EventEmitter<void>();

  onRetry(): void {
    this.cs.reload();
  }

  onCreate(): void {
    this.createConnection.emit();
  }

  onClearFilters(): void {
    this.cs.clearFilters();
  }
}
