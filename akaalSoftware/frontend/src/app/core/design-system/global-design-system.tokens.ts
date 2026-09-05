/**
 * AKAAL GLOBAL DESIGN SYSTEM SPECIFICATIONS & TOKENS
 * Encapsulated user selections (A, A, A, A, B, A, B, A, B, C, A, C, A, A, B, A, B, A, A, A)
 * 
 * 01. Buttons: [A] Subtle Bordered Enterprise (h-9 px-4 rounded-lg bg-blue-600, secondary bg-white border-slate-200)
 * 02. Badges: [A] Tint Surface with 6px Dot (bg-emerald-50 text-emerald-700, bg-amber-50, bg-rose-50)
 * 03. Dropdowns: [A] Rectangular Framed Popover (h-9 px-3 rounded-lg bg-white border-slate-200 + popover)
 * 04. Inputs: [A] Inset Left Icon + Clear Button (h-9 pl-10 pr-8 rounded-lg bg-white border-slate-200 + clear)
 * 05. Tabs: [B] Segmented Pill Slider (p-1 bg-slate-100 rounded-lg, active white card shadow-2xs)
 * 06. Definitions: [A] Structured 2-Column Grid (grid-cols-[120px_1fr] key: slate-500, value: slate-900 font-mono)
 * 07. Tables: [B] Zebra-Striped Compact Enterprise (table-fixed, alternating bg-slate-50/50, tabular-nums right-align)
 * 08. Workbench: [A] Dynamic Auto-Compressing Split (320px <-> 260px tree, 100% flex table, 380px drawer)
 * 09. Tree: [B] Folder Branch Explorer with Badges (folder tree icons, visual connecting branch lines, count pill tags)
 * 10. Metrics: [C] Tinted Accent Surface (bg-blue-50/50 border-blue-200 rounded-xl, bold blue metric numbers)
 * 11. Modals: [A] Centered Blur Modal (rounded-2xl bg-white backdrop-blur-xs, sticky header, fixed footer)
 * 12. Toasts: [C] Left Accent Border Strip (border-l-4 border-l-emerald-600 / border-l-rose-600, high visibility)
 * 13. Code Viewers: [A] Light Slate Enterprise Code Box (bg-slate-100/90 text-slate-800 font-mono text-xs)
 * 14. Shell: [A] Clean Light Enterprise Frame (h-14 header, collapsible 64px/240px sidebar rail, bottom status strip)
 * 15. Logos: [B] Solid Vibrant Brand Pill (high-contrast official brand background with bold white text)
 * 16. Stepper: [A] Compact Segmented Rail with Step Badges (low-profile 48px numbered circle badges + checkmarks)
 * 17. DAG Flow: [B] Compact Horizontal Pipeline Blocks (sequential stage blocks connected by directional arrows)
 * 18. Dropzone: [A] Dashed Border Drag-and-Drop Surface (border-2 border-dashed border-slate-300 + upload icon)
 * 19. Empty States: [A] Minimal Centered Graphic with Subtext (line-art icon, bold title, descriptive paragraph + CTA)
 * 20. Datetime: [A] Standard UTC Time Picker with Status Badge (explicit UTC format input + "Scheduled" tag)
 */

export const GDS = {
  // 01. Buttons
  btnPrimary: 'h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-2xs disabled:opacity-50 disabled:cursor-not-allowed select-none',
  btnSecondary: 'h-9 px-3.5 rounded-lg border border-slate-200/90 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 font-medium text-xs inline-flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-2xs disabled:opacity-50 disabled:cursor-not-allowed select-none',
  btnGhost: 'h-9 px-3 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 font-medium text-xs inline-flex items-center justify-center gap-1.5 cursor-pointer transition-colors select-none',
  btnDanger: 'h-9 px-3.5 rounded-lg bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 font-semibold text-xs inline-flex items-center justify-center gap-2 cursor-pointer transition-colors select-none',
  btnIcon: 'w-8 h-8 rounded-lg border border-slate-200/90 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 inline-flex items-center justify-center cursor-pointer transition-colors select-none shadow-2xs',

  // 02. Operational Status Badges (Option A)
  badgeReady: 'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 select-none',
  badgeAttention: 'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 select-none',
  badgeBlocked: 'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 select-none',
  badgeRunning: 'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 select-none',
  badgeNeutral: 'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 select-none',

  // 03. Dropdowns (Option A)
  dropdownTrigger: 'h-9 px-3 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 flex items-center justify-between text-xs font-medium text-slate-800 cursor-pointer shadow-2xs transition-colors',
  dropdownPopover: 'absolute z-50 mt-1.5 w-full rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-0.5 animate-in fade-in zoom-in-95 duration-150',

  // 04. Search & Inputs (Option A)
  inputBase: 'h-9 px-3 bg-white border border-slate-200 focus:border-blue-500 rounded-lg text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all placeholder:text-slate-400',
  inputSearch: 'w-full h-8 pl-9 pr-7 bg-white border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none transition-all placeholder:text-slate-400 shadow-2xs',
  searchContainer: 'relative w-64 flex items-center',
  searchIcon: 'absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none shrink-0',
  searchClearBtn: 'absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold cursor-pointer select-none',

  // 05. Tabs (Option B - Segmented Pill Slider)
  tabContainer: 'p-1 bg-slate-100/90 border border-slate-200/60 rounded-xl flex items-center gap-1 select-none',
  tabItemActive: 'px-3 py-1.5 rounded-lg bg-white font-bold text-slate-900 text-xs shadow-2xs transition-all flex items-center gap-2 cursor-pointer',
  tabItemInactive: 'px-3 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 font-medium text-xs transition-colors flex items-center gap-2 cursor-pointer',

  // 06. Key-Value Definition Grid (Option A)
  defGridContainer: 'p-4 bg-white border border-slate-200/90 rounded-2xl grid grid-cols-[120px_1fr] gap-y-3 gap-x-3 text-xs shadow-2xs',
  defKey: 'text-slate-500 font-normal truncate self-center',
  defValue: 'font-semibold text-slate-900 font-mono truncate self-center',

  // 07. Data Tables (Option B - Zebra-Striped Compact Enterprise)
  tableHeader: 'bg-slate-100/90 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 px-4 py-2.5 select-none',
  tableRowEven: 'bg-white hover:bg-blue-50/40 border-b border-slate-100 transition-colors text-xs text-slate-800',
  tableRowOdd: 'bg-slate-50/50 hover:bg-blue-50/40 border-b border-slate-100 transition-colors text-xs text-slate-800',
  tableCellNumeric: 'tabular-nums text-right font-mono font-medium',

  // 08. Multi-Pane Workbench Geometry (Option A)
  workbenchTreeExpanded: 'w-[320px]',
  workbenchTreeCompressed: 'w-[260px]',
  workbenchTreeCollapsed: 'w-[48px]',
  workbenchDrawer: 'w-[380px]',

  // 10. Metric KPI Cards (Option C - Tinted Accent Surface)
  kpiSurface: 'p-4 rounded-2xl bg-blue-50/40 border border-blue-200/80 flex flex-col justify-between h-28 select-none shadow-2xs',
  kpiLabel: 'text-[11px] font-bold text-blue-900 uppercase tracking-wider',
  kpiValue: 'text-2xl font-bold font-mono text-blue-700 tracking-tight',

  // 11. Modals (Option A - Centered Blur Modal)
  modalBackdrop: 'fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200',
  modalShell: 'w-full max-w-xl bg-white border border-slate-200/90 rounded-2xl shadow-2xl overflow-hidden flex flex-col',

  // 12. Alert Toasts (Option C - Left Accent Border Strip)
  toastSuccess: 'p-3 bg-white border border-slate-200 border-l-4 border-l-emerald-600 rounded-r-xl shadow-md text-xs font-semibold text-slate-800 flex items-center justify-between gap-3',
  toastWarning: 'p-3 bg-white border border-slate-200 border-l-4 border-l-amber-500 rounded-r-xl shadow-md text-xs font-semibold text-slate-800 flex items-center justify-between gap-3',
  toastDanger: 'p-3 bg-white border border-slate-200 border-l-4 border-l-rose-600 rounded-r-xl shadow-md text-xs font-semibold text-slate-800 flex items-center justify-between gap-3',

  // 13. Code & DDL Viewers (Option A)
  codeBox: 'p-4 bg-slate-100/90 border border-slate-200 rounded-xl font-mono text-xs text-slate-800 leading-relaxed overflow-x-auto selection:bg-blue-200',

  // 15. Provider Logos (Option B - Solid Vibrant Brand Pill)
  brandOracle: 'px-2.5 py-0.5 rounded-md bg-red-600 text-white font-bold text-[10px] tracking-wide select-none',
  brandPostgres: 'px-2.5 py-0.5 rounded-md bg-blue-700 text-white font-bold text-[10px] tracking-wide select-none',
  brandSnowflake: 'px-2.5 py-0.5 rounded-md bg-sky-600 text-white font-bold text-[10px] tracking-wide select-none',
  brandMysql: 'px-2.5 py-0.5 rounded-md bg-amber-600 text-white font-bold text-[10px] tracking-wide select-none',
  brandKafka: 'px-2.5 py-0.5 rounded-md bg-slate-900 text-white font-bold text-[10px] tracking-wide select-none',

  // 16. Stepper (Option A)
  stepperRail: 'h-12 bg-white border-b border-slate-200 px-6 flex items-center justify-between select-none shrink-0',

  // 17. DAG (Option B - Horizontal Stage Blocks)
  dagStageCard: 'p-3 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1.5',

  // 18. Dropzone (Option A - Dashed Surface)
  dropzoneSurface: 'p-6 border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-2xl bg-slate-50/60 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors',

  // 19. Empty States (Option A)
  emptyStateBox: 'py-12 px-6 flex flex-col items-center justify-center text-center gap-2 select-none',

  // 20. Datetime (Option A)
  datetimeInput: 'h-9 px-3 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-800 inline-flex items-center gap-2'
} as const;
