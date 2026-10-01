package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	wailsRuntime "github.com/wailsapp/wails/v2/pkg/runtime"
)

type AutomationDriver struct {
	app        *App
	server     *http.Server
	listener   net.Listener
	mu         sync.Mutex
	pendingMu  sync.Mutex
	pending    map[string]chan automationEvalResult
	reqCounter uint64
}

type automationEvalResult struct {
	ReqID   string      `json:"reqId"`
	Success bool        `json:"success"`
	Result  interface{} `json:"result,omitempty"`
	Error   string      `json:"error,omitempty"`
}

var globalAutomationDriver *AutomationDriver

func (a *App) startAutomationDriver() {
	portStr := os.Getenv("DEVKROS_ACCEPTANCE_PORT")
	if portStr == "" {
		for _, arg := range os.Args {
			if strings.HasPrefix(arg, "--acceptance-port=") {
				portStr = strings.TrimPrefix(arg, "--acceptance-port=")
				break
			}
		}
	}

	if portStr == "" {
		// Acceptance driver inactive in standard non-acceptance execution
		return
	}

	port, err := strconv.Atoi(portStr)
	if err != nil || port <= 0 {
		port = 9244
	}

	driver := &AutomationDriver{
		app:     a,
		pending: make(map[string]chan automationEvalResult),
	}
	globalAutomationDriver = driver

	// Register result event listener from Wails WebView
	wailsRuntime.EventsOn(a.ctx, "akaal:automation:result", func(optionalData ...interface{}) {
		if len(optionalData) == 0 {
			return
		}
		dataBytes, err := json.Marshal(optionalData[0])
		if err != nil {
			return
		}
		var res automationEvalResult
		if err := json.Unmarshal(dataBytes, &res); err != nil {
			return
		}

		driver.pendingMu.Lock()
		ch, exists := driver.pending[res.ReqID]
		if exists {
			delete(driver.pending, res.ReqID)
			ch <- res
		}
		driver.pendingMu.Unlock()
	})

	mux := http.NewServeMux()
	mux.HandleFunc("/attest", driver.handleAttest)
	mux.HandleFunc("/eval", driver.handleEval)
	mux.HandleFunc("/gesture", driver.handleGesture)
	mux.HandleFunc("/dom_query", driver.handleDomQuery)

	addr := fmt.Sprintf("127.0.0.1:%d", port)
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		fmt.Printf("[Acceptance Automation Driver] Failed to bind %s: %v\n", addr, err)
		return
	}

	driver.listener = ln
	driver.server = &http.Server{Handler: mux}

	fmt.Printf("[Acceptance Automation Driver] Listening for operator-equivalent automation on http://%s\n", addr)
	go func() {
		if err := driver.server.Serve(ln); err != nil && err != http.ErrServerClosed {
			fmt.Printf("[Acceptance Automation Driver] Server terminated: %v\n", err)
		}
	}()
}

func (a *App) stopAutomationDriver() {
	if globalAutomationDriver != nil && globalAutomationDriver.server != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		_ = globalAutomationDriver.server.Shutdown(ctx)
		globalAutomationDriver = nil
	}
}

func (d *AutomationDriver) handleAttest(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"status":      "PASS",
		"app":         "DevKros Enterprise Platform",
		"runtime":     "wails-v2",
		"aut":         "AKAAL.exe",
		"pid":         os.Getpid(),
		"wailsBridge": true,
		"timestamp":   time.Now().UTC().Format(time.RFC3339),
	})
}

type evalRequestBody struct {
	Script  string `json:"script"`
	Timeout int    `json:"timeoutMs,omitempty"`
}

func (d *AutomationDriver) handleEval(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var body evalRequestBody
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	timeoutMs := body.Timeout
	if timeoutMs <= 0 {
		timeoutMs = 15000
	}

	res, err := d.executeScript(body.Script, time.Duration(timeoutMs)*time.Millisecond)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(res)
}

type gestureRequestBody struct {
	Action   string `json:"action"` // "click", "fill", "select", "check_text"
	Selector string `json:"selector"`
	Value    string `json:"value,omitempty"`
	Timeout  int    `json:"timeoutMs,omitempty"`
}

func (d *AutomationDriver) handleGesture(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var body gestureRequestBody
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	timeoutMs := body.Timeout
	if timeoutMs <= 0 {
		timeoutMs = 15000
	}

	selBytes, _ := json.Marshal(body.Selector)
	valBytes, _ := json.Marshal(body.Value)
	selJSON := string(selBytes)
	valJSON := string(valBytes)

	helperJS := `
		function findElement(selectorList) {
			const parts = selectorList.split(',').map(s => s.trim()).filter(Boolean);
			for (const sel of parts) {
				if (sel.includes(':has-text(')) {
					const match = sel.match(/^(.*?):has-text\((["']?)(.*?)\2\)$/);
					if (match) {
						const tag = match[1] || '*';
						const text = match[3].trim();
						const candidates = Array.from(document.querySelectorAll(tag));
						const matched = candidates.filter(el => (el.innerText || el.textContent || '').includes(text));
						if (matched.length > 0) {
							matched.sort((a, b) => (a.innerText || a.textContent || '').length - (b.innerText || b.textContent || '').length);
							return matched[0];
						}
					}
				}
				if (sel.startsWith('text=')) {
					const text = sel.slice(5).replace(/^["']|["']$/g, '').trim();
					const candidates = Array.from(document.querySelectorAll('a, button, [role="button"], input, select, label, span, p, h1, h2, h3, div'));
					const matched = candidates.filter(el => {
						const t = (el.innerText || el.textContent || '').trim();
						return t === text || (t.includes(text) && t.length < text.length + 30);
					});
					if (matched.length > 0) {
						matched.sort((a, b) => (a.innerText || a.textContent || '').length - (b.innerText || b.textContent || '').length);
						return matched[0];
					}
				}
				try {
					const el = document.querySelector(sel);
					if (el) return el;
				} catch (e) {}
			}
			return null;
		}
	`

	var jsCode string
	switch body.Action {
	case "click":
		jsCode = fmt.Sprintf(`(() => {
			%s
			const targetSel = %s;
			const el = findElement(targetSel);
			if (!el) throw new Error("Element not found: " + targetSel);
			el.scrollIntoView({ behavior: 'instant', block: 'center' });
			el.click();
			return true;
		})()`, helperJS, selJSON)

	case "fill":
		jsCode = fmt.Sprintf(`(() => {
			%s
			const targetSel = %s;
			const targetVal = %s;
			const el = findElement(targetSel);
			if (!el) throw new Error("Input element not found: " + targetSel);
			el.focus();
			el.value = targetVal;
			el.dispatchEvent(new Event('input', { bubbles: true }));
			el.dispatchEvent(new Event('change', { bubbles: true }));
			el.blur();
			return el.value;
		})()`, helperJS, selJSON, valJSON)

	case "select":
		jsCode = fmt.Sprintf(`(() => {
			%s
			const targetSel = %s;
			const targetVal = %s;
			const el = findElement(targetSel);
			if (!el) throw new Error("Select element not found: " + targetSel);
			el.value = targetVal;
			el.dispatchEvent(new Event('change', { bubbles: true }));
			return el.value;
		})()`, helperJS, selJSON, valJSON)

	case "text":
		jsCode = fmt.Sprintf(`(() => {
			%s
			const targetSel = %s;
			const el = findElement(targetSel);
			if (!el) return null;
			return el.innerText || el.textContent || '';
		})()`, helperJS, selJSON)

	case "exists":
		jsCode = fmt.Sprintf(`(() => {
			%s
			const targetSel = %s;
			const el = findElement(targetSel);
			return !!el;
		})()`, helperJS, selJSON)

	default:
		http.Error(w, "Unsupported gesture action: "+body.Action, http.StatusBadRequest)
		return
	}

	res, err := d.executeScript(jsCode, time.Duration(timeoutMs)*time.Millisecond)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(res)
}

func (d *AutomationDriver) handleDomQuery(w http.ResponseWriter, r *http.Request) {
	selector := r.URL.Query().Get("selector")
	if selector == "" {
		http.Error(w, "Missing selector query param", http.StatusBadRequest)
		return
	}

	selBytes, _ := json.Marshal(selector)
	selJSON := string(selBytes)

	jsCode := fmt.Sprintf(`(() => {
		function findElements(selectorList) {
			const parts = selectorList.split(',').map(s => s.trim()).filter(Boolean);
			for (const sel of parts) {
				if (sel.includes(':has-text(')) {
					const match = sel.match(/^(.*?):has-text\((["']?)(.*?)\2\)$/);
					if (match) {
						const tag = match[1] || '*';
						const text = match[3].trim();
						const candidates = Array.from(document.querySelectorAll(tag));
						const matched = candidates.filter(el => (el.innerText || el.textContent || '').includes(text));
						if (matched.length > 0) return matched;
					}
				}
				if (sel.startsWith('text=')) {
					const text = sel.slice(5).replace(/^["']|["']$/g, '').trim();
					const candidates = Array.from(document.querySelectorAll('a, button, [role="button"], input, select, label, span, p, h1, h2, h3, div'));
					const matched = candidates.filter(el => {
						const t = (el.innerText || el.textContent || '').trim();
						return t === text || (t.includes(text) && t.length < text.length + 30);
					});
					if (matched.length > 0) return matched;
				}
				try {
					const els = Array.from(document.querySelectorAll(sel));
					if (els.length > 0) return els;
				} catch (e) {}
			}
			return [];
		}
		const elements = findElements(%s);
		return elements.map(el => ({
			tagName: el.tagName,
			id: el.id,
			className: el.className,
			text: (el.innerText || el.textContent || '').trim(),
			value: el.value !== undefined ? el.value : null,
			disabled: !!el.disabled,
			visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
		}));
	})()`, selJSON)

	res, err := d.executeScript(jsCode, 10*time.Second)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(res)
}

func (d *AutomationDriver) executeScript(script string, timeout time.Duration) (automationEvalResult, error) {
	d.mu.Lock()
	d.reqCounter++
	reqID := fmt.Sprintf("req_%d_%d", time.Now().UnixNano(), d.reqCounter)
	d.mu.Unlock()

	ch := make(chan automationEvalResult, 1)

	d.pendingMu.Lock()
	d.pending[reqID] = ch
	d.pendingMu.Unlock()

	defer func() {
		d.pendingMu.Lock()
		delete(d.pending, reqID)
		d.pendingMu.Unlock()
	}()

	wrappedJS := fmt.Sprintf(`
(function() {
	try {
		const val = (function() { return %s; })();
		if (val && typeof val.then === 'function') {
			val.then(resolved => {
				if (window.runtime && window.runtime.EventsEmit) {
					window.runtime.EventsEmit('akaal:automation:result', { reqId: '%s', success: true, result: resolved });
				}
			}).catch(rejected => {
				if (window.runtime && window.runtime.EventsEmit) {
					window.runtime.EventsEmit('akaal:automation:result', { reqId: '%s', success: false, error: String(rejected) });
				}
			});
		} else {
			if (window.runtime && window.runtime.EventsEmit) {
				window.runtime.EventsEmit('akaal:automation:result', { reqId: '%s', success: true, result: val });
			}
		}
	} catch (err) {
		if (window.runtime && window.runtime.EventsEmit) {
			window.runtime.EventsEmit('akaal:automation:result', { reqId: '%s', success: false, error: err.message || String(err) });
		}
	}
})();
`, script, reqID, reqID, reqID, reqID)

	wailsRuntime.WindowExecJS(d.app.ctx, wrappedJS)

	select {
	case res := <-ch:
		if !res.Success {
			return res, fmt.Errorf("DOM execution error: %s", res.Error)
		}
		return res, nil
	case <-time.After(timeout):
		return automationEvalResult{ReqID: reqID, Success: false, Error: "TIMEOUT"}, fmt.Errorf("DOM execution timed out after %v", timeout)
	}
}
