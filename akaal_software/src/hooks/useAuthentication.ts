import { useState, useEffect, useCallback } from 'react';
import {
  authenticationManager,
  type AuthManagerState,
} from '../services/authenticationManager';

export function useAuthentication() {
  const [state, setState] = useState<AuthManagerState>(() =>
    authenticationManager.getState()
  );

  useEffect(() => {
    const unsubscribe = authenticationManager.subscribe((newState) => {
      setState(newState);
    });
    return unsubscribe;
  }, []);

  const login = useCallback(
    async (username: string, password: string, rememberDevice: boolean) => {
      await authenticationManager.login(username, password, rememberDevice);
    },
    []
  );

  const logout = useCallback(async () => {
    await authenticationManager.logout();
  }, []);

  return {
    authState: state.authState,
    session: state.session,
    lastUser: state.lastUser,
    providers: state.providers,
    errorMessage: state.errorMessage,
    isAuthenticated: state.authState === 'authenticated',
    login,
    logout,
  };
}
