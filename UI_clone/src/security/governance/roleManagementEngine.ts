import { Role, Permission } from '../types/security.types';

export class RoleManagementEngine {
  private static customRoles = new Map<string, Role>([
    [
      'custom_sec_lead',
      {
        id: 'custom_sec_lead',
        name: 'SecOps Team Lead',
        description: 'Custom governance role with audit inspection and credential approval rights',
        permissions: [
          { id: 'p_audit_all', resource: 'audit', action: 'read' },
          { id: 'p_approve_cred', resource: 'credentials', action: 'approve' },
        ],
      },
    ],
  ]);

  public static createCustomRole(name: string, description: string, permissions: Permission[]): Role {
    const roleId = `role_${Date.now()}`;
    const role: Role = {
      id: roleId,
      name,
      description,
      permissions,
    };
    this.customRoles.set(roleId, role);
    return role;
  }

  public static getRoles(): Role[] {
    return Array.from(this.customRoles.values());
  }
}
