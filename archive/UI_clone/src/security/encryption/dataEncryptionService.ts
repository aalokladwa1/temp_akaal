/**
 * AKAAL Data Encryption Service
 * Stage 7.3
 *
 * Implements encryption at rest, payload wrapping/unwrapping, and secure configuration loading.
 */

import { CryptoService } from '../crypto/crypto.service';

export interface EncryptedContainer {
  algorithm: 'AES-256-GCM';
  ciphertext: string;
  iv: string;
  version: number;
  timestamp: string;
}

export class DataEncryptionService {
  private static activeKey: CryptoKey | null = null;
  private static rawKeyBase64: string | null = null;

  private static async getOrCreateKey(): Promise<CryptoKey> {
    if (this.activeKey) return this.activeKey;
    const res = await CryptoService.generateAESKey();
    this.activeKey = res.cryptoKey;
    this.rawKeyBase64 = res.rawBase64;
    return this.activeKey;
  }

  public static async encryptAtRest(plaintext: string): Promise<EncryptedContainer> {
    const key = await this.getOrCreateKey();
    const res = await CryptoService.encryptAES(plaintext, key);

    return {
      algorithm: 'AES-256-GCM',
      ciphertext: res.ciphertext,
      iv: res.iv,
      version: 1,
      timestamp: new Date().toISOString(),
    };
  }

  public static async decryptAtRest(container: EncryptedContainer): Promise<string> {
    const key = await this.getOrCreateKey();
    return CryptoService.decryptAES(container.ciphertext, container.iv, key);
  }

  public static async encryptConfig<T extends Record<string, unknown>>(configObj: T): Promise<string> {
    const json = JSON.stringify(configObj);
    const container = await this.encryptAtRest(json);
    return JSON.stringify(container);
  }

  public static async decryptConfig<T extends Record<string, unknown>>(encryptedStr: string): Promise<T> {
    const container: EncryptedContainer = JSON.parse(encryptedStr);
    const json = await this.decryptAtRest(container);
    return JSON.parse(json) as T;
  }
}
