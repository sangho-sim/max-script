// 쇼핑몰 하나를 긁어서 원본 상품 목록을 돌려준다.
import { fetchText, fetchJson, isAllowedByRobots, sleep } from './fetch.js';
import { getPlatform } from './platforms.js';
import { parseListing, parseDetail } from './parse.js';
import { NOT_GREEN_BEAN } from '../shops.js';

const DEFAULTS = {
  delayMs: Number(process.env.CRAWL_DELAY_MS ?? 1500),
  maxDetailsPerShop: Number(process.env.CRAWL_MAX_DETAILS ?? 40),
};

/**
 * @param {object} shop  shops.js 의 항목
 * @param {object} opts
 * @param {(productId: string) => boolean} opts.needsDetail 상세 페이지를 새로 읽을지 (새 상품이면 true)
 * @param {typeof fetchText} [opts.fetchText] 테스트용 주입
 * @returns {Promise<{ products: object[], pages: number, errors: string[] }>}
 */
export async function crawlShop(shop, opts = {}) {
  const o = { ...DEFAULTS, needsDetail: () => true, fetchText, fetchJson, robots: true, ...opts };
  let result;
  if (shop.source === 'shopify') result = await crawlShopify(shop, o);
  else if (shop.source === 'momos') result = await crawlMomos(shop, o);
  else result = await crawlHtml(shop, o);
  result.products = result.products.filter((p) => p.name && !NOT_GREEN_BEAN.test(p.name));
  return result;
}

async function crawlHtml(shop, o) {
  const platform = getPlatform(shop.platform);
  const byId = new Map();
  const errors = [];
  let pages = 0;

  const allowed = async (url) => !o.robots || (await isAllowedByRobots(url, o.fetchText));

  for (const tmpl of shop.listUrls) {
    for (let page = 1; page <= (shop.maxPages ?? 5); page++) {
      const url = tmpl.replace('{page}', String(page));
      if (!(await allowed(url))) {
        errors.push(`robots.txt 가 막음: ${url}`);
        break;
      }
      let items;
      try {
        items = parseListing(await o.fetchText(url), url, platform);
        pages++;
      } catch (e) {
        errors.push(`${url}: ${e.message}`);
        break;
      }
      let fresh = 0;
      for (const it of items) {
        if (!byId.has(it.productId)) {
          byId.set(it.productId, it);
          fresh++;
        }
      }
      if (o.delayMs) await sleep(o.delayMs);
      if (fresh === 0) break; // 마지막 페이지를 넘어가면 같은 상품이 반복되거나 비어 있다
    }
  }

  // 새 상품만 상세 페이지를 읽어서 설명/컵노트를 보강한다 (몰에 부담을 덜 주려고)
  let details = 0;
  for (const it of byId.values()) {
    if (details >= o.maxDetailsPerShop || !o.needsDetail(it.productId)) continue;
    if (!(await allowed(it.url))) continue;
    try {
      const d = parseDetail(await o.fetchText(it.url), it.url);
      details++;
      it.description = d.description;
      it.detailText = d.detailText;
      it.optionText = d.optionText;
      it.imageUrl = it.imageUrl || d.imageUrl;
      if (!it.price && d.price) it.price = d.price;
      if (!it.listPrice && d.listPrice && d.listPrice > (it.price ?? 0)) it.listPrice = d.listPrice;
      if (d.soldOut != null) it.soldOut = it.soldOut || d.soldOut;
      it.detailFetchedAt = new Date().toISOString();
    } catch (e) {
      errors.push(`${it.url}: ${e.message}`);
    }
    if (o.delayMs) await sleep(o.delayMs);
  }
  return { products: [...byId.values()], pages, errors };
}

// Shopify 몰은 /collections/<handle>/products.json 을 공개한다.
async function crawlShopify(shop, o) {
  const products = [];
  const errors = [];
  let pages = 0;
  for (let page = 1; page <= (shop.maxPages ?? 5); page++) {
    const url = `${shop.homepage}/collections/${shop.collection}/products.json?limit=250&page=${page}`;
    let data;
    try {
      data = await o.fetchJson(url);
      pages++;
    } catch (e) {
      errors.push(`${url}: ${e.message}`);
      break;
    }
    const list = data.products ?? [];
    for (const p of list) {
      const variants = p.variants ?? [];
      const prices = variants.map((v) => Number(v.price)).filter((n) => n > 0);
      products.push({
        productId: String(p.id),
        url: `${shop.homepage}/products/${p.handle}`,
        name: p.title,
        imageUrl: p.images?.[0]?.src ?? null,
        price: prices.length ? Math.min(...prices) : null,
        listPrice: null,
        soldOut: variants.length > 0 && variants.every((v) => v.available === false),
        description: [p.product_type, ...(Array.isArray(p.tags) ? p.tags : String(p.tags ?? '').split(','))].filter(Boolean).join(', '),
        detailText: String(p.body_html ?? '').replace(/<[^>]+>/g, ' '),
        optionText: variants.map((v) => v.title).join(' / '),
      });
    }
    if (list.length < 250) break;
    if (o.delayMs) await sleep(o.delayMs);
  }
  return { products, pages, errors };
}

// 모모스커피는 생두 목록을 JSON 으로 공개한다.
async function crawlMomos(shop, o) {
  try {
    const data = await o.fetchJson(shop.apiUrl);
    const products = (data.greenBeans ?? []).map((b) => ({
      productId: String(b.prodNo),
      url: `${shop.homepage}/shop_view/?idx=${b.prodNo}`,
      name: b.name,
      imageUrl: b.thumbnail ?? null,
      price: b.price ?? null,
      listPrice: null,
      soldOut: b.status != null && b.status !== 'sale',
      description: [b.country, b.region, b.variety, b.process, b.cupNote ?? b.cupNotes ?? b.notes].flat().filter(Boolean).join(' '),
      detailText: b.cupNote || b.cupNotes || b.notes ? `컵노트: ${[].concat(b.cupNote ?? b.cupNotes ?? b.notes).join(', ')}` : '',
    }));
    return { products, pages: 1, errors: [] };
  } catch (e) {
    return { products: [], pages: 0, errors: [`${shop.apiUrl}: ${e.message}`] };
  }
}
