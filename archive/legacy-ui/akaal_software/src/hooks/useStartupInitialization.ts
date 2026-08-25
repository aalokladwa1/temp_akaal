import { useState, useEffect, useCallback } from 'react';
import {
  authenticationManager,
  type AuthManagerState,
} from '../services/authenticationManager';

export function useStartupInitialization() {
  const [state, setState] = useState<AuthManagerState>(() =>
    authenticationManager.getState()
  );

  useEffect(() => {
    const unsubscribe = authenticationManager.subscribe((newState) => {
      setState(newState);
    });
    return unsubscribe;
  }, []);

  const initialize = useCallback(async () => {
    return await authenticationManager.initialize();
  }, []);

  return {
    authState: state.authState,
    bootstrapStatus: state.bootstrapStatus,
    errorMessage: state.errorMessage,
    isBootstrapping: state.authState === 'bootstrapping',
    initialize,
  };
}
