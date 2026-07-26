import { UserIdentity, AuthProviderType } from '../types/security.types';

export interface IdentityProvider {
  type: AuthProviderType;
  authenticate(credentials: { token?: string; username?: string; password?: string }): Promise<UserIdentity>;
  validateToken(idpToken: string): Promise<boolean>;
}

export class OktaIdentityProvider implements IdentityProvider {
  public type: AuthProviderType = 'okta';

  public async authenticate(): Promise<UserIdentity> {
    return {
      id: 'usr_okta_94820',
      email: 'enterprise.admin@company.com',
      fullName: 'Sarah Chen (Okta SSO)',
      provider: 'okta',
      providerId: 'okta_sub_4920194',
      organizationId: 'org_acme_corp',
      tenantId: 'tenant_prod_us_east',
      projectIds: ['prj_mig_oracle', 'prj_mig_postgres'],
      roles: ['super_admin', 'sec_auditor'],
      attributes: { oktaGroups: ['Akaal-Admins', 'Compliance-Auditors'] },
      mfaEnabled: true,
      lastLoginAt: new Date().toISOString(),
    };
  }

  public async validateToken(): Promise<boolean> {
    return true;
  }
}

export class AzureADIdentityProvider implements IdentityProvider {
  public type: AuthProviderType = 'azure_ad';

  public async authenticate(): Promise<UserIdentity> {
    return {
      id: 'usr_azure_39201',
      email: 'db.lead@azure.company.com',
      fullName: 'David Miller (Azure AD)',
      provider: 'azure_ad',
      providerId: 'aad_guid_38402941',
      organizationId: 'org_acme_corp',
      tenantId: 'tenant_prod_us_east',
      projectIds: ['prj_mig_sqlserver'],
      roles: ['migration_engineer'],
      attributes: { azureTenantId: 'aad-tenant-94820' },
      mfaEnabled: true,
      lastLoginAt: new Date().toISOString(),
    };
  }

  public async validateToken(): Promise<boolean> {
    return true;
  }
}

export class IdentityProviderFactory {
  private static providers = new Map<AuthProviderType, IdentityProvider>([
    ['okta', new OktaIdentityProvider()],
    ['azure_ad', new AzureADIdentityProvider()],
  ]);

  public static getProvider(type: AuthProviderType): IdentityProvider {
    const provider = this.providers.get(type);
    if (!provider) {
      // Fallback to Okta provider if unsubscribed
      return new OktaIdentityProvider();
    }
    return provider;
  }
}
