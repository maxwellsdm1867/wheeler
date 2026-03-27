#!/usr/bin/env node
// Wheeler update checker — runs on SessionStart, writes cache for statusline/commands.
// Mirrors GSD pattern: background check, detached child, JSON cache.

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

const homeDir = os.homedir();
const cacheDir = path.join(homeDir, '.cache', 'wheeler');
const cacheFile = path.join(cacheDir, 'version-check.json');

// Ensure cache directory exists
if (!fs.existsSync(cacheDir)) {
  fs.mkdirSync(cacheDir, { recursive: true });
}

// Run check in background (detached child so SessionStart returns immediately)
const child = spawn(process.execPath, ['-e', `
  const fs = require('fs');
  const https = require('https');
  const { execSync } = require('child_process');

  const cacheFile = ${JSON.stringify(cacheFile)};

  // Get installed version from wheeler
  let installed = '0.0.0';
  try {
    const out = execSync('wheeler version 2>/dev/null || echo "Wheeler 0.0.0"',
      { encoding: 'utf8', timeout: 5000, windowsHide: true });
    const match = out.match(/Wheeler\\s+([\\d.]+)/);
    if (match) installed = match[1];
  } catch (e) {}

  // Check GitHub releases API
  function checkGitHub() {
    return new Promise((resolve) => {
      const options = {
        hostname: 'api.github.com',
        path: '/repos/maxwellsdm1867/wheeler/releases/latest',
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'wheeler-update-checker'
        },
        timeout: 5000
      };
      const req = https.get(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            const tag = (json.tag_name || '').replace(/^v/, '');
            resolve(tag || null);
          } catch (e) { resolve(null); }
        });
      });
      req.on('error', () => resolve(null));
      req.on('timeout', () => { req.destroy(); resolve(null); });
    });
  }

  // Check PyPI as fallback
  function checkPyPI() {
    return new Promise((resolve) => {
      const options = {
        hostname: 'pypi.org',
        path: '/pypi/wheeler/json',
        headers: { 'Accept': 'application/json', 'User-Agent': 'wheeler-update-checker' },
        timeout: 5000
      };
      const req = https.get(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            resolve(json.info?.version || null);
          } catch (e) { resolve(null); }
        });
      });
      req.on('error', () => resolve(null));
      req.on('timeout', () => { req.destroy(); resolve(null); });
    });
  }

  // Compare semver strings (true if latest > installed)
  function isNewer(installed, latest) {
    const a = installed.split('.').map(Number);
    const b = latest.split('.').map(Number);
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      const ai = a[i] || 0, bi = b[i] || 0;
      if (bi > ai) return true;
      if (bi < ai) return false;
    }
    return false;
  }

  (async () => {
    const latest = await checkGitHub() || await checkPyPI();
    const result = {
      update_available: latest ? isNewer(installed, latest) : false,
      installed,
      latest: latest || 'unknown',
      checked: Math.floor(Date.now() / 1000)
    };
    fs.writeFileSync(cacheFile, JSON.stringify(result));
  })();
`], {
  stdio: 'ignore',
  windowsHide: true,
  detached: true
});

child.unref();
