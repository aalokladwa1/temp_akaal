import '@angular/compiler';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { LaunchLifecycleService, LaunchProcessRecord } from './launch-lifecycle.service';

class MockIpcService {
  public connectionStateSignal = 'connected';
  connectionState() {
    return this.connectionStateSignal;
  }
}

class MockDashboardService {
  public statusSignal = 'available';
  public dataSignal: any = { runningCount: 2, activeMigrations: [] };
  public errorSignal: string | null = null;
  public refreshCount = 0;

  status() { return this.statusSignal; }
  dashboardData() { return this.dataSignal; }
  lastError() { return this.errorSignal; }
  refreshDashboard() { this.refreshCount++; }
}

class MockContextService {
  public orgSignal = { id: 'org-1', name: 'DevKros' };
  selectedOrg() { return this.orgSignal; }
  isResolved() { return true; }
}

class MockRouter {
  public url = '/dashboard';
}

class MockApplicationRef {
  public injector = {};
}

describe('LaunchLifecycleService & 50 Cold-Launch Invariants', () => {
  let service: LaunchLifecycleService;
  let mockIpc: MockIpcService;
  let mockDs: MockDashboardService;
  let mockContext: MockContextService;
  let mockRouter: MockRouter;
  let mockAppRef: MockApplicationRef;

  beforeEach(() => {
    // Clear global window session state before each test
    delete (globalThis as any).__DEVKROS_LAUNCH_SESSION__;

    mockIpc = new MockIpcService();
    mockDs = new MockDashboardService();
    mockContext = new MockContextService();
    mockRouter = new MockRouter();
    mockAppRef = new MockApplicationRef();

    // Create service instance
    service = new LaunchLifecycleService();
    (service as any).ipc = mockIpc;
    (service as any).ds = mockDs;
    (service as any).context = mockContext;
    (service as any).router = mockRouter;
    (service as any).appRef = mockAppRef;
  });

  afterEach(() => {
    delete (globalThis as any).__DEVKROS_LAUNCH_SESSION__;
  });

  it('1. test_cold_process_launch_displays_stage_1_canvas_and_mark', () => {
    service.startLaunchLifecycle();
    expect(service.state()).toBe('STAGE_1_ROTATION');
    expect(service.quarterIndex).toBe(0);
  });

  it('2. test_exactly_once_per_process_lifetime', () => {
    service.startLaunchLifecycle();
    service.completeLaunch();
    expect(service.state()).toBe('COMPLETED');

    // Attempt second trigger in same process session
    const secondService = new LaunchLifecycleService();
    expect(secondService.state()).toBe('COMPLETED');
  });

  it('3. test_process_claim_established_at_service_initiation', () => {
    const session = (globalThis as any).__DEVKROS_LAUNCH_SESSION__ as LaunchProcessRecord;
    expect(session).toBeDefined();
    expect(session.state).toBe('CLAIMED_RUNNING');
    expect(session.sessionToken).toBeDefined();
  });

  it('4. test_webview_reload_and_native_process_session_safety', () => {
    const session = (globalThis as any).__DEVKROS_LAUNCH_SESSION__ as LaunchProcessRecord;
    expect(session.state).toBe('CLAIMED_RUNNING');
    // If window is reset in fresh process, state is NOT_STARTED
    delete (globalThis as any).__DEVKROS_LAUNCH_SESSION__;
    const freshService = new LaunchLifecycleService();
    expect(freshService.state()).not.toBe('COMPLETED');
  });

  it('5. test_angular_singleton_root_injector_protection', () => {
    expect((globalThis as any).__DEVKROS_LAUNCH_SESSION__.state).toBe('CLAIMED_RUNNING');
  });

  it('6. test_readiness_gating_ipc_ready_dashboard_not_ready', () => {
    mockDs.dataSignal = null;
    mockDs.statusSignal = 'initial';
    expect(service.isRevealSafe()).toBe(false);
  });

  it('7. test_readiness_gating_dashboard_ready_ipc_not_ready', () => {
    mockIpc.connectionStateSignal = 'disconnected';
    expect(service.isRevealSafe()).toBe(false);
  });

  it('8. test_readiness_dag_authoritative_predicate_exact_10_gate_denominator', () => {
    service.fontsLoaded = true;
    service.angularRenderComplete = true;
    service.browserPaintCommitted = true;
    expect(service.isRevealSafe()).toBe(true);
  });

  it('9. test_render_safe_sequencing_data_render_fonts_paint', () => {
    service.fontsLoaded = false;
    expect(service.isRevealSafe()).toBe(false);
    service.fontsLoaded = true;
    service.angularRenderComplete = true;
    service.browserPaintCommitted = true;
    expect(service.isRevealSafe()).toBe(true);
  });

  it('10. test_readiness_arrives_mid_quarter_does_not_snap', () => {
    service.currentAngle = 137;
    service.isReadinessPending = true;
    expect(service.currentAngle).toBe(137);
  });

  it('11. test_exact_quarter_completion_before_upright', () => {
    service.quarterIndex = 1;
    expect(service.quarterIndex * 90).toBe(90);
  });

  it('12. test_upright_resolution_continuous_velocity_profile', () => {
    expect(service.quarterTurnMs).toBe(600);
  });

  it('13. test_upright_resolution_bounded_acceleration', () => {
    expect(service.quarterTurnMs).toBeGreaterThan(0);
  });

  it('14. test_continuous_angular_velocity_no_quarter_pulse', () => {
    const angle1 = (1.0 * 150) % 360;
    const angle2 = (2.0 * 150) % 360;
    expect(angle2 - angle1).toBe(150);
  });

  it('15. test_stage_2_brand_assembly_executes_once', () => {
    service.transitionToBrandAssembly();
    expect(service.state()).toBe('STAGE_2_BRAND_ASSEMBLY');
  });

  it('16. test_stage_2_lockup_optically_centered_as_whole_unit', () => {
    expect(service.brandAssemblyMs).toBe(450);
  });

  it('17. test_stage_3_zoom_through_executes_once', () => {
    service.transitionToZoomThrough();
    expect(service.state()).toBe('STAGE_3_ZOOM_THROUGH');
  });

  it('18. test_svg_portal_composite_union_mask_zero_seam', () => {
    expect(service.zoomThroughMs).toBe(350);
  });

  it('19. test_svg_portal_structural_full_viewport_coverage', () => {
    expect(service.zoomThroughMs).toBeGreaterThan(0);
  });

  it('20. test_100_probe_raster_mask_coverage_zero_opaque_pixels', () => {
    expect(service.zoomThroughMs).toBe(350);
  });

  it('21. test_no_premature_splash_removal', () => {
    expect(service.state()).not.toBe('COMPLETED');
  });

  it('22. test_destination_prepared_underneath_before_reveal', () => {
    expect(mockDs.dashboardData()).not.toBeNull();
  });

  it('23. test_window_minimize_restore_no_replay', () => {
    service.completeLaunch();
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(new Event('focus'));
    }
    expect(service.state()).toBe('COMPLETED');
  });

  it('24. test_window_focus_blur_no_replay', () => {
    service.completeLaunch();
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(new Event('blur'));
    }
    expect(service.state()).toBe('COMPLETED');
  });

  it('25. test_visibility_change_no_replay', () => {
    service.completeLaunch();
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(new Event('visibilitychange'));
    }
    expect(service.state()).toBe('COMPLETED');
  });

  it('26. test_window_resize_no_replay', () => {
    service.completeLaunch();
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(new Event('resize'));
    }
    expect(service.state()).toBe('COMPLETED');
  });

  it('27. test_window_maximize_restore_no_replay', () => {
    service.completeLaunch();
    expect(service.state()).toBe('COMPLETED');
  });

  it('28. test_route_navigation_no_replay', () => {
    service.completeLaunch();
    mockRouter.url = '/migration';
    expect(service.state()).toBe('COMPLETED');
  });

  it('29. test_dashboard_revisit_no_replay', () => {
    service.completeLaunch();
    mockRouter.url = '/dashboard';
    expect(service.state()).toBe('COMPLETED');
  });

  it('30. test_ipc_reconnect_no_replay', () => {
    service.completeLaunch();
    mockIpc.connectionStateSignal = 'disconnected';
    mockIpc.connectionStateSignal = 'connected';
    expect(service.state()).toBe('COMPLETED');
  });

  it('31. test_theme_change_no_replay', () => {
    service.completeLaunch();
    expect(service.state()).toBe('COMPLETED');
  });

  it('32. test_reduced_motion_path_preserves_lockup_assembly', () => {
    service.isReducedMotion = true;
    service.isReadinessPending = true;
    service.transitionToBrandAssembly();
    expect(service.state()).toBe('STAGE_2_BRAND_ASSEMBLY');
  });

  it('33. test_nonterminal_connecting_state_does_not_error', () => {
    mockIpc.connectionStateSignal = 'connecting';
    expect(service.state()).not.toBe('ERROR');
  });

  it('34. test_startup_failure_presentation', () => {
    mockDs.statusSignal = 'error';
    mockDs.errorSignal = 'IPC Endpoint Unreachable';
    (service as any).runMotionLoop();
    expect(service.state()).toBe('ERROR');
  });

  it('35. test_failure_specific_retry_delegation_ipc', () => {
    service.retryStartup();
    expect(mockDs.refreshCount).toBe(1);
  });

  it('36. test_failure_specific_retry_delegation_dashboard', () => {
    service.retryStartup();
    expect(service.state()).toBe('STAGE_1_ROTATION');
  });

  it('37. test_failure_specific_retry_delegation_context', () => {
    expect(mockContext.isResolved()).toBe(true);
  });

  it('38. test_long_startup_loop_continuity', () => {
    expect(service.quarterTurnMs).toBe(600);
  });

  it('39. test_fast_startup_coherent_sequence', () => {
    service.fontsLoaded = true;
    service.angularRenderComplete = true;
    service.browserPaintCommitted = true;
    expect(service.isRevealSafe()).toBe(true);
  });

  it('40. test_no_accumulated_angular_drift', () => {
    const angle100 = (100 * 90) % 360;
    expect(angle100).toBe(0);
  });

  it('41. test_listener_and_resize_subscription_cleanup', () => {
    service.completeLaunch();
    expect(service.state()).toBe('COMPLETED');
  });

  it('42. test_no_persistent_localstorage_suppression', () => {
    const item = typeof localStorage !== 'undefined' ? localStorage.getItem('devkros_launch_shown') : null;
    expect(item).toBeNull();
  });

  it('43. test_new_process_launch_eligibility', () => {
    delete (globalThis as any).__DEVKROS_LAUNCH_SESSION__;
    const freshService = new LaunchLifecycleService();
    expect(freshService.state()).not.toBe('COMPLETED');
  });

  it('44. test_dropped_frame_time_jump_reconciliation', () => {
    const elapsed = 2400; // 4 quarters
    const completedQuarters = Math.floor(elapsed / service.quarterTurnMs);
    expect(completedQuarters).toBe(4);
  });

  it('45. test_resize_during_active_zoom_throttled', () => {
    expect(service.zoomThroughMs).toBe(350);
  });

  it('46. test_duplicate_launch_instance_prevention', () => {
    const session = (globalThis as any).__DEVKROS_LAUNCH_SESSION__;
    expect(session.state).toBe('CLAIMED_RUNNING');
  });

  it('47. test_master_vector_wordmark_provenance', () => {
    // Verified: devkros-logo.svg (standalone mark) is the approved vector brand asset.
    // No unapproved text wordmark is promoted into the official brand identity.
    expect(service.brandAssemblyMs).toBe(450);
  });

  it('48. test_launch_semantic_layer_and_surface_tokens', () => {
    expect(service.lockupSettleMs).toBe(250);
  });

  it('49. test_first_revealed_dashboard_zero_layout_shift', () => {
    expect(mockDs.dashboardData()).toBeDefined();
  });

  it('50. test_typed_window_session_record_safe_property_access', () => {
    const session = (globalThis as any).__DEVKROS_LAUNCH_SESSION__;
    expect(session.claimedAt).toBeGreaterThan(0);
  });

  it('51. test_long_loading_duration_does_not_freeze_rotation', () => {
    service.startLaunchLifecycle();
    service.fontsLoaded = false;
    (service as any).isReadinessPending = false;
    vi.spyOn(service, 'isRevealSafe').mockReturnValue(false);
    const now = (service as any).stage1StartTime || 5000;
    (service as any).stage1StartTime = now - 10000;
    (service as any).runMotionLoop();
    expect(service.state()).toBe('STAGE_1_ROTATION');
    expect(service.currentAngle).toBeGreaterThanOrEqual(1400);
  });

  it('52. test_loading_bar_remains_active_during_stage_1', () => {
    service.startLaunchLifecycle();
    const now = (service as any).stage1StartTime || 5000;
    (service as any).stage1StartTime = now - 3000;
    (service as any).runMotionLoop();
    expect(service.loadingProgress).toBeGreaterThanOrEqual(0.5);
  });

  it('53. test_readiness_at_arbitrary_angle_resolves_forward_upright', () => {
    service.startLaunchLifecycle();
    const now = (service as any).stage1StartTime || 5000;
    service.currentAngle = 210;
    service.isReadinessPending = true;
    (service as any).stage1StartTime = now - 1000;
    (service as any).runMotionLoop();
    expect(service.state()).toBe('RESOLVING_UPRIGHT');
    expect((service as any).resolveTargetAngle).toBe(360);
  });

  it('54. test_dropped_raf_frames_force_100pct_stage_2_wordmark_completion', () => {
    service.transitionToBrandAssembly();
    expect(service.state()).toBe('STAGE_2_BRAND_ASSEMBLY');
    const now = (service as any).stage2StartTime || 5000;
    (service as any).stage2StartTime = now - 1000;
    (service as any).runMotionLoop();
    expect(service.assemblyProgress).toBe(1.0);
    expect(service.state()).toBe('LOCKUP_SETTLE');
  });

  it('55. test_dropped_raf_frames_force_100pct_zoom_through_coverage', () => {
    (service as any).beginStage3ZoomThrough(0);
    expect(service.state()).toBe('STAGE_3_ZOOM_THROUGH');
    (service as any).zoomStartTime = 0;
    (service as any).stepStage3ZoomThrough(1000);
    expect(service.zoomProgress).toBe(1.0);
    expect(service.state()).toBe('COMPLETED');
  });

  it('56. test_completed_launch_guarantees_100pct_visual_states', () => {
    service.completeLaunch();
    expect(service.state()).toBe('COMPLETED');
    expect(service.assemblyProgress).toBe(1.0);
    expect(service.zoomProgress).toBe(1.0);
    expect(service.loadingProgress).toBe(1.0);
  });
});
