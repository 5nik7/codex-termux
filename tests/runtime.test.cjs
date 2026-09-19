'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const net = require('node:net');
const events = require('node:events');
const { spawnSync } = require('node:child_process');
const rt = require('../src/runtime.cjs');

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-termux-tests-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}
function expiredRecord(server = 'codex_apps', time = new Date().toISOString()) {
  return time + ' ERROR codex_rmcp_client::event_notification_transport: ' + server + ': unexpected server response: HTTP 401: {\n' +
    '  "error": {"code": "token_expired", "message": "private-fixture-never-echo"}\n}\n';
}
test('auth evidence requires an MCP warning/error, HTTP 401 and the exact expiry code', () => {
  const record = expiredRecord();
  assert.equal(rt.authLogEvidence(record).server, 'codex_apps');
  assert.equal(rt.authLogEvidence(expiredRecord('')).server, null);
  assert.equal(rt.authLogEvidence(record.replace(' ERROR ', ' INFO ')), null);
  assert.equal(rt.authLogEvidence(record.replace('HTTP 401', 'HTTP 403')), null);
  assert.equal(rt.authLogEvidence(record.replace('token_expired', 'invalid_api_key')), null);
  assert.equal(rt.authLogEvidence(record.replace('codex_rmcp_client::event_notification_transport', 'user_tool')), null);
  const info = new Date().toISOString() + ' INFO codex_core::tools: prompt mentions HTTP 401 {"code":"token_expired"} codex_apps\n';
  assert.equal(rt.authLogEvidence(info), null);
  assert.equal(rt.authLogEvidence(record.split('HTTP 401')[0] + '\n' + info), null);
  assert.equal(rt.authLogEvidence(record, Date.now() + 60000), null);
  assert.equal(rt.authLogEvidence(record.replace(' ERROR ', ' \x1b[31mERROR\x1b[0m ')).server, 'codex_apps');
  assert.equal(rt.authLogEvidence(record.replaceAll('"', '\\"')).server, 'codex_apps');
});
test('automatic auth scan ignores old bytes and detects new errors without leaking records', t => {
  const file = path.join(fixture(t), 'codex-tui.log');
  fs.writeFileSync(file, expiredRecord());
  const before = rt.authLogSnapshot(file);
  assert.equal(rt.checkAuthLog(file, before).status, 'no_match');
  fs.appendFileSync(file, expiredRecord());
  const result = rt.checkAuthLog(file, before);
  assert.equal(result.status, 'expired_token_logged');
  assert.equal(result.authentication_verified, false);
  assert.equal(JSON.stringify(result).includes('private-fixture'), false);
  assert.equal(JSON.stringify(result).includes(file), false);
});
test('auth scan supports a newly created log and skips rotation/truncation', t => {
  const file = path.join(fixture(t), 'codex-tui.log');
  const missing = rt.authLogSnapshot(file);
  assert.equal(missing.kind, 'missing');
  fs.writeFileSync(file, expiredRecord());
  assert.equal(rt.checkAuthLog(file, missing).status, 'expired_token_logged');
  const before = rt.authLogSnapshot(file);
  fs.renameSync(file, file + '.old');
  fs.writeFileSync(file, expiredRecord());
  assert.equal(rt.checkAuthLog(file, before).status, 'unavailable');
  const current = rt.authLogSnapshot(file);
  fs.truncateSync(file, 0);
  assert.equal(rt.checkAuthLog(file, current).status, 'unavailable');
});
test('auth scanner is bounded and separates startup bytes from explicit saved-log tail', t => {
  const file = path.join(fixture(t), 'codex-tui.log');
  const before = rt.authLogSnapshot(file);
  fs.writeFileSync(file, expiredRecord() + new Date().toISOString() + ' INFO codex_core: ' + 'x'.repeat(300000) + '\n');
  assert.equal(rt.checkAuthLog(file, before).status, 'expired_token_logged');
  assert.equal(rt.checkAuthLog(file).status, 'no_match');
  fs.appendFileSync(file, expiredRecord());
  assert.equal(rt.checkAuthLog(file).status, 'expired_token_logged');
});
test('auth scanner refuses special files, symlinks and auth.json without blocking', { timeout: 3000 }, t => {
  const root = fixture(t), file = path.join(root, 'codex-tui.log');
  fs.writeFileSync(file, expiredRecord());
  const link = path.join(root, 'link'); fs.symlinkSync(file, link);
  const fifo = path.join(root, 'fifo');
  assert.equal(spawnSync('mkfifo', [fifo]).status, 0);
  const credentials = path.join(root, 'auth.json'); fs.writeFileSync(credentials, expiredRecord());
  for (const item of [root, link, fifo, credentials, 'relative.log']) {
    assert.equal(rt.checkAuthLog(item).status, 'unavailable');
    assert.equal(rt.authLogSnapshot(item).kind, 'unavailable');
  }
  assert.equal(rt.checkAuthLog(path.join(root, 'absent')).status, 'unavailable');
  assert.equal(rt.checkAuthLog(file, { kind: 'present', size: -1, started: Date.now() }).status, 'unavailable');
});
function meta(v = '0.153.4', arch = 'arm64') {
  return { version: v, arch, native: `@openai/codex-linux-${arch}`, alias: `npm:@openai/codex@${v}-linux-${arch}` };
}
function upstream(v = '0.153.4', arch = 'arm64') {
  const m = meta(v, arch);
  return { name: '@openai/codex', version: v, bin: { codex: 'bin/codex.js' }, optionalDependencies: { [m.native]: m.alias } };
}
function fakeInstall(m, options = {}) {
  let probes = 0;
  const calls = [];
  function run(command, args, opts) {
    calls.push({ command, args, opts });
    if (args[0] === 'install') {
      if (options.npmFail) return { status: 1, stdout: '', stderr: 'private token must not be printed' };
      const root = args[args.indexOf('--prefix') + 1];
      const base = path.join(root, 'node_modules/@openai');
      fs.mkdirSync(path.join(base, 'codex/bin'), { recursive: true });
      fs.mkdirSync(path.join(base, `codex-linux-${m.arch}`), { recursive: true });
      fs.writeFileSync(path.join(base, 'codex/package.json'), JSON.stringify(upstream(m.version, m.arch)));
      fs.writeFileSync(path.join(base, 'codex/bin/codex.js'), '// fixture');
      fs.writeFileSync(path.join(base, `codex-linux-${m.arch}/package.json`), JSON.stringify({ name: '@openai/codex', version: options.badNative ? '0.0.0' : `${m.version}-linux-${m.arch}` }));
      return { status: 0, stdout: '' };
    }
    probes++;
    if (probes === options.failProbe) return { status: 1, stdout: '' };
    return { status: 0, stdout: `codex-cli ${m.version}\n` };
  }
  return { run, calls };
}
test('strict versions and numeric comparison reject injection and prereleases', () => {
  assert.equal(rt.newer('0.155.0', '0.99.9'), true);
  assert.equal(rt.newer('0.153.4', '0.153.4'), false);
  for (const bad of ['01.2.3', '../oops', '1.2.3;touch', '1.2.3-beta', '999999999.2.3']) assert.throws(() => rt.stable(bad));
});
test('metadata requires an exact platform alias and known launcher layout', async () => {
  const a = await rt.metadata('0.153.4', 'arm64', async () => upstream());
  assert.deepEqual(a, meta());
  for (const item of [{ ...upstream(), version: '0.153.5' }, { ...upstream(), optionalDependencies: {} }, { ...upstream(), dependencies: { unexpected: '*' } }]) {
    await assert.rejects(rt.metadata('0.153.4', 'arm64', async () => item));
  }
});
test('check updates private cache; a failed check preserves prior cache', async t => {
  const dir = path.join(fixture(t), 'cache');
  await rt.checkUpdate(dir, 'arm64', async () => upstream());
  const prior = fs.readFileSync(path.join(dir, 'update'));
  assert.match(prior.toString(), /^1\n\d+\n0\.153\.4\n$/);
  assert.equal(fs.statSync(path.join(dir, 'update')).mode & 0o777, 0o600);
  await assert.rejects(rt.checkUpdate(dir, 'arm64', async () => { throw Error('offline'); }));
  assert.deepEqual(fs.readFileSync(path.join(dir, 'update')), prior);
  assert.equal(fs.existsSync(path.join(dir, 'check.lock')), false);
});
test('staged install pins both packages, disables scripts, probes relocated runtime, activates atomically', async t => {
  const data = path.join(fixture(t), 'data'), fake = fakeInstall(meta());
  await rt.install(data, meta(), { node: '/native/node', npm: '/native/npm' }, fake);
  const selected = rt.selection(data);
  assert.match(selected.current, /^v0\.153\.4-[a-f0-9]{16}$/);
  assert.equal(selected.previous, 'system');
  assert.equal(fake.calls.length, 3);
  const npm = fake.calls[0];
  for (const arg of ['--ignore-scripts', '--omit=optional', '--force', '@openai/codex@0.153.4', '@openai/codex-linux-arm64@npm:@openai/codex@0.153.4-linux-arm64']) assert.ok(npm.args.includes(arg));
  assert.ok(fake.calls[1].args[0].includes('.install-'));
  assert.ok(fake.calls[2].args[0].includes('/runtimes/'));
  assert.equal(fs.existsSync(path.join(data, 'update.lock')), false);
  assert.equal(fs.readdirSync(data).some(p => p.startsWith('.install-')), false);
});
test('npm failure, corrupt package, and each smoke-test failure preserve active runtime', async t => {
  for (const options of [{ npmFail: true }, { badNative: true }, { failProbe: 1 }, { failProbe: 2 }]) {
    const data = path.join(fixture(t), 'data');
    const first = fakeInstall(meta()); await rt.install(data, meta(), {}, first);
    const before = fs.readFileSync(path.join(data, 'selection'));
    await assert.rejects(rt.install(data, meta('0.154.0'), {}, fakeInstall(meta('0.154.0'), options)));
    assert.deepEqual(fs.readFileSync(path.join(data, 'selection')), before);
    assert.equal(fs.readdirSync(path.join(data, 'runtimes')).length, 1);
    assert.equal(fs.existsSync(path.join(data, 'update.lock')), false);
  }
});
test('update lock refuses concurrency without changing lock or selection', async t => {
  const data = path.join(fixture(t), 'data'); fs.mkdirSync(data, { mode: 0o700 });
  fs.mkdirSync(path.join(data, 'update.lock'));
  await assert.rejects(rt.install(data, meta(), {}, fakeInstall(meta())), /another update/);
  assert.equal(fs.existsSync(path.join(data, 'update.lock')), true);
  assert.equal(fs.existsSync(path.join(data, 'selection')), false);
});
test('rollback validates the prior selection; a failed probe changes nothing', async t => {
  const data = path.join(fixture(t), 'data');
  await rt.install(data, meta(), {}, fakeInstall(meta()));
  const before = fs.readFileSync(path.join(data, 'selection'));
  await assert.rejects(rt.rollback(data, '/system/launcher', {}, fakeInstall(meta(), { failProbe: 1 })));
  assert.deepEqual(fs.readFileSync(path.join(data, 'selection')), before);
  await rt.rollback(data, '/system/launcher', {}, fakeInstall(meta()));
  const current = rt.selection(data);
  assert.equal(current.current, 'system');
  assert.match(current.previous, /^v0.153.4-/);
});
test('managed paths reject writable dirs, symlinks, and malformed selections', t => {
  const root = fixture(t), data = path.join(root, 'data');
  fs.mkdirSync(data, { mode: 0o755 });
  // Explicit fixture permissions, independent of the caller's umask.
  fs.chmodSync(data, 0o755);
  assert.equal(fs.lstatSync(data).mode & 0o777, 0o755);
  assert.throws(() => rt.privateDir(data), /0700/);
  const link = path.join(root, 'link'); fs.symlinkSync(data, link);
  assert.throws(() => rt.privateDir(link));
  fs.writeFileSync(path.join(data, 'selection'), '1\n../../evil\n-\n');
  assert.throws(() => rt.selection(data));
});
test('installer environment clears auth and npm config; keeps native PATH and transport proxy', () => {
  const keys = ['OPENAI_API_KEY', 'CODEX_ACCESS_TOKEN', 'npm_config_registry', 'NODE_OPTIONS'];
  const prior = Object.fromEntries(keys.map(k => [k, process.env[k]]));
  try {
    for (const k of keys) process.env[k] = 'private-fixture';
    const env = rt.cleanEnv('/owned/home');
    for (const k of keys) assert.equal(env[k], undefined);
    assert.equal(env.HOME, '/owned/home'); assert.equal(env.PATH, process.env.PATH);
    assert.equal(env.HTTPS_PROXY, process.env.HTTPS_PROXY);
  } finally { for (const k of keys) if (prior[k] === undefined) delete process.env[k]; else process.env[k] = prior[k]; }
});
test('CONNECT authority parsing preserves explicit ports and rejects URL forms', () => {
  assert.deepEqual(rt.authority('AUTH.OpenAI.com:80'), { host: 'auth.openai.com', port: 80 });
  for (const item of ['auth.openai.com', 'user@auth.openai.com:443', 'auth.openai.com:443/path', 'auth.openai.com:0', 'auth.openai.com:65536', 'auth.openai.com:443?x', 'auth.openai.com:443#x']) assert.equal(rt.authority(item), null);
  assert.throws(() => rt.allowHosts('https://example.com'));
});
async function connect(port, request) {
  const sock = net.connect({ host: '127.0.0.1', port });
  await events.once(sock, 'connect'); sock.write(request);
  const [buffer] = await events.once(sock, 'data');
  return { sock, text: buffer.toString() };
}
test('real loopback proxy denies unknown/suffix-confusion hosts and plain HTTP', { timeout: 5000 }, async t => {
  let ready; const port = new Promise(r => { ready = r; });
  const service = rt.proxy('', 1000, ready); t.after(() => service.close());
  const p = await port;
  assert.equal(service.server.address().address, '127.0.0.1');
  for (const host of ['evil.example', 'openai.com.evil.example', 'notopenai.com']) {
    const r = await connect(p, `CONNECT ${host}:443 HTTP/1.1\r\nHost: ${host}\r\n\r\n`);
    assert.match(r.text, /403 Forbidden/); r.sock.destroy();
  }
  const r = await connect(p, 'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n');
  assert.match(r.text, /405/); r.sock.destroy();
});
test('real CONNECT tunnel transports bytes and survives connection timeout after establishment', { timeout: 5000 }, async t => {
  const echo = net.createServer(s => s.pipe(s)); echo.listen(0, '127.0.0.1');
  await events.once(echo, 'listening'); t.after(() => echo.close());
  let ready; const port = new Promise(r => { ready = r; });
  const service = rt.proxy('127.0.0.1', 30, ready); t.after(() => service.close());
  const upstream = echo.address().port;
  const r = await connect(await port, `CONNECT 127.0.0.1:${upstream} HTTP/1.1\r\nHost: localhost\r\n\r\n`);
  assert.match(r.text, /200 Connection Established/);
  await new Promise(done => setTimeout(done, 100));
  r.sock.write('opaque TLS-like bytes\0');
  const [reply] = await events.once(r.sock, 'data');
  assert.equal(reply.toString(), 'opaque TLS-like bytes\0'); r.sock.destroy();
});
test('CONNECT handshake timeout is bounded', { timeout: 3000 }, async t => {
  let ready; const port = new Promise(r => { ready = r; });
  const service = rt.proxy('', 30, ready, { connect: () => new net.Socket() });
  t.after(() => service.close());
  const r = await connect(await port, 'CONNECT auth.openai.com:443 HTTP/1.1\r\nHost: auth.openai.com\r\n\r\n');
  assert.match(r.text, /504 Gateway Timeout/); r.sock.destroy();
});
