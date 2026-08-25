import { useState, useEffect, useCallback } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { SplashScreen } from './screens/SplashScreen/SplashScreen';
import { WelcomeScreen } from './screens/WelcomeScreen';
import { SetupWizardScreen } from './screens/SetupWizardScreen';
import { AuthScreen } from './screens/AuthScreen';
import { RecoveryScreen } from './screens/RecoveryScreen';
import { WorkspaceHome } from './screens/WorkspaceHome';
import { useAuthentication } from './hooks/useAuthentication';
import { authenticationManager } from './services/authenticationManager';
import { workspaceConfigurationService } from './services/workspaceConfigurationService';
import type { WorkspaceConfig } from './types/workspace';

export type AppScreenState =
  | 'splash'
  | 'welcome'
  | 'wizard'
  | 'auth'
  | 'recovery'
  | 'home';

export function App() {
  const [screenState, setScreenState] = useState<AppScreenState>('splash');
  const [activeConfig, setActiveConfig] = useState<WorkspaceConfig | null>(null);
  const { authState, session, errorMessage } = useAuthentication();

  useEffect(() => {
    async function loadConfig() {
      try {
        const loaded = await workspaceConfigurationService.load();
        setActiveConfig(loaded);
      } catch (err) {
        console.warn('Failed to load initial workspace configuration:', err);
      }
    }
    loadConfig();
  }, []);

  // React to AuthenticationManager state updates when not in splash
  useEffect(() => {
    if (screenState === 'splash') return; // Wait for splash sequence completion
    if (screenState === 'wizard') return; // User has entered the wizard — do not override

    let target: AppScreenState | null = null;
    if (authState === 'setup_required') {
      target = 'welcome';
    } else if (authState === 'recovery') {
      target = 'recovery';
    } else if (authState === 'unauthenticated' || authState === 'locked') {
      target = 'auth';
    } else if (authState === 'authenticated') {
      // Reload config fresh on authentication to pick up ownerDisplayName
      workspaceConfigurationService.load().then((cfg) => setActiveConfig(cfg)).catch(() => {});
      target = 'home';
    }

    if (target && target !== screenState) {
      setScreenState(target);
    }
  }, [authState, screenState]);

  const handleSplashComplete = useCallback(() => {
    const currentAuthState = authenticationManager.getState().authState;
    if (currentAuthState === 'setup_required') {
      setScreenState('welcome');
    } else if (currentAuthState === 'recovery') {
      setScreenState('recovery');
    } else if (currentAuthState === 'authenticated') {
      setScreenState('home');
    } else {
      setScreenState('auth');
    }
  }, []);

  const handleStartSetup = useCallback(() => {
    setScreenState('wizard');
  }, []);

  const handleLaunchWorkspace = useCallback(async (config: WorkspaceConfig) => {
    setActiveConfig(config);
    setScreenState('auth');
  }, []);

  const handleExit = async (e?: React.MouseEvent) => {
    if (e && typeof e.preventDefault === 'function') {
      e.preventDefault();
    }
    try {
      const appWindow = getCurrentWindow();
      await appWindow.destroy();
    } catch {
      try {
        const appWindow = getCurrentWindow();
        await appWindow.close();
      } catch {
        if (typeof window !== 'undefined') {
          window.close();
        }
      }
    }
  };

  // 1. Splash Screen Bootstrapper
  if (screenState === 'splash') {
    return <SplashScreen onComplete={handleSplashComplete} />;
  }

  // 2. Recovery Screen
  if (screenState === 'recovery') {
    return (
      <RecoveryScreen
        message={errorMessage}
        onAuthenticateAgain={() => setScreenState('auth')}
        onReconfigureWorkspace={() => setScreenState('wizard')}
      />
    );
  }

  // 3. Welcome Onboarding Screen (Sprint 1)
  if (screenState === 'welcome') {
    return <WelcomeScreen onStartSetup={handleStartSetup} onExit={handleExit} />;
  }

  // 4. Workspace Setup Wizard (Sprint 2)
  if (screenState === 'wizard') {
    return (
      <SetupWizardScreen
        initialConfig={activeConfig || undefined}
        onLaunchWorkspace={handleLaunchWorkspace}
      />
    );
  }

  // 5. Authentication Screen (Sprint 3)
  if (screenState === 'auth' || !session) {
    return <AuthScreen />;
  }

  // 6. Application Home
  return (
    <WorkspaceHome
      config={
        activeConfig || {
          schemaVersion: 1,
          workspaceName: session.displayName || 'Workspace',
          workspacePath: 'C:\\AKAAL_Workspace',
          theme: 'light',
          onboardingCompleted: true,
        }
      }
    />
  );
}

export default App;
