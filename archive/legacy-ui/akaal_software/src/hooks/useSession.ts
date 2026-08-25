import { useState, useEffect, useCallback } from 'react';
import {
  authenticationManager,
  type AuthManagerState,
} from '../services/authenticationManager';

export function useSession() {
  const [state, setState] = useState<AuthManagerState>(() =>
    authenticationManager.getState()
  );

  useEffect(() => {
    const unsubscribe = authenticationManager.subscribe((newState) => {
      setState(newState);
    });
    return unsubscribe;
  }, []);

  const lockSession = useCallback(async () => {
    await authenticationManager.lockSession();
  }, []);

  const unlockSession = useCallback(async (password: string) => {
    await authenticationManager.unlockSession(password);
  }, []);

  return {
    session: state.session,
    isLocked: state.authState === 'locked',
    errorMessage: state.errorMessage,
    lockSession,
    unlockSession,
  };
}
