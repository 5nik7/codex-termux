/* Embedded in bin/codex-termux. Node standard library only. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const crypto = require('node:crypto');
const cp = require('node:child_process');

const REGISTRY = 'https://registry.npmjs.org';
const VERSION = /^(0|[1-9]\d{0,7})\.(0|[1-9]\d{0,7})\.(0|[1-9]\d{0,7})$/;
const RUNTIME = /^v\d+\.\d+\.\d+-[a-f0-9]{16}$/;
const MAX_JSON = 1024 * 1024;
const checkLocks = new Set();
function fail(message) { throw new Error(message); }
function stable(v) { if (!VERSION.test(v)) fail('expected a stable numeric version (for example 0.153.4)'); return v; }
function newer(a, b) {
  stable(a); stable(b);
  const aa = a.split('.').map(Number), bb = b.split('.').map(Number);
  for (let i = 0; i < 3; i++) if (aa[i] !== bb[i]) return aa[i] > bb[i];
  return false;
}
function privateDir(dir) {
  if (!path.isAbsolute(dir)) fail('managed directories must be absolute paths');
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  const stat = fs.lstatSync(dir);
  if (!stat.isDirectory() || stat.isSymbolicLink() || (stat.mode & 0o077) ||
      (process.getuid && stat.uid !== process.getuid())) {
    fail('managed directory must be owned by this user, not a symlink, and mode 0700');
  }
}
function readRegular(file, limit = 4096) {
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const st = fs.fstatSync(fd);
    if (!st.isFile() || st.size > limit) fail('invalid or oversized state file');
    const buffer = Buffer.alloc(limit + 1);
    let used = 0, n;
    while (used < buffer.length && (n = fs.readSync(fd, buffer, used, buffer.length - used, null)) > 0) used += n;
    if (used > limit) fail('oversized state file');
    return buffer.subarray(0, used).toString('utf8');
  } finally { fs.closeSync(fd); }
}
function atomic(file, content) {
  const tmp = `${file}.${crypto.randomBytes(8).toString('hex')}.tmp`;
  let fd;
  try {
    fd = fs.openSync(tmp, 'wx', 0o600);
    fs.writeFileSync(fd, content); fs.fsyncSync(fd); fs.closeSync(fd); fd = undefined;
    fs.renameSync(tmp, file);
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    try { fs.unlinkSync(tmp); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  }
}
function selection(data) {
  try {
    const text = readRegular(path.join(data, 'selection'));
    const m = /^1\n(system|v\d+\.\d+\.\d+-[a-f0-9]{16})\n(-|system|v\d+\.\d+\.\d+-[a-f0-9]{16})\n$/.exec(text);
    if (!m) fail('invalid managed selection; refusing to guess a runtime');
    return { current: m[1], previous: m[2] };
  } catch (e) {
    if (e.code === 'ENOENT') return { current: 'system', previous: '-' };
    throw e;
  }
}
function writeSelection(data, current, previous) {
  atomic(path.join(data, 'selection'), `1\n${current}\n${previous}\n`);
}
function withLock(data, fn) {
  privateDir(data);
  const lock = path.join(data, 'update.lock');
  try { fs.mkdirSync(lock, { mode: 0o700 }); }
  catch (e) { if (e.code === 'EEXIST') fail('another update may be running; retained update.lock requires review'); throw e; }
  return Promise.resolve().then(fn).finally(() => fs.rmdirSync(lock));
}
function getJSON(url, timeout = 12000) {
  return new Promise((resolve, reject) => {
    if (!url.startsWith(`${REGISTRY}/`)) return reject(new Error('unexpected registry URL'));
    let total = 0, chunks = [], settled = false;
    const agent = new https.Agent({ proxyEnv: process.env });
    const finish = (error, value) => {
      if (settled) return; settled = true; clearTimeout(timer);
      if (error) { req.destroy(); reject(error); } else resolve(value);
      agent.destroy();
    };
    const req = https.get(url, { agent, headers: { Accept: 'application/json', 'User-Agent': 'codex-termux/@@VERSION@@' } }, res => {
      if (res.statusCode !== 200) { res.resume(); finish(new Error(`registry returned HTTP ${res.statusCode}`)); return; }
      res.on('data', chunk => {
        total += chunk.length;
        if (total > MAX_JSON) finish(new Error('registry response too large'));
        else chunks.push(chunk);
      });
      res.on('error', () => finish(new Error('registry response failed')));
      res.on('end', () => {
        if (settled) return;
        try { finish(null, JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
        catch (_) { finish(new Error('registry returned invalid JSON')); }
      });
    });
    const timer = setTimeout(() => finish(new Error('registry request timed out')), timeout);
    req.on('error', error => finish(new Error(`registry HTTPS request failed${/^[A-Z0-9_]+$/.test(error.code || '') ? ' (' + error.code + ')' : ''}`)));
  });
}
async function metadata(version, arch, fetch = getJSON) {
  if (!['arm64', 'x64'].includes(arch)) fail('only native ARM64 and x64 are supported');
  if (version !== 'latest') stable(version);
  const item = await fetch(`${REGISTRY}/@openai%2Fcodex/${version}`);
  stable(item.version || '');
  if (version !== 'latest' && item.version !== version) fail('registry version mismatch');
  const native = `@openai/codex-linux-${arch}`;
  const expected = `npm:@openai/codex@${item.version}-linux-${arch}`;
  if (item.name !== '@openai/codex' || item.optionalDependencies?.[native] !== expected ||
      item.bin?.codex !== 'bin/codex.js' || Object.keys(item.dependencies || {}).length) {
    fail('upstream package layout changed; keep the working runtime and review the wrapper');
  }
  return { version: item.version, native, alias: expected, arch };
}
async function checkUpdate(cache, arch, fetch = getJSON) {
  privateDir(cache);
  const lock = path.join(cache, 'check.lock');
  let owned = false;
  try {
    // A hung check has a bounded network deadline; a killed check can leave its lock.
    try { fs.mkdirSync(lock, { mode: 0o700 }); owned = true; checkLocks.add(lock); }
    catch (e) { if (e.code === 'EEXIST') return null; throw e; }
    atomic(path.join(cache, 'check-attempt'), `${Math.floor(Date.now() / 1000)}\n`);
    const result = await metadata('latest', arch, fetch);
    atomic(path.join(cache, 'update'), `1\n${Math.floor(Date.now() / 1000)}\n${result.version}\n`);
    return result;
  } finally { if (owned) { checkLocks.delete(lock); fs.rmdirSync(lock); } }
}
function cleanEnv(home) {
  const env = { ...process.env };
  for (const key of Object.keys(env)) {
    if (/^(OPENAI_API_KEY|CODEX_API_KEY|CODEX_ACCESS_TOKEN|NODE_OPTIONS|NODE_PATH|NPM_TOKEN|NODE_AUTH_TOKEN|npm_config_.*|NPM_CONFIG_.*)$/.test(key)) delete env[key];
  }
  return { ...env, HOME: home, XDG_CONFIG_HOME: path.join(home, 'config'),
    XDG_CACHE_HOME: path.join(home, 'cache'), XDG_DATA_HOME: path.join(home, 'data'),
    XDG_STATE_HOME: path.join(home, 'state'), CODEX_HOME: path.join(home, 'codex'),
    NPM_CONFIG_USERCONFIG: path.join(home, 'empty-npmrc'),
    NPM_CONFIG_GLOBALCONFIG: path.join(home, 'empty-global-npmrc'),
    NPM_CONFIG_CACHE: path.join(home, 'npm-cache'), NPM_CONFIG_UPDATE_NOTIFIER: 'false',
    NPM_CONFIG_COLOR: 'false', NO_COLOR: '1' };
}
function probe(launcher, node, env, expected, run = cp.spawnSync) {
  const child = run(node, [launcher, '--version'], { env, encoding: 'utf8', timeout: 20000, maxBuffer: 65536 });
  const m = /^codex-cli (\d+\.\d+\.\d+)\s*$/.exec(child.stdout || '');
  if (child.error || child.status !== 0 || !m || (expected && m[1] !== expected)) fail('Codex version smoke test failed; active runtime was not changed');
  return m[1];
}
function validatePackage(root, meta) {
  const base = path.join(root, 'node_modules', '@openai');
  const launcher = JSON.parse(readRegular(path.join(base, 'codex', 'package.json'), MAX_JSON));
  const native = JSON.parse(readRegular(path.join(base, `codex-linux-${meta.arch}`, 'package.json'), MAX_JSON));
  if (launcher.version !== meta.version || launcher.name !== '@openai/codex' ||
      launcher.optionalDependencies?.[meta.native] !== meta.alias ||
      native.version !== `${meta.version}-linux-${meta.arch}` || native.name !== '@openai/codex') {
    fail('installed launcher/native package identity mismatch');
  }
  return path.join(base, 'codex', 'bin', 'codex.js');
}
async function install(data, meta, options = {}, deps = {}) {
  const run = deps.run || cp.spawnSync;
  const node = options.node || process.execPath;
  return withLock(data, async () => {
    const old = selection(data);
    const runtimes = path.join(data, 'runtimes'); privateDir(runtimes);
    const work = fs.mkdtempSync(path.join(data, '.install-'));
    const stage = path.join(work, 'prefix'), home = path.join(work, 'home');
    fs.mkdirSync(stage, { mode: 0o700 }); fs.mkdirSync(home, { mode: 0o700 });
    fs.writeFileSync(path.join(home, 'empty-npmrc'), '', { mode: 0o600 });
    fs.writeFileSync(path.join(home, 'empty-global-npmrc'), '', { mode: 0o600 });
    const env = cleanEnv(home);
    let destination;
    try {
      const npm = options.npm || 'npm';
      const args = ['install', '--prefix', stage, '--no-save', '--package-lock=false', '--ignore-scripts',
        '--omit=optional', '--no-audit', '--no-fund', '--force', '--registry=' + REGISTRY,
        '--fetch-retries=1', '--fetch-timeout=30000',
        `@openai/codex@${meta.version}`, `${meta.native}@${meta.alias}`];
      // Explicit native alias + --force admits the Linux build on Android. Scripts stay disabled.
      const result = run(npm, args, { cwd: work, env, encoding: 'utf8', timeout: 300000, maxBuffer: 1024 * 1024 });
      if (result.error || result.status !== 0) fail('npm install failed or timed out; active runtime was not changed');
      let launcher = validatePackage(stage, meta);
      probe(launcher, node, env, meta.version, run);
      const id = `v${meta.version}-${crypto.randomBytes(8).toString('hex')}`;
      destination = path.join(runtimes, id);
      fs.renameSync(stage, destination);
      launcher = validatePackage(destination, meta);
      probe(launcher, node, env, meta.version, run);
      atomic(path.join(destination, 'identity.json'), JSON.stringify({ schema_version: 1, version: meta.version, arch: meta.arch }) + '\n');
      writeSelection(data, id, old.current);
      destination = undefined; // Activated runtimes are never automatically removed.
      return { version: meta.version, previous: old.current };
    } finally {
      if (destination) fs.rmSync(destination, { recursive: true, force: true });
      fs.rmSync(work, { recursive: true, force: true });
    }
  });
}
async function rollback(data, systemLauncher, options = {}, deps = {}) {
  return withLock(data, async () => {
    const old = selection(data);
    if (old.previous === '-') fail('no previous selection is recorded');
    let launcher;
    if (old.previous === 'system') {
      if (!systemLauncher) fail('original npm launcher is unavailable; no selection changed');
      launcher = systemLauncher;
    } else {
      const root = path.join(data, 'runtimes', old.previous);
      privateDir(root);
      launcher = path.join(root, 'node_modules', '@openai', 'codex', 'bin', 'codex.js');
    }
    const home = fs.mkdtempSync(path.join(data, '.probe-'));
    try {
      const v = probe(launcher, options.node || process.execPath, cleanEnv(home), undefined, deps.run || cp.spawnSync);
      writeSelection(data, old.previous, old.current);
      return { version: v };
    } finally { fs.rmSync(home, { recursive: true, force: true }); }
  });
}
function allowHosts(extra) {
  const hosts = ['openai.com', 'chatgpt.com', 'oaistatic.com', 'oaiusercontent.com'];
  for (let h of (extra || '').split(',')) {
    h = h.trim().toLowerCase().replace(/^\*?\./, '').replace(/\.$/, '');
    if (!h) continue;
    if (h.length > 253 || !h.split('.').every(s => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(s))) fail('invalid additional proxy hostname');
    hosts.push(h);
  }
  return [...new Set(hosts)];
}
function authority(text) {
  // Hostname authority only, no URL credentials, paths, query strings, or IPv6 literals.
  const m = /^([a-zA-Z0-9.-]+):([0-9]{1,5})$/.exec(text);
  if (!m) return null;
  const host = m[1].toLowerCase().replace(/\.$/, ''), port = Number(m[2]);
  if (!port || port > 65535 || host.length > 253 ||
      !host.split('.').every(s => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(s))) return null;
  return { host, port };
}
function proxy(extra, timeout, onReady, deps = {}) {
  const hosts = allowHosts(extra), sockets = new Set();
  const server = http.createServer({ maxHeaderSize: 16384, requestTimeout: 15000, headersTimeout: 10000 }, (_req, res) => {
    res.writeHead(405, { Connection: 'close', 'Content-Length': '0' }); res.end();
  });
  server.maxConnections = 256;
  server.on('connection', sock => { sockets.add(sock); sock.on('close', () => sockets.delete(sock)); sock.on('error', () => {}); });
  server.on('clientError', (_error, sock) => { sock.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n'); });
  server.on('connect', (req, client, head) => {
    const target = authority(req.url);
    const reject = (status, message) => client.end(`HTTP/1.1 ${status} ${message}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n`);
    if (!target) { reject(400, 'Bad Request'); return; }
    if (!hosts.some(h => target.host === h || target.host.endsWith('.' + h))) { reject(403, 'Forbidden'); return; }
    let established = false;
    const upstream = (deps.connect || net.connect)({ host: target.host, port: target.port });
    sockets.add(upstream); upstream.on('close', () => sockets.delete(upstream));
    const timer = setTimeout(() => { if (!established) { reject(504, 'Gateway Timeout'); upstream.destroy(); } }, timeout);
    upstream.on('connect', () => {
      established = true; clearTimeout(timer); client.setTimeout(0); upstream.setTimeout(0);
      if (client.destroyed) { upstream.destroy(); return; }
      client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
      if (head.length) upstream.write(head);
      client.pipe(upstream); upstream.pipe(client);
    });
    upstream.on('error', () => { clearTimeout(timer); if (!client.destroyed) { if (established) client.destroy(); else reject(502, 'Bad Gateway'); } });
    upstream.on('close', () => { clearTimeout(timer); if (established) client.destroy(); });
    client.on('error', () => upstream.destroy());
    client.on('close', () => { clearTimeout(timer); upstream.destroy(); });
  });
  server.listen(0, '127.0.0.1', () => onReady(server.address().port));
  return { server, close() { for (const socket of sockets) socket.destroy(); server.close(); } };
}
async function main(args) {
  const [action, ...rest] = args;
  if (action === 'proxy') {
    const [extra, timeout, cache, arch] = rest;
    const service = proxy(extra, Number(timeout), port => {
      process.stdout.write(`${port}\n`);
      if (cache) {
        checkUpdate(cache, arch).catch(() => {});
      }
    });
    const stop = () => {
      service.close();
      for (const lock of checkLocks) { try { fs.rmdirSync(lock); } catch (_) {} }
      process.exit(0);
    };
    process.on('SIGTERM', stop); process.on('SIGHUP', stop);
    // Console Ctrl+C can interrupt a request while Codex stays open. Keep its
    // proxy alive until the wrapper exits; do not interpret that event as stop.
    process.on('SIGINT', () => {});
    service.server.on('error', () => { process.stderr.write('proxy listener failed\n'); process.exit(1); });
    return;
  }
  if (action === 'check-update') {
    const [cache, arch, json, installed] = rest;
    const meta = await checkUpdate(cache, arch);
    if (!meta) fail('an update check is already active; review check.lock if a prior check was killed');
    if (json === 'json') console.log(JSON.stringify({ schema_version: 1, installed: installed || null, latest: meta.version,
      update_available: installed && VERSION.test(installed) ? newer(meta.version, installed) : null }));
    else console.log(meta.version);
    return;
  }
  if (action === 'install') {
    const [data, arch, requested, npm] = rest;
    const meta = await metadata(requested, arch);
    const result = await install(data, meta, { npm });
    console.log(`Activated Codex ${result.version}. Previous runtime retained.`); return;
  }
  if (action === 'rollback') {
    const [data, system] = rest;
    const result = await rollback(data, system);
    console.log(`Activated previous Codex runtime (${result.version}).`); return;
  }
  fail('unknown internal operation');
}
module.exports = { stable, newer, privateDir, readRegular, atomic, selection, metadata, checkUpdate,
  cleanEnv, probe, validatePackage, install, rollback, allowHosts, authority, proxy, main };
if (require.main === module || module.id === '[stdin]') {
  main(process.argv.slice(2)).catch(error => { process.stderr.write(`codex-termux: ${error.message}\n`); process.exitCode = 1; });
}
