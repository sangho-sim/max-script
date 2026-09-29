import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/server.js';
import { Store } from '../src/store.js';
import { KakaoClient } from '../src/kakao.js';
import { loadDemoData, DEMO_SHOP } from '../src/demo.js';

let server;
let base;
const store = new Store(null);
const DEVICE = 'test-device-0123456789';

before(async () => {
  loadDemoData(store);
  const kakao = new KakaoClient({ restApiKey: 'key', redirectUri: 'https://srv/auth/kakao/callback' });
  const app = createApp({ store, shops: [DEMO_SHOP], kakao, cfg: { baseUrl: 'https://srv', appScheme: 'greenbean', adminToken: 'secret' } });
  await new Promise((r) => (server = app.listen(0, r)));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => server.close());

const get = async (p) => {
  const r = await fetch(base + p, { redirect: 'manual' });
  return { status: r.status, headers: r.headers, body: r.headers.get('content-type')?.includes('json') ? await r.json() : await r.text() };
};

test('GET /api/beans 검색', async () => {
  const r = await get('/api/beans?q=' + encodeURIComponent('게이샤'));
  assert.equal(r.status, 200);
  assert.equal(r.body.total, 1);
  assert.match(r.body.items[0].name, /게이샤/);
});

test('GET /api/beans/:id 와 /go/:id 리다이렉트', async () => {
  const id = encodeURIComponent('demo:1000');
  const r = await get(`/api/beans/${id}`);
  assert.equal(r.status, 200);
  assert.equal(r.body.id, 'demo:1000');
  const go = await get(`/go/${id}`);
  assert.equal(go.status, 302);
  assert.equal(go.headers.get('location'), 'https://example.com/demo/1000');
  assert.equal((await get('/go/none')).status, 404);
});

test('GET /api/meta', async () => {
  const r = await get('/api/meta');
  assert.ok(r.body.facets.origins.length > 5);
  assert.ok(r.body.keywordPresets.some((g) => g.group === '가공방식'));
  assert.equal(r.body.flavorCategories[0].profile, undefined);
  assert.equal(r.body.shops[0].id, 'demo');
});

test('기기 알림 설정 저장/조회 (쇼핑몰 선택 포함)', async () => {
  const put = await fetch(`${base}/api/devices/${DEVICE}/alerts`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ keywords: ['게이샤', ''], shops: ['demo'], restock: true, maxPricePerKg: '30000' }),
  }).then((r) => r.json());
  assert.deepEqual(put.alerts.keywords, ['게이샤']);
  assert.deepEqual(put.alerts.shops, ['demo']);
  assert.equal(put.alerts.maxPricePerKg, 30000);
  const r = await get(`/api/devices/${DEVICE}`);
  assert.equal(r.body.kakaoConnected, false);
  assert.equal(r.body.alerts.restock, true);
  assert.equal((await get('/api/devices/bad')).status, 400);
});

test('카카오 로그인은 state 를 붙여 카카오로 보냄, 모르는 state 는 거절', async () => {
  const r = await get(`/auth/kakao/login?device=${DEVICE}`);
  assert.equal(r.status, 302);
  const loc = new URL(r.headers.get('location'));
  assert.equal(loc.host, 'kauth.kakao.com');
  assert.equal(loc.searchParams.get('scope'), 'talk_message');
  assert.ok(loc.searchParams.get('state'));
  const cb = await get('/auth/kakao/callback?code=abc&state=unknown');
  assert.match(cb.body, /만료/);
});

test('관리자 크롤은 토큰 필요', async () => {
  const r = await fetch(`${base}/api/admin/crawl`, { method: 'POST' });
  assert.equal(r.status, 401);
});

test('웹 목록 페이지', async () => {
  const r = await get('/');
  assert.match(r.body, /최근 입고 생두/);
  assert.match(r.body, /\/go\/demo%3A/);
});
