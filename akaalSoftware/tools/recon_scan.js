const fs = require('fs');
const path = require('path');

const srcDir = 'a:/temp_akaal/akaalSoftware/frontend/src/app';

let tsFiles = [];
function walk(dir) {
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, f.name);
    if (f.isDirectory()) {
      walk(full);
    } else if (f.name.endsWith('.ts')) {
      tsFiles.push(full);
    }
  }
}
walk(srcDir);

const results = {
  totalFiles: tsFiles.length,
  components: 0,
  services: 0,
  specs: 0,
  fixtures: 0,
  buttons: {
    totalButtons: 0,
    gdsPrimary: 0,
    gdsSecondary: 0,
    gdsGhost: 0,
    gdsDanger: 0,
    gdsIcon: 0,
    localBluePrimary: 0,
    localWhiteSecondary: 0,
    localDanger: 0,
    buttonsWithIcons: 0,
    iconOnlyButtons: 0,
    actionButtonsWithDecorativeIcons: 0,
    disabledStateButtons: 0
  },
  inputs: {
    totalInputs: 0,
    textInputs: 0,
    searchInputs: 0,
    numberInputs: 0,
    passwordInputs: 0,
    checkboxInputs: 0,
    radioInputs: 0,
    textareas: 0
  },
  selects: {
    customSelectUsages: 0,
    nativeSelectUsages: 0,
    primeNgSelectUsages: 0,
    segmentedControlUsages: 0
  },
  tables: {
    nativeTableUsages: 0,
    primeNgTableUsages: 0,
    tablesWithPagination: 0,
    customPaginationUsages: 0
  },
  dialogs: {
    modalBackdrops: 0, // fixed inset-0 z-50
    standaloneModalComponents: 0,
    destructiveConfirmations: 0,
    drawers: 0
  },
  alerts: {
    gdsToasts: 0,
    inlineBanners: 0,
    toastServices: 0
  },
  emptyStates: {
    totalEmptyStateBlocks: 0
  },
  loadingStates: {
    spinners: 0,
    skeletons: 0
  },
  accordions: {
    appAccordionUsages: 0,
    customExpanders: 0
  },
  editors: {
    appCodeEditorUsages: 0,
    monacoDirectUsages: 0
  },
  icons: {
    appLucideIconUsages: 0,
    primeIconsUsages: 0,
    fontAwesomeUsages: 0,
    inlineSvgUsages: 0,
    emojiIcons: 0
  },
  typography: {
    fontSans: 0,
    fontMono: 0,
    fontHeading: 0,
    nonRobotoMentions: 0
  },
  sharedUsageByModule: {
    'custom-select': {},
    'lucide-icon': {},
    'segmented-control': {},
    'code-editor': {},
    'metric-surface': {},
    'accordion': {}
  },
  designLaws: {
    roundedFullPillBadges: 0,
    roundedMdBadges: 0,
    gradientClasses: 0,
    neonGlowShadows: 0,
    hoverLiftCards: 0
  }
};

for (const file of tsFiles) {
  const content = fs.readFileSync(file, 'utf-8');
  const isSpec = file.endsWith('.spec.ts');
  const isFixture = file.endsWith('.fixtures.ts');
  const isComponent = content.includes('@Component(');
  const isService = content.includes('@Injectable(');

  if (isSpec) results.specs++;
  if (isFixture) results.fixtures++;
  if (isComponent) results.components++;
  if (isService) results.services++;

  // Determine module
  let mod = 'other';
  if (file.includes('modules\\dashboard') || file.includes('modules/dashboard')) mod = 'Dashboard';
  else if (file.includes('modules\\migration') || file.includes('modules/migration') || file.includes('modules\\connections') || file.includes('modules/connections') || file.includes('modules\\validation') || file.includes('modules/validation')) mod = 'Migration';
  else if (file.includes('modules\\monitoring') || file.includes('modules/monitoring')) mod = 'Monitoring';
  else if (file.includes('modules\\reports') || file.includes('modules/reports')) mod = 'Reports';
  else if (file.includes('modules\\admin') || file.includes('modules/admin')) mod = 'Administration';
  else if (file.includes('modules\\settings') || file.includes('modules/settings')) mod = 'Settings';
  else if (file.includes('modules\\shell') || file.includes('modules/shell')) mod = 'Shell';
  else if (file.includes('shared')) mod = 'Shared';
  else if (file.includes('core')) mod = 'Core';

  // Shared component usages
  const countMatches = (regex) => (content.match(regex) || []).length;

  const lucideCount = countMatches(/<app-lucide-icon/g);
  if (lucideCount > 0) {
    results.icons.appLucideIconUsages += lucideCount;
    results.sharedUsageByModule['lucide-icon'][mod] = (results.sharedUsageByModule['lucide-icon'][mod] || 0) + lucideCount;
  }

  const customSelectCount = countMatches(/<app-custom-select/g);
  if (customSelectCount > 0) {
    results.selects.customSelectUsages += customSelectCount;
    results.sharedUsageByModule['custom-select'][mod] = (results.sharedUsageByModule['custom-select'][mod] || 0) + customSelectCount;
  }

  const segCount = countMatches(/<app-segmented-control/g);
  if (segCount > 0) {
    results.selects.segmentedControlUsages += segCount;
    results.sharedUsageByModule['segmented-control'][mod] = (results.sharedUsageByModule['segmented-control'][mod] || 0) + segCount;
  }

  const codeEdCount = countMatches(/<app-code-editor/g);
  if (codeEdCount > 0) {
    results.editors.appCodeEditorUsages += codeEdCount;
    results.sharedUsageByModule['code-editor'][mod] = (results.sharedUsageByModule['code-editor'][mod] || 0) + codeEdCount;
  }

  const metricCount = countMatches(/<app-metric-surface/g);
  if (metricCount > 0) {
    results.sharedUsageByModule['metric-surface'][mod] = (results.sharedUsageByModule['metric-surface'][mod] || 0) + metricCount;
  }

  const accordionCount = countMatches(/<app-accordion/g);
  if (accordionCount > 0) {
    results.accordions.appAccordionUsages += accordionCount;
    results.sharedUsageByModule['accordion'][mod] = (results.sharedUsageByModule['accordion'][mod] || 0) + accordionCount;
  }

  // Buttons
  const buttonTags = countMatches(/<button\b/g);
  results.buttons.totalButtons += buttonTags;

  results.buttons.gdsPrimary += countMatches(/GDS\.btnPrimary/g);
  results.buttons.gdsSecondary += countMatches(/GDS\.btnSecondary/g);
  results.buttons.gdsGhost += countMatches(/GDS\.btnGhost/g);
  results.buttons.gdsDanger += countMatches(/GDS\.btnDanger/g);
  results.buttons.gdsIcon += countMatches(/GDS\.btnIcon/g);

  // Local styled buttons
  results.buttons.localBluePrimary += countMatches(/bg-blue-600/g);
  results.buttons.localWhiteSecondary += countMatches(/bg-white.*border-slate-200/g);

  // Inputs
  results.inputs.totalInputs += countMatches(/<input\b/g);
  results.inputs.textInputs += countMatches(/type=["']text["']/g);
  results.inputs.searchInputs += countMatches(/type=["']search["']|placeholder=.*search/gi);
  results.inputs.numberInputs += countMatches(/type=["']number["']/g);
  results.inputs.passwordInputs += countMatches(/type=["']password["']/g);
  results.inputs.checkboxInputs += countMatches(/type=["']checkbox["']/g);
  results.inputs.radioInputs += countMatches(/type=["']radio["']/g);
  results.inputs.textareas += countMatches(/<textarea\b/g);

  // Native Select vs PrimeNG
  results.selects.nativeSelectUsages += countMatches(/<select\b/g);
  results.selects.primeNgSelectUsages += countMatches(/<p-select\b|<p-dropdown\b/g);

  // Tables
  results.tables.nativeTableUsages += countMatches(/<table\b/g);
  results.tables.primeNgTableUsages += countMatches(/<p-table\b/g);
  results.tables.customPaginationUsages += countMatches(/pagination|pageSize|currentPage|totalPages/gi);

  // Modals & Backdrops
  results.dialogs.modalBackdrops += countMatches(/fixed inset-0 z-50/g);
  results.dialogs.destructiveConfirmations += countMatches(/isDestructiveConfirmModalOpen|confirmDestructiveAction|DROP TARGET TABLES/gi);

  // Spinners & Loading
  results.loadingStates.spinners += countMatches(/animate-spin/g);
  results.loadingStates.skeletons += countMatches(/animate-pulse/g);

  // Empty states
  results.emptyStates.totalEmptyStateBlocks += countMatches(/No .* found|Nothing needs your attention|No active |No unread |No items/gi);

  // Icons check
  results.icons.primeIconsUsages += countMatches(/pi pi-|primeicons/g);
  results.icons.fontAwesomeUsages += countMatches(/fa-|font-awesome/g);
  results.icons.inlineSvgUsages += countMatches(/<svg\b/g);

  // Design laws
  results.designLaws.roundedFullPillBadges += countMatches(/rounded-full px-|rounded-full text-/g);
  results.designLaws.roundedMdBadges += countMatches(/rounded-md.*text-\[1[01]px\]/g);
  results.designLaws.gradientClasses += countMatches(/bg-gradient-|from-|to-/g);
  results.designLaws.neonGlowShadows += countMatches(/shadow-neon|shadow-glow/g);
  results.designLaws.hoverLiftCards += countMatches(/hover:-translate-y-|hover:shadow-2xl/g);
}

fs.writeFileSync('a:/temp_akaal/akaalSoftware/tools/recon_results.json', JSON.stringify(results, null, 2));
console.log('Reconnaissance scan complete.');
console.log(JSON.stringify(results, null, 2));
