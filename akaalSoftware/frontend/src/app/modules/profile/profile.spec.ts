import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ProfileHomeComponent } from './profile-home.component';
import { DashboardService } from '../../core/services/dashboard.service';
import { ContextService } from '../../core/services/context.service';
import { AdministrationIpc } from '../../core/services/ipc/administration.ipc';

describe('ProfileHomeComponent Master Suite — Real Self-Service Product Invariants', () => {
  let component: ProfileHomeComponent;
  let mockDs: DashboardService;
  let mockCs: ContextService;
  let mockAdminIpc: AdministrationIpc;

  beforeEach(() => {
    mockDs = new DashboardService();
    mockCs = new ContextService();
    mockAdminIpc = new AdministrationIpc();
    component = new ProfileHomeComponent(mockDs, mockCs, mockAdminIpc);
  });

  it('should create ProfileHomeComponent', () => {
    expect(component).toBeTruthy();
  });

  it('should derive user initials dynamically from userName signal without hardcoded constants', () => {
    mockDs.userName.set('Pratham Patel');
    expect(component.userInitials()).toBe('PP');

    mockDs.userName.set('Aalok');
    expect(component.userInitials()).toBe('AA');
  });

  it('should support self-service display name inline editing and persist to canonical authority', async () => {
    mockDs.userName.set('Original Name');
    expect(component.isEditingName()).toBe(false);

    component.startEditName();
    expect(component.isEditingName()).toBe(true);
    expect(component.editNameInput()).toBe('Original Name');

    component.editNameInput.set('Aalok Ladwa');

    const updateSpy = vi.spyOn(mockAdminIpc, 'updateSelfProfile').mockResolvedValue({
      status: 'SUCCESS',
      data: { display_name: 'Aalok Ladwa' }
    });

    await component.saveName();

    expect(updateSpy).toHaveBeenCalledWith({ display_name: 'Aalok Ladwa' });
    expect(mockDs.userName()).toBe('Aalok Ladwa');
    expect(component.isEditingName()).toBe(false);
  });

  it('should fail closed when display name save receives error response', async () => {
    component.startEditName();
    component.editNameInput.set('Invalid Name');

    vi.spyOn(mockAdminIpc, 'updateSelfProfile').mockResolvedValue({
      status: 'ERROR',
      error: 'Backend permission denied'
    });

    await component.saveName();

    expect(component.nameError()).toBe('Backend permission denied');
    expect(component.isEditingName()).toBe(true);
  });

  it('should support email editing with format validation and self-service backend call', async () => {
    component.startEditEmail();
    component.editEmailInput.set('invalid-email');

    await component.saveEmail();
    expect(component.emailError()).toBe('Please enter a valid email address');

    component.editEmailInput.set('aalok.ladwa@akaal.io');
    const emailSpy = vi.spyOn(mockAdminIpc, 'updateSelfProfile').mockResolvedValue({
      status: 'SUCCESS',
      data: { email: 'aalok.ladwa@akaal.io' }
    });

    await component.saveEmail();
    expect(emailSpy).toHaveBeenCalledWith({ email: 'aalok.ladwa@akaal.io' });
    expect(component.userEmail()).toBe('aalok.ladwa@akaal.io');
    expect(component.isEditingEmail()).toBe(false);
  });

  it('should manage avatar image selection, size validation, and backend removal', async () => {
    expect(component.userAvatar()).toBeNull();

    // Oversized file test
    const fakeOversizedFile = { size: 3 * 1024 * 1024, type: 'image/png' } as File;
    const fakeEvent = { target: { files: [fakeOversizedFile] } } as unknown as Event;

    component.onAvatarFileSelected(fakeEvent);
    expect(component.avatarError()).toBe('Image size must be under 2MB');

    // Remove photo calls removeSelfAvatar
    component.userAvatar.set('data:image/png;base64,fakeData');
    expect(component.userAvatar()).toBeTruthy();

    const removeSpy = vi.spyOn(mockAdminIpc, 'removeSelfAvatar').mockResolvedValue({
      status: 'SUCCESS',
      data: { avatar: null }
    });

    await component.removeAvatar();
    expect(removeSpy).toHaveBeenCalled();
    expect(component.userAvatar()).toBeNull();
  });

  it('should validate password change fields and verify current password with backend credential authority', async () => {
    component.isPasswordModalOpen.set(true);
    component.currentPasswordInput.set('');

    await component.savePassword();
    expect(component.passwordError()).toBe('Current password is required');

    component.currentPasswordInput.set('currentPass123');
    component.newPasswordInput.set('short');

    await component.savePassword();
    expect(component.passwordError()).toBe('New password must be at least 8 characters long');

    component.newPasswordInput.set('newSecretPassword123');
    component.confirmPasswordInput.set('mismatchPassword');

    await component.savePassword();
    expect(component.passwordError()).toBe('New passwords do not match');

    // Valid inputs dispatch to changeSelfPassword with current + new password
    component.confirmPasswordInput.set('newSecretPassword123');
    const pwdSpy = vi.spyOn(mockAdminIpc, 'changeSelfPassword').mockResolvedValue({
      status: 'SUCCESS',
      data: { status: 'SUCCESS' }
    });

    await component.savePassword();
    expect(pwdSpy).toHaveBeenCalledWith('currentPass123', 'newSecretPassword123');
  });

  it('should initialize with overview tab active and allow tab switching', () => {
    expect(component.activeTab()).toBe('overview');

    component.setTab('security');
    expect(component.activeTab()).toBe('security');

    component.setTab('sessions');
    expect(component.activeTab()).toBe('sessions');
  });

  it('should execute exit application action without throwing uncaught exceptions', () => {
    expect(() => component.signOut()).not.toThrow();
  });
});
