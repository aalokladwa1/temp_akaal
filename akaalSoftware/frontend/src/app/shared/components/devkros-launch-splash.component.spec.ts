import '@angular/compiler';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { DevkrosLaunchSplashComponent } from './devkros-launch-splash.component';
import { LaunchLifecycleService } from '../../core/services/launch-lifecycle.service';

class MockLaunchLifecycleService {
  public currentState = 'STAGE_1_ROTATION';
  public currentAngle = 45;

  state() { return this.currentState; }
  isCompleted() { return this.currentState === 'COMPLETED'; }
  isError() { return this.currentState === 'ERROR'; }
  retryStartup() {}
}

class MockDashboardService {
  lastError() { return 'IPC Connection Timeout'; }
}

describe('DevkrosLaunchSplashComponent & Visual Overlay Invariants', () => {
  let component: DevkrosLaunchSplashComponent;
  let mockLaunch: MockLaunchLifecycleService;
  let mockDs: MockDashboardService;

  beforeEach(() => {
    mockLaunch = new MockLaunchLifecycleService();
    mockDs = new MockDashboardService();
    component = new DevkrosLaunchSplashComponent();
    (component as any).launch = mockLaunch;
    (component as any).ds = mockDs;
  });

  it('should calculate mark rotation transform accurately', () => {
    expect(component.markRotationTransform).toBe('rotate(45deg)');
  });

  it('should translate lockup container left in Stage 2 for whole-unit optical centering', () => {
    mockLaunch.currentState = 'STAGE_2_BRAND_ASSEMBLY';
    expect(component.lockupContainerTransform).toBe('scale(1)');
  });

  it('should unmask vector wordmark in Stage 2 with coordinated timeline', () => {
    mockLaunch.currentState = 'STAGE_2_BRAND_ASSEMBLY';
    expect(component.wordmarkMaxWidth).toBe(222);
    expect(component.wordmarkOpacity).toBe(1);
    expect(component.wordmarkMarginLeft).toBe(20);
  });

  it('should calculate zoom origin at viewport center', () => {
    component.viewportWidth = 1920;
    component.viewportHeight = 1080;
    expect(component.zoomOriginX).toBe(960);
    expect(component.zoomOriginY).toBe(540);
  });

  it('should compute terminal aperture coordinates to cover full viewport in Stage 3', () => {
    component.viewportWidth = 1920;
    component.viewportHeight = 1080;
    mockLaunch.currentState = 'STAGE_3_ZOOM_THROUGH';

    expect(component.terminalApertureX).toBe(0);
    expect(component.terminalApertureY).toBe(0);
    expect(component.terminalApertureW).toBe(1920);
    expect(component.terminalApertureH).toBe(1080);
  });

  it('should provide clean light launch surface default', () => {
    expect(component.launchSurfaceBg).toBe('#ffffff');
    expect(component.launchSurfaceFg).toBe('#0f172a');
  });
});
