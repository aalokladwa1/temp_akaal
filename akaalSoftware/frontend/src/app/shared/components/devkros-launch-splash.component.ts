import { Component, inject, HostListener, ElementRef, OnInit, OnDestroy, Renderer2 } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LaunchLifecycleService } from '../../core/services/launch-lifecycle.service';
import { DashboardService } from '../../core/services/dashboard.service';
import { DevkrosLogoComponent } from './devkros-logo.component';
import { DevkrosWordmarkComponent } from './devkros-wordmark.component';

@Component({
  selector: 'app-devkros-launch-splash',
  standalone: true,
  imports: [CommonModule, DevkrosLogoComponent, DevkrosWordmarkComponent],
  template: `
    @if (launch && !launch.isCompleted()) {
      <div
        class="fixed inset-0 z-[500] flex items-center justify-center select-none overflow-hidden bg-transparent"
        [style.color]="launchSurfaceFg"
        role="dialog"
        aria-label="Application Launch Screen">

        <!-- =============================================================== -->
        <!-- MASKED LAUNCH SURFACE (CONCEALS DASHBOARD UNTIL PORTAL EXPANDS) -->
        <!-- =============================================================== -->
        <svg class="absolute inset-0 w-full h-full pointer-events-none z-0" [attr.viewBox]="'0 0 ' + viewportWidth + ' ' + viewportHeight">
          <defs>
            <mask id="devkros-portal-mask">
              <!-- Solid white rect covers viewport (concealing dashboard) -->
              <rect x="0" y="0" [attr.width]="viewportWidth" [attr.height]="viewportHeight" fill="white" />
              <!-- Aperture hole centered on letter V, expanding synchronously during Stage 3 -->
              <g
                [style.transformOrigin]="'calc(50% + 32px) 50%'"
                [style.transform]="portalMaskTransform"
                [style.transition]="portalMaskTransition">
                <polygon points="-24,-24 24,-24 0,24" fill="black" />
              </g>
            </mask>
          </defs>
          <rect
            x="0"
            y="0"
            [attr.width]="viewportWidth"
            [attr.height]="viewportHeight"
            [attr.fill]="launchSurfaceBg"
            mask="url(#devkros-portal-mask)" />
        </svg>

        <!-- =============================================================== -->
        <!-- CONTINUOUS BRAND IDENTITY & ZOOM CHOREOGRAPHY CONTAINER         -->
        <!-- =============================================================== -->
        @if (!launch.isError()) {
          <div class="relative flex items-center justify-center w-full h-full pointer-events-none overflow-hidden z-10">

            <!-- Lockup Container (Whole-Unit Optically Centered & Zooming) -->
            <div
              class="relative flex flex-col items-center justify-center pointer-events-none"
              [style.transition]="lockupContainerTransition"
              [style.transformOrigin]="'calc(50% + 32px) 50%'"
              [style.transform]="lockupContainerTransform">

              <div class="flex items-center justify-center relative">
                <!-- Standalone Approved Mark (SVG Geometry) -->
                <div
                  class="shrink-0 flex items-center justify-center transition-all duration-500 ease-out"
                  [style.transform]="markRotationTransform">
                  <app-devkros-logo [size]="standaloneLogoSize" variant="auto"></app-devkros-logo>
                </div>

                <!-- Approved Vector Wordmark (Unmasks horizontally in Stage 2) -->
                <div
                  class="overflow-hidden transition-all duration-700 ease-out flex items-center shrink-0"
                  [style.maxWidth.px]="wordmarkMaxWidth"
                  [style.opacity]="wordmarkOpacity"
                  [style.marginLeft.px]="wordmarkMarginLeft">
                  <app-devkros-wordmark [height]="48"></app-devkros-wordmark>
                </div>
              </div>

              <!-- Minimal Premium Loading Bar (Stage 1 Only, Clean Monochrome Line) -->
              <div
                class="w-14 h-[2px] mt-6 rounded-full bg-slate-300/40 dark:bg-white/10 overflow-hidden relative transition-all duration-300 ease-out shrink-0"
                [class.opacity-100]="showLoadingBar"
                [class.opacity-0]="!showLoadingBar"
                [class.scale-95]="!showLoadingBar">
                <div
                  class="h-full bg-slate-700 dark:bg-slate-200 rounded-full transition-all duration-300 cubic-bezier(0.16, 1, 0.3, 1)"
                  [style.width.%]="loadingBarWidthPercent">
                </div>
              </div>

            </div>

          </div>
        }

        <!-- =============================================================== -->
        <!-- TRUTHFUL ERROR & RECOVERY PRESENTATION                          -->
        <!-- =============================================================== -->
        @if (launch.isError()) {
          <div class="flex flex-col items-center gap-4 max-w-md p-6 bg-white dark:bg-[#17181b] rounded-xl border border-slate-200 dark:border-white/10 shadow-xl text-center z-20">
            <div class="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center">
              <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
            <div class="flex flex-col gap-1">
              <h3 class="text-lg font-bold text-slate-900 dark:text-white">Startup Initialization Issue</h3>
              <p class="text-xs text-slate-600 dark:text-slate-400">
                {{ ds.lastError() || 'Backend connection could not be established.' }}
              </p>
            </div>
            <button
              type="button"
              (click)="retry()"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors cursor-pointer">
              Retry Initialization
            </button>
          </div>
        }

      </div>
    }
  `
})
export class DevkrosLaunchSplashComponent implements OnInit, OnDestroy {
  public launch!: LaunchLifecycleService;
  public ds!: DashboardService;
  private renderer?: Renderer2;

  public viewportWidth = 1920;
  public viewportHeight = 1080;
  private unbindResize: (() => void) | null = null;

  constructor(launch?: LaunchLifecycleService, ds?: DashboardService) {
    if (launch) {
      this.launch = launch;
    } else {
      try {
        this.launch = inject(LaunchLifecycleService, { optional: true }) as LaunchLifecycleService;
      } catch {
        // Fallback for direct unit test instantiation
      }
    }

    if (ds) {
      this.ds = ds;
    } else {
      try {
        this.ds = inject(DashboardService, { optional: true }) as DashboardService;
      } catch {
        // Fallback for direct unit test instantiation
      }
    }

    try {
      this.renderer = inject(Renderer2, { optional: true }) as Renderer2;
    } catch {
      // Fallback for direct unit test instantiation
    }
  }

  ngOnInit(): void {
    this.updateViewportDimensions();
    if (typeof window !== 'undefined' && this.renderer) {
      this.unbindResize = this.renderer.listen('window', 'resize', () => {
        this.updateViewportDimensions();
      });
    }
  }

  ngOnDestroy(): void {
    if (this.unbindResize) {
      this.unbindResize();
    }
  }

  private updateViewportDimensions(): void {
    if (typeof window !== 'undefined') {
      this.viewportWidth = window.innerWidth || 1920;
      this.viewportHeight = window.innerHeight || 1080;
    }
  }

  public get launchSurfaceBg(): string {
    if (typeof document !== 'undefined') {
      const isDark = document.documentElement.classList.contains('dark') || document.documentElement.getAttribute('data-theme') === 'dark';
      return isDark ? '#111214' : '#ffffff';
    }
    return '#ffffff';
  }

  public get splashContainerBg(): string {
    return 'transparent';
  }

  public get standaloneLogoSize(): number {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    if (state === 'STAGE_2_BRAND_ASSEMBLY' || state === 'LOCKUP_SETTLE' || state === 'STAGE_3_ZOOM_THROUGH') {
      return 76;
    }
    return 66; // Modest ~13% reduction in Stage 1 for refined breathing room
  }

  public get showLoadingBar(): boolean {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    return state === 'STAGE_1_CANVAS' || state === 'STAGE_1_ROTATION';
  }

  public get loadingBarWidthPercent(): number {
    if (!this.launch) return 15;
    const ratio = (this.launch as any).getReadinessGateRatio ? (this.launch as any).getReadinessGateRatio() : 0.15;
    return Math.max(15, Math.round(ratio * 100));
  }

  public get portalMaskTransform(): string {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    if (state === 'STAGE_3_ZOOM_THROUGH') {
      return 'scale(60)';
    }
    return 'scale(0)';
  }

  public get portalMaskTransition(): string {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    if (state === 'STAGE_3_ZOOM_THROUGH') {
      return 'transform 350ms cubic-bezier(0.6, 0, 0.85, 0.1)';
    }
    return 'none';
  }

  public get zoomOriginPoint(): string {
    return `${this.zoomOriginX}px ${this.zoomOriginY}px`;
  }

  public get launchSurfaceFg(): string {
    if (typeof document !== 'undefined') {
      const isDark = document.documentElement.classList.contains('dark') || document.documentElement.getAttribute('data-theme') === 'dark';
      return isDark ? '#f8fafc' : '#0f172a';
    }
    return '#0f172a';
  }

  public get markRotationTransform(): string {
    const angle = this.launch ? this.launch.currentAngle : 0;
    return `rotate(${angle}deg)`;
  }

  public get lockupContainerTransform(): string {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    if (state === 'STAGE_3_ZOOM_THROUGH') {
      return 'scale(45)';
    }
    return 'scale(1)';
  }

  public get lockupContainerTransition(): string {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    if (state === 'STAGE_3_ZOOM_THROUGH') {
      return 'transform 350ms cubic-bezier(0.6, 0, 0.85, 0.1)';
    }
    return 'transform 700ms cubic-bezier(0.16, 1, 0.3, 1)';
  }

  public get wordmarkMaxWidth(): number {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    if (state === 'STAGE_2_BRAND_ASSEMBLY' || state === 'LOCKUP_SETTLE' || state === 'STAGE_3_ZOOM_THROUGH') {
      return 222;
    }
    return 0;
  }

  public get wordmarkOpacity(): number {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    if (state === 'STAGE_2_BRAND_ASSEMBLY' || state === 'LOCKUP_SETTLE' || state === 'STAGE_3_ZOOM_THROUGH') {
      return 1;
    }
    return 0;
  }

  public get wordmarkMarginLeft(): number {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    if (state === 'STAGE_2_BRAND_ASSEMBLY' || state === 'LOCKUP_SETTLE' || state === 'STAGE_3_ZOOM_THROUGH') {
      return 20;
    }
    return 0;
  }

  // Zoom Portal Calculations
  public get zoomOriginX(): number {
    return this.viewportWidth / 2;
  }

  public get zoomOriginY(): number {
    return this.viewportHeight / 2;
  }

  public get zoomScale(): number {
    const maxDist = Math.sqrt(Math.pow(this.viewportWidth / 2, 2) + Math.pow(this.viewportHeight / 2, 2));
    return (maxDist / 50) * 1.5;
  }

  // Terminal Aperture Full Viewport Coverage Proof
  public get terminalApertureX(): number {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    return state === 'STAGE_3_ZOOM_THROUGH' ? 0 : this.viewportWidth / 2;
  }

  public get terminalApertureY(): number {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    return state === 'STAGE_3_ZOOM_THROUGH' ? 0 : this.viewportHeight / 2;
  }

  public get terminalApertureW(): number {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    return state === 'STAGE_3_ZOOM_THROUGH' ? this.viewportWidth : 0;
  }

  public get terminalApertureH(): number {
    const state = this.launch ? this.launch.state() : 'STAGE_1_ROTATION';
    return state === 'STAGE_3_ZOOM_THROUGH' ? this.viewportHeight : 0;
  }

  public retry(): void {
    if (this.launch) {
      this.launch.retryStartup();
    }
  }
}
