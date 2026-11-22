'use strict';
// Opt-in, read-only forwarding of local Node console output to Royal Staff Panel.
// Start: node -r ./bot-console-forwarder.js index.js
// Never accepts commands from the website or exposes BOT_API_KEY in its payload.
const fs = require('fs');
const util = require('util');
let dotenv = {};
try {
  const raw = fs.readFileSync('.env', 'utf8').replace(/^\uFEFF/, '');
  for (const line of raw.split(/\r?\n/)) {
    const match = /^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/i.exec(line);
    if (match) dotenv[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2').trim();
  }
} catch (_) { /* Environment variables may be provided by the shell. */ }
const key = process.env.BOT_API_KEY || dotenv.BOT_API_KEY;
const base = (process.env.DONUT_ROYALE_URL || process.env.WEB_URL || dotenv.DONUT_ROYALE_URL || dotenv.WEB_URL ||
  'https://donut-royale.onrender.com').replace(/\/+$/, '');
const forbidden = /(bot[_ -]?api[_ -]?key|authorization|bearer\s+|password|secret|session=|cookie:|\.env|attempt[_ -]?token|token\s*[:=])/i;
const pending = [];
const MAX_QUEUE = 200;
const native = {};
for (const level of ['log','info','warn','error']) {
  native[level] = console[level].bind(console);
  console[level] = function (...args) {
    native[level](...args);
    if (!key) return;
    let output;
    try { output = util.format(...args); } catch (_) { return; }
    for (const piece of String(output).split(/\r?\n/)) {
      const text = piece.replace(/\x1b\[[0-9;]*m/g,'').trim();
      if (!text || forbidden.test(text)) continue;
      pending.push({level:level==='error'?'error':level==='warn'?'warn':'info',text:text.slice(0,500)});
      if (pending.length > MAX_QUEUE) pending.shift();
    }
  };
}
let busy = false;
async function flush() {
  if (!key || busy || !pending.length || typeof fetch !== 'function') return;
  busy = true;
  const batch = pending.splice(0,20);
  try {
    const response = await fetch(base+'/api/bot/console',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-Bot-Api-Key':key},
      body:JSON.stringify({lines:batch}),
      signal:AbortSignal.timeout(6000)
    });
    if (!response.ok) throw new Error('Console relay HTTP '+response.status);
  } catch (_) {
    // Keep a bounded backlog without logging failures into the capture hook.
    pending.unshift(...batch);
    if (pending.length > MAX_QUEUE) pending.splice(0,pending.length-MAX_QUEUE);
  } finally { busy = false; }
}
const interval = setInterval(()=>{void flush();},3000);
if (typeof interval.unref === 'function') interval.unref();
if (!key) process.stderr.write('[CMD relay] BOT_API_KEY missing: log forwarding is disabled.\n');
