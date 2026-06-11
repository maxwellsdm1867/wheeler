#!/usr/bin/env node
// Wheeler statusline — shows update indicator and basic session info.
// Reads update cache written by wheeler-check-update.js (SessionStart hook).
//
// Two modes, configured in settings.json:
//   Full:    "statusLine": { "type": "command", "command": "node \"<path>/wheeler-statusline.js\"" }
//   Wrapper: "statusLine": { "type": "command", "command": "node \"<path>/wheeler-statusline.js\" --wrap-b64 <base64-cmd>" }
// In wrapper mode the base64-decoded original statusline command is run
// with the same stdin and its output is shown unchanged; the Wheeler
// update badge is prepended only when an update is pending. This lets
// the badge coexist with any other tool's statusline (e.g. GSD's).

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

function wheelerBadge() {
  const cacheFile = path.join(os.homedir(), '.cache', 'wheeler', 'version-check.json');
  if (fs.existsSync(cacheFile)) {
    try {
      const cache = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
      if (cache.update_available) {
        return `\x1b[33m⬆ /wh:update\x1b[0m │ `;
      }
    } catch (e) {}
  }
  return '';
}

const wrapIdx = process.argv.indexOf('--wrap-b64');
const wrapCmd = wrapIdx !== -1 && process.argv[wrapIdx + 1]
  ? Buffer.from(process.argv[wrapIdx + 1], 'base64').toString('utf8')
  : null;

let input = '';
const stdinTimeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  clearTimeout(stdinTimeout);

  if (wrapCmd) {
    // Wrapper mode: delegate to the original statusline, prepend badge.
    let delegateOut = '';
    try {
      const res = spawnSync(wrapCmd, {
        shell: true,
        input,
        encoding: 'utf8',
        timeout: 3000,
        windowsHide: true
      });
      if (res.stdout) delegateOut = res.stdout.replace(/\n+$/, '');
    } catch (e) {}
    if (delegateOut) {
      process.stdout.write(`${wheelerBadge()}${delegateOut}`);
      return;
    }
    // Delegate produced nothing: fall through to the full rendering so
    // the status line never goes blank.
  }

  try {
    const data = JSON.parse(input);
    const model = data.model?.display_name || 'Claude';
    const dir = data.workspace?.current_dir || process.cwd();
    const remaining = data.context_window?.remaining_percentage;

    // Context window display
    const AUTO_COMPACT_BUFFER_PCT = 16.5;
    let ctx = '';
    if (remaining != null) {
      const usableRemaining = Math.max(0, ((remaining - AUTO_COMPACT_BUFFER_PCT) / (100 - AUTO_COMPACT_BUFFER_PCT)) * 100);
      const used = Math.max(0, Math.min(100, Math.round(100 - usableRemaining)));
      const filled = Math.floor(used / 10);
      const bar = '\u2588'.repeat(filled) + '\u2591'.repeat(10 - filled);
      if (used < 50) {
        ctx = ` \x1b[32m${bar} ${used}%\x1b[0m`;
      } else if (used < 65) {
        ctx = ` \x1b[33m${bar} ${used}%\x1b[0m`;
      } else if (used < 80) {
        ctx = ` \x1b[38;5;208m${bar} ${used}%\x1b[0m`;
      } else {
        ctx = ` \x1b[5;31m${bar} ${used}%\x1b[0m`;
      }
    }

    // Wheeler update available?
    const wheelerUpdate = wheelerBadge();

    // GSD update available? (coexist with GSD if installed)
    let gsdUpdate = '';
    const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
    const gsdCacheFile = path.join(claudeDir, 'cache', 'gsd-update-check.json');
    if (fs.existsSync(gsdCacheFile)) {
      try {
        const cache = JSON.parse(fs.readFileSync(gsdCacheFile, 'utf8'));
        if (cache.update_available) {
          gsdUpdate = `\x1b[33m\u2B06 /gsd:update\x1b[0m \u2502 `;
        }
        if (cache.stale_hooks && cache.stale_hooks.length > 0) {
          gsdUpdate += `\x1b[31m\u26A0 stale hooks \u2014 run /gsd:update\x1b[0m \u2502 `;
        }
      } catch (e) {}
    }

    const dirname = path.basename(dir);
    process.stdout.write(
      `${wheelerUpdate}${gsdUpdate}\x1b[2m${model}\x1b[0m \u2502 \x1b[2m${dirname}\x1b[0m${ctx}`
    );
  } catch (e) {}
});
