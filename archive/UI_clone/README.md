# AKAAL — Enterprise Database Migration Platform

A production-grade Next.js 15 enterprise application built with TypeScript and Tailwind CSS, featuring a complete multi-tenant identity, security, and governance platform.

## 🚀 Features

- **Next.js 15** - Latest version with improved performance and App Router
- **React 19** - Latest React version with enhanced capabilities
- **Tailwind CSS** - Utility-first CSS framework for rapid UI development
- **Enterprise Security Foundation** - Complete Stage 7.1 identity and authentication platform
- **Multi-Tenant Governance** - Full Stage 7.2 enterprise authorization and governance platform

## 📋 Release Stage

| Stage | Description | Status |
|-------|-------------|--------|
| Batches 1–8 | Visual identity, navigation, API integration readiness, QA | ✅ Complete |
| Stage 7.1 | Enterprise Identity & Security Foundation | ✅ Complete |
| Stage 7.1B | Production Identity & Authentication Completion | ✅ Complete |
| Stage 7.1C | Enterprise Identity Hardening & Production Certification | ✅ Complete |
| Stage 7.2 | Enterprise Authorization, Multi-Tenancy & Governance Platform | ✅ Complete |
| Stage 7.2B | Enterprise Administration, Governance Completion & Authorization Finalization | ✅ Complete |
| Stage 7.2C | Enterprise Administration Application Completion | ✅ Complete |
| Stage 7.2D | Governance Stabilization, Persistence Readiness & CRUD Reliability | ✅ Complete |
| Stage 7.3 | _Pending_ | ⏳ Pending |

## 🛡️ Enterprise Security Architecture

### Stage 7.1 — Identity & Authentication
- OAuth 2.1 + PKCE authorization code flow
- OpenID Connect login engine (`OIDCEngine`)
- SAML 2.0 authentication (`SAMLEngine`)
- JWT lifecycle management with revocation registry
- Argon2id-style password hashing with account lockout
- TOTP-based MFA with recovery codes
- Persistent session management with device tracking
- HTTP Security Headers (HSTS, CSP, X-Frame-Options)
- Immutable append-only audit pipeline

### Stage 7.2 — Authorization & Governance
- Multi-tenant architecture with strict isolation boundaries (`TenantEngine`)
- RBAC engine with inherited and custom roles (`RoleManagementEngine`)
- ABAC engine with time, risk, and classification policies (`ABACEngine`)
- Separation of Duties conflict detection (`SoDEngine`)
- Just-In-Time privilege elevation with approval workflows (`JITEngine`)
- Access request and approval management (`AccessRequestEngine`)
- Session-safe browser persistence (`GovernancePersistenceStore`)
- Enterprise governance administration UI for Tenants, Users, Roles, Approvals

## 🛠️ Installation

1. Install dependencies:
  ```bash
  npm install
  ```

2. Start the development server:
  ```bash
  NODE_OPTIONS=--max-old-space-size=4096 npm run dev
  ```

3. Open [http://localhost:4028](http://localhost:4028) with your browser to see the result.

## 📁 Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── dashboard/          # Main dashboard
│   ├── governance/         # Enterprise governance console
│   │   ├── tenants/        # Multi-tenant management
│   │   ├── users/          # User administration
│   │   ├── roles/          # Role & permission catalog
│   │   └── approvals/      # Access requests & approval workflows
│   ├── security/           # Security management pages
│   │   ├── sessions/       # Device session management
│   │   └── mfa-enroll/     # MFA enrollment
│   ├── migrate-dashboard/  # Migration dashboard
│   ├── migration-workspace/ # Migration workspace
│   └── ...                 # Other application pages
├── components/             # Reusable UI components
│   └── security/           # PermissionGuard, etc.
├── security/               # Enterprise security modules
│   ├── auth/               # PKCEService, OAuth flows
│   ├── authz/              # PermissionEvaluator, ABACEngine
│   ├── audit/              # AuditPipeline, PersistentAuditStore
│   ├── config/             # Security configuration
│   ├── context/            # SecurityContext
│   ├── cookies/            # CookieService, CSRF
│   ├── crypto/             # CryptoService
│   ├── governance/         # TenantEngine, SoDEngine, JITEngine, etc.
│   ├── idp/                # IDPProviderFactory, OIDCEngine, SAMLEngine
│   ├── middleware/         # SecurityMiddleware, ApiProtectionMiddleware
│   ├── mfa/                # MFAService
│   ├── passwords/          # PasswordService
│   ├── protection/         # ThreatProtectionService
│   ├── secrets/            # SecretResolver
│   ├── session/            # SessionService, PersistentSessionStore
│   ├── tokens/             # TokenService, JWTService
│   └── types/              # Security domain types
└── services/               # API & backend service layer
```

## 📦 Available Scripts

- `npm run dev` - Start development server on port 4028
- `npm run build` - Build the application for production
- `npm run start` - Start the production server
- `npm run lint` - Run ESLint to check code quality
- `npm run format` - Format code with Prettier

## 📱 Production Build

```bash
set NODE_OPTIONS=--max-old-space-size=4096
npm run build
```

## 🔐 Governance Admin Console

| Route | Description |
|-------|-------------|
| `/governance/tenants` | Multi-tenant provisioning & management |
| `/governance/users` | Enterprise user administration |
| `/governance/roles` | RBAC role & permission catalog |
| `/governance/approvals` | Access requests & JIT approval workflows |
| `/security/sessions` | Active device session management |
| `/security/mfa-enroll` | MFA TOTP enrollment |

## 📚 Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial

Built with ❤️ on Rocket.new