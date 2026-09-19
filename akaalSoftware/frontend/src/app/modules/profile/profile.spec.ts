import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { ProfileHomeComponent } from './profile-home.component';
import { DashboardService } from '../../core/services/dashboard.service';
import { ContextService } from '../../core/services/context.service';

describe('ProfileHomeComponent Master Suite — Final Truth & Avatar UX', () => {
  let component: ProfileHomeComponent;
  let mockDs: DashboardService;
  let mockCs: ContextService;

  beforeEach(() => {
    mockDs = new DashboardService();
    mockCs = new ContextService();
    component = new ProfileHomeComponent(mockDs, mockCs);
  });

  it('should create ProfileHomeComponent', () => {
    expect(component).toBeTruthy();
  });

  it('should derive user initials dynamically from userName signal without hardcoded string constants', () => {
    mockDs.userName.set('Pratham Patel');
    expect(component.userInitials()).toBe('PP');

    mockDs.userName.set('Aalok');
    expect(component.userInitials()).toBe('AA');
  });

  it('should initialize with overview tab active and allow tab switching', () => {
    expect(component.activeTab()).toBe('overview');

    component.setTab('security');
    expect(component.activeTab()).toBe('security');

    component.setTab('sessions');
    expect(component.activeTab()).toBe('sessions');
  });

  it('should support opening and closing the capability-aware avatar dialog', () => {
    expect(component.isAvatarDialogOpen()).toBe(false);

    component.isAvatarDialogOpen.set(true);
    expect(component.isAvatarDialogOpen()).toBe(true);

    component.isAvatarDialogOpen.set(false);
    expect(component.isAvatarDialogOpen()).toBe(false);
  });

  it('should execute sign out without throwing uncaught exceptions', () => {
    expect(() => component.signOut()).not.toThrow();
  });
});
