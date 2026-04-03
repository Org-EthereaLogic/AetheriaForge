#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { appendToLog, readStdin, ensureSessionLogDir } = require('./utils');

async function main() {
  try {
    const input = await readStdin();
    const sessionId = input.session_id || 'unknown';
    appendToLog(sessionId, 'subagent_stop.json', input);

    if (input.transcript_path) {
      const dir = ensureSessionLogDir(sessionId);
      const dest = path.join(dir, 'subagent_chat.json');
      try {
        fs.copyFileSync(input.transcript_path, dest);
      } catch { /* fail open */ }
    }

    process.exit(0);
  } catch {
    process.exit(0);
  }
}

main();
