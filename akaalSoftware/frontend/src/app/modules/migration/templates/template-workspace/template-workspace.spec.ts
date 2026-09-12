import { describe, it, expect, beforeEach } from 'vitest';
import { TemplateWorkspaceService } from './template-workspace.service';
import { TEMPLATE_WORKSPACE_FIXTURES } from './template-workspace.fixtures';
import { TEMPLATE_MODE_DESCRIPTORS, TemplateMigrationMode } from '../templates.models';
import { TEMPLATE_WORKSPACE_TABS, TemplateWorkspaceTab } from './template-workspace.models';

describe('Template Workspace (Part C) — Unit & Hostile Test Suite', () => {
  let service: TemplateWorkspaceService;

  beforeEach(() => {
    service = new TemplateWorkspaceService();
  });

  // =========================================================================
  // 1. HARD MODE BOUNDARY: M1-M7 ONLY, STRICT ZERO OCCURRENCE OF M8
  // =========================================================================
  describe('1. Hard Mode Boundary & M8 Exclusion Laws', () => {
    it('should only contain canonical M1 through M7 in TEMPLATE_MODE_DESCRIPTORS', () => {
      const modes = Object.keys(TEMPLATE_MODE_DESCRIPTORS);
      expect(modes).toEqual([
        'M1_BULK',
        'M2_BULK_CDC',
        'M3_CDC',
        'M4_INCREMENTAL',
        'M5_STATE_SYNC',
        'M6_SCHEMA_ONLY',
        'M7_DATA_ONLY'
      ]);
      expect((TEMPLATE_MODE_DESCRIPTORS as any)['M8_VALIDATION']).toBeUndefined();
      expect((TEMPLATE_MODE_DESCRIPTORS as any)['M8']).toBeUndefined();
    });

    it('should verify all workspace fixtures belong exclusively to M1 through M7', () => {
      const allowedModes: TemplateMigrationMode[] = [
        'M1_BULK',
        'M2_BULK_CDC',
        'M3_CDC',
        'M4_INCREMENTAL',
        'M5_STATE_SYNC',
        'M6_SCHEMA_ONLY',
        'M7_DATA_ONLY'
      ];

      Object.values(TEMPLATE_WORKSPACE_FIXTURES).forEach(tmpl => {
        expect(allowedModes).toContain(tmpl.mode);
        expect((tmpl.mode as string)).not.toBe('M8');
        expect((tmpl.mode as string)).not.toBe('M8_VALIDATION');
      });
    });

    it('should reject or sanitize hostile M8 injection gracefully', () => {
      const hostileData: any = {
        id: 'hostile-tmpl-m8',
        mode: 'M8_VALIDATION'
      };
      expect(TEMPLATE_MODE_DESCRIPTORS[hostileData.mode as TemplateMigrationMode]).toBeUndefined();
    });
  });

  // =========================================================================
  // 2. 7-TAB WORKSPACE NAVIGATION ARCHITECTURE
  // =========================================================================
  describe('2. 7-Tab Navigation Architecture', () => {
    it('should contain exactly 7 canonical tabs in TEMPLATE_WORKSPACE_TABS', () => {
      const tabKeys = TEMPLATE_WORKSPACE_TABS.map(t => t.key);
      expect(tabKeys).toEqual([
        'overview',
        'configuration',
        'applicability',
        'versions',
        'usage',
        'activity',
        'settings'
      ]);
    });

    it('should initialize activeTab to overview and allow switching tabs', () => {
      expect(service.activeTab()).toBe('overview');

      service.setActiveTab('configuration');
      expect(service.activeTab()).toBe('configuration');

      service.setActiveTab('applicability');
      expect(service.activeTab()).toBe('applicability');

      service.setActiveTab('versions');
      expect(service.activeTab()).toBe('versions');

      service.setActiveTab('usage');
      expect(service.activeTab()).toBe('usage');

      service.setActiveTab('activity');
      expect(service.activeTab()).toBe('activity');

      service.setActiveTab('settings');
      expect(service.activeTab()).toBe('settings');
    });
  });

  // =========================================================================
  // 3. TEMPLATE DATA LOADING & SERVICE SIGNALS
  // =========================================================================
  describe('3. Template Data Loading & State Management', () => {
    it('should load template details from fixtures and populate signals', async () => {
      service.loadTemplate('tmpl-ora-pg-m2');
      
      // Await simulated fixture load
      await new Promise(resolve => setTimeout(resolve, 200));

      const tmpl = service.template();
      expect(tmpl).not.toBeNull();
      expect(tmpl?.id).toBe('tmpl-ora-pg-m2');
      expect(tmpl?.name).toBe('Oracle to PostgreSQL Continuous Migration');
      expect(tmpl?.mode).toBe('M2_BULK_CDC');
      expect(tmpl?.versionLabel).toBe('v2.1.0');
      expect(tmpl?.lifecycle).toBe('PUBLISHED');
      expect(service.isLoading()).toBe(false);
      expect(service.errorMessage()).toBeNull();
    });

    it('should handle template ID copy trigger with temporary status signal', () => {
      service.template.set(TEMPLATE_WORKSPACE_FIXTURES['tmpl-ora-pg-m2']);
      service.copyTemplateId();
      expect(service.copiedId()).toBe(true);
    });
  });

  // =========================================================================
  // 4. CONFIGURATION TAB & EDIT STATE
  // =========================================================================
  describe('4. Configuration Tab & Edit Presentation State', () => {
    beforeEach(async () => {
      service.loadTemplate('tmpl-ora-pg-m2');
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    it('should start editing configuration and clone draft state', () => {
      expect(service.isEditingConfig()).toBe(false);

      service.startEditingConfig();
      expect(service.isEditingConfig()).toBe(true);
      expect(service.editDraft().migrationDefaults.migrationNamePattern).toBe('MIG-ORA-PG-{{PROJECT}}-{{ENV}}-{{SEQ}}');
    });

    it('should allow modifying draft and cancel without mutating original', () => {
      service.startEditingConfig();
      service.updateEditDraft({
        migrationDefaults: {
          ...service.editDraft().migrationDefaults,
          migrationNamePattern: 'MUTATED-PATTERN'
        }
      });
      expect(service.editDraft().migrationDefaults.migrationNamePattern).toBe('MUTATED-PATTERN');

      service.cancelEditingConfig();
      expect(service.isEditingConfig()).toBe(false);
      expect(service.template()?.configuration.migrationDefaults.migrationNamePattern).toBe('MIG-ORA-PG-{{PROJECT}}-{{ENV}}-{{SEQ}}');
    });

    it('should save configuration changes into template presentation signal', () => {
      service.startEditingConfig();
      service.updateEditDraft({
        migrationDefaults: {
          ...service.editDraft().migrationDefaults,
          migrationNamePattern: 'MIG-ORA-PG-SAVED-{{ENV}}'
        }
      });
      service.saveEditingConfig();
      expect(service.isEditingConfig()).toBe(false);
      expect(service.template()?.configuration.migrationDefaults.migrationNamePattern).toBe('MIG-ORA-PG-SAVED-{{ENV}}');
      expect(service.configSaveMessage()).toContain('Configuration draft updated');
    });
  });

  // =========================================================================
  // 5. VERSION HISTORY & SEMANTIC DIFF ENGINE
  // =========================================================================
  describe('5. Version History & Semantic Diff Engine', () => {
    beforeEach(async () => {
      service.loadTemplate('tmpl-ora-pg-m2');
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    it('should compute semantic field-by-field differences between revisions', () => {
      service.setDiffVersions('v2.0.0', 'v2.1.0');
      const diff = service.diffResult();

      expect(diff.baseVersion).toBe('v2.0.0');
      expect(diff.compareVersion).toBe('v2.1.0');
      expect(diff.changes.length).toBeGreaterThan(0);

      // Verify extract threads change detected
      const threadChange = diff.changes.find(c => c.fieldLabel === 'Extract Threads');
      expect(threadChange).toBeDefined();
      expect(threadChange?.oldValue).toBe('4 workers');
      expect(threadChange?.newValue).toBe('8 workers');
      expect(threadChange?.changeType).toBe('MODIFIED');

      // Verify batch size change detected
      const batchChange = diff.changes.find(c => c.fieldLabel === 'Batch Size');
      expect(batchChange).toBeDefined();
      expect(batchChange?.oldValue).toBe('5000 rows');
      expect(batchChange?.newValue).toBe('10000 rows');
      expect(batchChange?.changeType).toBe('MODIFIED');
    });
  });

  // =========================================================================
  // 6. USAGE & REFERENCE PROTECTION
  // =========================================================================
  describe('6. Usage & Reference Protection', () => {
    beforeEach(async () => {
      service.loadTemplate('tmpl-ora-pg-m2');
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    it('should enforce reference protection when active migrations are bound', () => {
      const tmpl = service.template();
      expect(tmpl?.referenceProtection.isProtected).toBe(true);
      expect(tmpl?.referenceProtection.deletionPermitted).toBe(false);
      expect(tmpl?.referenceProtection.activeMigrationCount).toBe(2);
    });

    it('should verify materialization law: all migrations are marked independent', () => {
      const migrations = service.template()?.usage.migrations || [];
      expect(migrations.length).toBeGreaterThan(0);
      migrations.forEach(m => {
        expect(m.isIndependentMaterialization).toBe(true);
      });
    });
  });

  // =========================================================================
  // 7. SETTINGS & LIFECYCLE MANAGEMENT DIALOGS
  // =========================================================================
  describe('7. Settings & Lifecycle Management', () => {
    beforeEach(async () => {
      service.loadTemplate('tmpl-ora-pg-m2');
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    it('should open and close deprecation dialog and update lifecycle state', () => {
      expect(service.isDeprecateDialogOpen()).toBe(false);
      service.openDeprecateDialog();
      expect(service.isDeprecateDialogOpen()).toBe(true);

      service.applyDeprecate();
      expect(service.isDeprecateDialogOpen()).toBe(false);
      expect(service.template()?.lifecycle).toBe('DEPRECATED');
    });

    it('should open and close archive dialog and update lifecycle state', () => {
      expect(service.isArchiveDialogOpen()).toBe(false);
      service.openArchiveDialog();
      expect(service.isArchiveDialogOpen()).toBe(true);

      service.applyArchive();
      expect(service.isArchiveDialogOpen()).toBe(false);
      expect(service.template()?.lifecycle).toBe('ARCHIVED');
    });

    it('should open and close delete dialog', () => {
      expect(service.isDeleteDialogOpen()).toBe(false);
      service.openDeleteDialog();
      expect(service.isDeleteDialogOpen()).toBe(true);
      service.closeDeleteDialog();
      expect(service.isDeleteDialogOpen()).toBe(false);
    });
  });

  // =========================================================================
  // 8. ZERO PLAINTEXT SECRETS AUDIT
  // =========================================================================
  describe('8. Zero Plaintext Secrets Audit', () => {
    it('should verify no plaintext passwords or tokens exist in fixtures', () => {
      const rawJson = JSON.stringify(TEMPLATE_WORKSPACE_FIXTURES);
      expect(rawJson).not.toMatch(/password/i);
      expect(rawJson).not.toMatch(/client_secret/i);
      expect(rawJson).not.toMatch(/private_key/i);
      expect(rawJson).not.toMatch(/bearer\s+/i);
    });
  });
});
