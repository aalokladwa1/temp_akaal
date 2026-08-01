export interface SoDConflict {
  hasConflict: boolean;
  conflictingRoles: [string, string];
  reason: string;
}

export class SoDEngine {
  private static incompatiblePairs: Array<[string, string]> = [
    ['migration_operator', 'approval_admin'],
    ['sec_auditor', 'super_admin'],
  ];

  public static checkRoleConflict(existingRoles: string[], newRole: string): SoDConflict {
    for (const role of existingRoles) {
      for (const [r1, r2] of this.incompatiblePairs) {
        if ((role === r1 && newRole === r2) || (role === r2 && newRole === r1)) {
          return {
            hasConflict: true,
            conflictingRoles: [role, newRole],
            reason: `Separation of Duties violation: ${role} cannot be assigned alongside ${newRole}`,
          };
        }
      }
    }
    return { hasConflict: false, conflictingRoles: ['', ''], reason: '' };
  }
}
