// 생두 알리미 간편 실행기.
//   node scripts/launch.mjs            실제 쇼핑몰 수집으로 실행
//   node scripts/launch.mjs --demo     샘플 데이터로 실행 (쇼핑몰 접속 없음)
//   node scripts/launch.mjs --tunnel   휴대폰이 다른 네트워크(LTE 등)에 있을 때
//   node scripts/launch.mjs --server   서버만 (앱 개발 서버 없이)
// 처음 실행하면 필요한 패키지를 알아서 설치하고, PC 의 내부 IP 를 찾아 앱이 서버를 바라보게 한 뒤
// 서버와 앱(Expo)을 함께 띄운다. 창을 닫거나 Ctrl+C 를 누르면 둘 다 꺼진다.
import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readEnv } from './envfile.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SERVER = path.join(ROOT, 'server');
const MOBILE = path.join(ROOT, 'mobile');
const isWin = process.platform === 'win32';
const args = new Set(process.argv.slice(2));
const demo = args.has('--demo');

const say = (msg = '') => console.log(msg);
const fail = (msg) => {
  console.error(`\n❌ ${msg}\n`);
  process.exit(1);
};

// ---------- 1. Node 버전 ----------
const [major, minor] = process.versions.node.split('.').map(Number);
if (major < 20 || (major === 20 && minor < 12)) {
  fail(`Node.js ${process.versions.node} 은(는) 너무 오래되었습니다. https://nodejs.org 에서 LTS 버전을 설치한 뒤 다시 실행해 주세요.`);
}

// ---------- 2. 처음이면 설치 ----------
// 설치가 끝나면 package-lock.json 의 지문을 남겨 두고, 지문이 달라지면(업데이트 후) 다시 설치한다
const lockHash = (dir) => {
  const lock = path.join(dir, 'package-lock.json');
  return fs.existsSync(lock) ? createHash('sha1').update(fs.readFileSync(lock)).digest('hex') : 'none';
};
const markerOf = (dir) => path.join(dir, 'node_modules', '.greenbean-installed');

export function needsInstall(dir) {
  const marker = markerOf(dir);
  return !fs.existsSync(marker) || fs.readFileSync(marker, 'utf8').trim() !== lockHash(dir);
}

function install(dir, label) {
  say(`📦 ${label} 설치 중… (처음 한 번만, 몇 분 걸릴 수 있어요)`);
  const r = spawnSync(isWin ? 'npm.cmd' : 'npm', ['install', '--no-fund', '--no-audit', '--loglevel=error'], { cwd: dir, stdio: 'inherit', shell: isWin });
  if (r.status !== 0) fail(`${label} 설치에 실패했습니다. 인터넷 연결을 확인하고 다시 실행해 주세요.`);
  fs.writeFileSync(markerOf(dir), lockHash(dir));
}

// ---------- 3. PC 의 내부 IP ----------
const VIRTUAL = /(vethernet|virtual|vmware|vbox|docker|wsl|hyper-v|loopback|tailscale|zerotier|utun|bridge|br-|veth|tun|tap)/i;
const PREFERRED = /(wi-?fi|wlan|wireless|무선|en0|en1|eth|이더넷|ethernet|로컬 영역)/i;

export function pickLanIp(interfaces = os.networkInterfaces()) {
  const candidates = [];
  for (const [name, addrs] of Object.entries(interfaces)) {
    for (const a of addrs ?? []) {
      if (a.family !== 'IPv4' && a.family !== 4) continue;
      if (a.internal || a.address.startsWith('169.254.')) continue;
      const priv = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(a.address);
      let score = 0;
      if (priv) score += 4;
      if (a.address.startsWith('192.168.')) score += 1; // 가정용 공유기
      if (PREFERRED.test(name)) score += 2;
      if (VIRTUAL.test(name)) score -= 10;
      candidates.push({ name, address: a.address, score });
    }
  }
  candidates.sort((x, y) => y.score - x.score);
  return candidates[0]?.address ?? null;
}

// ---------- 4. 서버 ----------
const portFree = (port) =>
  new Promise((resolve) => {
    const s = net.createServer().once('error', () => resolve(false)).once('listening', () => s.close(() => resolve(true)));
    s.listen(port, '0.0.0.0');
  });

async function health(port) {
  try {
    const r = await fetch(`http://127.0.0.1:${port}/health`, { signal: AbortSignal.timeout(1500) });
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  }
}

const children = [];
function shutdown(code = 0) {
  for (const c of children) {
    if (c.exitCode != null) continue;
    if (isWin) spawnSync('taskkill', ['/pid', String(c.pid), '/t', '/f'], { stdio: 'ignore' });
    else c.kill('SIGINT');
  }
  process.exit(code);
}
process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

async function main() {
  say('');
  say('☕  생두 알리미' + (demo ? '  (샘플 데이터 모드)' : ''));
  say('────────────────────────────────────────');

  if (needsInstall(SERVER)) install(SERVER, '서버');
  if (!args.has('--server') && needsInstall(MOBILE)) install(MOBILE, '앱');

  // 포트·서버 주소는 server/.env 를 따른다 (카카오 설정 스크립트가 만든 파일)
  const envFile = readEnv(path.join(SERVER, '.env'));
  const port = Number(process.env.PORT || envFile.PORT || 8787);

  const ip = pickLanIp();
  if (!ip) say('⚠️  와이파이/랜 IP 를 찾지 못했습니다. 휴대폰에서 접속하려면 PC 가 공유기에 연결되어 있어야 해요.');
  const apiUrl = `http://${ip ?? 'localhost'}:${port}`;

  if (!(await portFree(port))) {
    if (await health(port)) say(`ℹ️  서버가 이미 켜져 있어 그대로 사용합니다 (포트 ${port}).`);
    else fail(`포트 ${port} 를 다른 프로그램이 쓰고 있습니다. server/.env 에 PORT=8788 처럼 다른 번호를 적어 주세요.`);
  } else {
    fs.mkdirSync(path.join(SERVER, 'data'), { recursive: true });
    const logFile = path.join(SERVER, 'data', 'server.log');
    const log = fs.openSync(logFile, 'a');
    const server = spawn(process.execPath, ['src/server.js', ...(demo ? ['--demo'] : [])], {
      cwd: SERVER,
      // 서버 주소를 따로 정하지 않았으면 휴대폰이 닿는 내부 IP 주소를 쓴다 (알림 링크·웹 목록용)
      env: { ...process.env, PORT: String(port), ...(process.env.PUBLIC_BASE_URL || envFile.PUBLIC_BASE_URL ? {} : { PUBLIC_BASE_URL: apiUrl }) },
      // 앱(Expo) 화면과 섞이지 않게 서버 기록은 파일로
      stdio: args.has('--server') ? 'inherit' : ['ignore', log, log],
    });
    children.push(server);
    server.on('exit', (code) => {
      if (code) {
        say(`\n❌ 서버가 꺼졌습니다 (코드 ${code}). 기록: ${logFile}`);
        shutdown(1);
      }
    });
    let ok = null;
    for (let i = 0; i < 40 && !ok; i++) {
      await new Promise((r) => setTimeout(r, 250));
      ok = await health(port);
    }
    if (!ok) fail(`서버가 켜지지 않았습니다. 기록을 확인해 주세요: ${logFile}`);
    say(`✅ 서버 켜짐  → ${apiUrl}   (생두 ${ok.beans}개)`);
    if (!args.has('--server')) say(`   서버 기록: ${logFile}`);
    if (!demo) say('   쇼핑몰 수집을 시작했어요. 처음 수집은 몇 분 걸리고, 그 뒤 60분마다 다시 수집합니다.');
  }
  say(
    process.env.KAKAO_REST_API_KEY || envFile.KAKAO_REST_API_KEY
      ? '💬 카카오톡 알림: 설정됨'
      : `💬 카카오톡 알림: 아직 설정 안 됨 → "${isWin ? '카카오톡 알림 설정.bat' : '카카오톡 알림 설정.command'}" 실행`,
  );

  if (args.has('--server')) return;

  say('');
  say('📱 휴대폰에서 여는 방법');
  say('   1) 앱스토어/플레이스토어에서 "Expo Go" 설치');
  say('   2) 휴대폰을 이 PC 와 같은 와이파이에 연결');
  say('   3) 아래에 나오는 QR 코드를 찍기 (아이폰: 기본 카메라, 안드로이드: Expo Go 앱 안에서)');
  if (isWin) say('   ※ Windows 방화벽 창이 뜨면 "허용"을 눌러 주세요.');
  say('   끄려면 이 창을 닫거나 Ctrl+C');
  say('────────────────────────────────────────');

  const expoArgs = ['expo', 'start', ...(args.has('--tunnel') ? ['--tunnel'] : [])];
  const expo = spawn(isWin ? 'npx.cmd' : 'npx', expoArgs, {
    cwd: MOBILE,
    env: { ...process.env, EXPO_PUBLIC_API_URL: apiUrl },
    stdio: 'inherit',
    shell: isWin,
  });
  children.push(expo);
  expo.on('exit', (code) => shutdown(code ?? 0));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((e) => fail(e.message));
}
