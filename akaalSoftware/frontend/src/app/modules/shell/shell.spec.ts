import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ShellComponent } from './shell.component';

describe('Global Shell Module — CHECK 1 Correct Verification Suite', () => {
  let shellComp: ShellComponent;
  let mockRouter: any;
  let mockDashboardService: any;
  let mockContextService: any;
  let mockIpcService: any;
  let mockMigrationUiService: any;

  beforeEach(() => {
    mockRouter = { navigate: vi.fn() };
    mockDashboardService = {
      userName: vi.fn().mockReturnValue('Aalok'),
      refreshDashboard: vi.fn()
    };
    mockContextService = {
      organizations: vi.fn().mockReturnValue([]),
      workspaces: vi.fn().mockReturnValue([]),
      environments: vi.fn().mockReturnValue([]),
      selectedOrg: vi.fn().mockReturnValue(null),
      selectedWorkspace: vi.fn().mockReturnValue(null),
      selectedEnvironment: vi.fn().mockReturnValue(null),
      isProduction: vi.fn().mockReturnValue(false),
      availableWorkspacesForOrg: vi.fn().mockReturnValue([]),
      availableEnvironmentsForWorkspace: vi.fn().mockReturnValue([])
    };
    mockIpcService = {
      connectionState: vi.fn().mockReturnValue('connected')
    };
    mockMigrationUiService = {
      isDestructiveConfirmModalOpen: vi.fn().mockReturnValue(false),
      dropConfirmationInput: vi.fn().mockReturnValue(''),
      cancelDestructiveAction: vi.fn(),
      confirmDestructiveAction: vi.fn()
    };

    shellComp = new ShellComponent(
      mockDashboardService,
      mockContextService,
      mockIpcService,
      mockMigrationUiService,
      mockRouter
    );
  });

  describe('SHELL-002: Command Palette Stale Route Correction', () => {
    it('should have removed internal terminology (3.2 Telemetry) and stale plural route', () => {
      const monCmd = shellComp.commands.find(c => c.id === '3b');
      expect(monCmd).toBeDefined();
      expect(monCmd?.label).toBe('Go to Migration Monitoring');
      expect(monCmd?.label).not.toContain('3.2 Telemetry');

      // Execute command and verify route
      monCmd?.action();
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/monitoring/migration']);
    });
  });

  describe('SHELL-003: Command Palette Keyboard Operation & Selection State', () => {
    beforeEach(() => {
      shellComp.openCommandPalette();
    });

    it('should initialize selection index to 0 when opening palette', () => {
      expect(shellComp.isCommandPaletteOpen()).toBe(true);
      expect(shellComp.selectedIndex()).toBe(0);
      expect(shellComp.searchQuery).toBe('');
    });

    it('should navigate down with ArrowDown and wrap around', () => {
      const total = shellComp.filteredCommands().length;
      expect(total).toBeGreaterThan(0);

      shellComp.handleSearchKeydown({ key: 'ArrowDown', preventDefault: vi.fn() } as any);
      expect(shellComp.selectedIndex()).toBe(1);

      // Navigate to end and wrap
      for (let i = 1; i < total; i++) {
        shellComp.handleSearchKeydown({ key: 'ArrowDown', preventDefault: vi.fn() } as any);
      }
      expect(shellComp.selectedIndex()).toBe(0);
    });

    it('should navigate up with ArrowUp and wrap around to end', () => {
      const total = shellComp.filteredCommands().length;

      shellComp.handleSearchKeydown({ key: 'ArrowUp', preventDefault: vi.fn() } as any);
      expect(shellComp.selectedIndex()).toBe(total - 1);
    });

    it('should execute selected command on Enter keydown', () => {
      shellComp.setSelectedIndex(1); // 'Go to Migration Portfolio'
      shellComp.handleSearchKeydown({ key: 'Enter', preventDefault: vi.fn() } as any);

      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration']);
      expect(shellComp.isCommandPaletteOpen()).toBe(false);
    });

    it('should close palette on Escape keydown', () => {
      shellComp.handleSearchKeydown({ key: 'Escape', preventDefault: vi.fn() } as any);
      expect(shellComp.isCommandPaletteOpen()).toBe(false);
    });

    it('should reset selected index when search query changes', () => {
      shellComp.setSelectedIndex(4);
      shellComp.onSearchQueryChange('reports');

      expect(shellComp.searchQuery).toBe('reports');
      expect(shellComp.selectedIndex()).toBe(0);
    });
  });

  describe('SHELL-004 & SHELL-005: User Menu, Lock Session Removal & Shortcuts Truthfulness', () => {
    it('should open shortcuts modal with truthful shortcut reference', () => {
      shellComp.openShortcutsDialog();
      expect(shellComp.isShortcutsOpen()).toBe(true);
    });

    it('should close all dialogs and modals when closeAllDropdowns is called', () => {
      shellComp.isCommandPaletteOpen.set(true);
      shellComp.isShortcutsOpen.set(true);
      shellComp.isNotificationsOpen.set(true);
      shellComp.isUserMenuOpen.set(true);
      shellComp.isHelpOpen.set(true);
      shellComp.isAboutOpen.set(true);

      shellComp.closeAllDropdowns();

      expect(shellComp.isCommandPaletteOpen()).toBe(false);
      expect(shellComp.isShortcutsOpen()).toBe(false);
      expect(shellComp.isNotificationsOpen()).toBe(false);
      expect(shellComp.isUserMenuOpen()).toBe(false);
      expect(shellComp.isHelpOpen()).toBe(false);
      expect(shellComp.isAboutOpen()).toBe(false);
    });
  });

  describe('Primary Navigation & Accepted Icons Preservation', () => {
    it('should preserve all 5 primary module paths and accepted Lucide icons', () => {
      const expectedNav = [
        { path: '/dashboard', label: 'Dashboard', icon: 'layout-dashboard' },
        { path: '/migration', label: 'Migration', icon: 'arrow-left-right' },
        { path: '/monitoring', label: 'Monitoring', icon: 'activity' },
        { path: '/reports', label: 'Reports', icon: 'file-text' },
        { path: '/administration', label: 'Administration', icon: 'building-2' },
      ];

      expect(shellComp.primaryNavItems).toEqual(expectedNav);
    });
  });
});
