import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ConnectionsService } from '../connections.service';

@Component({
  selector: 'app-connections-header',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap select-none">
      
      <!-- Title & Context Area -->
      <div class="flex flex-col gap-1">
        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">INFRASTRUCTURE &amp; CONNECTIVITY</span>
        <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Connections</h1>
        <p class="text-sm font-medium text-slate-600 max-w-3xl">
          Inventory of reusable database, lakehouse, streaming, object storage, and enterprise application connection resources governed in this workspace.
        </p>
      </div>

      <!-- Header Primary Action: New Connection (Strictly Text-Led, No Lucide Icon Inside Action Button) -->
      <div class="flex items-center gap-3 pt-1 shrink-0">
        <button
          type="button"
          (click)="onNewConnection()"
          class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/40">
          New Connection
        </button>
      </div>

    </div>
  `
})
export class ConnectionsHeaderComponent {
  public connService = inject(ConnectionsService);
  public cs = this.connService.cs;
  private router = inject(Router);

  public onNewConnection(): void {
    const isMigrationPrefix = this.router.url.startsWith('/migration');
    this.router.navigate([isMigrationPrefix ? '/migration/connections/new' : '/connections/new']);
  }
}
