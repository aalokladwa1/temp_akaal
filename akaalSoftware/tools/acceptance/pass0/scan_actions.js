/**
 * Pass 0 - Calibrated Interaction & Action Inventory Scanner
 * 
 * Corrects S1-1:
 * - Scans inline component templates and class methods directly.
 * - Explicitly strips TypeScript language keywords (import, export class, export type).
 * - Strips @Component metadata (selector: '...').
 * - Strips Tailwind CSS utility class names (e.g. select-none) to avoid false positives.
 * - Maps 17 distinct action families with precise template/method semantics.
 */

const fs = require('fs');
const path = require('path');

const manifestsDir = path.resolve(__dirname, 'manifests');
const inventoryPath = path.join(manifestsDir, 'inventory_breakdown.json');
const frontendRoot = path.resolve(__dirname, '../../../frontend');

const inventory = JSON.parse(fs.readFileSync(inventoryPath, 'utf8'));

const actionDefinitions = {
  create_add: {
    name: 'Create / Add / Provision',
    templateTerms: ['create', 'add', 'new', 'provision'],
    methodTerms: ['create', 'add', 'onAdd', 'onCreate', 'provision', 'generate']
  },
  edit_modify: {
    name: 'Edit / Update / Configure',
    templateTerms: ['edit', 'update', 'modify', 'configure'],
    methodTerms: ['edit', 'update', 'onEdit', 'onUpdate', 'modify', 'configure']
  },
  delete_archive: {
    name: 'Delete / Remove / Archive',
    templateTerms: ['delete', 'remove', 'destroy', 'archive'],
    methodTerms: ['delete', 'remove', 'onDelete', 'onRemove', 'destroy', 'archive']
  },
  save_submit: {
    name: 'Save / Submit / Apply',
    templateTerms: ['save', 'submit', 'apply'],
    methodTerms: ['save', 'submit', 'onSave', 'onSubmit', 'apply', 'onApply']
  },
  cancel_close: {
    name: 'Cancel / Dismiss / Close',
    templateTerms: ['cancel', 'dismiss', 'close'],
    methodTerms: ['cancel', 'dismiss', 'onCancel', 'close', 'onClose']
  },
  test_probe_verify: {
    name: 'Test / Probe / Verify / Validate',
    templateTerms: ['test', 'probe', 'verify', 'validate', 'check'],
    methodTerms: ['test', 'probe', 'verify', 'validate', 'onTest', 'onVerify', 'runProbe']
  },
  start_execute_launch: {
    name: 'Start / Launch / Execute',
    templateTerms: ['start', 'launch', 'execute', 'run'],
    methodTerms: ['start', 'launch', 'execute', 'onStart', 'onLaunch', 'onExecute', 'startRun']
  },
  pause_resume: {
    name: 'Pause / Resume / Suspend',
    templateTerms: ['pause', 'resume', 'suspend'],
    methodTerms: ['pause', 'resume', 'suspend', 'onPause', 'onResume']
  },
  halt_abort_terminate: {
    name: 'Halt / Abort / Terminate / Stop',
    templateTerms: ['halt', 'abort', 'terminate', 'stop', 'kill'],
    methodTerms: ['halt', 'abort', 'terminate', 'stop', 'onHalt', 'onAbort']
  },
  approve_reject_barrier: {
    name: 'Approve / Reject / Barrier Override',
    templateTerms: ['approve', 'reject', 'override', 'barrier', 'sign-off'],
    methodTerms: ['approve', 'reject', 'override', 'onApprove', 'onReject', 'resolveBarrier']
  },
  retry_recover_repair: {
    name: 'Retry / Recover / Repair / Reconcile',
    templateTerms: ['retry', 'recover', 'repair', 'reconcile'],
    methodTerms: ['retry', 'recover', 'repair', 'reconcile', 'onRetry', 'onRecover', 'applyRepair']
  },
  export_download: {
    name: 'Export / Download / Bundle',
    templateTerms: ['export', 'download', 'upload', 'bundle'],
    methodTerms: ['export', 'download', 'upload', 'onExport', 'onDownload', 'downloadBundle', 'exportData']
  },
  filter_search_sort: {
    name: 'Filter / Search / Sort / Paginate',
    templateTerms: ['filter', 'search', 'sort', 'paginate', 'clearFilter'],
    methodTerms: ['filter', 'search', 'sort', 'onSearch', 'onFilter', 'setSort', 'setPage']
  },
  refresh_reload: {
    name: 'Refresh / Reload / Resync',
    templateTerms: ['refresh', 'reload', 'resync', 'poll'],
    methodTerms: ['refresh', 'reload', 'resync', 'onRefresh', 'onReload', 'poll']
  },
  toggle_select_switch: {
    name: 'Toggle / Select / Switch State',
    templateTerms: ['toggle', 'switch', 'segmented-control'],
    methodTerms: ['toggle', 'switch', 'onToggle', 'toggleView', 'toggleSidebar', 'toggleTheme']
  },
  navigate_route: {
    name: 'Navigate / Deep-Link / Drilldown',
    templateTerms: ['routerLink', 'navigate', 'drilldown', 'viewDetails'],
    methodTerms: ['navigate', 'navigateTo', 'openDetail', 'goTo', 'goBack']
  },
  cutover_failback: {
    name: 'Cutover / Switchover / Failback',
    templateTerms: ['cutover', 'failback', 'switchover', 'failover'],
    methodTerms: ['cutover', 'failback', 'switchover', 'failover', 'onCutover', 'onFailback']
  }
};

const actionResults = {};
for (const key of Object.keys(actionDefinitions)) {
  actionResults[key] = {
    name: actionDefinitions[key].name,
    count: 0,
    components: [],
    details: []
  };
}

inventory.components.forEach(compRelPath => {
  const fullPath = path.resolve(frontendRoot, compRelPath);
  const code = fs.readFileSync(fullPath, 'utf8');

  // 1. Extract template
  const tMatch = code.match(/template:\s*`([\s\S]*?)`(?:\s*,\s*|\s*\})/);
  const rawTemplate = tMatch ? tMatch[1] : '';

  // Clean template: remove CSS class attributes to prevent matching Tailwind utilities
  const cleanTemplate = rawTemplate.replace(/\bclass=["'][^"']*["']/g, '');

  // 2. Extract class body
  const cMatch = code.match(/export\s+class\s+([a-zA-Z0-9_]+)[\s\S]*?\{([\s\S]*)\}/);
  const className = cMatch ? cMatch[1] : 'UnknownComponent';
  const rawClassBody = cMatch ? cMatch[2] : '';

  // Clean class body: strip comments
  const cleanClassBody = rawClassBody.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '');

  for (const [key, def] of Object.entries(actionDefinitions)) {
    let matched = false;
    const matchType = [];

    // Check template click/change/submit or button labels
    for (const term of def.templateTerms) {
      if (term === 'segmented-control') {
        if (cleanTemplate.includes('<app-segmented-control')) {
          matched = true;
          matchType.push('template:segmented-control');
          break;
        }
      } else if (term === 'routerLink') {
        if (cleanTemplate.includes('routerLink')) {
          matched = true;
          matchType.push('template:routerLink');
          break;
        }
      } else {
        const clickRegex = new RegExp(`\\((?:click|change|submit)\\)=["'][^"']*\\b${term}\\b[^"']*["']`, 'i');
        const buttonRegex = new RegExp(`<button[^>]*>\\s*(?:<[^>]+>\\s*)*\\b${term}\\b`, 'i');
        const actionAttrRegex = new RegExp(`data-action=["'][^"']*\\b${term}\\b[^"']*["']`, 'i');

        if (clickRegex.test(cleanTemplate)) {
          matched = true;
          matchType.push(`template-click:${term}`);
          break;
        }
        if (buttonRegex.test(cleanTemplate)) {
          matched = true;
          matchType.push(`template-button:${term}`);
          break;
        }
        if (actionAttrRegex.test(cleanTemplate)) {
          matched = true;
          matchType.push(`template-action:${term}`);
          break;
        }
      }
    }

    // Check class methods if not yet matched
    if (!matched) {
      for (const term of def.methodTerms) {
        const methodRegex = new RegExp(`(?:\\bon|\\bhandle)?${term}[A-Z0-9_]\\w*\\s*\\(`, 'i');
        const exactMethodRegex = new RegExp(`\\b${term}\\s*\\(`, 'i');
        if (['start', 'run'].includes(term)) {
          if (cleanClassBody.match(methodRegex) && !cleanClassBody.match(/\bngOnInit\b/)) {
            matched = true;
            matchType.push(`method:${term}`);
            break;
          }
        } else {
          if (methodRegex.test(cleanClassBody) || exactMethodRegex.test(cleanClassBody)) {
            matched = true;
            matchType.push(`method:${term}`);
            break;
          }
        }
      }
    }

    if (matched) {
      actionResults[key].count++;
      actionResults[key].components.push(compRelPath);
      actionResults[key].details.push({
        file: compRelPath,
        className,
        matchType: matchType.join('; ')
      });
    }
  }
});

fs.writeFileSync(path.join(manifestsDir, 'actions_inventory.json'), JSON.stringify(actionResults, null, 2));

console.log('=== CALIBRATED ACTION SCAN COMPLETE ===');
for (const [key, val] of Object.entries(actionResults)) {
  console.log(`${val.name.padEnd(42)} (${key.padEnd(22)}): ${val.count.toString().padStart(3)} components`);
}
