import { chromium } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const screenshotDir = 'C:/Users/AALOK/.gemini/antigravity/brain/7bb13979-7a02-48e3-9d1b-7626fcc38ff8/screenshots_fresh';
if (!fs.existsSync(screenshotDir)) {
  fs.mkdirSync(screenshotDir, { recursive: true });
}

async function run() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const baseUrl = 'http://localhost:49373';
  
  const viewports = [
    { width: 1440, height: 900, name: '1440x900' },
    { width: 1024, height: 768, name: '1024x768' }
  ];

  const routes = [
    { name: 'create_template_step1', url: `${baseUrl}/migration/templates/create` },
    { name: 'template_workspace', url: `${baseUrl}/migration/templates/T-001` },
    { name: 'global_history', url: `${baseUrl}/migration/history` },
    { name: 'evidence_explorer', url: `${baseUrl}/reports/evidence` }
  ];

  for (const vp of viewports) {
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await context.newPage();

    for (const r of routes) {
      try {
        console.log(`Navigating to ${r.url} at ${vp.name}...`);
        await page.goto(r.url, { waitUntil: 'networkidle', timeout: 15000 });
        await page.waitForTimeout(1000);
        const file = path.join(screenshotDir, `${r.name}_${vp.name}.png`);
        await page.screenshot({ path: file });
        console.log(`Captured ${file}`);
      } catch (err) {
        console.error(`Error capturing ${r.name} at ${vp.name}:`, err.message);
      }
    }

    // Capture Evidence Detail
    try {
      console.log(`Navigating to evidence explorer for detail at ${vp.name}...`);
      await page.goto(`${baseUrl}/reports/evidence`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(1000);
      const inspectBtn = page.locator('button:has-text("Inspect")').first();
      if (await inspectBtn.isVisible()) {
        await inspectBtn.click();
        await page.waitForTimeout(1000);
        const file = path.join(screenshotDir, `evidence_detail_${vp.name}.png`);
        await page.screenshot({ path: file });
        console.log(`Captured ${file}`);
      }
    } catch (err) {
      console.error(`Error capturing evidence_detail at ${vp.name}:`, err.message);
    }

    await context.close();
  }

  await browser.close();
  console.log('Done capturing fresh screenshots.');
}

run();
