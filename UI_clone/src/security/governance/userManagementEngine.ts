import { UserIdentity } from '../types/security.types';

export type UserStatus = 'active' | 'invited' | 'suspended' | 'deactivated';

export interface ManagedUser extends UserIdentity {
  status: UserStatus;
  department: string;
  userGroups: string[];
  invitedBy?: string;
  createdAt: string;
}

export class UserManagementEngine {
  private static users = new Map<string, ManagedUser>([
    [
      'usr_prod_1',
      {
        id: 'usr_prod_1',
        email: 'sarah.chen@acme.com',
        fullName: 'Sarah Chen',
        provider: 'okta',
        providerId: 'okta_sc_9482',
        organizationId: 'org_acme_corp',
        tenantId: 'tenant_prod_us_east',
        projectIds: ['prj_mig_oracle', 'prj_mig_postgres'],
        roles: ['super_admin'],
        attributes: {},
        mfaEnabled: true,
        lastLoginAt: new Date().toISOString(),
        status: 'active',
        department: 'Infrastructure Architecture',
        userGroups: ['Akaal-Admins', 'SecOps-Lead'],
        createdAt: new Date().toISOString(),
      },
    ],
  ]);

  public static inviteUser(email: string, fullName: string, role: string, department: string, invitedBy: string): ManagedUser {
    const newUser: ManagedUser = {
      id: `usr_${Date.now()}`,
      email,
      fullName,
      provider: 'okta',
      providerId: `okta_inv_${Date.now()}`,
      organizationId: 'org_acme_corp',
      tenantId: 'tenant_prod_us_east',
      projectIds: [],
      roles: [role],
      attributes: {},
      mfaEnabled: false,
      lastLoginAt: 'Never',
      status: 'invited',
      department,
      userGroups: ['Standard-Users'],
      invitedBy,
      createdAt: new Date().toISOString(),
    };
    this.users.set(newUser.id, newUser);
    return newUser;
  }

  public static updateUserStatus(userId: string, status: UserStatus): boolean {
    const user = this.users.get(userId);
    if (!user) return false;
    user.status = status;
    return true;
  }

  public static getUsers(): ManagedUser[] {
    return Array.from(this.users.values());
  }
}
