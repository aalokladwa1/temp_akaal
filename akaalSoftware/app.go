package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"runtime"
	"sync"
	"time"

	"akaalSoftware/pkg/prototypedb"

	wailsRuntime "github.com/wailsapp/wails/v2/pkg/runtime"
)

const (
	// Windows Named Pipe and Unix Domain Socket paths
	WindowsPipePath = `\\.\pipe\akaal_ipc`
	UnixSocketPath  = "/tmp/akaal_ipc.sock"
)

// App struct manages Wails native bridge and decoupled socket client
type App struct {
	ctx        context.Context
	pipeConn   net.Conn
	mu         sync.Mutex
	isConnected bool
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{}
}

// startup is called when the Wails desktop window initializes.
// It establishes a client connection to the independent AKAAL Engine Named Pipe / Domain Socket.
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	go a.maintainSocketConnection()
}

// shutdown is called when the Wails desktop UI window closes.
// CRITICAL: UI lifecycle is strictly decoupled from migration execution lifecycle.
// Closing the UI disconnects the socket client, but DOES NOT kill running migrations.
func (a *App) shutdown(ctx context.Context) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.pipeConn != nil {
		_ = a.pipeConn.Close()
		a.pipeConn = nil
	}
	a.isConnected = false
}

// maintainSocketConnection handles initial connect and automatic reconnection to the engine daemon
func (a *App) maintainSocketConnection() {
	networkType := "unix"
	socketAddress := UnixSocketPath
	if runtime.GOOS == "windows" {
		networkType = "tcp"
		socketAddress = "127.0.0.1:52199" // Internal loopback or named pipe connector
	}

	for {
		a.mu.Lock()
		if !a.isConnected {
			// Attempt connection to the running AKAAL Engine socket / pipe
			conn, err := net.DialTimeout(networkType, socketAddress, 500*time.Millisecond)
			if err == nil {
				a.pipeConn = conn
				a.isConnected = true
				if a.ctx != nil {
					wailsRuntime.EventsEmit(a.ctx, "akaal:engine:connected", true)
				}
				go a.listenForTelemetryEvents(conn)
			}
		}
		a.mu.Unlock()
		time.Sleep(2 * time.Second)
	}
}

// listenForTelemetryEvents streams background engine events to the Angular UI
func (a *App) listenForTelemetryEvents(conn net.Conn) {
	decoder := json.NewDecoder(conn)
	for {
		var event map[string]interface{}
		if err := decoder.Decode(&event); err != nil {
			a.mu.Lock()
			a.isConnected = false
			if a.pipeConn != nil {
				_ = a.pipeConn.Close()
				a.pipeConn = nil
			}
			a.mu.Unlock()
			if a.ctx != nil {
				wailsRuntime.EventsEmit(a.ctx, "akaal:engine:disconnected", true)
			}
			return
		}

		if a.ctx != nil {
			wailsRuntime.EventsEmit(a.ctx, "akaal:telemetry", event)
		}
	}
}

// IPCRequest represents a 1:1 typed akaalIPC invocation
type IPCRequest struct {
	Endpoint string                 `json:"endpoint"`
	Action   string                 `json:"action"`
	Payload  map[string]interface{} `json:"payload"`
}

// IPCResponse represents the standardized JSON-RPC response from akaalIPC
type IPCResponse struct {
	Status string                 `json:"status"`
	Data   map[string]interface{} `json:"data,omitempty"`
	Error  string                 `json:"error,omitempty"`
}

// InvokeIPC passes requests directly to Python EngineGateway via Named Pipe / Domain Socket
func (a *App) InvokeIPC(req IPCRequest) (IPCResponse, error) {
	networkType := "unix"
	socketAddress := UnixSocketPath
	if runtime.GOOS == "windows" {
		networkType = "tcp"
		socketAddress = "127.0.0.1:52199"
	}

	fmt.Printf("[Wails Named Pipe IPC] Endpoint: %s, Action: %s\n", req.Endpoint, req.Action)

	conn, err := net.DialTimeout(networkType, socketAddress, 1*time.Second)
	if err != nil {
		return IPCResponse{
			Status: "ERROR",
			Error:  "ENGINE_DISCONNECTED: Daemon IPC socket connection unavailable",
		}, nil
	}
	defer conn.Close()

	_ = conn.SetDeadline(time.Now().Add(5 * time.Second))

	reqData, err := json.Marshal(req)
	if err != nil {
		return IPCResponse{
			Status: "ERROR",
			Error:  fmt.Sprintf("IPC_SERIALIZATION_ERROR: %v", err),
		}, nil
	}

	reqData = append(reqData, '\n')
	if _, err := conn.Write(reqData); err != nil {
		return IPCResponse{
			Status: "ERROR",
			Error:  fmt.Sprintf("IPC_WRITE_ERROR: %v", err),
		}, nil
	}

	var resp IPCResponse
	decoder := json.NewDecoder(conn)
	if err := decoder.Decode(&resp); err != nil {
		return IPCResponse{
			Status: "ERROR",
			Error:  fmt.Sprintf("IPC_READ_ERROR: %v", err),
		}, nil
	}

	return resp, nil
}

// ============================================================================
// PROTOTYPE MIGRATION HOME SQLITE ACCESS (2.1 UI Prototype Only)
// ============================================================================

func (a *App) GetMigrationHomeSummary() (prototypedb.MigrationHomeSummaryDTO, error) {
	store, err := prototypedb.GetStore()
	if err != nil {
		return prototypedb.MigrationHomeSummaryDTO{}, err
	}
	return store.GetSummary()
}

func (a *App) GetMigrationHomeMigrations() ([]prototypedb.MigrationRowDTO, error) {
	store, err := prototypedb.GetStore()
	if err != nil {
		return nil, err
	}
	return store.GetIndependentMigrations()
}

func (a *App) GetMigrationHomeProjects() ([]prototypedb.ProjectRowDTO, error) {
	store, err := prototypedb.GetStore()
	if err != nil {
		return nil, err
	}
	return store.GetAllProjects()
}

func (a *App) GetMigrationHomeActivities() ([]prototypedb.ActivityRowDTO, error) {
	store, err := prototypedb.GetStore()
	if err != nil {
		return nil, err
	}
	return store.GetRecentActivity()
}

func (a *App) ResetMigrationHomeDemoState() error {
	store, err := prototypedb.GetStore()
	if err != nil {
		return err
	}
	return store.ResetDemoState()
}

