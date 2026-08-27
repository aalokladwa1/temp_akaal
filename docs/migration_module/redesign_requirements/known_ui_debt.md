# Known UI Technical Debt Inventory

**Phase Baseline:** P1.5

---

## 1. Mission Control Interface

- **Visual Density:** Cards and stage steps use high vertical padding; future multi-table DAG displays will require compact grid layout.
- **Oracle / PostgreSQL Text Assumptions:** Certain static strings in early wizard sub-steps reference Oracle or PostgreSQL specifically.
- **CDC / Cutover Control Slots:** Currently lacks native UI action buttons for CDC catch-up pause or Cutover traffic flip.

---

## 2. Monitoring Module Interface

- **Tab Separation:** 6 separate tabs require manual clicking to inspect metrics; future redesign will provide a customizable single-page grid layout option.
- **Historical vs Live Indicator:** Mode badge is prominent, but time-series charts for historical runs are disabled (as required). Future redesign will include persisted snapshot history charts.
