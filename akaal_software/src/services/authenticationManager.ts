/**
 * AKAAL Enterprise AuthenticationManager Service
 * 
 * Provides isolated infrastructure authentication and session management.
 * UI components NEVER manage global auth in React Context; they subscribe
 * to the AuthenticationManager via dedicated custom hooks.
 */

import { ipcService } from './ipcService';
import type {
  BootstrapStatus,
  SessionInfo,
  UserDisplayInfo,
  AuthProviderInfo,
} from '../types/auth';

export type AuthState =
  | 'bootstrapping'
  | 'unauthenticated'
  | 'authenticated'
  | 'locked'
  | 'recovery'
  | 'setup_required';

export interface AuthManagerState {
  authState: AuthState;
  session: SessionInfo | null;
  lastUser: UserDisplayInfo | null;
  providers: AuthProviderInfo[];
  bootstrapStatus: BootstrapStatus | null;
  errorMessage: string | null;
}

type Listener = (state: AuthManagerState) => void;

class AuthenticationManager {
  private state: AuthManagerState = {
    authState: 'bootstrapping',
    session: null,
    lastUser: null,
    providers: [],
    bootstrapStatus: null,
    errorMessage: null,
  };

  private listeners: Set<Listener> = new Set();
  private _heartbeatTimer: number | null = null;
  private initialized = false;
  private initPromise: Promise<BootstrapStatus> | null = null;

  constructor() {
    this.startHeartbeat();
  }

  public getHeartbeatTimer(): number | null {
    return this._heartbeatTimer;
  }

  public getState(): AuthManagerState {
    return { ...this.state };
  }

  public subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    // Push immediate initial state
    listener(this.getState());
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify() {
    const currentState = this.getState();
    this.listeners.forEach((listener) => listener(currentState));
  }

  private updateState(partial: Partial<AuthManagerState>) {
    this.state = { ...this.state, ...partial };
    this.notify();
  }

  public async initialize(): Promise<BootstrapStatus> {
    if (this.initialized && this.state.bootstrapStatus) {
      return this.state.bootstrapStatus;
    }

    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = (async () => {
      this.updateState({ authState: 'bootstrapping', errorMessage: null });

      try {
        // 1. Fetch Auth Providers
        const providers = await ipcService.getAuthProviders();
        const lastUser = await ipcService.getLastKnownUser();

        // 2. Perform Startup Bootstrap (IPC runs once)
        const bootstrapStatus = await ipcService.bootstrapApp();

        this.initialized = true;

        if (!bootstrapStatus.isWorkspaceConfigured) {
          this.updateState({
            authState: 'setup_required',
            providers,
            lastUser,
            bootstrapStatus,
          });
          return bootstrapStatus;
        }

        if (!bootstrapStatus.isIntegrityOk) {
          this.updateState({
            authState: 'recovery',
            providers,
            lastUser,
            bootstrapStatus,
            errorMessage:
              bootstrapStatus.errorMessage ||
              'Storage integrity verification failed.',
          });
          return bootstrapStatus;
        }

        if (bootstrapStatus.activeSession) {
          this.updateState({
            authState: 'authenticated',
            session: bootstrapStatus.activeSession,
            providers,
            lastUser,
            bootstrapStatus,
          });
        } else {
          this.updateState({
            authState: 'unauthenticated',
            providers,
            lastUser,
            bootstrapStatus,
          });
        }

        return bootstrapStatus;
      } catch (err: unknown) {
        console.warn(
          'Initialization running in web preview fallback mode:',
          err
        );
        this.initialized = true;

        // In web preview fallback mode, provide seamless development defaults
        const fallbackProviders: AuthProviderInfo[] = [
          {
            id: 'local',
            name: 'Local Account',
            providerType: 'local',
            supportsMfa: true,
            supportsPasswordReset: true,
            supportsRememberDevice: true,
            supportsAutoLogin: false,
            supportsSso: false,
            supportsOfflineLogin: true,
            isSelectable: true,
          },
        ];

        const fallbackStatus: BootstrapStatus = {
          isWorkspaceConfigured: true,
          isIntegrityOk: true,
          activeSession: null,
          lastUsername: 'administrator',
          lastDisplayName: 'System Administrator',
          errorMessage: null,
        };

        this.updateState({
          authState: 'unauthenticated',
          providers: fallbackProviders,
          lastUser: {
            username: 'administrator',
            displayName: 'System Administrator',
            avatarInitials: 'SA',
          },
          bootstrapStatus: fallbackStatus,
          errorMessage: null,
        });

        return fallbackStatus;
      } finally {
        this.initPromise = null;
      }
    })();

    return this.initPromise;
  }

  public async login(
    username: string,
    password: string,
    rememberDevice: boolean
  ): Promise<void> {
    this.updateState({ errorMessage: null });
    try {
      const response = await ipcService.authenticateUser(
        username,
        password,
        rememberDevice
      );
      this.updateState({
        authState: 'authenticated',
        session: response.session,
        lastUser: {
          username: response.session.username,
          displayName: response.session.displayName,
          avatarInitials: response.session.displayName
            .split(' ')
            .map((n) => n[0])
            .join('')
            .toUpperCase(),
        },
      });
    } catch (err: unknown) {
      const msg =
        typeof err === 'string'
          ? err
          : err instanceof Error
          ? err.message
          : 'Invalid credentials.';
      this.updateState({ errorMessage: msg });
      throw new Error(msg);
    }
  }

  public async logout(): Promise<void> {
    if (this.state.session) {
      try {
        await ipcService.logoutSession(this.state.session.sessionId);
      } catch (err) {
        console.warn('Logout IPC notification warning:', err);
      }
    }
    this.updateState({
      authState: 'unauthenticated',
      session: null,
      errorMessage: null,
    });
  }

  public async lockSession(): Promise<void> {
    if (this.state.session) {
      try {
        await ipcService.lockSession(this.state.session.sessionId);
      } catch (err) {
        console.warn('Lock IPC error:', err);
      }
      this.updateState({
        authState: 'locked',
        session: this.state.session
          ? { ...this.state.session, isLocked: true }
          : null,
      });
    }
  }

  public async unlockSession(password: string): Promise<void> {
    if (!this.state.session) return;

    try {
      const session = await ipcService.unlockSession(
        this.state.session.sessionId,
        password
      );
      this.updateState({
        authState: 'authenticated',
        session,
        errorMessage: null,
      });
    } catch (err: unknown) {
      const msg = typeof err === 'string' ? err : 'Invalid password.';
      this.updateState({ errorMessage: msg });
      throw new Error(msg);
    }
  }

  public triggerRecovery(errorMessage: string) {
    this.updateState({
      authState: 'recovery',
      errorMessage,
      session: null,
    });
  }

  private startHeartbeat() {
    if (typeof window === 'undefined') return;

    this._heartbeatTimer = window.setInterval(async () => {
      if (this.state.authState === 'authenticated' && this.state.session) {
        try {
          const session = await ipcService.validateSession(
            this.state.session.sessionId
          );
          this.updateState({ session });
        } catch (err: unknown) {
          const msg =
            typeof err === 'string' ? err : 'Session expired or invalidated.';
          if (msg.includes('locked')) {
            this.updateState({ authState: 'locked' });
          } else {
            this.triggerRecovery(msg);
          }
        }
      }
    }, 30000); // 30-second session heartbeat check
  }
}

export const authenticationManager = new AuthenticationManager();
