import { useState, useEffect } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { WelcomeScreen } from "./screens/WelcomeScreen";
import { SetupWizardScreen } from "./screens/SetupWizardScreen";
import { WorkspaceHome } from "./screens/WorkspaceHome";
import { workspaceConfigurationService } from "./services/workspaceConfigurationService";
import type { WorkspaceConfig } from "./types/workspace";

export type ScreenState = "loading" | "welcome" | "wizard" | "home";

export function App() {
  const [screenState, setScreenState] = useState<ScreenState>("loading");
  const [activeConfig, setActiveConfig] = useState<WorkspaceConfig | null>(null);

  useEffect(() => {
    async function initAppConfig() {
      try {
        const loaded = await workspaceConfigurationService.load();
        setActiveConfig(loaded);
        if (loaded.onboardingCompleted && loaded.workspacePath) {
          setScreenState("home");
        } else {
          setScreenState("welcome");
        }
      } catch (err) {
        console.warn("Failed to load workspace config during app init:", err);
        setScreenState("welcome");
      }
    }
    initAppConfig();
  }, []);

  const handleStartSetup = () => {
    setScreenState("wizard");
  };

  const handleLaunchWorkspace = (config: WorkspaceConfig) => {
    setActiveConfig(config);
    setScreenState("home");
  };

  const handleExit = async (e?: React.MouseEvent) => {
    if (e && typeof e.preventDefault === "function") {
      e.preventDefault();
    }

    try {
      const appWindow = getCurrentWindow();
      await appWindow.destroy();
      return;
    } catch {
      try {
        const appWindow = getCurrentWindow();
        await appWindow.close();
        return;
      } catch {
        try {
          const { invoke } = await import("@tauri-apps/api/core");
          await invoke("exit_app");
          return;
        } catch {
          if (typeof window !== "undefined") {
            window.close();
          }
        }
      }
    }
  };

  if (screenState === "loading") {
    return (
      <div style={{ width: "100vw", height: "100vh", backgroundColor: "#0B0D11" }} />
    );
  }

  if (screenState === "home" && activeConfig) {
    return <WorkspaceHome config={activeConfig} />;
  }

  if (screenState === "wizard") {
    return (
      <SetupWizardScreen
        initialConfig={activeConfig || undefined}
        onLaunchWorkspace={handleLaunchWorkspace}
      />
    );
  }

  return <WelcomeScreen onStartSetup={handleStartSetup} onExit={handleExit} />;
}

export default App;
