// API 서버 + 주기적 크롤 + 카카오톡 알림.
import crypto from 'node:crypto';
import express from 'express';
import { config } from './config.js';
import { SHOPS } from './shops.js';
import { Store, publicBean, defaultAlerts } from './store.js';
import { search, facets } from './search.js';
import { KEYWORD_PRESETS } from './keywords.js';
import { FLAVOR_CATEGORIES } from './dictionaries/flavors.js';
import { KakaoClient, buildTestTemplate } from './kakao.js';
import { runCrawl } from './runner.js';
import { loadDemoData, DEMO_SHOP } from './demo.js';

export function createApp({ store, shops, kakao, cfg = config, triggerCrawl = async () => ({}) }) {
  const app = express();
  app.use(express.json({ limit: '100kb' }));
  app.use((req, res, next) => {
    res.set('access-control-allow-origin', '*');
    res.set('access-control-allow-headers', 'content-type, authorization');
    res.set('access-control-allow-methods', 'GET, PUT, POST, DELETE, OPTIONS');
    if (req.method === 'OPTIONS') return res.sendStatus(204);
    next();
  });

  const validDevice = (id) => typeof id === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(id);

  app.get('/health', (req, res) => res.json({ ok: true, beans: store.allBeans().length, lastCrawlAt: store.data.lastCrawlAt ?? null }));

  // ---------- 생두 ----------
  app.get('/api/beans', (req, res) => res.json(search(store.allBeans(), req.query)));

  app.get('/api/beans/:id', (req, res) => {
    const b = store.getBean(req.params.id);
    if (!b) return res.status(404).json({ error: '없는 생두입니다' });
    res.json(publicBean(b));
  });

  app.get('/api/meta', (req, res) => {
    res.json({
      facets: facets(store.allBeans(), shops),
      keywordPresets: KEYWORD_PRESETS,
      flavorCategories: FLAVOR_CATEGORIES.map(({ profile, ...c }) => c),
      shops: shops.map((s) => ({ id: s.id, name: s.name, homepage: s.homepage, status: store.shopStatus(s.id) })),
      lastCrawlAt: store.data.lastCrawlAt ?? null,
      kakaoConfigured: kakao.configured,
    });
  });

  // 카카오톡 메시지 링크는 등록된 도메인만 쓸 수 있어서 여기서 쇼핑몰로 넘긴다
  app.get('/go/:id', (req, res) => {
    const b = store.getBean(req.params.id);
    if (!b?.url) return res.status(404).send('상품을 찾을 수 없습니다');
    res.redirect(302, b.url);
  });

  // 알림 메시지의 '앱에서 보기' 가 여는 간단한 웹 목록
  app.get('/', (req, res) => {
    const { items } = search(store.allBeans(), { sort: 'new', pageSize: 50 });
    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
    const cat = Object.fromEntries(FLAVOR_CATEGORIES.map((c) => [c.id, c]));
    const rows = items
      .map(
        (b) => `<a class="card" href="/go/${encodeURIComponent(b.id)}">
  ${b.imageUrl ? `<img src="${esc(b.imageUrl)}" alt="" loading="lazy">` : '<div class="noimg">☕</div>'}
  <div><small>${esc(b.shopName)}${b.soldOut ? ' · 품절' : ''}</small><b>${esc(b.name)}</b>
  <span>${b.origin ? `${b.origin.flag} ${esc(b.origin.country)} · ` : ''}${b.price ? `${b.price.toLocaleString('ko-KR')}원` : ''}</span>
  <span>${(b.notes ?? []).slice(0, 4).map((n) => `<i style="background:${cat[n.category]?.color}22">${cat[n.category]?.emoji ?? ''} ${esc(n.label)}</i>`).join(' ')}</span></div></a>`,
      )
      .join('\n');
    res.type('html').send(`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>생두 알리미</title><style>
:root{--bg:#faf7f2;--fg:#2b211b;--muted:#7a6a5d;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#171311;--fg:#f2ebe4;--muted:#b3a497;--card:#221c19}}
body{margin:0;padding:16px;font-family:system-ui,-apple-system,'Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--fg)}
h1{font-size:20px}.card{display:flex;gap:12px;padding:10px;margin-bottom:10px;background:var(--card);border-radius:12px;color:inherit;text-decoration:none}
img,.noimg{width:72px;height:72px;border-radius:8px;object-fit:cover;flex:none;display:grid;place-items:center;background:#0001;font-size:28px}
.card div{display:flex;flex-direction:column;gap:3px;min-width:0}small{color:var(--muted)}b{font-size:15px}span{font-size:13px}
i{font-style:normal;border-radius:999px;padding:1px 7px;margin-right:2px;white-space:nowrap}</style></head>
<body><h1>☕ 최근 입고 생두</h1>${rows || '<p>아직 수집된 생두가 없습니다.</p>'}</body></html>`);
  });

  // ---------- 카카오톡 연결 ----------
  const pendingStates = new Map(); // state → { deviceId, at }

  app.get('/auth/kakao/login', (req, res) => {
    const deviceId = req.query.device;
    if (!validDevice(deviceId)) return res.status(400).send('잘못된 기기 ID');
    if (!kakao.configured) return res.status(503).send('서버에 KAKAO_REST_API_KEY 가 설정되지 않았습니다');
    const state = crypto.randomBytes(16).toString('hex');
    const now = Date.now();
    for (const [k, v] of pendingStates) if (now - v.at > 10 * 60_000) pendingStates.delete(k);
    // 연결이 끝나면 돌아갈 앱 주소. 앱 스킴이나 Expo Go(exp://) 주소만 허용한다.
    const ret = typeof req.query.return === 'string' && new RegExp(`^(${cfg.appScheme}|exps?)://`).test(req.query.return) ? req.query.return : null;
    pendingStates.set(state, { deviceId, at: now, ret });
    res.redirect(302, kakao.authorizeUrl(state));
  });

  app.get('/auth/kakao/callback', async (req, res) => {
    const { code, state, error } = req.query;
    const pending = pendingStates.get(state);
    pendingStates.delete(state);
    const back = (status) => {
      const base = pending?.ret ?? `${cfg.appScheme}://alerts`;
      return `${base}${base.includes('?') ? '&' : '?'}kakao=${status}`;
    };
    const page = (msg, status) =>
      res.type('html').send(`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>카카오톡 연결</title></head>
<body style="font-family:system-ui;padding:24px;text-align:center"><p style="font-size:18px">${msg}</p><p><a href="${back(status).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)}">앱으로 돌아가기</a></p>
<script>setTimeout(function(){location.href=${JSON.stringify(back(status)).replace(/</g, '\\u003c')}},300)</script></body></html>`);
    if (error || !code) return page('카카오 연결이 취소되었습니다.', 'cancelled');
    if (!pending) return page('연결 요청이 만료되었습니다. 앱에서 다시 시도해 주세요.', 'expired');
    try {
      const tokens = await kakao.exchangeCode(code);
      const profile = await kakao.profile(tokens.accessToken).catch(() => ({}));
      const user = store.upsertUser(pending.deviceId, { kakao: { ...tokens, ...profile }, kakaoError: null });
      user.alerts ??= defaultAlerts();
      store.save();
      await kakao.sendWithRefresh(user.kakao, buildTestTemplate(cfg.baseUrl)).catch(() => {});
      page('✅ 카카오톡 알림이 연결되었습니다. 카카오톡 &lsquo;나와의 채팅&rsquo; 을 확인해 보세요.', 'connected');
    } catch (e) {
      page(`연결 실패: ${String(e.message).replace(/[<>&]/g, '')}`, 'error');
    }
  });

  // ---------- 기기별 설정 ----------
  app.get('/api/devices/:device', (req, res) => {
    const { device } = req.params;
    if (!validDevice(device)) return res.status(400).json({ error: '잘못된 기기 ID' });
    const u = store.getUser(device);
    res.json({
      kakaoConfigured: kakao.configured,
      kakaoConnected: Boolean(u?.kakao?.refreshToken) && !u?.kakaoError,
      kakaoError: u?.kakaoError ?? null,
      nickname: u?.kakao?.nickname ?? null,
      alerts: u?.alerts ?? defaultAlerts(),
      lastNotifiedAt: u?.lastNotifiedAt ?? null,
    });
  });

  app.put('/api/devices/:device/alerts', (req, res) => {
    const { device } = req.params;
    if (!validDevice(device)) return res.status(400).json({ error: '잘못된 기기 ID' });
    const b = req.body ?? {};
    const strs = (v, max = 30) => (Array.isArray(v) ? v.map((s) => String(s).trim().slice(0, 40)).filter(Boolean).slice(0, max) : []);
    const alerts = {
      enabled: b.enabled !== false,
      newArrivals: b.newArrivals !== false,
      restock: Boolean(b.restock),
      keywords: strs(b.keywords),
      origins: strs(b.origins),
      shops: strs(b.shops, 50),
      maxPricePerKg: Number(b.maxPricePerKg) > 0 ? Math.round(Number(b.maxPricePerKg)) : null,
    };
    store.upsertUser(device, { alerts });
    store.save();
    res.json({ alerts });
  });

  app.post('/api/devices/:device/test', async (req, res) => {
    const u = store.getUser(req.params.device);
    if (!u?.kakao?.refreshToken) return res.status(400).json({ error: '카카오톡이 연결되지 않았습니다' });
    try {
      const k = await kakao.sendWithRefresh(u.kakao, buildTestTemplate(cfg.baseUrl));
      store.upsertUser(u.deviceId, { kakao: { ...u.kakao, ...k }, kakaoError: null });
      store.save();
      res.json({ ok: true });
    } catch (e) {
      res.status(502).json({ error: e.message });
    }
  });

  app.delete('/api/devices/:device/kakao', (req, res) => {
    const u = store.getUser(req.params.device);
    if (u) {
      store.upsertUser(u.deviceId, { kakao: null, kakaoError: null });
      store.save();
    }
    res.json({ ok: true });
  });

  // ---------- 관리 ----------
  app.post('/api/admin/crawl', async (req, res) => {
    if (!cfg.adminToken || req.get('authorization') !== `Bearer ${cfg.adminToken}`) return res.status(401).json({ error: 'unauthorized' });
    res.json(await triggerCrawl());
  });

  return app;
}

async function main() {
  const store = new Store(config.dataFile);
  const shops = config.shopFilter.length ? SHOPS.filter((s) => config.shopFilter.includes(s.id)) : SHOPS;
  const kakao = new KakaoClient(config.kakao);

  if (config.demoData && store.allBeans().length === 0) {
    const n = loadDemoData(store);
    console.log(`[데모] 샘플 생두 ${n}개를 넣었습니다 (DEMO_DATA=1)`);
  }

  let running = null;
  const triggerCrawl = () => {
    running ??= runCrawl({ store, shops, kakao, baseUrl: config.baseUrl, concurrency: config.crawlConcurrency })
      .then((r) => ({ new: r.newBeans.length, restocked: r.restocked.length, shops: r.shops }))
      .finally(() => (running = null));
    return running;
  };

  const listedShops = config.demoData ? [...shops, DEMO_SHOP] : shops;
  createApp({ store, shops: listedShops, kakao, triggerCrawl }).listen(config.port, () => {
    console.log(`생두 알리미 서버: ${config.baseUrl} (포트 ${config.port})`);
    if (!kakao.configured) console.log('  ⚠ KAKAO_REST_API_KEY 가 없어 카카오톡 알림은 꺼져 있습니다.');
  });

  // 데모 모드에서는 실제 쇼핑몰을 긁지 않는다
  if (config.demoData) return;
  if (config.crawlOnStart) triggerCrawl();
  if (config.crawlIntervalMin > 0) setInterval(triggerCrawl, config.crawlIntervalMin * 60_000);
}

if (import.meta.url === `file://${process.argv[1]}`) main();
