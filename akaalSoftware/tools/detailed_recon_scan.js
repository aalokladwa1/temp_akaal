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

const detailed = {
  buttonBreakdown: {
    primaryActions: 0,
    secondaryActions: 0,
    ghostActions: 0,
    dangerActions: 0,
    iconOnlyButtons: 0,
    buttonsWithDecorativeIcons: 0, // <button>...<app-lucide-icon>...<span>Text</span>...</button>
    blackPrimaryButtons: 0 // checking if any bg-black or bg-slate-900 is used as primary button
  },
  pillUsageDetails: [],
  gradientDetails: [],
  nativeSelectFiles: [],
  tablePaginationDetails: [],
  pageHeaderPatterns: {
    standardTitleSubtitleAction: 0,
    customHeaders: 0
  },
  drawers: 0
};

for (const file of tsFiles) {
  const content = fs.readFileSync(file, 'utf-8');
  const relPath = path.relative(srcDir, file).replace(/\\/g, '/');

  // Check black primary buttons
  const blackBtns = content.match(/<button[^>]*class="[^"]*\b(bg-slate-900|bg-black|bg-gray-900)\b[^"]*"[^>]*>/g);
  if (blackBtns) {
    detailed.buttonBreakdown.blackPrimaryButtons += blackBtns.length;
  }

  // Buttons with icons and text
  const btnMatches = content.match(/<button[\s\S]*?<\/button>/g) || [];
  for (const btn of btnMatches) {
    const hasIcon = /<app-lucide-icon|<svg/i.test(btn);
    const hasText = /<span[^>]*>[^<]+<\/span>|[^<>\s]{2,}/i.test(btn.replace(/<app-lucide-icon[\s\S]*?<\/app-lucide-icon>/g, '').replace(/<svg[\s\S]*?<\/svg>/g, ''));
    
    if (hasIcon && hasText) {
      detailed.buttonBreakdown.buttonsWithDecorativeIcons++;
    } else if (hasIcon && !hasText) {
      detailed.buttonBreakdown.iconOnlyButtons++;
    }

    if (/bg-blue-600|bg-blue-700/.test(btn)) {
      detailed.buttonBreakdown.primaryActions++;
    } else if (/bg-rose-50|bg-rose-600|text-rose-/.test(btn)) {
      detailed.buttonBreakdown.dangerActions++;
    } else if (/border-slate-200|bg-white/.test(btn)) {
      detailed.buttonBreakdown.secondaryActions++;
    } else if (/hover:bg-slate-100|text-slate-600/.test(btn)) {
      detailed.buttonBreakdown.ghostActions++;
    }
  }

  // Native select
  if (content.includes('<select')) {
    detailed.nativeSelectFiles.push(relPath);
  }

  // Drawers (slide overs)
  if (/inset-y-0 right-0|translate-x-full/.test(content)) {
    detailed.drawers++;
  }

  // Gradients
  const grad = content.match(/bg-gradient-[a-z0-9-]+/g);
  if (grad) {
    detailed.gradientDetails.push({ file: relPath, count: grad.length, instances: grad });
  }

  // Pills (rounded-full)
  const pills = content.match(/rounded-full[^"'>]*/g);
  if (pills) {
    // Filter out 6px dots: w-1.5 h-1.5 rounded-full, spinners: border-2 rounded-full, avatars: w-8 h-8 rounded-full
    const realPills = pills.filter(p => !/w-1\.5|h-1\.5|w-1|h-1|w-2|h-2|w-3|h-3|w-4|h-4|w-6|h-6|w-8|h-8|w-10|h-10|w-12|h-12|border-t-transparent/.test(p));
    if (realPills.length > 0) {
      detailed.pillUsageDetails.push({ file: relPath, count: realPills.length, pills: realPills });
    }
  }
}

fs.writeFileSync('a:/temp_akaal/akaalSoftware/tools/detailed_recon_results.json', JSON.stringify(detailed, null, 2));
console.log('Detailed scan complete.');
console.log('Button breakdown:', detailed.buttonBreakdown);
console.log('Native select files:', detailed.nativeSelectFiles.length);
console.log('Drawers count:', detailed.drawers);
console.log('Gradients count:', detailed.gradientDetails.length);
console.log('Pill badges files count:', detailed.pillUsageDetails.length);
