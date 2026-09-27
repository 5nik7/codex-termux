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

// Existing diagnostic logs only. Never open the auth store, probe an account,
// echo a log record, or capture Codex's terminal streams for this advisory.
const AUTH_LOG_LIMIT = 256 * 1024;
function openAuthLog(file) {
  if (!path.isAbsolute(file) || /[\x00-\x1f\x7f]/.test(file) || path.basename(file) === 'auth.json') {
    fail('unavailable auth diagnostic log');
  }
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const st = fs.fstatSync(fd);
    if (!st.isFile() || !Number.isSafeInteger(st.size) || (process.getuid && st.uid !== process.getuid())) {
      fail('unavailable auth diagnostic log');
    }
    return { fd, st };
  } catch (error) { fs.closeSync(fd); throw error; }
}
function authLogSnapshot(file) {
  const started = Date.now();
  try {
    const { fd, st } = openAuthLog(file);
    fs.closeSync(fd);
    return { kind: 'present', dev: st.dev, ino: st.ino, size: st.size, started };
  } catch (error) {
    return { kind: error.code === 'ENOENT' ? 'missing' : 'unavailable', started };
  }
}
function authLogEvidence(text, since = 0) {
  // A record starts at a tracing timestamp, including INFO/DEBUG boundaries.
  // Merely mentioning the error in a prompt/tool INFO record is not evidence.
  const plain = text.replace(/\x1b\[[0-9;]*m/g, '');
  const header = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))\s+(TRACE|DEBUG|INFO|WARN|ERROR)\s+([^\n]*)/gm;
  const starts = [...plain.matchAll(header)];
  let found = null;
  for (let i = 0; i < starts.length; i++) {
    const match = starts[i], at = Date.parse(match[1]);
    if (!Number.isFinite(at) || at < since || !['WARN', 'ERROR'].includes(match[2])) continue;
    if (!/\b(?:codex_rmcp_client(?:::|:)|codex_core::mcp_connection_manager:|rmcp::transport::)/.test(match[3])) continue;
    const end = i + 1 < starts.length ? starts[i + 1].index : plain.length;
    if (end - match.index > 16384) continue;
    const record = plain.slice(match.index, end).replace(/\\"/g, '"');
    if (!/\bHTTP(?:\/\d(?:\.\d)?)?\s+401\b|"status"\s*:\s*401\b/.test(record) ||
        !/"code"\s*:\s*"token_expired"/.test(record)) continue;
    found = { status: 'expired_token_logged', server: /\bcodex_apps\b/.test(record) ? 'codex_apps' : null,
      recorded_at: new Date(at).toISOString() };
  }
  return found;
}
function checkAuthLog(file, snapshot = null) {
  const empty = status => ({ schema_version: 1, status, server: null, recorded_at: null,
    authentication_verified: false });
  let fd;
  try {
    const opened = openAuthLog(file); fd = opened.fd;
    const st = opened.st;
    let start = Math.max(0, st.size - AUTH_LOG_LIMIT);
    if (snapshot) {
      if (!['present', 'missing'].includes(snapshot.kind) || !Number.isFinite(snapshot.started)) return empty('unavailable');
      if (snapshot.kind === 'present') {
        if (snapshot.dev !== st.dev || snapshot.ino !== st.ino || !Number.isSafeInteger(snapshot.size) ||
            snapshot.size < 0 || st.size < snapshot.size) return empty('unavailable');
        start = snapshot.size;
      } else start = 0;
    }
    // Automatic scan: first 256 KiB appended since launch (startup errors).
    // Explicit scan: last 256 KiB of saved evidence. Neither is a live check.
    const data = Buffer.alloc(Math.min(AUTH_LOG_LIMIT, st.size - start));
    let used = 0, n;
    while (used < data.length && (n = fs.readSync(fd, data, used, data.length - used, start + used)) > 0) used += n;
    const found = authLogEvidence(data.subarray(0, used).toString('utf8'), snapshot ? snapshot.started - 5000 : 0);
    return found ? { ...empty(found.status), ...found } : empty('no_match');
  } catch (_) { return empty('unavailable'); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}
function authAdvice(server) {
  return server === 'codex_apps'
    ? ['codex_apps reported an expired authentication token.', 'Refresh your ChatGPT sign-in when ready:']
    : ['An MCP request reported an expired authentication token.', 'If the failed server is codex_apps, refresh ChatGPT sign-in:'];
}
function printAuthAdvice(server) {
  for (const line of authAdvice(server)) console.error(`codex-termux: ${line}`);
  console.error('  codex-termux logout');
  console.error('  codex-termux login');
  console.error('  codex-termux chatgpt');
  if (!server) console.error('codex-termux: For another MCP server, use its authentication flow.');
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
// Managed app server: private per-CODEX_HOME state and an authenticated live
// supervisor, never PID-based adoption or PID-based stop. Same-user state is
// trusted; surviving state after SIGKILL requires owner review.
const SERVER_FALLBACK = 'Use: codex-termux --wrapper-no-update run --no-daemon';
const AUTH_KEYS = ['OPENAI_API_KEY', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN'];
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
function serverFail(message) { fail(`${message}. ${SERVER_FALLBACK}`); }
function secretFile(file) {
  const st = fs.lstatSync(file);
  if (!st.isFile() || st.isSymbolicLink() || (st.mode & 0o077) || st.uid !== process.getuid()) serverFail('Unsafe server state');
  return readRegular(file, 65536);
}
function serverRoot(data) {
  // Resolve existing CODEX_HOME aliases without opening credentials or config.
  const home = process.env.CODEX_HOME || path.join(process.env.HOME, '.codex');
  if (!path.isAbsolute(home) || /[\x00-\x1f\x7f]/.test(home)) serverFail('CODEX_HOME must be an absolute path without control characters');
  const canonical = fs.realpathSync(home);
  privateDir(data);
  const parent = path.join(data, 'servers'); privateDir(parent);
  const root = path.join(parent, crypto.createHash('sha256').update(canonical).digest('hex').slice(0, 32));
  privateDir(root);
  return { root, home: canonical, active: path.join(root, 'active') };
}
function mac(secret, value) { return crypto.createHmac('sha256', secret).update(value).digest('hex'); }
function equalSecret(a, b) {
  // All callers compare SHA-256 MACs in canonical lowercase hex. Validate the
  // encoding before decoding: equal JS string lengths need not mean equal bytes.
  return typeof a === 'string' && typeof b === 'string' && a.length === 64 && b.length === 64 &&
    /^[a-f0-9]{64}$/.test(a) && /^[a-f0-9]{64}$/.test(b) &&
    crypto.timingSafeEqual(Buffer.from(a, 'hex'), Buffer.from(b, 'hex'));
}
function authIdentity(mode, secret) {
  return mac(secret, JSON.stringify([mode, ...AUTH_KEYS.map(k => mode === 'chatgpt' ? null : process.env[k] ?? null)]));
}
function runtimeIdentity(command, version) {
  const entries = command.map(file => {
    const real = fs.realpathSync(file), s = fs.statSync(real);
    return [real, s.dev, s.ino, s.size, s.mtimeMs];
  });
  // For npm launches validate the exact native pairing and include its identity.
  if (command.length === 2 && path.basename(command[1]) === 'codex.js') {
    const root = path.resolve(path.dirname(command[1]), '../../../..');
    const arch = process.arch === 'arm64' ? 'arm64' : 'x64';
    validatePackage(root, { version, arch, native: `@openai/codex-linux-${arch}`, alias: `npm:@openai/codex@${version}-linux-${arch}` });
    const triple = arch === 'arm64' ? 'aarch64' : 'x86_64';
    const binary = path.join(root, 'node_modules', '@openai', `codex-linux-${arch}`, 'vendor', `${triple}-unknown-linux-musl`, 'bin', 'codex');
    const s = fs.statSync(binary);
    entries.push([fs.realpathSync(binary), s.dev, s.ino, s.size, s.mtimeMs]);
  }
  return { version, digest: crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex') };
}
function websocketCheck(port, token) {
  return new Promise((resolve, reject) => {
    const key = crypto.randomBytes(16).toString('base64');
    const expected = crypto.createHash('sha1').update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    const headers = { Connection: 'Upgrade', Upgrade: 'websocket', 'Sec-WebSocket-Version': '13', 'Sec-WebSocket-Key': key };
    if (token) headers.Authorization = `Bearer ${token}`;
    let socket, done = false;
    const finish = (error, value) => {
      if (done) return; done = true; clearTimeout(timer); req.destroy(); socket?.destroy();
      error ? reject(new Error('WebSocket authentication check failed')) : resolve(value);
    };
    const req = http.request({ host: '127.0.0.1', port, path: '/', headers, agent: false });
    const timer = setTimeout(() => finish(true), 1200);
    req.on('upgrade', (res, sock) => {
      socket = sock; sock.on('error', () => {});
      finish(res.statusCode !== 101 || res.headers['sec-websocket-accept'] !== expected, 101);
    });
    req.on('response', res => { res.resume(); finish(false, res.statusCode); });
    req.on('error', () => finish(true)); req.end();
  });
}
async function authenticatedServer(port, token) {
  if (await websocketCheck(port, token) !== 101 || await websocketCheck(port, null) !== 401) throw new Error('Authentication not enforced');
}
function controlRequest(state, secret, operation) {
  return new Promise((resolve, reject) => {
    const nonce = crypto.randomBytes(24).toString('hex');
    const route = `/${operation}/${nonce}`;
    let done = false;
    const finish = (error, value) => {
      if (done) return; done = true; clearTimeout(timer); req.destroy();
      error ? reject(new Error('Owned supervisor unavailable or state mismatched; state retained; no PID was signalled')) : resolve(value);
    };
    const req = http.request({ host: '127.0.0.1', port: state.controlPort, path: route, method: 'POST', agent: false,
      headers: { 'X-Codex-Termux-Proof': mac(secret, route) } }, res => {
      let text = '';
      res.on('data', chunk => { text += chunk; if (text.length > 16384) finish(true); });
      res.on('error', () => finish(true));
      res.on('end', () => {
        if (done) return;
        try {
          if (res.statusCode !== 200 || !equalSecret(res.headers['x-codex-termux-proof'], mac(secret, nonce + text))) return finish(true);
          const reply = JSON.parse(text);
          if (JSON.stringify(reply.state) !== JSON.stringify(state)) return finish(true);
          finish(false, reply);
        } catch (_) { finish(true); }
      });
    });
    const timer = setTimeout(() => finish(true), 4000);
    req.on('error', () => finish(true)); req.end();
  });
}
function entryExists(file) {
  try { fs.lstatSync(file); return true; }
  catch (error) { if (error.code === 'ENOENT') return false; throw error; }
}
function readServer(active) {
  const st = fs.lstatSync(active);
  if (!st.isDirectory() || st.isSymbolicLink() || (st.mode & 0o077) || st.uid !== process.getuid()) serverFail('Unsafe server instance directory');
  const state = JSON.parse(secretFile(path.join(active, 'state.json')));
  if (state.schema !== 1 || !/^[a-f0-9]{32}$/.test(state.id) ||
      ![state.controlPort, state.port, state.proxyPort].every(p => Number.isInteger(p) && p > 0 && p < 65536)) serverFail('Invalid server state');
  return { state, secret: secretFile(path.join(active, 'control.token')).trim(), token: secretFile(path.join(active, 'ws.token')).trim() };
}
function portOpen(port) {
  return new Promise(resolve => {
    const sock = net.connect({ host: '127.0.0.1', port });
    const finish = value => { sock.destroy(); resolve(value); };
    sock.setTimeout(500, () => finish(true)); // uncertainty retains recovery state
    sock.on('connect', () => finish(true));
    sock.on('error', error => finish(error.code !== 'ECONNREFUSED'));
  });
}
async function serverWorker(active) {
  process.umask(0o077);
  const cfg = JSON.parse(secretFile(path.join(active, 'launch.json')));
  const secret = secretFile(path.join(active, 'control.token')).trim();
  const token = secretFile(path.join(active, 'ws.token')).trim();
  let service, control, child, state, appPort, closing = false, ready = false;
  const result = (ok, message) => atomic(path.join(cfg.root, `result-${cfg.id}.json`), JSON.stringify({ ok, message }));
  const cleanup = async (message, ok = false) => {
    if (closing) return; closing = true;
    clearTimeout(deadline);
    // Signal only the direct child handle created by this supervisor. The npm
    // launcher forwards TERM to its native child. No stored PID is used here.
    if (child && child.exitCode === null && child.signalCode === null) {
      child.kill('SIGTERM');
      const until = Date.now() + 5000;
      while (child.exitCode === null && child.signalCode === null && Date.now() < until) await delay(50);
      if (child.exitCode === null && child.signalCode === null) {
        if (!ready) result(false, 'Server did not terminate; private recovery state retained');
        ready = false; closing = false;
        return; // retain supervisor/proxy/control for a later reviewed stop
      }
    }
    // A launcher can die while its native child survives. Never declare that
    // stopped, discard its token, or infer a PID to kill from the open port.
    if (child && appPort && await portOpen(appPort)) {
      if (!ready) result(false, 'Child exited but app port remains occupied; recovery state retained');
      ready = false; closing = false; return;
    }
    service?.close(); control?.close();
    // Only known files in the directory exclusively created by this start.
    for (const name of ['state.json', 'launch.json', 'worker.cjs', 'ws.token', 'control.token']) {
      try { fs.unlinkSync(path.join(active, name)); } catch (e) { if (e.code !== 'ENOENT') return; }
    }
    try { fs.rmdirSync(active); } catch (_) { return; }
    if (!ready) result(ok, message);
    process.exit(0);
  };
  const deadline = setTimeout(() => cleanup('Startup timed out; app-server WebSocket capability or authentication unavailable'), 12000);
  process.on('SIGHUP', () => {});
  process.on('SIGINT', () => {});
  process.on('SIGTERM', () => cleanup('Startup interrupted'));
  try {
    if (JSON.stringify(runtimeIdentity(cfg.command, cfg.runtime.version)) !== JSON.stringify(cfg.runtime)) throw new Error();
    let proxyPort;
    await new Promise((resolve, reject) => {
      service = proxy(cfg.allow, cfg.timeout, p => { proxyPort = p; resolve(); });
      service.server.on('error', reject);
    });
    if (closing) return;
    // Select a temporary loopback port when omitted. The unavoidable close/bind
    // race fails closed: authentication and the child's liveness are checked.
    let port = cfg.port;
    const reserve = net.createServer();
    await new Promise((resolve, reject) => { reserve.once('error', reject); reserve.listen(port, '127.0.0.1', resolve); });
    port = reserve.address().port;
    await new Promise(resolve => reserve.close(resolve));
    if (closing) return;
    if (port === 4500) throw new Error();
    const env = { ...process.env, CODEX_HOME: cfg.home,
      HTTPS_PROXY: `http://127.0.0.1:${proxyPort}`, https_proxy: `http://127.0.0.1:${proxyPort}`,
      NO_PROXY: '127.0.0.1,localhost', no_proxy: '127.0.0.1,localhost',
      CODEX_CA_CERTIFICATE: cfg.ca, SSL_CERT_FILE: cfg.ca };
    if (cfg.auth === 'chatgpt') for (const k of AUTH_KEYS) delete env[k];
    delete env.CODEX_TERMUX_SERVER_TOKEN;
    appPort = port;
    child = cp.spawn(cfg.command[0], [...cfg.command.slice(1), 'app-server', '--listen', `ws://127.0.0.1:${port}`,
      '--ws-auth', 'capability-token', '--ws-token-file', path.join(active, 'ws.token')], { env, stdio: 'ignore' });
    child.on('error', () => cleanup('App-server could not execute'));
    child.on('exit', () => { if (!closing) cleanup('App-server exited; required WebSocket flags may be unavailable'); });
    control = http.createServer({ maxHeaderSize: 4096, requestTimeout: 2000, headersTimeout: 2000 }, (req, res) => {
      if (!state || req.method !== 'POST' || !/^\/(status|stop)\/[a-f0-9]{48}$/.test(req.url) ||
          !equalSecret(req.headers['x-codex-termux-proof'], mac(secret, req.url))) {
        res.writeHead(403); res.end(); return;
      }
      const text = JSON.stringify({ state, ready, closing });
      res.setHeader('X-Codex-Termux-Proof', mac(secret, req.url.split('/')[2] + text));
      res.end(text);
      if (req.url.startsWith('/stop/')) res.on('finish', () => cleanup('Stopped'));
    });
    control.maxConnections = 16;
    control.setTimeout(2000, socket => socket.destroy());
    control.on('clientError', (_e, sock) => sock.destroy());
    await new Promise((resolve, reject) => { control.once('error', reject); control.listen(0, '127.0.0.1', resolve); });
    state = { schema: 1, id: cfg.id, pid: process.pid, childPid: child.pid, port, proxyPort,
      controlPort: control.address().port, home: cfg.home, auth: cfg.auth, authIdentity: cfg.authIdentity, runtime: cfg.runtime };
    atomic(path.join(active, 'state.json'), JSON.stringify(state));
    while (!closing) {
      try { await authenticatedServer(port, token); break; } catch (_) { await delay(100); }
    }
    if (closing) return;
    if (child.exitCode !== null || child.signalCode !== null) return cleanup('App-server exited during readiness');
    ready = true; clearTimeout(deadline); result(true, 'Authenticated server ready');
  } catch (_) { await cleanup('Startup failed; check port availability, runtime pairing and WebSocket capabilities'); }
}
async function managedServer(args) {
  const [operation, data, wrapper, version, auth, portText, allow, timeout, ca, ...command] = args;
  const location = serverRoot(data), { root, active, home } = location;
  if (operation === 'status') console.log(`Instance: ${root}`);
  if (operation === 'start') {
    const runtime = runtimeIdentity(command, version);
    const port = Number(portText);
    if (!['inherited', 'chatgpt'].includes(auth) || !Number.isInteger(port) || port < 0 || port > 65535 || port === 4500) serverFail('Invalid server auth mode or port (4500 is reserved for external use)');
    try { fs.mkdirSync(active, { mode: 0o700 }); }
    catch (_) { serverFail('Instance already exists or startup is concurrent; use manage server status; surviving state requires review'); }
    const id = crypto.randomBytes(16).toString('hex');
    let launched = false;
    try {
      const secret = crypto.randomBytes(32).toString('hex');
      fs.writeFileSync(path.join(active, 'control.token'), secret + '\n', { flag: 'wx', mode: 0o600 });
      fs.writeFileSync(path.join(active, 'ws.token'), crypto.randomBytes(32).toString('hex') + '\n', { flag: 'wx', mode: 0o600 });
      const source = fs.readFileSync(wrapper, 'utf8');
      const marker = "<<'CODEX_TERMUX_NODE'\n";
      const begin = source.indexOf(marker), end = source.indexOf('\nCODEX_TERMUX_NODE\n', begin);
      if (begin < 0 || end < 0) throw new Error();
      fs.writeFileSync(path.join(active, 'worker.cjs'), source.slice(begin + marker.length, end), { flag: 'wx', mode: 0o600 });
      atomic(path.join(active, 'launch.json'), JSON.stringify({ root, home, id, command, runtime, auth,
        authIdentity: authIdentity(auth, secret), port, allow, timeout: Number(timeout), ca }));
      const worker = cp.spawn(process.execPath, [path.join(active, 'worker.cjs'), 'server-worker', active],
        { detached: true, stdio: 'ignore', env: { ...process.env, NODE_OPTIONS: '', NODE_PATH: '' } });
      await new Promise((resolve, reject) => { worker.once('spawn', resolve); worker.once('error', reject); });
      worker.unref(); launched = true;
      const resultPath = path.join(root, `result-${id}.json`), until = Date.now() + 20000;
      while (Date.now() < until) {
        try {
          const result = JSON.parse(secretFile(resultPath)); fs.unlinkSync(resultPath);
          if (!result.ok) serverFail(result.message);
          const live = readServer(active);
          if (live.state.id !== id) serverFail('Started instance ended and was replaced; inspect status before connecting');
          const proof = await controlRequest(live.state, live.secret, 'status');
          if (!proof.ready || proof.closing) serverFail('Server left ready state during startup; inspect status');
          console.log(`Server started: ws://127.0.0.1:${live.state.port} | Codex ${version} | auth ${auth}`);
          console.log(`Instance: ${root}`);
          console.log('Authentication is retained from server start; clients do not replace it.'); return;
        } catch (e) { if (e.code !== 'ENOENT') throw e; }
        await delay(100);
      }
      serverFail('Supervisor startup outcome unknown; state retained; inspect manage server status');
    } catch (error) {
      if (!launched) {
        for (const name of ['launch.json', 'worker.cjs', 'control.token', 'ws.token']) {
          try { fs.unlinkSync(path.join(active, name)); } catch (_) {}
        }
        try { fs.rmdirSync(active); } catch (_) {}
      }
      throw error;
    }
  }
  if (!entryExists(active)) {
    if (operation === 'status' || operation === 'stop') { console.log(`Server stopped. Instance: ${root}`); return; }
    serverFail('No managed server; use manage server start --auth inherited or --auth chatgpt');
  }
  const { state, secret, token } = readServer(active);
  // Verify the complete live record before sending a destructive request or
  // sending the WebSocket token to a port recorded on disk.
  const live = await controlRequest(state, secret, 'status');
  if (operation === 'stop') {
    await controlRequest(state, secret, 'stop');
    const until = Date.now() + 6500;
    while (entryExists(active) && Date.now() < until) await delay(100);
    if (entryExists(active)) serverFail('Stop incomplete; recovery state retained');
    console.log('Managed server and proxy stopped.'); return;
  }
  if (!live.ready || live.closing) serverFail('Managed server is not ready: starting, stopping, or recovery required');
  await authenticatedServer(state.port, token);
  let selected;
  try { selected = runtimeIdentity(command, version); } catch (_) { selected = null; }
  const matches = JSON.stringify(selected) === JSON.stringify(state.runtime);
  if (operation === 'status') {
    console.log(`Server running: ws://127.0.0.1:${state.port} | authenticated WebSocket verified`);
    console.log(`Auth: ${state.auth} (start-time environment); Codex ${state.runtime.version}; runtime ${state.runtime.digest.slice(0, 16)}`);
    console.log(`Selected runtime: ${selected ? 'Codex ' + selected.version + '; ' : ''}${matches ? 'matches' : 'MISMATCH or unavailable; connect refused; stop explicitly before restarting'}`);
    if (!matches) process.exitCode = 1;
    return;
  }
  if (operation !== 'connect') serverFail('Unknown server operation');
  if (!matches) serverFail('Running server runtime differs from the selected runtime; stop explicitly before restarting');
  if (state.auth !== auth || !equalSecret(state.authIdentity, authIdentity(auth, secret))) serverFail('Server authentication mode or credential environment differs; client cannot change server authentication');
  // Internal machine output to the frontend: URL and token *path*, never token.
  console.log(`ws://127.0.0.1:${state.port}\n${path.join(active, 'ws.token')}`);
}

async function main(args) {
  if (args[0] === "server-worker") return serverWorker(args[1]);
  if (args[0] === "server") {
    try { return await managedServer(args.slice(1)); }
    catch (error) {
      // Filesystem and child errors can contain arbitrary private paths.
      if (!error.message.includes(SERVER_FALLBACK) && !error.message.startsWith("Owned supervisor")) serverFail("Server operation failed; unsafe, missing or mismatched state/runtime");
      throw error;
    }
  }
  const [action, ...rest] = args;
  if (action === 'proxy') {
    const [extra, timeout, cache, arch, authLog, authState] = rest;
    if (authLog && authState) {
      try { fs.writeFileSync(authState, JSON.stringify(authLogSnapshot(authLog)), { mode: 0o600, flag: 'wx' }); }
      catch (_) { /* Optional, disposable advisory metadata; no startup failure. */ }
    }
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
  if (action === 'auth-check' || action === 'auth-notice') {
    const [file, option] = rest;
    let snapshot = null;
    if (action === 'auth-notice') {
      try { snapshot = JSON.parse(readRegular(option)); } catch (_) { return; }
      if (!snapshot || typeof snapshot !== 'object') return;
    }
    const result = checkAuthLog(file, snapshot);
    if (action === 'auth-notice') {
      if (result.status === 'expired_token_logged') printAuthAdvice(result.server);
      return;
    }
    if (option === 'json') console.log(JSON.stringify(result));
    else {
      if (result.status === 'expired_token_logged') {
        console.log(`Saved MCP token-expiry error: ${result.recorded_at}`);
        printAuthAdvice(result.server);
      } else if (result.status === 'no_match') console.log('No matching expired-token error in the scanned log tail.');
      else console.log('Auth diagnostic log unavailable; no authentication conclusion.');
      console.log('Saved log evidence only; current authentication was not verified.');
    }
    process.exitCode = result.status === 'expired_token_logged' ? 1 : result.status === 'unavailable' ? 3 : 0;
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
  cleanEnv, probe, validatePackage, install, rollback, allowHosts, authority, proxy,
  authLogSnapshot, authLogEvidence, checkAuthLog, websocketCheck, authenticatedServer, main };
if (require.main === module || module.id === '[stdin]') {
  main(process.argv.slice(2)).catch(error => { process.stderr.write(`codex-termux: ${error.message}\n`); process.exitCode = 1; });
}
