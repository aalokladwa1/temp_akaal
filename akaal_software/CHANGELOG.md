# CHANGELOG

## [0.3.0] - Sprint 3 — Identity & Security Foundation

### Added
- **Startup Bootstrapper (`src-tauri/src/core/`)**: Modular initialization sequence validating workspace config, storage integrity, and restoring sessions from DPAPI vault.
- **Argon2id & Memory Zeroization (`src-tauri/src/security/hashing.rs`)**: Secure password hashing with Argon2id and `zeroize` memory clearing on plaintext credential buffers.
- **Native Windows DPAPI Vault (`src-tauri/src/security/vault.rs`)**: OS-encrypted persistent token storage via `CryptProtectData` and `CryptUnprotectData` Win32 APIs.
- **Sliding Rate Limiter (`src-tauri/src/security/rate_limiter.rs`)**: Account lockout after 5 failed login attempts in a 15-minute window.
- **Categorized Audit Engine (`src-tauri/src/audit/`)**: Structured append-only audit event logging across Authentication, Session, Security, Administration, Migration, and System categories.
- **Decoupled `AuthenticationManager` (`src/services/authenticationManager.ts`)**: Service-oriented auth manager replacing React Context with Rx/Observer subscriptions.
- **Custom Hooks (`src/hooks/`)**: `useAuthentication`, `useSession`, and `useStartupInitialization`.
- **Adaptive Greeting Auth Screen (`src/screens/AuthScreen/`)**: Enterprise sign-in view displaying "Welcome back, <Display Name>" for known users or "Secure Sign In" for first-time authentication.
- **Organization Provider Modal (`src/components/Auth/OrganizationModal.tsx`)**: Data-driven provider selector populated dynamically via `get_auth_providers_cmd`.
- **Dedicated Recovery Screen (`src/screens/RecoveryScreen/`)**: Graceful enterprise error recovery view for session expiration or workspace integrity failures.
- **Unified App Routing (`src/App.tsx`)**: Full lifecycle flow (`Splash` -> `Welcome` / `Wizard` -> `Recovery` -> `Auth` -> `Workspace Home`).
