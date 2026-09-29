// 목록/상세 HTML 파싱. 몰 디자인(스킨)에 기대지 않고
//  1) 플랫폼의 상품 링크 모양으로 상품을 찾고
//  2) 그 링크를 감싼 '한 상품만 들어 있는 가장 큰 요소' 를 카드로 보고
//  3) 카드 안에서 이름·썸네일·가격·품절 여부를 뽑는다.
import * as cheerio from 'cheerio';
import { parsePrice } from '../normalize.js';

const NAME_CLASS = /(^|[\s_-])(name|title|subject|prd_?name|prdname|goods_?nm|item_?name|item_?tit|sct_txt|tit)([\s_-]|$)/i;
const NOT_A_NAME = /^(상세보기|자세히 ?보기|장바구니|관심상품|옵션 ?보기|미리보기|바로구매|구매하기|new|best|hot|sale|품절|sold ?out|더보기|찜하기|리뷰|상품명|판매가|소비자가|할인가)$/i;
const ICON_IMG = /(icon|ico_|\/ico\/|btn_|_btn|\/btn\/|soldout|sold_out|blank\.gif|spacer|loading|placeholder|\/common\/|badge)/i;
const PRICE_RE = /(?:₩\s*)?(\d{1,3}(?:,\d{3})+|\d{3,})\s*원|₩\s*(\d{1,3}(?:,\d{3})+|\d{3,})/g;
const NOT_PRICE_BEFORE = /(적립|포인트|마일리지|배송비|쿠폰|예치금|리뷰|후기)[^\d]{0,8}$/;
const SOLD_OUT = /(품절|일시\s*품절|sold\s*-?\s*out|재고\s*없음|판매\s*종료|입고\s*예정)/i;

function absUrl(href, base) {
  if (!href) return null;
  try {
    return new URL(href.trim(), base).toString();
  } catch {
    return null;
  }
}

function cleanText(s) {
  return String(s ?? '')
    .replace(/\s+/g, ' ')
    .replace(/^\s*상품명\s*[:：]?\s*/, '')
    .trim();
}

function imgSrc($img) {
  for (const a of ['ec-data-src', 'data-src', 'data-original', 'data-lazy', 'data-lazy-src', 'src']) {
    const v = $img.attr(a);
    if (v && !v.startsWith('data:')) return v;
  }
  const srcset = $img.attr('srcset') || $img.attr('data-srcset');
  if (srcset) return srcset.split(',')[0].trim().split(/\s+/)[0];
  return null;
}

function pickImage($, $card, base) {
  let found = null;
  $card.find('img').each((_, el) => {
    if (found) return;
    const src = imgSrc($(el));
    if (src && !ICON_IMG.test(src)) found = absUrl(src, base);
  });
  if (found) return found;
  // 배경 이미지로 썸네일을 넣는 스킨
  $card.find('[style*="background"]').each((_, el) => {
    if (found) return;
    const m = ($(el).attr('style') || '').match(/url\(\s*['"]?([^'")]+)['"]?\s*\)/);
    if (m && !ICON_IMG.test(m[1])) found = absUrl(m[1], base);
  });
  return found;
}

function pickName($, $card, anchors) {
  const candidates = [];
  $card.find('*').each((_, el) => {
    const cls = $(el).attr('class') || '';
    if (NAME_CLASS.test(cls)) candidates.push(cleanText($(el).text()));
  });
  for (const a of anchors) candidates.push(cleanText($(a).text()));
  const ok = candidates.filter((t) => t.length >= 2 && t.length <= 150 && !NOT_A_NAME.test(t) && !/^[\d,.\s원₩%]+$/.test(t));
  // 이름 칸(class 기반)이 먼저, 그다음이 링크 텍스트
  if (ok.length) return ok[0];
  const alt = $card.find('img[alt]').map((_, el) => cleanText($(el).attr('alt'))).get().find((t) => t.length >= 2 && !NOT_A_NAME.test(t));
  return alt || null;
}

export function pricesIn(text) {
  const out = [];
  for (const m of text.matchAll(PRICE_RE)) {
    if (NOT_PRICE_BEFORE.test(text.slice(Math.max(0, m.index - 16), m.index))) continue;
    const n = parsePrice(m[1] ?? m[2]);
    if (n && n >= 100 && n <= 50_000_000) out.push(n);
  }
  return out;
}

function pickPrices($, $card) {
  const text = $card.text().replace(/\s+/g, ' ');
  let prices = pricesIn(text);
  if (!prices.length) {
    $card.find('[class*="price"],[class*="Price"],[class*="cost"],[class*="sell"]').each((_, el) => {
      const n = parsePrice($(el).text());
      if (n && n >= 100) prices.push(n);
    });
  }
  if (!prices.length) {
    // '원' 없이 '판매가 12500' 처럼만 쓰는 스킨
    for (const m of text.matchAll(/(판매가|할인가|판매 가격|가격)\s*[:：]?\s*₩?\s*(\d{1,3}(?:,\d{3})+|\d{4,})/g)) prices.push(parsePrice(m[2]));
  }
  // 앞의 '원' 이 붙은 가격이 전부 1,000원 미만이면(적립금 등) 가격이 아닌 것으로 본다
  prices = prices.filter((p) => p >= 1000);
  if (!prices.length) return { price: null, listPrice: null };
  const price = Math.min(...prices);
  const max = Math.max(...prices);
  return { price, listPrice: max > price ? max : null };
}

function isSoldOut($, $card) {
  if (SOLD_OUT.test($card.text())) return true;
  let sold = false;
  $card.find('img').each((_, el) => {
    const alt = $(el).attr('alt') || '';
    const src = imgSrc($(el)) || '';
    if (SOLD_OUT.test(alt) || /sold_?out/i.test(src)) sold = true;
  });
  if (sold) return true;
  return /sold_?out/i.test($card.attr('class') || '') || $card.find('[class*="soldout"],[class*="sold_out"],[class*="SoldOut"]').length > 0;
}

function load(html) {
  const $ = cheerio.load(html);
  $('script, style, noscript, template').remove();
  // Cafe24 는 안 보이는 요소를 displaynone 클래스로 숨긴다 (항목명, 숨긴 품절 아이콘 등)
  $('.displaynone, [style*="display:none"], [style*="display: none"]').remove();
  // 블록 요소 사이에 공백을 넣어 글자가 붙지 않게 ('1kg</option><option>5kg' → '1kg 5kg')
  $('br, p, div, li, td, th, tr, dt, dd, h1, h2, h3, h4, h5, h6, option, ul, ol, table, section, article').after(' ');
  return $;
}

/**
 * 목록 페이지에서 상품 카드들을 뽑는다.
 * @returns {Array<{productId,url,name,imageUrl,price,listPrice,soldOut}>}
 */
export function parseListing(html, pageUrl, platform) {
  const $ = load(html);
  const origin = new URL(pageUrl).origin;
  const anchorsById = new Map();
  $('a[href]').each((_, a) => {
    const href = $(a).attr('href');
    const id = platform.idFromHref(href);
    if (!id) return;
    if (!anchorsById.has(id)) anchorsById.set(id, []);
    anchorsById.get(id).push(a);
  });

  // 링크에 카테고리가 붙는 플랫폼이면, 이 목록의 카테고리 상품만 남긴다 (배너·추천상품 제외)
  const cat = platform.listCategory?.(pageUrl);
  if (cat) {
    const inCat = (id) => anchorsById.get(id).some((a) => platform.hrefInCategory($(a).attr('href'), cat));
    if ([...anchorsById.keys()].some(inCat)) {
      for (const id of [...anchorsById.keys()]) if (!inCat(id)) anchorsById.delete(id);
    }
  }

  const idsIn = ($el) => {
    const ids = new Set();
    $el.find('a[href]').each((_, a) => {
      const id = platform.idFromHref($(a).attr('href'));
      if (id) ids.add(id);
    });
    return ids;
  };

  const items = [];
  for (const [id, anchors] of anchorsById) {
    // 카드 찾기: 다른 상품 링크가 섞이기 직전까지 위로 올라간다
    let $card = $(anchors[0]);
    for (let depth = 0; depth < 8; depth++) {
      const $parent = $card.parent();
      if (!$parent.length || ['body', 'html'].includes($parent[0].tagName)) break;
      const ids = idsIn($parent);
      if (ids.size > 1) break;
      $card = $parent;
    }
    const cardAnchors = $card.is('a') ? [$card[0]] : $card.find('a[href]').filter((_, a) => platform.idFromHref($(a).attr('href')) === id).get();
    const name = pickName($, $card, cardAnchors.length ? cardAnchors : anchors);
    if (!name) continue;
    const href = $(anchors[0]).attr('href');
    const url = platform.canonicalUrl ? platform.canonicalUrl(origin, id) : absUrl(href, pageUrl);
    items.push({
      productId: id,
      url,
      name,
      imageUrl: pickImage($, $card, pageUrl),
      ...pickPrices($, $card),
      soldOut: isSoldOut($, $card),
    });
  }
  return items;
}

/**
 * 상세 페이지에서 목록에 없던 정보(설명, 본문 텍스트, 옵션, 대표 이미지)를 뽑는다.
 */
export function parseDetail(html, pageUrl) {
  const raw = cheerio.load(html);
  const meta = (sel) => raw(sel).attr('content')?.trim() || null;
  const out = {
    ogTitle: meta('meta[property="og:title"]'),
    imageUrl: absUrl(meta('meta[property="og:image"]'), pageUrl),
    description: meta('meta[property="og:description"]') || meta('meta[name="description"]'),
    price: parsePrice(meta('meta[property="product:sale_price:amount"]') || meta('meta[property="product:price:amount"]')),
    listPrice: parsePrice(meta('meta[property="product:price:amount"]')),
    soldOut: null,
  };
  const avail = meta('meta[property="product:availability"]') || meta('meta[property="og:availability"]');
  if (avail) out.soldOut = /oos|out ?of ?stock|soldout/i.test(avail);

  // JSON-LD Product
  raw('script[type="application/ld+json"]').each((_, el) => {
    try {
      const data = JSON.parse(raw(el).contents().text());
      for (const node of [].concat(data['@graph'] ?? data)) {
        if (!node || !/product/i.test(String(node['@type']))) continue;
        const offer = [].concat(node.offers ?? [])[0];
        if (offer?.price && !out.price) out.price = parsePrice(String(offer.price));
        if (offer?.availability && out.soldOut == null) out.soldOut = /outofstock|soldout/i.test(offer.availability);
        if (node.image && !out.imageUrl) out.imageUrl = absUrl([].concat(node.image)[0], pageUrl);
        if (node.description && !out.description) out.description = String(node.description);
      }
    } catch {
      /* 깨진 JSON-LD 는 무시 */
    }
  });

  const $ = load(html);
  out.optionText = $('select option').map((_, o) => $(o).text().trim()).get().filter(Boolean).join(' / ').slice(0, 2000);
  out.detailText = $('body').text().replace(/\s+/g, ' ').trim().slice(0, 30000);
  return out;
}
