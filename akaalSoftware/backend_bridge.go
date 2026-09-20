package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"syscall"
)

// startBackendBridge launches the canonical akaalIPC desktop transport bridge
// (akaalIPC/transport/tcp_socket_host.py, bound to a real PipelineUnifiedCaller
// via akaalPipeline/api/desktop_ipc_bridge.py) as a child process, so a
// packaged desktop build does not require an operator to manually run it.
//
// This is a generic, domain-agnostic lifecycle binding -- it knows nothing
// about Monitoring, Dashboard, Migration, Reports, Administration, or
// Settings. It is the smallest production-correct shared solution: reusing
// the EXISTING Wails OnStartup/OnShutdown application lifecycle (main.go)
// already bound to app.startup/app.shutdown, rather than inventing a new
// launcher, a .bat script, or routing through legacy akaal/.
func startBackendBridge() (*exec.Cmd, error) {
	repoRoot, err := findRepoRoot()
	if err != nil {
		return nil, err
	}

	pythonCmd, pythonArgs := resolvePythonInterpreter(repoRoot)

	cmd := exec.Command(pythonCmd, append(pythonArgs, "-m", "akaalPipeline.api.desktop_ipc_bridge")...)
	cmd.Dir = repoRoot
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if runtime.GOOS == "windows" {
		cmd.SysProcAttr = &syscall.SysProcAttr{
			HideWindow:    true,
			CreationFlags: 0x08000000, // CREATE_NO_WINDOW
		}
	}

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to start canonical akaalIPC desktop bridge: %w", err)
	}
	return cmd, nil
}

// stopBackendBridge terminates the bridge process started by startBackendBridge.
// Mirrors app.shutdown's existing principle: UI lifecycle is decoupled from
// migration execution lifecycle -- this only stops the local transport bridge,
// never any running migration/engine work, which is owned by the canonical
// backend authorities themselves, not by this desktop process.
func stopBackendBridge(cmd *exec.Cmd) {
	if cmd == nil || cmd.Process == nil {
		return
	}
	_ = cmd.Process.Kill()
	_, _ = cmd.Process.Wait()
}

// findRepoRoot locates the repository root (the directory containing both
// akaalSoftware/ and akaalPipeline/) by walking up from the current working
// directory. This avoids hardcoding a path, since the Wails binary's working
// directory differs between `wails dev` and a packaged build.
func findRepoRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for i := 0; i < 6; i++ {
		if isRepoRoot(dir) {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("could not locate repository root (akaalPipeline/ + akaalSoftware/) from working directory")
}

func isRepoRoot(dir string) bool {
	pipelineInfo, err1 := os.Stat(filepath.Join(dir, "akaalPipeline"))
	softwareInfo, err2 := os.Stat(filepath.Join(dir, "akaalSoftware"))
	return err1 == nil && pipelineInfo.IsDir() && err2 == nil && softwareInfo.IsDir()
}

// resolvePythonInterpreter prefers the repository's own virtual environment
// (the same interpreter used by tests/pytest.ini) over a bare "python"/"py"
// PATH lookup, so the bridge runs with its real dependencies (fastapi, etc.)
// installed. Prefers pythonw.exe on Windows to prevent terminal window popups.
// Returns the interpreter command plus any leading arguments needed to invoke it.
// On Windows, bare "python"/"pythonw" on PATH can resolve to the Microsoft Store's
// App Execution Alias stub (present even with no real Python installed), which exits
// immediately without running anything -- silently killing the backend bridge.
// The "py" launcher is a real executable, not an alias stub, and reliably finds the
// actual installed interpreter, so it is preferred over a bare "pythonw" guess.
func resolvePythonInterpreter(repoRoot string) (string, []string) {
	if runtime.GOOS == "windows" {
		venvPythonW := filepath.Join(repoRoot, ".venv", "Scripts", "pythonw.exe")
		if info, err := os.Stat(venvPythonW); err == nil && !info.IsDir() {
			return venvPythonW, nil
		}
		venvPython := filepath.Join(repoRoot, ".venv", "Scripts", "python.exe")
		if info, err := os.Stat(venvPython); err == nil && !info.IsDir() {
			return venvPython, nil
		}
		if pyLauncher, err := exec.LookPath("py"); err == nil {
			return pyLauncher, []string{"-3"}
		}
		return "pythonw", nil
	}

	venvPython := filepath.Join(repoRoot, ".venv", "bin", "python")
	if info, err := os.Stat(venvPython); err == nil && !info.IsDir() {
		return venvPython, nil
	}
	return "python3", nil
}

