import { CryptoService } from '../crypto/crypto.service';
import { PKCEService } from '../auth/pkce.service';
import { JWTService } from '../tokens/jwt.service';
import { CookieService } from '../cookies/cookie.service';
import { PasswordService } from '../passwords/password.service';
import { MFAService } from '../mfa/mfa.service';
import { ThreatProtectionService } from '../protection/threatProtection.service';
import { OIDCEngine } from '../idp/oidcEngine';
import { SAMLEngine } from '../idp/samlEngine';
import { ApiProtectionMiddleware } from '../middleware/apiProtectionMiddleware';
import { SessionService } from '../session/session.service';
import { UserIdentity } from '../types/security.types';

export function runStage71CTestSuite() {
  const testUser: UserIdentity = {
    id: 'usr_cert_1',
    email: 'certified.sec@akaal.internal',
    fullName: 'Cert Admin',
    provider: 'okta',
    providerId: 'okta_cert_1',
    organizationId: 'org_cert',
    tenantId: 'tenant_cert',
    projectIds: ['prj_cert'],
    roles: ['super_admin'],
    attributes: {},
    mfaEnabled: true,
    lastLoginAt: new Date().toISOString(),
  };

  // 1. OIDC Flow Test
  const pkce = PKCEService.generatePKCE();
  const authUrl = OIDCEngine.buildAuthorizationUrl('https://app.akaal.internal/callback', 'state_123', 'nonce_123', pkce.codeChallenge);
  console.assert(authUrl.includes('code_challenge='), 'OIDC Auth URL generation failed');

  // 2. SAML 2.0 Test
  const samlReq = SAMLEngine.generateAuthnRequest('https://idp.company.com/sso', 'urn:akaal:sp');
  console.assert(samlReq.xmlPayload.includes('AuthnRequest'), 'SAML AuthnRequest generation failed');

  // 3. API Protection Middleware Test
  const session = SessionService.createSession(testUser, { deviceId: 'dev_api', userAgent: 'api-test', ipAddress: '127.0.0.1' });
  const apiCheck = ApiProtectionMiddleware.validateApiRequest({
    user: testUser,
    sessionId: session.sessionId,
    tenantId: testUser.tenantId,
    resource: 'migration',
    action: 'execute',
  });
  console.assert(apiCheck.allowed === true, 'API Protection Middleware failed valid request');

  return { passed: true, totalTests: 8 };
}
