import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Store } from '../src/store.js';
import { search, facets, beanMatches } from '../src/search.js';
import { alertMatches, notifyUsers } from '../src/notifier.js';
import { KakaoClient, buildAlertTemplate } from '../src/kakao.js';
import { demoRawProducts, DEMO_SHOP, loadDemoData } from '../src/demo.js';

const shopA = { id: 'a', name: 'A몰' };
const shopB = { id: 'b', name: 'B몰' };
const raw = (id, name, extra = {}) => ({ productId: id, url: `https://a/${id}`, name, price: 10000, ...extra });

test('applyCrawl: 처음 긁는 몰은 신규 알림 없음 → 이후 새 상품만 신규, 품절 해제는 재입고, 사라지면 판매 종료', () => {
  const s = new Store(null);
  let r = s.applyCrawl(shopA, [raw('1', '케냐 AA 1kg'), raw('2', '브라질 세하도 1kg', { soldOut: true })], { ok: true });
  assert.equal(r.newBeans.length, 0);
  r = s.applyCrawl(shopA, [raw('1', '케냐 AA 1kg'), raw('2', '브라질 세하도 1kg'), raw('3', '파나마 게이샤 200g')], { ok: true });
  assert.deepEqual(r.newBeans.map((b) => b.id), ['a:3']);
  assert.deepEqual(r.restocked.map((b) => b.id), ['a:2']);
  r = s.applyCrawl(shopA, [raw('1', '케냐 AA 1kg')], { ok: true });
  assert.equal(s.getBean('a:3').delisted, true);
  assert.equal(s.getBean('a:1').delisted, false);
});

test('applyCrawl: 상세를 다시 안 읽어도 예전 컵노트 유지', () => {
  const s = new Store(null);
  s.applyCrawl(shopA, [raw('1', '에티오피아 예가체프 1kg', { detailText: '컵노트: 자스민, 레몬', detailFetchedAt: new Date().toISOString() })], { ok: true });
  s.applyCrawl(shopA, [raw('1', '에티오피아 예가체프 1kg')], { ok: true });
  assert.deepEqual(s.getBean('a:1').notes.map((n) => n.label), ['자스민', '레몬']);
  assert.equal(s.needsDetail('a', '1'), false);
  assert.equal(s.needsDetail('a', '2'), true);
});

function demoStore() {
  const s = new Store(null);
  loadDemoData(s);
  return s;
}

test('검색: 이름·별칭·산지·품종·가공·회사·가격·키워드·향미', () => {
  const beans = demoStore().allBeans();
  const names = (p) => search(beans, { pageSize: 100, ...p }).items.map((b) => b.name);
  assert.ok(names({ q: '예가체프' }).every((n) => n.includes('예가체프')));
  assert.ok(names({ q: 'yirgacheffe' }).some((n) => n.includes('예가체프'))); // 영문 별칭
  assert.ok(names({ q: '게샤' }).some((n) => n.includes('게이샤'))); // 표기 차이
  assert.deepEqual(names({ origin: '케냐' }), ['케냐 니에리 AA 워시드 SL28 SL34 1kg']);
  assert.ok(names({ variety: '파카마라' }).length === 1);
  assert.ok(names({ process: '내추럴' }).length >= 3);
  assert.equal(names({ shop: 'nope' }).length, 0);
  assert.ok(names({ maxPrice: 12000 }).every((n) => n));
  const cheap = search(beans, { maxPrice: 12000, pageSize: 100 }).items;
  assert.ok(cheap.length > 0 && cheap.every((b) => b.price <= 12000));
  const perKg = search(beans, { priceBasis: 'kg', maxPrice: 15000, pageSize: 100 }).items;
  assert.ok(perKg.every((b) => b.pricePerKg <= 15000));
  assert.ok(names({ keyword: '케냐 AA' }).length === 1); // 여러 단어 키워드
  assert.ok(names({ keyword: ['워시드', 'G1'] }).every((n) => /G1/.test(n) && /워시드/.test(n)));
  assert.ok(search(beans, { flavor: 'berry', pageSize: 100 }).items.every((b) => b.notes.some((n) => n.category === 'berry')));
  assert.ok(names({ keyword: '초콜릿' }).length >= 5); // 향미 카테고리 이름으로도
});

test('검색: 정렬, 품절은 뒤로, 페이지', () => {
  const beans = demoStore().allBeans();
  const asc = search(beans, { sort: 'price_asc', pageSize: 100 }).items;
  const inStock = asc.filter((b) => !b.soldOut);
  for (let i = 1; i < inStock.length; i++) assert.ok(inStock[i - 1].price <= inStock[i].price);
  assert.equal(asc.at(-1).soldOut, true);
  const p2 = search(beans, { pageSize: 5, page: 2 });
  assert.equal(p2.items.length, 5);
  assert.equal(p2.total, beans.length);
  assert.equal(search(beans, { inStock: '1', pageSize: 100 }).items.some((b) => b.soldOut), false);
  assert.ok(!('_src' in p2.items[0]));
});

test('패싯', () => {
  const f = facets(demoStore().allBeans(), [DEMO_SHOP]);
  assert.equal(f.total, demoRawProducts().length);
  assert.ok(f.origins.find((o) => o.country === '에티오피아').count >= 2);
  assert.equal(f.shops[0].count, f.total);
  assert.ok(f.flavors.length > 5);
});

test('알림 조건: 쇼핑몰·산지·키워드·kg당 가격', () => {
  const s = new Store(null);
  s.applyCrawl(shopA, [raw('0', 'seed')], { ok: true });
  s.applyCrawl(shopB, [raw('0', 'seed')], { ok: true });
  const [geisha] = s.applyCrawl(shopA, [raw('0', 'seed'), raw('9', '파나마 보케테 게이샤 워시드 200g', { price: 40000 })], { ok: true }).newBeans;
  const base = { enabled: true, newArrivals: true, keywords: [], origins: [], shops: [], maxPricePerKg: null };
  assert.equal(alertMatches(geisha, base), true);
  assert.equal(alertMatches(geisha, { ...base, shops: ['a'] }), true);
  assert.equal(alertMatches(geisha, { ...base, shops: ['b'] }), false); // 원하는 몰에서만
  assert.equal(alertMatches(geisha, { ...base, origins: ['파나마'] }), true);
  assert.equal(alertMatches(geisha, { ...base, origins: ['케냐'] }), false);
  assert.equal(alertMatches(geisha, { ...base, keywords: ['게샤', '무산소'] }), true);
  assert.equal(alertMatches(geisha, { ...base, keywords: ['디카페인'] }), false);
  assert.equal(alertMatches(geisha, { ...base, maxPricePerKg: 100000 }), false); // 200g 4만원 = kg당 20만원
  assert.equal(alertMatches(geisha, { ...base, maxPricePerKg: 250000 }), true);
});

function fakeKakaoFetch(log) {
  return async (url, init) => {
    log.push({ url, body: init?.body?.toString() });
    if (url.endsWith('/oauth/token')) return new Response(JSON.stringify({ access_token: 'new-at', expires_in: 21599 }), { status: 200 });
    if (url.endsWith('/memo/default/send')) {
      const auth = init.headers.authorization;
      if (auth === 'Bearer expired') return new Response(JSON.stringify({ msg: 'this access token does not exist', code: -401 }), { status: 401 });
      return new Response(JSON.stringify({ result_code: 0 }), { status: 200 });
    }
    return new Response('{}', { status: 404 });
  };
}

test('카카오: 만료 임박 토큰은 갱신 후 전송, 401 이면 갱신 후 재시도', async () => {
  const log = [];
  const k = new KakaoClient({ restApiKey: 'key', redirectUri: 'https://srv/cb' }, fakeKakaoFetch(log));
  const soon = { accessToken: 'old', refreshToken: 'rt', expiresAt: new Date(Date.now() + 10_000).toISOString() };
  const r1 = await k.sendWithRefresh(soon, { object_type: 'text', text: 'hi', link: {} });
  assert.equal(r1.accessToken, 'new-at');
  assert.equal(r1.refreshToken, 'rt');
  const later = { accessToken: 'expired', refreshToken: 'rt', expiresAt: new Date(Date.now() + 3600_000).toISOString() };
  const r2 = await k.sendWithRefresh(later, { object_type: 'text', text: 'hi', link: {} });
  assert.equal(r2.accessToken, 'new-at');
  assert.equal(log.filter((l) => l.url.endsWith('/send')).length, 3);
});

test('카카오 템플릿: 1건은 feed, 여러 건은 list(최대 3개) + 링크는 서버 /go 경유', () => {
  const beans = demoStore().allBeans();
  const one = buildAlertTemplate(beans.slice(0, 1), { baseUrl: 'https://srv' });
  assert.equal(one.object_type, 'feed');
  assert.match(one.content.link.mobile_web_url, /^https:\/\/srv\/go\/demo%3A/);
  const many = buildAlertTemplate(beans.slice(0, 5), { baseUrl: 'https://srv', kind: 'restock' });
  assert.equal(many.object_type, 'list');
  assert.equal(many.contents.length, 3);
  assert.match(many.header_title, /재입고 5건/);
  assert.match(many.buttons[0].title, /외 2건/);
  for (const c of many.contents) assert.ok(c.title.length <= 60);
});

test('notifyUsers: 사용자 조건에 맞는 것만, 알림 꺼진 사용자는 제외', async () => {
  const s = new Store(null);
  s.applyCrawl(shopA, [raw('0', 'seed')], { ok: true });
  s.applyCrawl(shopB, [raw('0', 'seed')], { ok: true });
  const { newBeans: nA } = s.applyCrawl(shopA, [raw('0', 'seed'), raw('1', '케냐 AA 1kg')], { ok: true });
  const { newBeans: nB } = s.applyCrawl(shopB, [raw('0', 'seed'), raw('2', '에티오피아 구지 1kg')], { ok: true });
  const kakao = { at: new Date(Date.now() + 3600_000).toISOString() };
  const tok = { accessToken: 'ok', refreshToken: 'rt', expiresAt: kakao.at };
  const alerts = { enabled: true, newArrivals: true, restock: false, keywords: [], origins: [], shops: [], maxPricePerKg: null };
  s.upsertUser('dev-onlyA-000000000', { kakao: tok, alerts: { ...alerts, shops: ['a'] } });
  s.upsertUser('dev-all-00000000000', { kakao: tok, alerts });
  s.upsertUser('dev-off-00000000000', { kakao: tok, alerts: { ...alerts, enabled: false } });
  s.upsertUser('dev-nokakao-0000000', { alerts });
  const log = [];
  const client = new KakaoClient({ restApiKey: 'k', redirectUri: 'r' }, fakeKakaoFetch(log));
  const r = await notifyUsers({ store: s, kakao: client, newBeans: [...nA, ...nB], restocked: [], baseUrl: 'https://srv', log: () => {} });
  assert.equal(r.sent, 2);
  const bodies = log.filter((l) => l.url.endsWith('/send')).map((l) => JSON.parse(new URLSearchParams(l.body).get('template_object')));
  const onlyA = bodies.find((b) => b.object_type === 'feed');
  assert.match(onlyA.content.title, /케냐/);
  assert.equal(bodies.find((b) => b.object_type === 'list').contents.length, 2);
  assert.ok(s.getUser('dev-onlyA-000000000').lastNotifiedAt);
});

test('beanMatches 는 판매 종료 상품을 기본으로 숨김', () => {
  assert.equal(beanMatches({ name: 'x', delisted: true, notes: [] }, {}), false);
  assert.equal(beanMatches({ name: 'x', delisted: true, notes: [] }, { includeDelisted: '1' }), true);
});
