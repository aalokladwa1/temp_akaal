import { describe, it, expect, beforeEach } from 'vitest';
import { ConnectionsService } from './connections.service';
import { ContextService } from '../../core/services/context.service';
import { FIXTURE_STANDARD_CONNECTIONS } from './connections.fixtures';
import {
  ConnectionRecord,
  ConnectionFamily,
  ConnectionVerificationState
} from './connections.models';

describe('Connections Module — Part A Unit Tests', () => {
  let service: ConnectionsService;
  let contextService: ContextService;

  beforeEach(() => {
    contextService = new ContextService();
    service = new ConnectionsService(contextService);
    service.resetToFixtures();
  });

  describe('Domain & Fixtures Integrity', () => {
    it('should initialize with standard fixtures representing diverse provider families', () => {
      const conns = service.connections();
      expect(conns.length).toBeGreaterThanOrEqual(10);

      // Verify presence of diverse families
      const families = new Set(conns.map(c => c.family));
      expect(families.has('RELATIONAL')).toBe(true);
      expect(families.has('WAREHOUSE_LAKE')).toBe(true);
      expect(families.has('STREAMING')).toBe(true);
      expect(families.has('OBJECT_STORAGE')).toBe(true);
      expect(families.has('NOSQL_GRAPH')).toBe(true);
      expect(families.has('APPLICATION')).toBe(true);
    });

    it('should never expose sensitive raw passwords or secrets in endpoint summaries', () => {
      const conns = service.connections();
      for (const conn of conns) {
        expect(conn.endpointDisplay).not.toContain('password');
        expect(conn.endpointDisplay).not.toContain('secret');
        expect(conn.endpointDisplay).not.toContain('token=');
        expect(conn.authMethodDisplay).toBeDefined();
      }
    });

    it('should support all required truthful verification states without synthetic collapsing', () => {
      const conns = service.connections();
      const states = new Set(conns.map(c => c.verificationState));
      
      // Fixtures contain verified, stale, failed, config changed, partial, and never tested
      expect(states.has('VERIFIED_RECENT') || states.has('VERIFIED_POINT_IN_TIME')).toBe(true);
      expect(states.has('VERIFICATION_FAILED')).toBe(true);
      expect(states.has('VERIFIED_STALE') || states.has('CONFIG_CHANGED_SINCE_TEST')).toBe(true);
      expect(states.has('NEVER_TESTED')).toBe(true);
    });
  });

  describe('Search and Multi-Dimensional Filtering', () => {
    it('should filter connections by search query matching name', () => {
      service.setSearchQuery('Oracle RAC');
      const filtered = service.filteredConnections();
      expect(filtered.length).toBeGreaterThanOrEqual(1);
      expect(filtered.every(c => c.name.toLowerCase().includes('oracle'))).toBe(true);
    });

    it('should filter connections by search query matching provider', () => {
      service.setSearchQuery('Snowflake');
      const filtered = service.filteredConnections();
      expect(filtered.length).toBeGreaterThanOrEqual(1);
      expect(filtered[0].providerName).toContain('Snowflake');
    });

    it('should filter connections by family', () => {
      service.setFamilyFilter('STREAMING');
      const filtered = service.filteredConnections();
      expect(filtered.length).toBeGreaterThanOrEqual(1);
      expect(filtered.every(c => c.family === 'STREAMING')).toBe(true);
    });

    it('should filter connections by VERIFIED_GROUP', () => {
      service.setVerificationFilter('VERIFIED_GROUP');
      const filtered = service.filteredConnections();
      expect(filtered.length).toBeGreaterThanOrEqual(1);
      expect(filtered.every(c => c.verificationState === 'VERIFIED_RECENT' || c.verificationState === 'VERIFIED_POINT_IN_TIME')).toBe(true);
    });

    it('should filter connections by ATTENTION_GROUP', () => {
      service.setVerificationFilter('ATTENTION_GROUP');
      const filtered = service.filteredConnections();
      expect(filtered.length).toBeGreaterThanOrEqual(1);
      expect(filtered.every(c => 
        c.verificationState === 'VERIFICATION_FAILED' || 
        c.verificationState === 'VERIFIED_STALE' || 
        c.verificationState === 'CONFIG_CHANGED_SINCE_TEST'
      )).toBe(true);
    });

    it('should filter connections by usage status (UNUSED)', () => {
      service.setUsageFilter('UNUSED');
      const filtered = service.filteredConnections();
      expect(filtered.length).toBeGreaterThanOrEqual(1);
      expect(filtered.every(c => c.usage.isUnused)).toBe(true);
    });

    it('should filter connections by environment (Production)', () => {
      service.setEnvironmentFilter('Production');
      const filtered = service.filteredConnections();
      expect(filtered.length).toBeGreaterThanOrEqual(1);
      expect(filtered.every(c => c.environment === 'Production')).toBe(true);
    });

    it('should clear all filters correctly', () => {
      service.setSearchQuery('Oracle');
      service.setFamilyFilter('RELATIONAL');
      service.setEnvironmentFilter('Production');
      expect(service.activeFilterCount()).toBe(3);

      service.clearFilters();
      expect(service.activeFilterCount()).toBe(0);
      expect(service.filters().searchQuery).toBe('');
      expect(service.filters().family).toBe('ALL');
      expect(service.filters().environment).toBe('ALL');
      expect(service.filteredConnections().length).toBe(service.connections().length);
    });
  });

  describe('Deterministic Sorting', () => {
    it('should sort connections by name ascending and descending', () => {
      service.setSorting('name', 'asc');
      const ascNames = service.filteredConnections().map(c => c.name);
      const sortedAsc = [...ascNames].sort((a, b) => a.localeCompare(b));
      expect(ascNames).toEqual(sortedAsc);

      service.toggleSort('name');
      const descNames = service.filteredConnections().map(c => c.name);
      const sortedDesc = [...ascNames].reverse();
      expect(descNames).toEqual(sortedDesc);
    });

    it('should sort connections by usage count', () => {
      service.setSorting('usageCount', 'desc');
      const filtered = service.filteredConnections();
      for (let i = 0; i < filtered.length - 1; i++) {
        const uA = (filtered[i].usage.activeMigrationCount || 0) + (filtered[i].usage.activeValidationCount || 0);
        const uB = (filtered[i+1].usage.activeMigrationCount || 0) + (filtered[i+1].usage.activeValidationCount || 0);
        expect(uA).toBeGreaterThanOrEqual(uB);
      }
    });
  });

  describe('Summary Counters', () => {
    it('should accurately compute summary counters', () => {
      const counters = service.summaryCounters();
      const all = service.connections();
      expect(counters.total).toBe(all.length);

      const verified = all.filter(c => c.verificationState === 'VERIFIED_RECENT' || c.verificationState === 'VERIFIED_POINT_IN_TIME').length;
      expect(counters.verified).toBe(verified);

      const attention = all.filter(c => 
        c.verificationState === 'VERIFICATION_FAILED' || 
        c.verificationState === 'VERIFIED_STALE' || 
        c.verificationState === 'CONFIG_CHANGED_SINCE_TEST'
      ).length;
      expect(counters.needsAttention).toBe(attention);

      const unused = all.filter(c => c.usage.isUnused).length;
      expect(counters.unused).toBe(unused);
    });
  });

  describe('Inspection Drawer & Verification Probe Execution', () => {
    it('should open and close inspect drawer with selected connection', () => {
      const conn = service.connections()[0];
      service.openInspectDrawer(conn);
      expect(service.isInspectDrawerOpen()).toBe(true);
      expect(service.selectedConnection()?.id).toBe(conn.id);

      service.closeInspectDrawer();
      expect(service.isInspectDrawerOpen()).toBe(false);
      expect(service.selectedConnection()).toBeNull();
    });

    it('should execute simulated point-in-time verification probe', async () => {
      const conn = service.connections().find(c => c.verificationState === 'NEVER_TESTED') || service.connections()[0];
      
      service.verifyConnection(conn.id);
      expect(service.isVerifyingConnectionId()).toBe(conn.id);

      const connInList = service.connections().find(c => c.id === conn.id);
      expect(connInList?.verificationState).toBe('TESTING');

      // Wait for probe simulation to complete
      await new Promise(resolve => setTimeout(resolve, 650));

      const updatedConn = service.connections().find(c => c.id === conn.id);
      expect(updatedConn?.verificationState).toBe('VERIFIED_RECENT');
      expect(updatedConn?.lastVerifiedAt).toBeDefined();
      expect(service.isVerifyingConnectionId()).toBeNull();
    });
  });

  describe('Availability States', () => {
    it('should handle EMPTY and ERROR states gracefully', () => {
      service.connections.set([]);
      expect(service.connections().length).toBe(0);

      service.availabilityState.set('ERROR');
      service.errorMessage.set('Connection authority timeout');
      expect(service.availabilityState()).toBe('ERROR');
      expect(service.errorMessage()).toBe('Connection authority timeout');

      service.reload();
      expect(service.availabilityState()).toBe('READY');
      expect(service.connections().length).toBeGreaterThan(0);
    });
  });
});
