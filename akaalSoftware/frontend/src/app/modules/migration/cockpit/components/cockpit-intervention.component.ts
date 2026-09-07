import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CockpitStoreService } from '../../../../core/services/cockpit-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { OperatorIntervention } from '../cockpit.models';

@Component({
  selector: 'app-cockpit-intervention',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (store.intervention(); as intervention) {
      <div [ngClass]="getBannerContainerClasses(intervention.type)"
           class="rounded-xl border p-6 shadow-2xs flex flex-col md:flex-row items-start md:items-center justify-between gap-5 animate-in fade-in duration-150">
        
        <!-- Left: Icon & Description -->
        <div class="flex items-start gap-4">
          <div [ngClass]="getIconBgClasses(intervention.type)"
               class="w-11 h-11 rounded-lg flex items-center justify-center shrink-0 border">
            <app-lucide-icon [name]="getIconName(intervention.type)" [size]="22" />
          </div>

          <div class="flex flex-col gap-1.5">
            <div class="flex items-center gap-2.5">
              <span [ngClass]="getTypeBadgeClasses(intervention.type)"
                    class="px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border">
                {{ cleanText(formatTypeLabel(intervention.type)) }}
              </span>
              <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">
                {{ cleanText(intervention.title) }}
              </h3>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed max-w-2xl">
              {{ cleanText(intervention.description) }}
            </p>

            <!-- Governance / Failure Specific Details -->
            @if (intervention.type === 'APPROVAL_BARRIER') {
              <div class="flex items-center gap-4 text-xs font-mono text-slate-700 mt-1">
                <span>Signatures: <strong>{{ intervention.currentSignatures || 0 }}/{{ intervention.requiredSignatures || 1 }}</strong></span>
                <span class="text-slate-300">&middot;</span>
                <span>Gate: <strong>{{ cleanText(intervention.barrierGateName || 'Cutover Verification') }}</strong></span>
                <span class="text-slate-300">&middot;</span>
                <span class="text-emerald-700 font-sans font-medium text-[11px] flex items-center gap-1">
                  <app-lucide-icon name="shield-check" [size]="12" />
                  <span>{{ intervention.separationOfDutiesEnforced ? 'Maker Checker Enforced' : 'Solo Operator Mode' }}</span>
                </span>
              </div>
            }

            @if (intervention.recoveryGuidance) {
              <div class="text-[11px] text-slate-500 mt-1 flex items-center gap-1.5">
                <app-lucide-icon name="info" [size]="13" class="text-slate-400" />
                <span>{{ cleanText(intervention.recoveryGuidance) }}</span>
              </div>
            }
          </div>
        </div>

        <!-- Right: Action Buttons (Blue Enterprise & Standard Outlines with Blue hover) -->
        <div class="flex items-center gap-3 self-end md:self-center shrink-0">
          @if (intervention.type === 'APPROVAL_BARRIER') {
            <button
              (click)="store.resolveApprovalBarrier(intervention.barrierId || 'barrier', false)"
              [disabled]="store.actionInFlight()"
              class="h-9 px-4 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 transition-colors disabled:opacity-50 cursor-pointer shadow-2xs">
              Decline &amp; Hold
            </button>
            <button
              (click)="store.resolveApprovalBarrier(intervention.barrierId || 'barrier', true)"
              [disabled]="store.actionInFlight()"
              class="h-9 px-4 text-xs font-semibold rounded-lg bg-purple-700 hover:bg-purple-800 active:bg-purple-900 text-white transition-colors disabled:opacity-50 inline-flex items-center gap-1.5 cursor-pointer shadow-xs">
              <app-lucide-icon name="shield-check" [size]="14" />
              <span>Sign &amp; Authorize</span>
            </button>
          } @else if (intervention.type === 'EXECUTION_FAILURE') {
            <button
              (click)="store.triggerAction('TERMINATE')"
              [disabled]="store.actionInFlight()"
              class="h-9 px-4 text-xs font-semibold rounded-lg bg-white border border-rose-200 hover:border-rose-300 hover:bg-rose-50 text-rose-700 transition-colors disabled:opacity-50 cursor-pointer shadow-2xs">
              Abort Execution
            </button>
            <button
              (click)="store.triggerAction('RECOVER_EXECUTION')"
              [disabled]="store.actionInFlight()"
              class="h-9 px-4 text-xs font-semibold rounded-lg bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white transition-colors disabled:opacity-50 inline-flex items-center gap-1.5 cursor-pointer shadow-xs">
              <app-lucide-icon name="rotate-ccw" [size]="14" />
              <span>Retry from Checkpoint</span>
            </button>
          } @else if (intervention.type === 'HEALTH_DEGRADED') {
            <button
              (click)="store.setSessionState({ isHealthDegraded: false })"
              class="h-9 px-4 text-xs font-semibold rounded-lg bg-white border border-amber-200 hover:border-amber-300 hover:bg-amber-50 text-amber-800 transition-colors cursor-pointer shadow-2xs">
              Acknowledge &amp; Rescan
            </button>
          } @else if (intervention.type === 'MANUAL_HOLD') {
            <button
              (click)="store.triggerAction('RESUME')"
              class="h-9 px-4 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white transition-colors inline-flex items-center gap-1.5 cursor-pointer shadow-xs">
              <app-lucide-icon name="play" [size]="14" />
              <span>Resume Migration</span>
            </button>
          }
        </div>
      </div>
    }
  `
})
export class CockpitInterventionComponent {
  public store = inject(CockpitStoreService);

  public cleanText(val: string | undefined | null): string {
    if (!val) return '';
    return val.replace(/_/g, ' ');
  }

  public formatTypeLabel(type: OperatorIntervention['type']): string {
    switch (type) {
      case 'APPROVAL_BARRIER': return 'Governance Barrier';
      case 'EXECUTION_FAILURE': return 'Execution Failure';
      case 'HEALTH_DEGRADED': return 'Subsystem Warning';
      case 'MANUAL_HOLD': return 'Operator Hold';
      default: return 'Intervention Required';
    }
  }

  public getBannerContainerClasses(type: OperatorIntervention['type']): string {
    switch (type) {
      case 'APPROVAL_BARRIER': return 'bg-purple-50/70 border-purple-200';
      case 'EXECUTION_FAILURE': return 'bg-rose-50/70 border-rose-200';
      case 'HEALTH_DEGRADED': return 'bg-amber-50/70 border-amber-200';
      case 'MANUAL_HOLD': return 'bg-amber-50/70 border-amber-200';
      default: return 'bg-slate-50 border-slate-200';
    }
  }

  public getIconBgClasses(type: OperatorIntervention['type']): string {
    switch (type) {
      case 'APPROVAL_BARRIER': return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'EXECUTION_FAILURE': return 'bg-rose-100 text-rose-700 border-rose-200';
      case 'HEALTH_DEGRADED': return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'MANUAL_HOLD': return 'bg-amber-100 text-amber-700 border-amber-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  public getIconName(type: OperatorIntervention['type']): string {
    switch (type) {
      case 'APPROVAL_BARRIER': return 'shield-alert';
      case 'EXECUTION_FAILURE': return 'alert-octagon';
      case 'HEALTH_DEGRADED': return 'alert-triangle';
      case 'MANUAL_HOLD': return 'pause';
      default: return 'info';
    }
  }

  public getTypeBadgeClasses(type: OperatorIntervention['type']): string {
    switch (type) {
      case 'APPROVAL_BARRIER': return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'EXECUTION_FAILURE': return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'HEALTH_DEGRADED': return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'MANUAL_HOLD': return 'bg-amber-100 text-amber-800 border-amber-300';
      default: return 'bg-slate-100 text-slate-800 border-slate-300';
    }
  }
}
