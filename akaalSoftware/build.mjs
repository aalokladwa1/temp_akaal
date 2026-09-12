import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const rootDir = 'A:\\temp_akaal\\akaalSoftware';
const frontendDir = path.join(rootDir, 'frontend');

console.log('--- 1. Building Production Angular Frontend (max-old-space-size=4096) ---');
try {
  const ngOut = execSync('npx ng build --base-href ./', {
    cwd: frontendDir,
    stdio: 'inherit',
    env: { ...process.env, NG_CLI_ANALYTICS: 'false' }
  });
  console.log('SUCCESS: Frontend build complete.');
} catch (err) {
  if (err.stdout) console.log(err.stdout.toString());
  if (err.stderr) console.error(err.stderr.toString());
  console.error('ERROR: Frontend build failed:', err.message);
  process.exit(1);
}

console.log('--- 2. Clearing WebView2 Cache ---');
const appData = process.env.APPDATA || '';
if (appData) {
  const eb1 = path.join(appData, 'AKAAL.exe', 'EBWebView');
  const eb2 = path.join(appData, 'akaalSoftware.exe', 'EBWebView');
  try { if (fs.existsSync(eb1)) fs.rmSync(eb1, { recursive: true, force: true }); } catch (_) {}
  try { if (fs.existsSync(eb2)) fs.rmSync(eb2, { recursive: true, force: true }); } catch (_) {}
}

console.log('--- 3. Compiling Go Windows GUI Binary (AKAAL.exe & akaalSoftware.exe) ---');
try {
  const goOut = execSync('go build -tags "desktop,production" -ldflags "-H windowsgui -s -w" -o AKAAL.exe .', {
    cwd: rootDir,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  console.log(goOut.toString());
  fs.copyFileSync(path.join(rootDir, 'AKAAL.exe'), path.join(rootDir, 'akaalSoftware.exe'));
  console.log('SUCCESS: Binaries compiled successfully.');
} catch (err) {
  if (err.stdout) console.log(err.stdout.toString());
  if (err.stderr) console.error(err.stderr.toString());
  console.error('ERROR: Go compilation failed:', err.message);
  process.exit(1);
}

console.log('=== BUILD COMPLETE: Desktop application ready to run ===');
