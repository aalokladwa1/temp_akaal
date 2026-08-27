# AKAAL Clean Design Constitution (v1.0)
## Canonical UI/UX & Spatial Design Principles

**Document Version:** 1.0
**Classification:** Authoritative UI/UX Design Law
**Target Applications:** `akaalUI/` (Tauri Desktop, Enterprise Web Control Plane)

---

## The 15 Immutable Clean Design Laws

1. **Deliberate Visual Home:** Every meaningful piece of information gets a deliberate visual home (a clean card, panel, table row, or bounded section). No text or metrics float randomly in space.
2. **Minimal, Not Empty:** Remove purely decorative elements that do not improve operator comprehension.
3. **Card-Based, Not Card Spam:** Related information shares a single unified card. Never nest separate rectangular boxes for individual label/value pairs.
4. **Strict Spatial Hierarchy:** $\text{Page} \longrightarrow \text{Section} \longrightarrow \text{Card} \longrightarrow \text{Content} \longrightarrow \text{Secondary Metadata}$.
5. **Generous Breathing Room:** Maintain 16px/24px padding and 8px spacing rhythm so dense database configurations never feel cramped.
6. **Consistent Geometry:** Standardize on the 8px/12px border radius family, 1px subtle borders, and unified drop-shadow elevations across all views.
7. **Subtle Surfaces:** Restrained 1px borders (`--border-subtle`), subtle glassmorphism (`backdrop-filter: blur(12px)`), and low-contrast surface elevation layers.
8. **Color Has Semantic Meaning:** Primary accent (`--accent-primary`) is reserved strictly for active selections and primary interactions. Green, amber, red, and cyan are reserved strictly for system health, warnings, blockers, and diagnostics.
9. **One Obvious Primary Action:** Exactly one prominent primary action per screen/context. Secondary actions are muted or ghosted.
10. **Progressive Disclosure:** Advanced engine knobs, CDC tuning parameters, and SQL hooks stay collapsed until explicitly requested.
11. **High-Density Data Stays Clean:** Tabular figures (via `JetBrains Mono`), virtualized tables, and DAG nodes remain calm, readable, and aligned.
12. **No Dashboard Carnival:** Avoid 25 equally weighted squares. Anchor the view with 1–2 dominant primary telemetry panels while supporting metrics remain compact and quiet.
13. **Restrained Motion:** Transitions operate strictly within 150–250ms ease-out curves to communicate state transitions, never for decorative distraction.
14. **Icons Support Text:** Every action icon is accompanied by a descriptive label or explicit tooltip. No icon-only guesswork.
15. **Consistency Beats Novelty:** Establish reusable, predictable component patterns and apply them uniformly across every single screen.
