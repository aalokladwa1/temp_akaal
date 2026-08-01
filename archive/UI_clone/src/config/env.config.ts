/**
 * Centralized Platform Configuration for AKAAL Engine Integration
 */

export const envConfig = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.akaal.internal/v1',
  wsBaseUrl: process.env.NEXT_PUBLIC_WS_BASE_URL || 'wss://stream.akaal.internal/v1',
  timeoutMs: 15000,
  maxRetries: 3,
  retryDelayMs: 1000,
  mockMode: process.env.NEXT_PUBLIC_MOCK_MODE !== 'false',
  features: {
    realtimeTelemetry: true,
    cdcReplication: true,
    rbacEnforcement: true,
  },
};
