// 모든 몰을 한 바퀴 긁고 → 저장하고 → 신규/재입고를 알린다.
import { crawlShop } from './crawler/crawl.js';
import { notifyUsers } from './notifier.js';

async function pool(items, size, fn) {
  const queue = [...items];
  await Promise.all(
    Array.from({ length: Math.max(1, size) }, async () => {
      while (queue.length) await fn(queue.shift());
    }),
  );
}

/**
 * @returns {Promise<{ newBeans: object[], restocked: object[], shops: object[] }>}
 */
export async function runCrawl({ store, shops, kakao, baseUrl, concurrency = 4, log = console.log, crawlOpts = {} }) {
  const newBeans = [];
  const restocked = [];
  const summary = [];
  await pool(shops, concurrency, async (shop) => {
    const started = Date.now();
    try {
      const res = await crawlShop(shop, { needsDetail: (pid) => store.needsDetail(shop.id, pid), ...crawlOpts });
      const ok = res.pages > 0 && res.products.length > 0;
      const diff = store.applyCrawl(shop, res.products, { ok });
      newBeans.push(...diff.newBeans);
      restocked.push(...diff.restocked);
      store.setShopStatus(shop.id, {
        lastCrawlAt: new Date().toISOString(),
        ...(ok ? { lastOkAt: new Date().toISOString() } : {}),
        lastCount: res.products.length,
        lastErrors: res.errors.slice(0, 5),
      });
      summary.push({ shop: shop.id, count: res.products.length, new: diff.newBeans.length, restocked: diff.restocked.length, errors: res.errors.length, ms: Date.now() - started });
      log(`[크롤] ${shop.name}: ${res.products.length}개 (신규 ${diff.newBeans.length}, 재입고 ${diff.restocked.length}, 오류 ${res.errors.length})`);
      if (res.errors.length) log(`       ${res.errors.slice(0, 3).join('\n       ')}`);
    } catch (e) {
      store.setShopStatus(shop.id, { lastCrawlAt: new Date().toISOString(), lastErrors: [e.message] });
      summary.push({ shop: shop.id, count: 0, new: 0, restocked: 0, errors: 1 });
      log(`[크롤] ${shop.name}: 실패 — ${e.message}`);
    }
    store.save();
  });
  store.data.lastCrawlAt = new Date().toISOString();
  store.save();

  if (kakao?.configured) {
    const r = await notifyUsers({ store, kakao, newBeans, restocked, baseUrl, log });
    if (r.sent || r.failed) log(`[알림] 카카오톡 ${r.sent}건 전송, ${r.failed}건 실패`);
  }
  return { newBeans, restocked, shops: summary };
}
