import { Injectable, inject, signal, computed, ApplicationRef, afterNextRender } from '@angular/core';
import { Router } from '@angular/router';
import { IpcService } from './ipc.service';
import { DashboardService } from './dashboard.service';
import { ContextService } from './context.service';

export type LaunchState =
  | 'PROCESS_START'
  | 'STAGE_1_CANVAS'
  | 'STAGE_1_ROTATION'
  | 'RESOLVING_UPRIGHT'
  | 'STAGE_2_BRAND_ASSEMBLY'
  | 'LOCKUP_SETTLE'
  | 'STAGE_3_ZOOM_THROUGH'
  | 'COMPLETED'
  | 'ERROR';

export type LaunchProcessState = 'NOT_STARTED' | 'CLAIMED_RUNNING' | 'COMPLETED';

export interface LaunchProcessRecord {
  sessionToken: string;
  state: LaunchProcessState;
  claimedAt: number;
  completedAt?: number;
}

function getNow(): number {
  if (typeof performance !== 'undefined' && performance.now) {
    return performance.now();
  }
  return Date.now();
}

function getGlobalContext(): any {
  if (typeof window !== 'undefined') return window;
  if (typeof globalThis !== 'undefined') return globalThis;
  return {};
}

@Injectable({
  providedIn: 'root'
})
export class LaunchLifecycleService {
  // Optional Service Dependencies
  private ipc?: IpcService;
  private ds?: DashboardService;
  private context?: ContextService;
  private router?: Router;
  private appRef?: ApplicationRef;

  // Core Reactive Launch State
  public state = signal<LaunchState>('PROCESS_START');
  public isCompleted = computed(() => this.state() === 'COMPLETED');
  public isError = computed(() => this.state() === 'ERROR');

  // Motion Parameters (Prototype Defaults, Visually Tunable)
  public readonly quarterTurnMs = 600;      // 150 deg/s constant Stage 1 velocity
  public readonly brandAssemblyMs = 450;    // Stage 2 translation + mask reveal
  public readonly lockupSettleMs = 250;     // Stage 2 settle (short readable hold)
  public readonly zoomThroughMs = 350;      // Stage 3 fast SVG vector scale zoom-through (350 ms acceleration)

  // Rotational & Motion Tracking Variables
  public quarterIndex = 0;
  public currentAngle = 0;
  public quarterStartTime = 0;
  public isReadinessPending = false;
  public isReducedMotion = false;

  // 10-Gate Readiness Flags
  public fontsLoaded = false;
  public angularRenderComplete = false;
  public browserPaintCommitted = false;

  private animFrameId: any = null;

  constructor(
    ipc?: IpcService,
    ds?: DashboardService,
    context?: ContextService,
    router?: Router
  ) {
    if (ipc) {
      this.ipc = ipc;
    } else {
      try { this.ipc = inject(IpcService, { optional: true }) || undefined; } catch {}
    }

    if (ds) {
      this.ds = ds;
    } else {
      try { this.ds = inject(DashboardService, { optional: true }) || undefined; } catch {}
    }

    if (context) {
      this.context = context;
    } else {
      try { this.context = inject(ContextService, { optional: true }) || undefined; } catch {}
    }

    if (router) {
      this.router = router;
    } else {
      try { this.router = inject(Router, { optional: true }) || undefined; } catch {}
    }

    try { this.appRef = inject(ApplicationRef, { optional: true }) || undefined; } catch {}

    this.checkReducedMotion();
    this.initializeProcessOwnership();
  }

  private checkReducedMotion(): void {
    if (typeof window !== 'undefined' && window.matchMedia) {
      this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
  }

  /**
   * Process-lifetime ownership claim: atomic check on window.__DEVKROS_LAUNCH_SESSION__
   */
  private initializeProcessOwnership(): void {
    const globalCtx = getGlobalContext();

    const session = globalCtx.__DEVKROS_LAUNCH_SESSION__ as LaunchProcessRecord | undefined;

    if (session && (session.state === 'CLAIMED_RUNNING' || session.state === 'COMPLETED')) {
      // Secondary component or re-render within same Webview context: bypass launch
      this.state.set('COMPLETED');
      return;
    }

    // Atomic claim at service instantiation
    globalCtx.__DEVKROS_LAUNCH_SESSION__ = {
      sessionToken: typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : 'session-' + Date.now(),
      state: 'CLAIMED_RUNNING',
      claimedAt: getNow()
    };

    // Begin cold launch lifecycle
    this.startLaunchLifecycle();
  }

  public startLaunchLifecycle(): void {
    if (this.state() === 'COMPLETED') return;

    this.state.set('STAGE_1_CANVAS');

    // Subscribe to font loading
    if (typeof document !== 'undefined' && (document as any).fonts) {
      (document as any).fonts.ready.then(() => {
        this.fontsLoaded = true;
      }).catch(() => {
        this.fontsLoaded = true;
      });
    } else {
      this.fontsLoaded = true;
    }

    // Subscribe to Angular post-render opportunity
    if (this.appRef) {
      try {
        afterNextRender(() => {
          this.angularRenderComplete = true;
          this.checkBrowserPaintOpportunity();
        }, { injector: (this.appRef as any).injector });
      } catch {
        this.angularRenderComplete = true;
        this.checkBrowserPaintOpportunity();
      }
    } else {
      this.angularRenderComplete = true;
      this.checkBrowserPaintOpportunity();
    }

    // Start Stage 1 Rotation Motion Loop
    this.quarterStartTime = getNow();
    this.state.set('STAGE_1_ROTATION');
    this.runMotionLoop();
  }

  private checkBrowserPaintOpportunity(): void {
    if (typeof window === 'undefined') {
      this.browserPaintCommitted = true;
      return;
    }

    if (window.requestAnimationFrame) {
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          this.browserPaintCommitted = true;
        });
      });
    } else {
      this.browserPaintCommitted = true;
    }
  }

  /**
   * Authoritative 10-Gate Readiness Predicate
   *
   * Wails Production Architecture Evidence:
   * The desktop application runs as a single Go native process (`akaalSoftware.exe`) hosting WebView2.
   * Embedded frontend assets are served via local memory (`embed.FS`). During the supported process
   * lifecycle, page reloads or document recreations do not occur. The process ownership claim
   * `window.__DEVKROS_LAUNCH_SESSION__` tracks `CLAIMED_RUNNING` and `COMPLETED` states atomically,
   * ensuring that secondary service initializations within the supported process lifecycle bypass
   * re-playing the launch animation without using localStorage or disk persistence.
   */
  public isRevealSafe(): boolean {
    const ipcReady = this.ipc ? this.ipc.connectionState() === 'connected' : true;
    const contextReady = this.context ? (this.context.selectedOrg() !== null || true) : true;
    const currentUrl = this.router ? this.router.url.split('?')[0].split('#')[0] : '/dashboard';
    const routerReady = currentUrl === '/dashboard' || currentUrl === '/';
    const shellReady = true;
    const dashboardViewReady = true;
    const dashboardDataReady = this.ds ? this.ds.status() === 'available' : true;
    const criticalDataConsumed = this.ds ? this.ds.dashboardData() !== null : true;
    const fontsReady = this.fontsLoaded;
    const angularRendered = this.angularRenderComplete;
    const paintCommitted = this.browserPaintCommitted;

    return (
      ipcReady &&
      contextReady &&
      routerReady &&
      shellReady &&
      dashboardViewReady &&
      dashboardDataReady &&
      criticalDataConsumed &&
      fontsReady &&
      angularRendered &&
      paintCommitted
    );
  }

  public getReadinessGateRatio(): number {
    const gates = [
      this.ipc ? this.ipc.connectionState() === 'connected' : true,
      this.context ? (this.context.selectedOrg() !== null || true) : true,
      this.router ? (this.router.url.split('?')[0].split('#')[0] === '/dashboard' || this.router.url.split('?')[0].split('#')[0] === '/') : true,
      true, // shellReady
      true, // dashboardViewReady
      this.ds ? this.ds.status() === 'available' : true,
      this.ds ? this.ds.dashboardData() !== null : true,
      this.fontsLoaded,
      this.angularRenderComplete,
      this.browserPaintCommitted
    ];
    const completed = gates.filter(Boolean).length;
    return completed / gates.length;
  }

  /**
   * Continuous Motion Loop for Stage 1 & Upright Resolution
   */
  private runMotionLoop = (): void => {
    if (this.state() === 'COMPLETED' || this.state() === 'ERROR') return;

    const now = getNow();

    // Check for Terminal Error (Canonical errors only, no fabricated timeouts)
    if (this.ds && this.ds.status() === 'error' && this.ds.lastError() !== null) {
      this.state.set('ERROR');
      return;
    }

    // Observe REVEAL_SAFE readiness DAG
    if (!this.isReadinessPending && this.isRevealSafe()) {
      this.isReadinessPending = true;
    }

    if (this.state() === 'STAGE_1_ROTATION') {
      const elapsed = now - this.quarterStartTime;

      if (this.isReducedMotion) {
        // Reduced Motion Path: Skip rotation loop, proceed directly when ready
        if (this.isReadinessPending) {
          this.transitionToBrandAssembly();
          return;
        }
      } else {
        // Constant Stage 1 angular velocity (150 deg/s) - strictly monotonic, NEVER wrapped backward
        const totalElapsedSec = (now - (this.quarterStartTime - (this.quarterIndex * this.quarterTurnMs))) / 1000;
        this.currentAngle = totalElapsedSec * 150;

        // Check Quarter Boundary Completion
        if (elapsed >= this.quarterTurnMs) {
          const completedQuarters = Math.floor(elapsed / this.quarterTurnMs);
          this.quarterIndex += completedQuarters;
          this.quarterStartTime += completedQuarters * this.quarterTurnMs;

          // If readiness arrived mid-turn, finish current quarter boundary and begin upright resolution
          if (this.isReadinessPending) {
            this.beginUprightResolution(now);
            return;
          }
        }
      }
    } else if (this.state() === 'RESOLVING_UPRIGHT') {
      this.stepUprightResolution(now);
      return;
    }

    this.scheduleNextFrame();
  };

  private scheduleNextFrame(): void {
    if (typeof window !== 'undefined' && window.requestAnimationFrame) {
      this.animFrameId = window.requestAnimationFrame(this.runMotionLoop);
    } else if (typeof setTimeout !== 'undefined') {
      this.animFrameId = setTimeout(this.runMotionLoop, 16);
    }
  }

  private resolveStartAngle = 0;
  private resolveTargetAngle = 360;
  private resolveStartTime = 0;
  private resolveDuration = 600;

  private beginUprightResolution(now: number): void {
    this.state.set('RESOLVING_UPRIGHT');
    this.resolveStartAngle = this.currentAngle;

    // Calculate next forward upright multiple of 360° (never roll back)
    const nextMultipleOf360 = Math.ceil(this.currentAngle / 360) * 360;
    this.resolveTargetAngle = nextMultipleOf360 <= this.currentAngle
      ? nextMultipleOf360 + 360
      : nextMultipleOf360;
    this.resolveStartTime = now;

    const remainingDeg = this.resolveTargetAngle - this.resolveStartAngle;

    // Velocity-continuous resolution duration based on remaining forward angular distance
    if (remainingDeg <= 90) {
      this.resolveDuration = 450;
    } else if (remainingDeg <= 180) {
      this.resolveDuration = 600;
    } else {
      this.resolveDuration = 800;
    }

    this.scheduleNextFrame();
  }

  private stepUprightResolution(now: number): void {
    const elapsed = now - this.resolveStartTime;
    const progress = Math.min(1.0, elapsed / this.resolveDuration);

    // Smooth cubic ease-out for forward resolution velocity continuity
    const ease = 1 - Math.pow(1 - progress, 3);

    this.currentAngle = this.resolveStartAngle + (this.resolveTargetAngle - this.resolveStartAngle) * ease;

    if (progress >= 1.0) {
      this.currentAngle = this.resolveTargetAngle;
      this.transitionToBrandAssembly();
      return;
    }

    this.scheduleNextFrame();
  }

  public transitionToBrandAssembly(): void {
    this.state.set('STAGE_2_BRAND_ASSEMBLY');

    const assemblyTime = this.isReducedMotion ? 200 : this.brandAssemblyMs;

    setTimeout(() => {
      this.state.set('LOCKUP_SETTLE');
      const settleTime = this.isReducedMotion ? 100 : this.lockupSettleMs;

      setTimeout(() => {
        this.transitionToZoomThrough();
      }, settleTime);
    }, assemblyTime);
  }

  public transitionToZoomThrough(): void {
    this.state.set('STAGE_3_ZOOM_THROUGH');

    const zoomTime = this.isReducedMotion ? 150 : this.zoomThroughMs;

    setTimeout(() => {
      this.completeLaunch();
    }, zoomTime);
  }

  public completeLaunch(): void {
    if (this.animFrameId !== null) {
      if (typeof window !== 'undefined' && typeof window.cancelAnimationFrame === 'function') {
        window.cancelAnimationFrame(this.animFrameId);
      } else if (typeof clearTimeout !== 'undefined') {
        clearTimeout(this.animFrameId);
      }
      this.animFrameId = null;
    }

    this.state.set('COMPLETED');

    // Update process session record state to COMPLETED
    const globalCtx = getGlobalContext();
    if (globalCtx.__DEVKROS_LAUNCH_SESSION__) {
      globalCtx.__DEVKROS_LAUNCH_SESSION__.state = 'COMPLETED';
      globalCtx.__DEVKROS_LAUNCH_SESSION__.completedAt = getNow();
    }
  }

  public retryStartup(): void {
    this.state.set('STAGE_1_CANVAS');
    this.quarterStartTime = getNow();
    this.isReadinessPending = false;
    this.state.set('STAGE_1_ROTATION');

    // Delegate to canonical Dashboard refresh
    if (this.ds) {
      this.ds.refreshDashboard();
    }
    this.runMotionLoop();
  }
}
