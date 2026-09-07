import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-cockpit-header',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <header class="bg-white border-b border-slate-200 px-6 lg:px-8 py-4 sticky top-0 z-30 shadow-2xs">
      <div class="max-w-[1600px] mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        <!-- Identity Zone -->
        <div class="flex flex-col gap-2">
          <!-- Breadcrumbs & Meta Badges (Rectangular with curved corners, NO capsule pills) -->
          <div class="flex items-center flex-wrap gap-2 text-xs">
            <span class="text-slate-400 font-medium">AKAAL Enterprise</span>
            <span class="text-slate-300">/</span>
            <span class="text-slate-500 font-medium">Migrations</span>
            <span class="text-slate-300">/</span>
            
            <button
              (click)="store.copyMigrationId()"
              class="inline-flex items-center gap-1.5 font-mono text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 hover:border-blue-300 transition-colors border border-slate-200 cursor-pointer"
              [title]="'Click to copy migration ID: ' + store.identity().migrationId">
              <span>{{ cleanText(store.identity().migrationId) }}</span>
              <app-lucide-icon
                [name]="store.copiedMigrationId() ? 'check' : 'copy'"
                [size]="12"
                [class]="store.copiedMigrationId() ? 'text-emerald-600' : 'text-slate-400'" />
            </button>

            <span class="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-50 text-slate-700 border border-slate-200">
              {{ cleanText(store.identity().environment) }}
            </span>

            <span class="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              {{ cleanText(store.identity().modeTitle) }}
            </span>

            <span class="inline-flex items-center gap-1.5 font-mono text-[11px] px-2.5 py-1 rounded-md bg-slate-50 text-slate-600 border border-slate-200" title="Plan Revision and Fingerprint">
              <span>Rev {{ store.identity().planRevision }}</span>
              <span class="text-slate-300">&middot;</span>
              <span class="truncate max-w-[110px]">{{ store.identity().planFingerprint.substring(0, 10) }}&hellip;</span>
            </span>
          </div>

          <!-- Title & Lifecycle Status (Rectangular with curved corners) -->
          <div class="flex items-center flex-wrap gap-3.5 pt-0.5">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight font-heading">
              {{ cleanText(store.identity().migrationName) }}
            </h1>

            <!-- Lifecycle Badge (Rectangular with curved corners rounded-md) -->
            <div [ngClass]="getLifecycleBadgeClasses(store.identity().lifecycleState)"
                 class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider border">
              <span class="w-2 h-2 rounded-sm" [ngClass]="getLifecycleDotClasses(store.identity().lifecycleState)"></span>
              <span>{{ cleanText(store.identity().lifecycleLabel) }}</span>
            </div>

            <!-- Endpoint Route Summary Card -->
            <div class="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100/80 border border-slate-200 text-xs text-slate-700 transition-colors">
              <div class="flex items-center gap-1.5 font-medium">
                <app-lucide-icon name="database" [size]="13" class="text-blue-600" />
                <span class="font-bold text-slate-900">{{ cleanText(store.identity().source.provider) }}</span>
                <span class="text-slate-400 font-mono text-[11px]">({{ cleanText(store.identity().source.label) }})</span>
              </div>
              <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400" />
              <div class="flex items-center gap-1.5 font-medium">
                <app-lucide-icon name="database" [size]="13" class="text-emerald-600" />
                <span class="font-bold text-slate-900">{{ cleanText(store.identity().target.provider) }}</span>
                <span class="text-slate-400 font-mono text-[11px]">({{ cleanText(store.identity().target.label) }})</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Command Bar Zone (Enterprise Blue Buttons + Blue-hover Secondary Buttons) -->
        <div class="flex items-center gap-2.5 shrink-0">
          <!-- Full DAG Topology Modal Trigger -->
          <button
            (click)="store.toggleFullDagModal(true)"
            class="h-9 px-3.5 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50 text-slate-700 hover:text-blue-700 transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs">
            <app-lucide-icon name="git-branch" [size]="14" class="text-slate-500 group-hover:text-blue-600" />
            <span>Full Plan DAG</span>
          </button>

          <!-- Primary Canonical Action Button (Blue Enterprise Button) -->
          @if (store.primaryAction(); as primary) {
            <button
              (click)="store.triggerAction(primary.id)"
              [disabled]="primary.disabled || store.actionInFlight()"
              [ngClass]="primary.isDestructive 
                ? 'bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white' 
                : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white'"
              class="h-9 px-4 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 shadow-xs disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
              <app-lucide-icon [name]="primary.icon" [size]="14" />
              <span>{{ cleanText(primary.label) }}</span>
            </button>
          }

          <!-- Secondary Actions Dropdown Menu Trigger -->
          <div class="relative inline-block text-left" (click)="$event.stopPropagation()">
            <button
              (click)="toggleMenu()"
              class="h-9 px-3.5 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50 text-slate-700 hover:text-blue-700 transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs">
              <span>Actions</span>
              <app-lucide-icon name="chevron-down" [size]="14" class="text-slate-400" />
            </button>

            <!-- Dropdown Flyout -->
            @if (isMenuOpen()) {
              <div
                class="origin-top-right absolute right-0 mt-2 w-64 rounded-xl bg-white border border-slate-200 shadow-xl py-1.5 z-50 focus:outline-none animate-in fade-in duration-100">
                <div class="px-3.5 py-1.5 text-[10px] font-bold tracking-wider uppercase text-slate-400 border-b border-slate-100">
                  Permitted Operations
                </div>

                @for (action of store.secondaryActions(); track action.id) {
                  <button
                    (click)="handleSecondaryAction(action.id)"
                    [disabled]="action.disabled || store.actionInFlight()"
                    [ngClass]="action.isDestructive 
                      ? 'text-rose-600 hover:bg-rose-50' 
                      : 'text-slate-700 hover:bg-blue-50 hover:text-blue-700'"
                    class="w-full text-left px-3.5 py-2.5 text-xs font-medium flex items-center gap-2.5 transition-colors disabled:opacity-40 cursor-pointer">
                    <app-lucide-icon [name]="action.icon" [size]="14" [class]="action.isDestructive ? 'text-rose-600' : 'text-slate-500'" />
                    <span class="flex-1">{{ cleanText(action.label) }}</span>
                  </button>
                }

                <div class="border-t border-slate-100 my-1"></div>
                <button
                  (click)="handleTriggerCheckpoint()"
                  class="w-full text-left px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-700 flex items-center gap-2.5 cursor-pointer">
                  <app-lucide-icon name="hard-drive" [size]="14" class="text-slate-400" />
                  <span>Request Immediate Checkpoint</span>
                </button>
                <button
                  (click)="handleRefresh()"
                  class="w-full text-left px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-700 flex items-center gap-2.5 cursor-pointer">
                  <app-lucide-icon name="refresh-cw" [size]="14" class="text-slate-400" />
                  <span>Rescan Subsystem Health</span>
                </button>
              </div>
            }
          </div>
        </div>
      </div>
    </header>

    <!-- Modal Dialog for Action Confirmation -->
    @if (store.pendingConfirmationAction(); as pending) {
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-150 backdrop-blur-xs">
        <div class="bg-white rounded-xl border border-slate-200 max-w-md w-full p-6 shadow-2xl flex flex-col gap-4">
          <div class="flex items-start gap-3.5">
            <div [ngClass]="pending.isDestructive ? 'bg-rose-100 text-rose-600 border-rose-200' : 'bg-blue-100 text-blue-600 border-blue-200'"
                 class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border">
              <app-lucide-icon [name]="pending.isDestructive ? 'alert-octagon' : 'alert-triangle'" [size]="20" />
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900">
                {{ cleanText(pending.confirmationTitle || 'Confirm ' + pending.label) }}
              </h3>
              <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                {{ cleanText(pending.confirmationMessage || 'Are you sure you want to proceed with this operation?') }}
              </p>
            </div>
          </div>

          <!-- Impact List -->
          @if (pending.confirmationImpacts && pending.confirmationImpacts.length > 0) {
            <div class="bg-slate-50 rounded-lg p-3.5 border border-slate-200">
              <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">Operational Impact</div>
              <ul class="text-xs text-slate-700 space-y-1.5">
                @for (impact of pending.confirmationImpacts; track impact) {
                  <li class="flex items-start gap-2">
                    <span class="text-blue-500 mt-0.5">&bull;</span>
                    <span>{{ cleanText(impact) }}</span>
                  </li>
                }
              </ul>
            </div>
          }

          <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
            <button
              (click)="store.cancelPendingAction()"
              [disabled]="store.actionInFlight()"
              class="h-9 px-4 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 transition-colors cursor-pointer">
              Cancel
            </button>
            <button
              (click)="store.confirmPendingAction()"
              [disabled]="store.actionInFlight()"
              [ngClass]="pending.isDestructive ? 'bg-rose-600 hover:bg-rose-700' : 'bg-blue-600 hover:bg-blue-700'"
              class="h-9 px-4 text-xs font-semibold rounded-lg text-white transition-colors cursor-pointer shadow-xs">
              Confirm &amp; Execute
            </button>
          </div>
        </div>
      </div>
    }
  `
})
export class CockpitHeaderComponent {
  public store = inject(CockpitStoreService);
  public isMenuOpen = signal<boolean>(false);

  public toggleMenu(): void {
    this.isMenuOpen.update(v => !v);
  }

  public handleSecondaryAction(actionId: string): void {
    this.isMenuOpen.set(false);
    this.store.triggerAction(actionId);
  }

  public handleTriggerCheckpoint(): void {
    this.isMenuOpen.set(false);
    this.store.triggerAction('REQUEST_CHECKPOINT');
  }

  public handleRefresh(): void {
    this.isMenuOpen.set(false);
    this.store.triggerAction('RESCAN_HEALTH');
  }

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }

  public getLifecycleBadgeClasses(state: string): string {
    switch (state) {
      case 'RUNNING':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'PAUSED':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'WAITING_FOR_APPROVAL':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'RECOVERING':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'FAILED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'COMPLETED':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      case 'CANCELLED':
        return 'bg-slate-100 text-slate-800 border-slate-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  }

  public getLifecycleDotClasses(state: string): string {
    switch (state) {
      case 'RUNNING':
        return 'bg-emerald-500 animate-pulse';
      case 'PAUSED':
        return 'bg-amber-500';
      case 'WAITING_FOR_APPROVAL':
        return 'bg-purple-500 animate-pulse';
      case 'RECOVERING':
        return 'bg-blue-500 animate-pulse';
      case 'FAILED':
        return 'bg-rose-500';
      case 'COMPLETED':
        return 'bg-slate-500';
      default:
        return 'bg-slate-400';
    }
  }
}
