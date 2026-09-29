// 카카오톡 알림 간편 설정: 질문에 답하면 server/.env 를 만들어 준다.
import path from 'node:path';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';
import { readEnv, writeEnv } from './envfile.mjs';
import { pickLanIp } from './launch.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ENV_FILE = path.join(ROOT, 'server', '.env');

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
// 줄을 버퍼링해서 읽는다 (여러 줄을 한꺼번에 붙여넣어도 답이 사라지지 않게)
const lines = rl[Symbol.asyncIterator]();
const cur = readEnv(ENV_FILE);
const mask = (s) => (s ? `${s.slice(0, 4)}…${s.slice(-4)}` : '');

async function ask(question, def = '') {
  process.stdout.write(def ? `${question} [${def}]: ` : `${question}: `);
  const { value, done } = await lines.next();
  const a = done ? '' : String(value).trim();
  if (done) process.stdout.write('\n');
  return a || def;
}

console.log(`
☕ 생두 알리미 — 카카오톡 알림 설정
────────────────────────────────────────
먼저 카카오 개발자 사이트에서 앱을 하나 만들어야 해요 (무료, 5분).

  1) https://developers.kakao.com 로그인 → [내 애플리케이션] → [애플리케이션 추가]
     (앱 이름 아무거나, 예: 생두 알리미)
  2) [앱 키]에서 "REST API 키" 복사 → 아래 질문에 붙여넣기
`);

let key = await ask('REST API 키', cur.KAKAO_REST_API_KEY ? mask(cur.KAKAO_REST_API_KEY) : '');
if (key === mask(cur.KAKAO_REST_API_KEY)) key = cur.KAKAO_REST_API_KEY;
if (!key) {
  console.log('\n키가 없어서 설정을 마치지 못했어요. 키를 복사한 뒤 다시 실행해 주세요.\n');
  process.exit(1);
}

const port = cur.PORT || '8787';
const ip = pickLanIp();
const suggested = cur.PUBLIC_BASE_URL || `http://${ip ?? 'localhost'}:${port}`;
console.log(`
서버 주소는 휴대폰에서 이 PC 서버로 들어올 때 쓰는 주소예요.
 - 집 와이파이에서만 쓸 거면 그대로 Enter
 - 밖에서도 알림 링크를 열고 싶거나 카카오가 주소를 받아 주지 않으면,
   ngrok / Cloudflare Tunnel 로 만든 https 주소나 클라우드 서버 주소를 적어 주세요.`);
const baseUrl = (await ask('서버 주소', suggested)).replace(/\/$/, '');

const secret = await ask('Client Secret (보안 → Client Secret 을 켰을 때만, 아니면 Enter)', cur.KAKAO_CLIENT_SECRET ? mask(cur.KAKAO_CLIENT_SECRET) : '');

writeEnv(ENV_FILE, {
  KAKAO_REST_API_KEY: key,
  KAKAO_CLIENT_SECRET: secret === mask(cur.KAKAO_CLIENT_SECRET) ? cur.KAKAO_CLIENT_SECRET : secret,
  PUBLIC_BASE_URL: baseUrl,
});
rl.close();

const origin = new URL(baseUrl).origin;
console.log(`
✅ 저장했어요: ${ENV_FILE}

마지막으로 카카오 개발자 사이트의 내 앱에서 아래 3가지를 해 주세요.

  ① [플랫폼] → [Web 플랫폼 등록] → 사이트 도메인:
       ${origin}
  ② [카카오 로그인] → 활성화 설정 ON → Redirect URI 등록:
       ${baseUrl}/auth/kakao/callback
  ③ [카카오 로그인] → [동의항목] → "카카오톡 메시지 전송" → 사용(선택 동의)

그다음 생두 알리미를 다시 실행하고, 앱의 [🔔 알림] 탭 → "카카오톡으로 알림 받기"를 누르면 끝!
`);
