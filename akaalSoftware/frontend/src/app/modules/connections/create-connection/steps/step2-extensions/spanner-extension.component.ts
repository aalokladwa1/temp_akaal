import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionDraft } from '../../create-connection.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-spanner-extension',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-4 select-none">
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        <!-- Google Cloud Project ID -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            GCP Project ID <span class="text-rose-500">*</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.spannerProjectId"
            placeholder="spanner-prod-global"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
        </div>

        <!-- Spanner Instance ID -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Spanner Instance ID <span class="text-rose-500">*</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.spannerInstanceId"
            placeholder="enterprise-banking-instance"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
        </div>

        <!-- Spanner Database ID -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Database ID <span class="text-rose-500">*</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.spannerDatabaseId"
            placeholder="accounts_db"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
        </div>

      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        <!-- Channel Pool Size -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            gRPC Channel Pool Size
          </label>
          <input
            type="number"
            [(ngModel)]="draft.spannerChannelPoolSize"
            placeholder="4"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          <span class="text-[11px] text-slate-400">
            Number of parallel sub-channels for partition queries.
          </span>
        </div>

        <!-- Priority Selector -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            RPC Priority Mode
          </label>
          <app-custom-select
            [options]="priorityOptions"
            [value]="draft.spannerPriority"
            (valueChange)="onPriorityChange($event)">
          </app-custom-select>
          <span class="text-[11px] text-slate-400">
            Priority assigned to bulk reading/writing sessions.
          </span>
        </div>

        <!-- Emulator Host (Optional for local testing) -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Emulator Host <span class="text-slate-400 font-normal">(Dev Only)</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.spannerEmulatorHost"
            placeholder="localhost:9010"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          <span class="text-[11px] text-slate-400">
            Optional local Cloud Spanner Emulator endpoint.
          </span>
        </div>

      </div>

    </div>
  `
})
export class SpannerExtensionComponent {
  @Input() draft!: CreateConnectionDraft;

  public priorityOptions: CustomSelectOption[] = [
    { label: 'HIGH (Interactive Priority)', value: 'HIGH' },
    { label: 'MEDIUM (Default Balanced)', value: 'MEDIUM' },
    { label: 'LOW (Background Batch Workload)', value: 'LOW' }
  ];

  public onPriorityChange(val: string): void {
    this.draft.spannerPriority = val as any;
  }
}
