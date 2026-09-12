/**
 * AKAAL Administration — 5.6 SDK / Developer Configuration
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-sdk-config',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/connectors/extensions-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Extensions
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">SDK &amp; Developer Configuration</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Extension compiler specifications, gRPC inter-process communication sockets, and sandbox memory limits.
            </p>
          </div>
        </div>
      </div>

      <!-- Config Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- SDK Core Properties -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
          <h2 class="text-sm font-bold text-slate-900 font-heading">SDK Runtime Parameters</h2>
          
          <div class="flex flex-col gap-3 text-xs">
            <div class="flex items-center justify-between py-2 border-b border-slate-100">
              <span class="text-slate-500">Active SDK Protocol Release</span>
              <span class="font-mono font-bold text-slate-900">{{ service.sdkConfig().sdkVersion }}</span>
            </div>

            <div class="flex items-center justify-between py-2 border-b border-slate-100">
              <span class="text-slate-500">Max Execution Timeout</span>
              <span class="font-mono font-bold text-slate-900">{{ service.sdkConfig().maxExecutionTimeoutSec }} seconds</span>
            </div>

            <div class="flex items-center justify-between py-2 border-b border-slate-100">
              <span class="text-slate-500">Kernel Sandbox Enforced</span>
              <span class="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {{ service.sdkConfig().sandboxingEnforced ? 'STRICT' : 'PERMISSIVE' }}
              </span>
            </div>

            <div class="flex items-center justify-between py-2 border-b border-slate-100">
              <span class="text-slate-500">IPC Socket Path</span>
              <span class="font-mono text-slate-700 text-[11px]">{{ service.sdkConfig().grpcSocketPath }}</span>
            </div>

            <div class="flex items-center justify-between py-2">
              <span class="text-slate-500">WebAssembly Engine</span>
              <span class="font-mono font-bold text-slate-900">{{ service.sdkConfig().wasmRuntimeEngine }}</span>
            </div>
          </div>
        </div>

        <!-- Supported Language Toolchains -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
          <h2 class="text-sm font-bold text-slate-900 font-heading">Supported Compilation Toolchains</h2>
          <p class="text-xs text-slate-600">Verified language bindings and ABI targets supported by the local AKAAL runtime engine.</p>
          
          <div class="flex flex-col gap-2.5 mt-2">
            @for (rt of service.sdkConfig().supportedRuntimes; track rt) {
              <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs font-mono font-bold text-slate-800">
                <span>{{ rt }}</span>
                <span class="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-sans font-semibold">
                  Verified Toolchain
                </span>
              </div>
            }
          </div>
        </div>

      </div>

    </div>
  `
})
export class SdkConfigComponent {
  public service = inject(ConnectorsPluginsService);
}
