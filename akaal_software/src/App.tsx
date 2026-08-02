import React from "react";
import { WelcomeScreen } from "./screens/WelcomeScreen";

export function App() {
  const handleStartSetup = () => {
    // Stopped per Sprint 1 scope
  };

  const handleExit = async (e?: React.MouseEvent) => {
    if (e && typeof e.preventDefault === "function") {
      e.preventDefault();
    }

    // 1. Primary Tauri API Window Destroy (Instant Unconditional Termination)
    try {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      const appWindow = getCurrentWindow();
      await appWindow.destroy();
      return;
    } catch (err) {
      console.warn("Tauri getCurrentWindow().destroy() call bypassed/failed:", err);
    }

    // 2. Secondary Tauri API Window Close
    try {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      const appWindow = getCurrentWindow();
      await appWindow.close();
      return;
    } catch (err) {
      console.warn("Tauri getCurrentWindow().close() call bypassed/failed:", err);
    }

    // 3. Custom Rust IPC Command (Explicit parameterless call)
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("exit_app");
      return;
    } catch (err) {
      console.warn("Tauri invoke('exit_app') failed:", err);
    }

    // 4. Fallback for non-Tauri browser context
    if (typeof window !== "undefined") {
      window.close();
    }
  };

  return <WelcomeScreen onStartSetup={handleStartSetup} onExit={handleExit} />;
}

export default App;
