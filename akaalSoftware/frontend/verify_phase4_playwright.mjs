import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve(process.cwd(), 'dist/akaal-software/browser');
const altDistDir = path.resolve(process.cwd(), 'dist/akaal-software');
const activeDistDir = fs.existsSync(distDir) ? distDir : altDistDir;

console.log('Serving SPA from:', activeDistDir);

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  const ext = path.extname(reqPath).toLowerCase();
  let filePath = path.join(activeDistDir, reqPath);

  if (ext) {
    if (!fs.existsSync(filePath)) {
      filePath = path.join(activeDistDir, path.basename(reqPath));
    }
  } else {
    filePath = path.join(activeDistDir, 'index.html');
  }

  if (!fs.existsSync(filePath)) {
    filePath = path.join(activeDistDir, 'index.html');
  }

  const mimeTypes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf'
  };

  const contentType = mimeTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(500);
      res.end('Server error: ' + err.code);
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

const PORT = 4399;
server.listen(PORT, async () => {
  console.log(`Phase 4 Playwright E2E server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ 
      headless: true,
      executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    console.log(`--- 1. Navigating to http://localhost:${PORT}/migration/create ---`);
    await page.goto(`http://localhost:${PORT}/migration/create`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    const createMigBtn = page.locator('button:has-text("Create Migration"), a[href*="migration/create"]').first();
    if (await createMigBtn.isVisible().catch(() => false)) {
      console.log('Clicking Create Migration button...');
      await createMigBtn.click();
      await page.waitForTimeout(1000);
    }

    const continueToSourceBtn = page.locator('button:has-text("Continue to Source")').first();
    if (await continueToSourceBtn.isVisible().catch(() => false)) {
      console.log('Filling Step 1 strategy & migration parameters...');
      const nameInput = page.locator('#step1-migration-title').first();
      if (await nameInput.isVisible().catch(() => false)) {
        await nameInput.fill('DevKros Migration Phase 4');
        await page.waitForTimeout(200);
      }

      // Click Bulk Migration card
      const modeCard = page.getByText('Bulk Migration', { exact: true }).first();
      if (await modeCard.isVisible().catch(() => false)) {
        await modeCard.click();
        await page.waitForTimeout(300);
      }

      console.log('Clicking Continue to Source button on Step 1...');
      await continueToSourceBtn.click();
      await page.waitForTimeout(1000);
    }

    // Verify window.__wizardMs is ABSENT from production build
    const hasGlobalHook = await page.evaluate(() => window.__wizardMs !== undefined);
    console.log('Is window.__wizardMs global hook present (expect FALSE):', hasGlobalHook);
    if (hasGlobalHook) throw new Error('Production Angular build leaks window.__wizardMs test hook!');

    // Helper: Select New Connection Mode
    const ensureNewConnectionMode = async () => {
      const newCard = page.locator('button:has-text("New Connection")').first();
      try {
        await newCard.waitFor({ state: 'visible', timeout: 3000 });
        await newCard.click();
        await page.waitForTimeout(400);
      } catch (e) {
        // Mode may already be set to NEW
      }
    };

    // Helper: Click Change Engine if already configured
    const ensureCatalogView = async () => {
      await ensureNewConnectionMode();
      const changeBtn = page.locator('button:has-text("Change Engine")').first();
      if (await changeBtn.isVisible().catch(() => false)) {
        await changeBtn.click();
        await page.waitForTimeout(400);
      }
    };

    // Helper: Select Provider Card from catalog
    const selectEngineByCard = async (engineName) => {
      await ensureCatalogView();
      const allButtons = await page.evaluate(() => Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim()));
      console.log('Visible buttons on page:', allButtons.filter(b => b.length > 0));

      const searchInput = page.locator('input[placeholder*="Search catalog"]').first();
      if (await searchInput.isVisible().catch(() => false)) {
        await searchInput.clear();
        await searchInput.fill(engineName);
        await page.waitForTimeout(300);
      }
      let cardBtn = page.locator(`button:has-text("${engineName}")`).filter({ hasText: /PROFILE|DRIVER|DATABASE|STORAGE|SAAS|STREAMING|ANALYTICS|NOSQL|WAREHOUSE/i }).first();
      if (!(await cardBtn.isVisible().catch(() => false))) {
        cardBtn = page.locator(`button:has-text("${engineName}")`).last();
      }
      await cardBtn.click();
      await page.waitForTimeout(400);
    };

    // Test A: AWS Managed Cloud UI DOM Flow
    console.log('--- 3. Testing AWS Managed Cloud via Customer UI DOM ---');
    await selectEngineByCard('AWS Managed Cloud');

    // Fill form inputs
    await page.locator('#field-host, input[placeholder*="rds.amazonaws.com"]').first().fill('rds-db.c123456789.us-east-1.rds.amazonaws.com');
    await page.locator('#field-database, input[placeholder="postgres"]').first().fill('postgres');
    await page.locator('#field-username, input[placeholder="postgres"]').first().fill('postgres');
    await page.locator('#field-secret_ref, input[placeholder*="vault://"]').first().fill('vault://secret/aws/rds/main');
    await page.waitForTimeout(300);

    // Verify Continue button is disabled before probe execution
    const continueBtn = page.locator('button:has-text("Continue to Target")').first();
    let isDisabledBefore = await continueBtn.isDisabled().catch(() => false);
    console.log('Continue button disabled before verification (expect TRUE):', isDisabledBefore);
    if (!isDisabledBefore) throw new Error('Continue button was enabled before running verification probe!');

    // Click "Verify Connection" probe button
    const probeBtn = page.locator('button:has-text("Verify Connection")').first();
    await probeBtn.click();
    console.log('Clicked verification probe button. Waiting for 7-phase probe completion...');
    await page.waitForTimeout(2200); // 7 phases * ~200ms

    let isDisabledAfter = await continueBtn.isDisabled().catch(() => false);
    console.log('Continue button disabled after verification (expect FALSE):', isDisabledAfter);
    if (isDisabledAfter) throw new Error('Continue button remained disabled after successful verification probe!');

    // Single-click Continue to Target
    console.log('Clicking Continue to Target...');
    await continueBtn.click();
    await page.waitForTimeout(800);

    // Verify transition to Target Connection Step 3
    const step3Heading = page.locator('h1:has-text("Target Connection"), h2:has-text("Target Connection"), app-step3-target').first();
    const isStep3Visible = await step3Heading.isVisible().catch(() => false);
    console.log('Step 3 Target Connection visible (expect TRUE):', isStep3Visible);
    if (!isStep3Visible) throw new Error('Failed single-click transition to Step 3 Target Connection!');

    // Back to Step 2
    console.log('Clicking Back to Source...');
    const backBtn = page.locator('button:has-text("Previous Step"), button:has-text("Back"), button:has-text("Back to Source")').first();
    await backBtn.click();
    await page.waitForTimeout(500);

    // Confirm AWS values preserved in DOM
    const preservedHost = await page.locator('#field-host, input[placeholder*="rds.amazonaws.com"]').first().inputValue().catch(() => '');
    console.log('Preserved AWS Host in DOM:', preservedHost);
    if (!preservedHost.includes('rds-db.c123456789')) throw new Error('AWS Host value lost upon Back navigation!');

    // Test B: Azure Managed Cloud UI DOM Flow
    console.log('--- 4. Testing Azure Managed Cloud via Customer UI DOM ---');
    await selectEngineByCard('Azure Managed Cloud');

    await page.locator('#field-host, input[placeholder*="azure.com"]').first().fill('myserver.postgres.database.azure.com');
    await page.locator('#field-database').first().fill('app_production');
    await page.locator('#field-username').first().fill('azureuser');
    await page.locator('#field-secret_ref').first().fill('vault://secret/azure/db');
    await page.waitForTimeout(300);

    await probeBtn.click();
    await page.waitForTimeout(2200);

    isDisabledAfter = await continueBtn.isDisabled().catch(() => false);
    console.log('Azure Continue button disabled after verification (expect FALSE):', isDisabledAfter);
    if (isDisabledAfter) throw new Error('Azure Continue button remained disabled after verification probe!');

    // Test C: Google Cloud Managed UI DOM Flow
    console.log('--- 5. Testing Google Cloud Managed via Customer UI DOM ---');
    await selectEngineByCard('Google Cloud Managed');

    await page.locator('#field-host').first().fill('10.128.0.5');
    await page.locator('#field-database').first().fill('main_db');
    await page.locator('#field-username').first().fill('postgres');
    await page.locator('#field-secret_ref').first().fill('vault://secret/gcp/cloudsql');
    await page.waitForTimeout(300);

    await probeBtn.click();
    await page.waitForTimeout(2200);

    isDisabledAfter = await continueBtn.isDisabled().catch(() => false);
    console.log('Google Cloud Continue button disabled after verification (expect FALSE):', isDisabledAfter);
    if (isDisabledAfter) throw new Error('Google Cloud Continue button remained disabled after verification probe!');

    // Test D: Oracle Cloud Infrastructure UI DOM Flow
    console.log('--- 6. Testing Oracle Cloud Infrastructure via Customer UI DOM ---');
    await selectEngineByCard('Oracle Cloud Infrastructure Managed');

    await page.locator('#field-host').first().fill('adb.us-ashburn-1.oraclecloud.com');
    await page.locator('#field-database').first().fill('atp_high.adb.oraclecloud.com');
    await page.locator('#field-username').first().fill('ADMIN');
    await page.locator('#field-secret_ref').first().fill('vault://secret/oci/atp');
    await page.waitForTimeout(300);

    await probeBtn.click();
    await page.waitForTimeout(2200);

    isDisabledAfter = await continueBtn.isDisabled().catch(() => false);
    console.log('OCI Continue button disabled after verification (expect FALSE):', isDisabledAfter);
    if (isDisabledAfter) throw new Error('Oracle Cloud Infrastructure Continue button remained disabled after verification probe!');

    // Test E: File Dataset UI DOM Flow
    console.log('--- 7. Testing File Dataset via Customer UI DOM ---');
    await selectEngineByCard('File Dataset');

    await page.locator('#field-database_path, #field-database, input[placeholder*="csv"]').first().fill('/data/exports/customers_2026.csv');
    await page.waitForTimeout(300);

    await probeBtn.click();
    await page.waitForTimeout(2200);

    isDisabledAfter = await continueBtn.isDisabled().catch(() => false);
    console.log('File Dataset Continue button disabled after verification (expect FALSE):', isDisabledAfter);
    if (isDisabledAfter) throw new Error('File Dataset Continue button remained disabled after verification probe!');

    // Test F: Parameter Mutation Invalidation via UI
    console.log('--- 8. Testing Field Mutation Invalidation via UI ---');
    // Mutate path input
    const pathInput = page.locator('#field-database_path, #field-database, input[placeholder*="csv"]').first();
    await pathInput.fill('/data/exports/customers_2026_MODIFIED.csv');
    await page.waitForTimeout(300);

    let isDisabledMutated = await continueBtn.isDisabled().catch(() => false);
    console.log('Continue button disabled after field mutation (expect TRUE):', isDisabledMutated);
    if (!isDisabledMutated) throw new Error('Stale verification remained valid after user mutated a field!');

    // Test G: Product Wording & Branding
    console.log('--- 9. Verifying Product Wording & Branding ---');
    const content = await page.content();
    const hasFalseEngineCount = content.includes('catalog of 54 supported physical database engines');
    console.log('Has false 54 physical database engines wording (expect FALSE):', hasFalseEngineCount);
    if (hasFalseEngineCount) throw new Error('False physical database engine count found in page text!');

    console.log('Console Errors Count:', consoleErrors.length);
    if (consoleErrors.length > 0) {
      console.log('Console Errors:', consoleErrors);
    }

    console.log('====================================================');
    console.log('ALL PHASE 4 PLAYWRIGHT E2E SCENARIOS PASSED CLEANLY!');
    console.log('====================================================');

    await browser.close();
    server.close();
    process.exit(0);
  } catch (err) {
    console.error('Playwright E2E Verification Failed:', err);
    server.close();
    process.exit(1);
  }
});
