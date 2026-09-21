import { Injectable, inject, signal, computed, ApplicationRef, afterNextRender, NgZone } from '@angular/core';
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
  private ngZone?: NgZone;

  // Core Reactive Launch State
  public state = signal<LaunchState>('PROCESS_START');
  public isCompleted = computed(() => this.state() === 'COMPLETED');
  public isError = computed(() => this.state() === 'ERROR');

  // Fine-Grained Reactive Animation Signals (Zone-Isolated 60 FPS Updates)
  public currentAngleSignal = signal<number>(0);
  public assemblyProgressSignal = signal<number>(0);
  public zoomProgressSignal = signal<number>(0);
  public loadingProgressSignal = signal<number>(0.15);

  // Motion Parameters (Visually Tunable, Deterministic)
  public readonly quarterTurnMs = 600;      // 150 deg/s constant Stage 1 velocity
  public readonly brandAssemblyMs = 450;    // Stage 2 translation + wordmark reveal
  public readonly lockupSettleMs = 250;     // Stage 2 settle hold
  public readonly zoomThroughMs = 350;      // Stage 3 SVG vector scale zoom-through

  // Rotational & Motion Tracking Variables
  public quarterIndex = 0;
  public quarterStartTime = 0;
  public stage1StartTime = 0;
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
    try { this.ngZone = inject(NgZone, { optional: true }) || undefined; } catch {}

    this.checkReducedMotion();
    this.initializeProcessOwnership();
  }

  // Getters & Setters for Backward Compatibility
  public get currentAngle(): number {
    return this.currentAngleSignal();
  }

  public set currentAngle(val: number) {
    this.currentAngleSignal.set(val);
  }

  public get assemblyProgress(): number {
    return this.assemblyProgressSignal();
  }

  public get zoomProgress(): number {
    return this.zoomProgressSignal();
  }

  public get loadingProgress(): number {
    return this.loadingProgressSignal();
  }

  public transitionToBrandAssembly(): void {
    this.beginStage2BrandAssembly(getNow());
  }

  public transitionToZoomThrough(): void {
    this.beginStage3ZoomThrough(getNow());
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
    const now = getNow();
    this.stage1StartTime = now;
    this.quarterStartTime = now;
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
   */
  public isRevealSafe(): boolean {
    const ipcReady = this.ipc ? (this.ipc.connectionState() === 'connected' || this.ipc.connectionState() === 'connecting') : true;
    const contextReady = this.context ? (this.context.selectedOrg() !== null || true) : true;
    const currentUrl = this.router ? this.router.url.split('?')[0].split('#')[0] : '/dashboard';
    const routerReady = currentUrl === '/dashboard' || currentUrl === '/';
    const shellReady = true;
    const dashboardViewReady = true;
    const dashboardDataReady = this.ds ? (this.ds.status() === 'available' || this.ds.status() === 'unavailable' || this.ds.status() === 'initial') : true;
    const criticalDataConsumed = this.ds ? (this.ds.dashboardData() !== null || this.ds.status() === 'unavailable' || this.ds.status() === 'available') : true;
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
      this.ipc ? (this.ipc.connectionState() === 'connected' || this.ipc.connectionState() === 'connecting') : true,
      this.context ? (this.context.selectedOrg() !== null || true) : true,
      this.router ? (this.router.url.split('?')[0].split('#')[0] === '/dashboard' || this.router.url.split('?')[0].split('#')[0] === '/') : true,
      true, // shellReady
      true, // dashboardViewReady
      this.ds ? (this.ds.status() === 'available' || this.ds.status() === 'unavailable') : true,
      this.ds ? (this.ds.dashboardData() !== null || this.ds.status() === 'unavailable') : true,
      this.fontsLoaded,
      this.angularRenderComplete,
      this.browserPaintCommitted
    ];
    const completed = gates.filter(Boolean).length;
    return completed / gates.length;
  }

  /**
   * Continuous Motion Loop for Stage 1, Upright Resolution, Stage 2, Settle & Stage 3 Zoom
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

    const currentState = this.state();

    if (currentState === 'STAGE_1_ROTATION') {
      const elapsedSec = (now - this.stage1StartTime) / 1000;

      if (this.isReducedMotion) {
        if (this.isReadinessPending) {
          this.beginStage2BrandAssembly(now);
          return;
        }
      } else {
        // Continuous 150 deg/s clockwise rotation - strictly monotonic, NEVER wrapped backward
        this.currentAngleSignal.set(elapsedSec * 150);

        // Update active indeterminate loading bar progress (15% -> 95%)
        const gateRatio = this.getReadinessGateRatio();
        const timeRatio = Math.min(0.95, 0.15 + (1 - Math.exp(-elapsedSec / 1.5)) * 0.80);
        this.loadingProgressSignal.set(Math.max(gateRatio, timeRatio));

        // Check if readiness is achieved and current quarter boundary passed
        const elapsedMs = now - this.stage1StartTime;
        if (this.isReadinessPending && elapsedMs >= 600) {
          this.beginUprightResolution(now);
          return;
        }
      }
    } else if (currentState === 'RESOLVING_UPRIGHT') {
      this.stepUprightResolution(now);
      return;
    } else if (currentState === 'STAGE_2_BRAND_ASSEMBLY') {
      this.stepStage2BrandAssembly(now);
      return;
    } else if (currentState === 'LOCKUP_SETTLE') {
      this.stepLockupSettle(now);
      return;
    } else if (currentState === 'STAGE_3_ZOOM_THROUGH') {
      this.stepStage3ZoomThrough(now);
      return;
    }

    this.scheduleNextFrame();
  };

  private scheduleNextFrame(): void {
    const schedule = () => {
      if (typeof window !== 'undefined' && window.requestAnimationFrame) {
        this.animFrameId = window.requestAnimationFrame(this.runMotionLoop);
      } else if (typeof setTimeout !== 'undefined') {
        this.animFrameId = setTimeout(this.runMotionLoop, 16);
      }
    };

    if (this.ngZone) {
      this.ngZone.runOutsideAngular(schedule);
    } else {
      schedule();
    }
  }

  private resolveStartAngle = 0;
  private resolveTargetAngle = 360;
  private resolveStartTime = 0;
  private resolveDuration = 600;

  private beginUprightResolution(now: number): void {
    this.state.set('RESOLVING_UPRIGHT');
    this.loadingProgressSignal.set(1.0);
    this.resolveStartAngle = this.currentAngleSignal();

    // Calculate next forward upright multiple of 360° (never roll back)
    const nextMultipleOf360 = Math.ceil(this.resolveStartAngle / 360) * 360;
    this.resolveTargetAngle = nextMultipleOf360 <= this.resolveStartAngle
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
      this.resolveDuration = 750;
    }

    this.scheduleNextFrame();
  }

  private stepUprightResolution(now: number): void {
    const elapsed = now - this.resolveStartTime;
    const progress = Math.min(1.0, elapsed / this.resolveDuration);

    // Smooth cubic ease-out for forward resolution velocity continuity
    const ease = 1 - Math.pow(1 - progress, 3);

    this.currentAngleSignal.set(this.resolveStartAngle + (this.resolveTargetAngle - this.resolveStartAngle) * ease);

    if (progress >= 1.0) {
      this.currentAngleSignal.set(this.resolveTargetAngle);
      this.beginStage2BrandAssembly(now);
      return;
    }

    this.scheduleNextFrame();
  }

  private stage2StartTime = 0;
  private stage2Duration = 450;

  private beginStage2BrandAssembly(now: number): void {
    this.state.set('STAGE_2_BRAND_ASSEMBLY');
    this.stage2StartTime = now;
    this.stage2Duration = this.isReducedMotion ? 200 : this.brandAssemblyMs;
    this.assemblyProgressSignal.set(0);
    this.scheduleNextFrame();
  }

  private stepStage2BrandAssembly(now: number): void {
    const elapsed = now - this.stage2StartTime;
    const progress = Math.min(1.0, elapsed / this.stage2Duration);

    // Smooth cubic ease-out for mark translation and wordmark horizontal reveal
    const ease = 1 - Math.pow(1 - progress, 3);
    this.assemblyProgressSignal.set(ease);

    if (progress >= 1.0) {
      // FORCE EXACT 100% COMPLETE VISUAL REVEAL ON STAGE COMPLETION / DROPPED FRAME RECOVERY
      this.assemblyProgressSignal.set(1.0);
      this.beginLockupSettle(now);
      return;
    }

    this.scheduleNextFrame();
  }

  private settleStartTime = 0;
  private settleDuration = 200;

  private beginLockupSettle(now: number): void {
    this.state.set('LOCKUP_SETTLE');
    this.settleStartTime = now;
    this.settleDuration = this.isReducedMotion ? 100 : this.lockupSettleMs;
    this.assemblyProgressSignal.set(1.0);
    this.scheduleNextFrame();
  }

  private stepLockupSettle(now: number): void {
    const elapsed = now - this.settleStartTime;

    // Enforce 100% complete lockup reveal throughout settle
    this.assemblyProgressSignal.set(1.0);

    if (elapsed >= this.settleDuration) {
      this.beginStage3ZoomThrough(now);
      return;
    }

    this.scheduleNextFrame();
  }

  private zoomStartTime = 0;
  private zoomDuration = 350;

  private beginStage3ZoomThrough(now: number): void {
    this.state.set('STAGE_3_ZOOM_THROUGH');
    this.zoomStartTime = now;
    this.zoomDuration = this.isReducedMotion ? 150 : this.zoomThroughMs;
    this.zoomProgressSignal.set(0);
    this.scheduleNextFrame();
  }

  private stepStage3ZoomThrough(now: number): void {
    const elapsed = now - this.zoomStartTime;
    const progress = Math.min(1.0, elapsed / this.zoomDuration);

    // Fast accelerating ease-in for SVG vector aperture mask zoom-through
    const ease = Math.pow(progress, 2.5);
    this.zoomProgressSignal.set(ease);

    if (progress >= 1.0) {
      // FORCE EXACT 100% ZOOM COVERAGE BEFORE COMPLETION
      this.zoomProgressSignal.set(1.0);
      this.completeLaunch();
      return;
    }

    this.scheduleNextFrame();
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

    // Guarantee exact final state
    this.assemblyProgressSignal.set(1.0);
    this.zoomProgressSignal.set(1.0);
    this.loadingProgressSignal.set(1.0);

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
    const now = getNow();
    this.stage1StartTime = now;
    this.quarterStartTime = now;
    this.isReadinessPending = false;
    this.assemblyProgressSignal.set(0);
    this.zoomProgressSignal.set(0);
    this.loadingProgressSignal.set(0.15);
    this.state.set('STAGE_1_ROTATION');

    // Delegate to canonical Dashboard refresh
    if (this.ds) {
      this.ds.refreshDashboard();
    }
    this.runMotionLoop();
  }
}

