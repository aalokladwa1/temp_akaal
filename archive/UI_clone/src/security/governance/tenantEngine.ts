export type TenantStatus = 'active' | 'suspended' | 'archived' | 'provisioning';

export interface Tenant {
  id: string;
  name: string;
  code: string;
  status: TenantStatus;
  region: string;
  createdAt: string;
}

export interface Organization {
  id: string;
  tenantId: string;
  name: string;
  code: string;
  parentOrgId?: string;
}

export interface Department {
  id: string;
  orgId: string;
  name: string;
}

export interface Workspace {
  id: string;
  tenantId: string;
  orgId: string;
  name: string;
}

export interface Project {
  id: string;
  workspaceId: string;
  tenantId: string;
  name: string;
  environment: 'production' | 'staging' | 'development';
}

export class TenantEngine {
  private static tenants = new Map<string, Tenant>([
    [
      'tenant_prod_us_east',
      {
        id: 'tenant_prod_us_east',
        name: 'Acme Financial Systems',
        code: 'ACME-FIN',
        status: 'active',
        region: 'us-east-1',
        createdAt: new Date().toISOString(),
      },
    ],
  ]);

  public static getTenant(tenantId: string): Tenant | null {
    return this.tenants.get(tenantId) ?? null;
  }

  public static validateTenantBoundary(requestTenantId: string, targetResourceTenantId: string): boolean {
    if (!requestTenantId || !targetResourceTenantId) return false;
    return requestTenantId === targetResourceTenantId;
  }
}
