// 한 번만 긁기:  npm run crawl            (모든 몰)
//               npm run crawl -- gsc sopex (몇 몰만)
//               npm run crawl -- --dry gsc (저장 없이 결과만 출력 — 새 몰 설정 확인용)
import { config } from './config.js';
import { SHOPS } from './shops.js';
import { Store } from './store.js';
import { KakaoClient } from './kakao.js';
import { runCrawl } from './runner.js';
import { crawlShop } from './crawler/crawl.js';
import { normalizeProduct } from './normalize.js';

const args = process.argv.slice(2);
const dry = args.includes('--dry');
const ids = args.filter((a) => !a.startsWith('--'));
const shops = ids.length ? SHOPS.filter((s) => ids.includes(s.id)) : SHOPS;
if (!shops.length) {
  console.error(`없는 몰 id: ${ids.join(', ')}\n가능한 id: ${SHOPS.map((s) => s.id).join(', ')}`);
  process.exit(1);
}

if (dry) {
  for (const shop of shops) {
    const res = await crawlShop(shop, { maxDetailsPerShop: 3 });
    console.log(`\n=== ${shop.name} (${res.products.length}개, 페이지 ${res.pages}, 오류 ${res.errors.length}) ===`);
    for (const e of res.errors.slice(0, 5)) console.log(`  ! ${e}`);
    for (const p of res.products.slice(0, 10)) {
      const b = normalizeProduct(p, shop);
      console.log(`  - ${b.name} | ${b.price ?? '?'}원 | ${b.origin ? b.origin.flag + b.origin.country : '산지?'} | ${b.processes.join(',')} | ${b.notes.map((n) => n.label).join(',')}${b.soldOut ? ' | 품절' : ''}`);
    }
  }
} else {
  const store = new Store(config.dataFile);
  const r = await runCrawl({ store, shops, kakao: new KakaoClient(config.kakao), baseUrl: config.baseUrl, concurrency: config.crawlConcurrency });
  console.log(`\n완료: 신규 ${r.newBeans.length}, 재입고 ${r.restocked.length}, 전체 ${store.allBeans().length}개 저장 → ${config.dataFile}`);
}
