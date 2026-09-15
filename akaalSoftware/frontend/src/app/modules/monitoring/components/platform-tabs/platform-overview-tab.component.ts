/**
 * AKAAL Monitoring — Part 3 of 4: Platform Overview Tab Component
 * Executive orientation surface summarizing platform readiness, liveness,
 * active conditions, 7-dimensional composed state, and core subsystem statuses.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { PlatformMonitoringService } from '../../services/platform-monitoring.service';
import { PlatformTabKey } from '../../models/platform-monitoring.models';

@Component({
  selector: 'app-platform-overview-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Executive Platform Health & Metrics Strip -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
        
        <!-- Nodes -->
        <div 
          (click)="onNavigate('infrastructure')"
          class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1 cursor-pointer hover:border-slate-300 transition-colors group">
          <span class="text-xs font-medium text-slate-500">Compute Fleet</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight group-hover:text-blue-600 transition-colors">
              {{ pms.summary().healthy_nodes }} / {{ pms.summary().total_nodes }}
            </span>
            <span class="text-xs text-slate-400">nodes</span>
          </div>
          <span class="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            100% Cluster Healthy
          </span>
        </div>

        <!-- Runtime Services -->
        <div 
          (click)="onNavigate('runtime')"
          class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1 cursor-pointer hover:border-slate-300 transition-colors group">
          <span class="text-xs font-medium text-slate-500">Internal Services</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight group-hover:text-blue-600 transition-colors">
              {{ pms.summary().healthy_services }} / {{ pms.summary().total_services }}
            </span>
            <span class="text-xs text-slate-400">active</span>
          </div>
          <span class="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            All Nominal (v2.4.1)
          </span>
        </div>

        <!-- Multi-Engine Connectors -->
        <div 
          (click)="onNavigate('connectivity')"
          class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1 cursor-pointer hover:border-slate-300 transition-colors group">
          <span class="text-xs font-medium text-slate-500">Data-Path Connectors</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight group-hover:text-blue-600 transition-colors">
              {{ pms.summary().healthy_connectors }} / {{ pms.summary().total_connectors }}
            </span>
            <span class="text-xs text-slate-400">nominal</span>
          </div>
          <span class="text-[11px] text-amber-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            1 Pool Elevated
          </span>
        </div>

        <!-- Active Workers -->
        <div 
          (click)="onNavigate('infrastructure')"
          class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1 cursor-pointer hover:border-slate-300 transition-colors group">
          <span class="text-xs font-medium text-slate-500">Worker Slots</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-blue-600 font-mono tracking-tight group-hover:text-blue-700 transition-colors">
              {{ pms.summary().active_workers }} / {{ pms.summary().total_workers }}
            </span>
            <span class="text-xs text-slate-400">busy</span>
          </div>
          <span class="text-[11px] text-slate-400 font-medium">5 standby slots available</span>
        </div>

        <!-- Capacity Headroom -->
        <div 
          (click)="onNavigate('capacity')"
          class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1 cursor-pointer hover:border-slate-300 transition-colors group">
          <span class="text-xs font-medium text-slate-500">CPU Headroom</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight group-hover:text-blue-600 transition-colors">
              {{ pms.summary().cpu_headroom_pct }}%
            </span>
            <span class="text-xs text-slate-400">free</span>
          </div>
          <span class="text-[11px] text-emerald-600 font-medium">92.3 GB RAM free</span>
        </div>

      </div>

      <!-- 2. Active Conditions & Attention Items -->
      @if (pms.conditions().length > 0) {
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-amber-500"></span>
              <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Active Platform Conditions</h3>
            </div>
            <span class="text-xs font-semibold text-amber-800 bg-amber-50 px-2 py-0.5 rounded">
              {{ pms.conditions().length }} active conditions
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            @for (cond of pms.conditions(); track cond.id) {
              <div 
                (click)="onNavigate(cond.target_tab)"
                class="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-blue-300 transition-colors flex flex-col justify-between gap-2.5 text-xs cursor-pointer group">
                <div class="flex flex-col gap-1">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-slate-900 group-hover:text-blue-600 transition-colors">{{ cond.title }}</span>
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-semibold uppercase"
                      [ngClass]="cond.severity === 'CRITICAL' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700'">
                      {{ cond.severity }}
                    </span>
                  </div>
                  <p class="text-slate-600 leading-relaxed">{{ cond.summary }}</p>
                </div>

                <div class="flex items-center justify-between pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 font-mono">
                  <span>{{ cond.subsystem }}</span>
                  <span class="text-blue-600 font-semibold group-hover:underline">Inspect in {{ pms.formatText(cond.target_tab) }} →</span>
                </div>
              </div>
            }
          </div>
        </div>
      }

      <!-- 3. Core Subsystems Matrix -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Subsystem Operational Readiness</h3>
          <span class="text-xs text-slate-500">Autonomous self-monitoring active</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          
          <!-- Runtime & Services -->
          <div 
            (click)="onNavigate('runtime')"
            class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between gap-2 cursor-pointer hover:border-blue-300 transition-colors">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Runtime &amp; Services</span>
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            </div>
            <p class="text-slate-500 text-[11px]">8/8 daemons running, zero fatal exceptions in 24h.</p>
            <span class="text-[11px] font-semibold text-blue-600">View Services →</span>
          </div>

          <!-- Connectivity -->
          <div 
            (click)="onNavigate('connectivity')"
            class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between gap-2 cursor-pointer hover:border-blue-300 transition-colors">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Connectivity &amp; Endpoints</span>
              <span class="w-2 h-2 rounded-full bg-amber-500"></span>
            </div>
            <p class="text-slate-500 text-[11px]">PostgreSQL pool elevated (24/32), all drivers authenticated.</p>
            <span class="text-[11px] font-semibold text-blue-600">View Endpoints →</span>
          </div>

          <!-- Infrastructure -->
          <div 
            (click)="onNavigate('infrastructure')"
            class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between gap-2 cursor-pointer hover:border-blue-300 transition-colors">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Infrastructure &amp; Fleet</span>
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            </div>
            <p class="text-slate-500 text-[11px]">4 nodes in Raft cluster, 11 busy workers, 5 idle slots.</p>
            <span class="text-[11px] font-semibold text-blue-600">View Nodes →</span>
          </div>

          <!-- Capacity -->
          <div 
            (click)="onNavigate('capacity')"
            class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between gap-2 cursor-pointer hover:border-blue-300 transition-colors">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900">Capacity &amp; Performance</span>
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            </div>
            <p class="text-slate-500 text-[11px]">90,170 ops/s throughput, 62% CPU headroom available.</p>
            <span class="text-[11px] font-semibold text-blue-600">View Capacity →</span>
          </div>

        </div>
      </div>

    </div>
  `
})
export class PlatformOverviewTabComponent {
  public pms = inject(PlatformMonitoringService);
  private router = inject(Router);

  public onNavigate(tab: PlatformTabKey): void {
    this.pms.selectTab(tab);
    this.router.navigate(['/monitoring/platform', tab]);
  }
}
