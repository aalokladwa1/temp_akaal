import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// Static HTTP server for Angular SPA
const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  if (reqPath === '/' || reqPath === '') reqPath = '/index.html';
  
  let filePath = path.join(distDir, reqPath);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(distDir, 'index.html');
  }

  const ext = path.extname(filePath).toLowerCase();
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

  const contentType = mimeTypes[ext] || 'application/octet-stream';
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

const PORT = 4289;
server.listen(PORT, async () => {
  console.log(`Static server listening on http://localhost:${PORT}`);

  const browser = await chromium.launch({ headless: true, channel: 'msedge' });

  const resolutions = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const res of resolutions) {
    console.log(`\n=== Capturing resolution: ${res.name} ===`);
    const page = await browser.newPage({
      viewport: { width: res.width, height: res.height }
    });

    // 1. Portfolio Home
    console.log('1. Portfolio Home');
    await page.goto(`http://localhost:${PORT}/migration/projects`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partb_01_portfolio_home_${res.name}.png`) });

    // 2. Create Initiative - Step 1
    console.log('2. Create Initiative - Step 1');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partb_02_create_step1_${res.name}.png`) });

    // 3. Create Initiative - Step 2 (fill name & objective, navigate to Step 2)
    console.log('3. Create Initiative - Step 2');
    const nameInput = page.locator('input[placeholder*="Data Center Exit"]');
    if (await nameInput.count() > 0) {
      await nameInput.fill('Global Multi-Cloud Modernization 2028');
      const objTextarea = page.locator('textarea');
      if (await objTextarea.count() > 0) {
        await objTextarea.fill('Strategic modernization program migrating core transactional databases and event streaming pipelines.');
      }
      await page.waitForTimeout(200);
      
      // Click Continue button to go to Step 2
      const continueBtn = page.locator('footer button:has-text("Continue")');
      if (await continueBtn.count() > 0) {
        await continueBtn.click();
        await page.waitForTimeout(600);
        await page.screenshot({ path: path.join(outDir, `partb_03_create_step2_${res.name}.png`) });

        // Select a project
        const projectItem = page.locator('.divide-y > div').first();
        if (await projectItem.count() > 0) {
          await projectItem.click();
          await page.waitForTimeout(300);
        }

        // 4. Create Initiative - Step 3 Review
        console.log('4. Create Initiative - Step 3 Review');
        const continueReviewBtn = page.locator('footer button:has-text("Continue")');
        if (await continueReviewBtn.count() > 0) {
          await continueReviewBtn.click();
          await page.waitForTimeout(600);
          await page.screenshot({ path: path.join(outDir, `partb_04_create_step3_${res.name}.png`) });

          // Click Create Initiative to test modal
          const createBtn = page.locator('footer button:has-text("Create Initiative")');
          if (await createBtn.count() > 0) {
            await createBtn.click();
            await page.waitForTimeout(400);
            await page.screenshot({ path: path.join(outDir, `partb_04b_create_modal_${res.name}.png`) });
          }
        }
      }
    }

    // 5. Initiative Workspace - Overview
    console.log('5. Initiative Workspace - Overview');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/init-dc-exit-2027/overview`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partb_05_workspace_overview_${res.name}.png`) });

    // 6. Initiative Workspace - Projects
    console.log('6. Initiative Workspace - Projects');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/init-dc-exit-2027/projects`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partb_06_workspace_projects_${res.name}.png`) });

    // 7. Initiative Workspace - Add Project Modal
    console.log('7. Initiative Workspace - Add Project Modal');
    const addProjBtn = page.locator('button:has-text("Add Projects")');
    if (await addProjBtn.count() > 0) {
      await addProjBtn.click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `partb_07_workspace_add_modal_${res.name}.png`) });
      // Close modal
      const cancelBtn = page.locator('button:has-text("Cancel")');
      if (await cancelBtn.count() > 0) await cancelBtn.first().click();
      await page.waitForTimeout(300);
    }

    // 8. Initiative Workspace - Activity
    console.log('8. Initiative Workspace - Activity');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/init-dc-exit-2027/activity`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partb_08_workspace_activity_${res.name}.png`) });

    // 9. Initiative Workspace - Settings
    console.log('9. Initiative Workspace - Settings');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/init-dc-exit-2027/settings`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partb_09_workspace_settings_${res.name}.png`) });

    // 10. Initiative Workspace - Archive Guardrail Modal
    console.log('10. Initiative Workspace - Archive Guardrail Modal');
    const archiveBtn = page.locator('button:has-text("Archive Initiative")');
    if (await archiveBtn.count() > 0) {
      await archiveBtn.click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `partb_10_workspace_archive_modal_${res.name}.png`) });
    }

    await page.close();
  }

  await browser.close();
  server.close();
  console.log('All Part B screenshots captured successfully!');
  process.exit(0);
});
