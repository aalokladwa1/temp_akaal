import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  const ext = path.extname(reqPath).toLowerCase();
  let filePath = path.join(distDir, reqPath);

  if (ext) {
    if (!fs.existsSync(filePath)) {
      filePath = path.join(distDir, path.basename(reqPath));
    }
  } else {
    filePath = path.join(distDir, 'index.html');
  }

  if (!fs.existsSync(filePath)) {
    filePath = path.join(distDir, 'index.html');
  }

  const mimeTypes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.svg': 'image/svg+xml'
  };

  const contentType = mimeTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(500);
      res.end('Error');
    } else {
      if (filePath.endsWith('index.html')) {
        let html = content.toString('utf-8');
        html = html.replace('<base href="./">', '<base href="/">');
        res.writeHead(200, { 'Content-Type': 'text/html' });
        return res.end(html, 'utf-8');
      }
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

server.listen(4391, async () => {
  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
    await page.goto('http://localhost:4391/settings', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    const links = await page.evaluate(() => {
      const items = document.querySelectorAll('nav a');
      return Array.from(items).map(a => ({
        text: a.textContent.trim().replace(/\s+/g, ' '),
        href: a.getAttribute('href')
      }));
    });

    console.log('FOUND LINKS:\n', JSON.stringify(links, null, 2));

    // Try clicking Appearance
    const appLink = page.getByRole('link', { name: /Appearance/i });
    console.log('Appearance link count:', await appLink.count());
    if (await appLink.count() > 0) {
      await appLink.first().click();
      await page.waitForTimeout(600);
      console.log('Current URL after click:', page.url());
      const heading = await page.locator('h2').textContent();
      console.log('Main H2 text after click:', heading);
    }

    await browser.close();
  } catch (err) {
    console.error(err);
  } finally {
    server.close();
  }
});
