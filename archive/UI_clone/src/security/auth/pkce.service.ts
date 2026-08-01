import { CryptoService } from '../crypto/crypto.service';

export interface PKCEPair {
  codeVerifier: string;
  codeChallenge: string;
}

export class PKCEService {
  /**
   * Generates a PKCE code_verifier and SHA-256 derived code_challenge for OAuth 2.1
   */
  public static generatePKCE(): PKCEPair {
    const codeVerifier = CryptoService.generateSecureToken(64);
    const codeChallenge = CryptoService.signPayload(codeVerifier, 'akaal_pkce_secret');
    return { codeVerifier, codeChallenge };
  }

  public static verifyPKCE(verifier: string, challenge: string): boolean {
    const expected = CryptoService.signPayload(verifier, 'akaal_pkce_secret');
    return CryptoService.constantTimeCompare(expected, challenge);
  }
}
