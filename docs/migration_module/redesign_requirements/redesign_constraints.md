# Architectural & UX Redesign Constraints

**Phase Baseline:** P1.5  

---

## Non-Negotiable Redesign Constraints

1. **Desktop-First Application:** Tauri + React + TypeScript stack.
2. **Dual Theme Compliance:** Full support for Enterprise Blue Light Theme (`.app-theme-light`) and Midnight Glass Dark Theme (`.app-theme-dark`).
3. **Backend Authority Rule:** Zero frontend state machine logic; 100% driven by `EngineGateway` and `CentralStateStore`.
4. **Data Integrity & Security:** Primary key high-water-marks and DB password handles must remain redacted over IPC.
5. **Fail-Closed Governance:** Destructive operations abort unless `GATE 1`, `GATE 2`, or `GATE 3` multi-custody approvals are verified.
