import { useCallback, type FC } from 'react';
import type { WorkspaceConfig } from '../../types/workspace';
import { Dashboard } from './Dashboard';
import { NotificationToastContainer } from '../../components/Notifications/NotificationToast';
import { useAuthentication } from '../../hooks/useAuthentication';

export interface WorkspaceHomeProps {
  config: WorkspaceConfig;
  onSignOut?: () => void;
}

export const WorkspaceHome: FC<WorkspaceHomeProps> = ({ config, onSignOut }) => {
  const { logout } = useAuthentication();

  const handleSignOut = useCallback(async () => {
    await logout();
    if (onSignOut) {
      onSignOut();
    }
  }, [logout, onSignOut]);

  const handleNavigate = useCallback((section: string) => {
    // Navigation router hook for future Sprint 4 modules
    console.log(`[AKAAL Navigation] Switched section: ${section}`);
  }, []);

  return (
    <>
      <Dashboard
        config={config}
        onSignOut={handleSignOut}
        onNavigate={handleNavigate}
      />
      <NotificationToastContainer />
    </>
  );
};
