/**
 * AKAAL Monitoring — Part 3 of 4: Platform Monitoring Home Component
 * Root container for Platform Operations, coordinating route subscriptions,
 * the contextual platform header, stable underline tab navigation, and the 8 investigation areas.
 */

import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';

import { PlatformMonitoringService } from './services/platform-monitoring.service';
import { PlatformTabKey } from './models/platform-monitoring.models';

import { PlatformHeaderComponent } from './components/platform-header.component';
import { PlatformNavComponent } from './components/platform-nav.component';

import { PlatformOverviewTabComponent } from './components/platform-tabs/platform-overview-tab.component';
import { PlatformRuntimeTabComponent } from './components/platform-tabs/platform-runtime-tab.component';
import { PlatformConnectivityTabComponent } from './components/platform-tabs/platform-connectivity-tab.component';
import { PlatformInfrastructureTabComponent } from './components/platform-tabs/platform-infrastructure-tab.component';
import { PlatformCapacityTabComponent } from './components/platform-tabs/platform-capacity-tab.component';
import { PlatformPerformanceTabComponent } from './components/platform-tabs/platform-performance-tab.component';
import { PlatformReliabilityTabComponent } from './components/platform-tabs/platform-reliability-tab.component';
import { PlatformDiagnosticsTabComponent } from './components/platform-tabs/platform-diagnostics-tab.component';

@Component({
  selector: 'app-platform-monitoring-home',
  standalone: true,
  imports: [
    CommonModule,
    PlatformHeaderComponent,
    PlatformNavComponent,
    PlatformOverviewTabComponent,
    PlatformRuntimeTabComponent,
    PlatformConnectivityTabComponent,
    PlatformInfrastructureTabComponent,
    PlatformCapacityTabComponent,
    PlatformPerformanceTabComponent,
    PlatformReliabilityTabComponent,
    PlatformDiagnosticsTabComponent
  ],
  template: `
    <div class="flex flex-col gap-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Contextual Platform Header -->
      <app-platform-header></app-platform-header>

      <!-- 2. Stable Rectangular Underline Navigation Bar (NO pills, NO capsules) -->
      <app-platform-nav></app-platform-nav>

      <!-- 3. Active Investigation Workspace -->
      @switch (pms.selectedTab()) {
        @case ('overview') {
          <app-platform-overview-tab></app-platform-overview-tab>
        }
        @case ('runtime') {
          <app-platform-runtime-tab></app-platform-runtime-tab>
        }
        @case ('connectivity') {
          <app-platform-connectivity-tab></app-platform-connectivity-tab>
        }
        @case ('infrastructure') {
          <app-platform-infrastructure-tab></app-platform-infrastructure-tab>
        }
        @case ('capacity') {
          <app-platform-capacity-tab></app-platform-capacity-tab>
        }
        @case ('performance') {
          <app-platform-performance-tab></app-platform-performance-tab>
        }
        @case ('reliability') {
          <app-platform-reliability-tab></app-platform-reliability-tab>
        }
        @case ('diagnostics') {
          <app-platform-diagnostics-tab></app-platform-diagnostics-tab>
        }
        @default {
          <app-platform-overview-tab></app-platform-overview-tab>
        }
      }

    </div>
  `
})
export class PlatformMonitoringHomeComponent implements OnInit, OnDestroy {
  public pms = inject(PlatformMonitoringService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private sub?: Subscription;

  ngOnInit(): void {
    this.sub = this.route.params.subscribe(params => {
      const tab = params['tab'] as PlatformTabKey;
      const validTabs: PlatformTabKey[] = [
        'overview',
        'runtime',
        'connectivity',
        'infrastructure',
        'capacity',
        'performance',
        'reliability',
        'diagnostics'
      ];

      if (tab && validTabs.includes(tab)) {
        this.pms.selectTab(tab);
      } else {
        this.pms.selectTab('overview');
      }

      if (params['id']) {
        if (tab === 'infrastructure') {
          this.pms.selectNode(params['id']);
        } else if (tab === 'runtime') {
          this.pms.selectService(params['id']);
        }
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
