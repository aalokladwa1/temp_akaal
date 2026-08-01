import { UserIdentity, Role, Permission } from '../types/security.types';

export class PermissionEvaluator {
  private static roleRegistry = new Map<string, Role>([
    [
      'super_admin',
      {
        id: 'super_admin',
        name: 'Super Administrator',
        description: 'Full administrative access across all tenant resources',
        permissions: [{ id: 'p_admin', resource: '*', action: 'admin' }],
      },
    ],
    [
      'migration_engineer',
      {
        id: 'migration_engineer',
        name: 'Migration Engineer',
        description: 'Can configure, execute, pause, and review migrations',
        permissions: [
          { id: 'p_mig_create', resource: 'migration', action: 'create' },
          { id: 'p_mig_read', resource: 'migration', action: 'read' },
          { id: 'p_mig_exec', resource: 'migration', action: 'execute' },
          { id: 'p_db_read', resource: 'database', action: 'read' },
        ],
      },
    ],
    [
      'sec_auditor',
      {
        id: 'sec_auditor',
        name: 'Security Auditor',
        description: 'Read-only access to security logs, compliance reports, and RBAC matrix',
        permissions: [
          { id: 'p_audit_read', resource: 'audit', action: 'read' },
          { id: 'p_report_read', resource: 'report', action: 'read' },
          { id: 'p_sec_read', resource: 'security_setting', action: 'read' },
        ],
      },
    ],
  ]);

  public static hasPermission(user: UserIdentity, resource: string, action: string): boolean {
    if (!user || !user.roles) return false;

    for (const roleId of user.roles) {
      const role = this.roleRegistry.get(roleId);
      if (!role) continue;

      for (const perm of role.permissions) {
        if (perm.action === 'admin' || (perm.resource === resource && perm.action === action)) {
          return true;
        }
      }
    }
    return false;
  }
}
