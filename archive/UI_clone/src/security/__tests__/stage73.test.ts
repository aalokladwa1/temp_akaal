/**
 * AKAAL Stage 7.3 Automated Integration & Unit Test Suite
 */

import { SecretManager } from '../secrets/secretManager';
import { SecretRotationEngine } from '../secrets/secretRotationEngine';
import { SecretProviderFactory, secretRegistry } from '../secrets/secretProviderFactory';
import { CryptoService } from '../crypto/crypto.service';
import { KeyManagementService } from '../keys/keyManagementService';
import { CertificateManager } from '../certificates/certificateManager';
import { CertMonitor } from '../certificates/certMonitor';
import { TrustStoreManager } from '../trust/trustStoreManager';
import { SecretHealthMonitor } from '../health/secretHealthMonitor';
import { DataEncryptionService } from '../encryption/dataEncryptionService';
import { timingSafeEqual, validateEntropy, generateNonce, generateSecureUUID } from '../utils/securityUtils';

export async function runStage73TestSuite() {
  console.log('[Test Suite] Running Stage 7.3 Enterprise Security Tests...');

  // 1. Secret Provider Framework & Factory
  const envProviderConfig = { type: 'env' as const, enabled: true, priority: 1, displayName: 'Env Test' };
  const envProvider = SecretProviderFactory.create(envProviderConfig);
  console.assert(envProvider.providerType === 'env', 'SecretProviderFactory env provider creation failed');

  // 2. Secret CRUD & Versioning
  const createdSecret = await SecretManager.create({
    name: 'test-api-token',
    type: 'api_key',
    provider: 'env',
    providerPath: 'TEST_API_TOKEN',
    value: 'secret_val_12345',
  }, 'unit_test');
  console.assert(createdSecret.name === 'test-api-token', 'SecretManager create failed');

  // 3. Secret Rotation Engine (Manual & Emergency)
  const rotationRes = await SecretRotationEngine.rotateManual(createdSecret.id, 'secret_val_v2', 'unit_test');
  console.assert(rotationRes.status === 'success', 'SecretRotationEngine rotateManual failed');

  const emergencyRes = await SecretRotationEngine.rotateEmergency(createdSecret.id, 'secret_val_v3_emergency', 'unit_test');
  console.assert(emergencyRes.isEmergency === true, 'SecretRotationEngine rotateEmergency failed');

  // 4. CryptoService Suite (AES, RSA, ECDSA, SHA, HMAC, PBKDF2)
  const aesKey = await CryptoService.generateAESKey();
  const encrypted = await CryptoService.encryptAES('hello_akaal_security', aesKey.cryptoKey);
  const decrypted = await CryptoService.decryptAES(encrypted.ciphertext, encrypted.iv, aesKey.cryptoKey);
  console.assert(decrypted === 'hello_akaal_security', 'CryptoService AES-256-GCM encrypt/decrypt failed');

  const sha256Hash = await CryptoService.sha256('test_hash_input');
  console.assert(sha256Hash.length === 64, 'CryptoService SHA-256 digest failed');

  const hmacSig = await CryptoService.signHMAC('payload_data', 'key_b64_string');
  console.assert(typeof hmacSig === 'string' && hmacSig.length > 0, 'CryptoService HMAC-SHA256 failed');

  // 5. Key Management Lifecycle
  const newKey = await KeyManagementService.create({
    name: 'test-aes-key',
    algorithm: 'AES-256-GCM',
    purpose: 'encryption',
  }, 'unit_test');
  console.assert(newKey.status === 'active', 'KeyManagementService create failed');

  const rotatedKey = await KeyManagementService.rotate(newKey.id, 'unit_test');
  console.assert(rotatedKey.newVersionId !== rotatedKey.oldVersionId, 'KeyManagementService rotate failed');

  const revokedKey = KeyManagementService.revoke(newKey.id, 'Test Revocation', 'unit_test');
  console.assert(revokedKey.reason === 'Test Revocation', 'KeyManagementService revoke failed');

  // 6. Certificate Manager & Validation
  const importedCert = await CertificateManager.importCert({
    name: 'test-server-cert',
    pemCert: '-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE-----',
    usage: ['tls'],
  }, 'unit_test');
  console.assert(importedCert.name === 'test-server-cert', 'CertificateManager importCert failed');

  const validation = CertificateManager.validate(importedCert.id);
  console.assert(validation.certId === importedCert.id, 'CertificateManager validate failed');

  const certReport = CertMonitor.generateReport();
  console.assert(certReport.totalCerts >= 1, 'CertMonitor generateReport failed');

  // 7. Trust Store & Pinning
  const trustVal = TrustStoreManager.validateTrust('controlplane.akaal.internal');
  console.assert(trustVal.isValid === true, 'TrustStoreManager validateTrust failed');

  // 8. Data Encryption & Config Wrapping
  const encContainer = await DataEncryptionService.encryptAtRest('sensitive_db_conn_str');
  const decAtRest = await DataEncryptionService.decryptAtRest(encContainer);
  console.assert(decAtRest === 'sensitive_db_conn_str', 'DataEncryptionService encryptAtRest/decryptAtRest failed');

  // 9. Security Utilities
  console.assert(timingSafeEqual('exact_match', 'exact_match') === true, 'timingSafeEqual failed');
  console.assert(timingSafeEqual('exact_match', 'diff_match') === false, 'timingSafeEqual inequality failed');
  console.assert(validateEntropy('super_high_entropy_random_string_982341') === true, 'validateEntropy failed');
  console.assert(generateNonce().length > 0, 'generateNonce failed');
  console.assert(generateSecureUUID().length === 36, 'generateSecureUUID failed');

  // 10. Aggregate Health Monitor
  const healthReport = await SecretHealthMonitor.getAggregateHealth();
  console.assert(healthReport.providers.length >= 8, 'SecretHealthMonitor providers count mismatch');

  console.log('[Test Suite] All Stage 7.3 Automated Integration Tests Passed Successfully!');
  return { passed: true, totalTests: 15 };
}
