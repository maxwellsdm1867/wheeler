#!/usr/bin/env node
// GENERATED FILE. Do not edit. Regenerate: python -m wheeler.build_plugin
//
// SessionStart: report a legacy `wheeler install` that is shadowing this plugin's
// skills. User-level commands in ~/.claude/commands/wh/ win over plugin skills of
// the same name, so a machine carrying both runs the legacy copies and the plugin
// looks broken. Silent when there is no legacy install, which is the normal case.

const fs = require('fs');
const os = require('os');
const path = require('path');

const legacyDir = path.join(os.homedir(), '.claude', 'commands', 'wh');

let files = [];
try {
  files = fs
    .readdirSync(legacyDir)
    .filter((f) => f.endsWith('.md') && f !== 'CLAUDE.md');
} catch (err) {
  process.exit(0);
}

if (files.length === 0) {
  process.exit(0);
}

const shadowed = files
  .map((f) => '/wh:' + f.replace(/\.md$/, ''))
  .sort()
  .join(', ');

process.stdout.write(
  '[wheeler] A legacy `wheeler install` is present at ' +
    legacyDir +
    ' (' +
    files.length +
    ' command files). User-level commands shadow plugin skills of the same ' +
    'name, so these resolve to the legacy copies rather than the wh ' +
    'plugin: ' +
    shadowed +
    '. Run `wheeler migrate-to-plugin` to remove them and let the plugin take ' +
    'over. Tell the user once, then continue with their request.\n'
);
