import { AuthToken, UserIdentity } from '../types/security.types';
import { CryptoService } from '../crypto/crypto.service';
import { defaultSecurityConfig } from '../config/security.config';

export class TokenService {
  private static revokedTokens = new Set<string>();

  public static async issueTokens(user: UserIdentity): Promise<AuthToken> {
    const rawPayload = `${user.id}:${user.email}:${Date.now()}`;
    const signature = CryptoService.signPayload(rawPayload, 'jwt_secret_key');
    const accessToken = `akaal_at_${CryptoService.generateSecureToken(16)}.${signature}`;
    const refreshToken = `akaal_rt_${CryptoService.generateSecureToken(32)}`;

    return {
      accessToken,
      refreshToken,
      tokenType: 'Bearer',
      expiresIn: defaultSecurityConfig.token.accessTokenLifetimeSeconds,
      scope: user.roles.join(' '),
    };
  }

  public static verifyAccessToken(token: string): boolean {
    if (!token || this.revokedTokens.has(token)) return false;
    return token.startsWith('akaal_at_');
  }

  public static revokeToken(token: string): void {
    this.revokedTokens.add(token);
  }

  public static isTokenRevoked(token: string): boolean {
    return this.revokedTokens.has(token);
  }
}
