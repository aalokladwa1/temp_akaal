/**
 * AKAAL Enterprise Identity & Security Configuration
 */

export interface SecurityConfig {
  environment: 'development' | 'staging' | 'production';
  token: {
    accessTokenLifetimeSeconds: number;
    refreshTokenLifetimeSeconds: number;
    rotationEnabled: boolean;
    issuer: string;
    audience: string;
  };
  session: {
    maxActiveSessionsPerUser: number;
    idleTimeoutMinutes: number;
    slidingExpirationMinutes: number;
    secureCookie: boolean;
    cookieSameSite: 'lax' | 'strict' | 'none';
  };
  audit: {
    appendOnlyLog: boolean;
    logPermissionFailures: boolean;
    syslogEnabled: boolean;
  };
  secret: {
    providerType: 'env' | 'vault' | 'dev';
    cacheTtlSeconds: number;
  };
}

export const defaultSecurityConfig: SecurityConfig = {
  environment: (process.env.NODE_ENV as any) || 'development',
  token: {
    accessTokenLifetimeSeconds: 3600, // 1 hour
    refreshTokenLifetimeSeconds: 86400 * 7, // 7 days
    rotationEnabled: true,
    issuer: 'https://akaal-auth.internal',
    audience: 'akaal-enterprise-control-plane',
  },
  session: {
    maxActiveSessionsPerUser: 5,
    idleTimeoutMinutes: 30,
    slidingExpirationMinutes: 120,
    secureCookie: true,
    cookieSameSite: 'strict',
  },
  audit: {
    appendOnlyLog: true,
    logPermissionFailures: true,
    syslogEnabled: true,
  },
  secret: {
    providerType: 'env',
    cacheTtlSeconds: 300,
  },
};
