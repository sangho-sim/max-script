// 검색/필터/정렬/패싯.
import { ORIGINS } from './dictionaries/origins.js';
import { VARIETIES, PROCESSES, TAGS } from './dictionaries/attributes.js';
import { FLAVOR_NOTES, FLAVOR_CATEGORIES } from './dictionaries/flavors.js';
import { normText } from './match.js';
import { publicBean } from './store.js';

// 별칭 → 대표 이름들 ('게샤' → '게이샤', 'natural' → '내추럴', '예가체프' → '에티오피아' …)
const ALIAS = new Map();
function addAlias(alias, canonical) {
  const a = normText(alias);
  if (!a) return;
  if (!ALIAS.has(a)) ALIAS.set(a, new Set());
  ALIAS.get(a).add(normText(canonical));
}
for (const o of ORIGINS) {
  for (const a of [...o.aliases, o.en]) addAlias(a, o.country);
  // 한글 지역명('예가체프')은 글자 그대로 찾고, 영문 지역명('yirgacheffe')만 국가로 넓혀 찾는다
  for (const r of o.regions) if (/^[\x00-\x7f]+$/.test(r)) addAlias(r, o.country);
}
for (const d of [...VARIETIES, ...PROCESSES]) for (const a of [d.en, ...d.aliases]) addAlias(a, d.name);
for (const t of TAGS) for (const a of t.aliases) addAlias(a, t.name);
for (const n of FLAVOR_NOTES) for (const a of n.aliases) addAlias(a, n.label);
for (const c of FLAVOR_CATEGORIES) addAlias(c.name, c.name);

export function expandTerm(term) {
  const t = normText(term);
  const out = new Set([t]);
  for (const c of ALIAS.get(t) ?? []) out.add(c);
  return [...out];
}

const CATEGORY_NAME = Object.fromEntries(FLAVOR_CATEGORIES.map((c) => [c.id, c.name]));

function haystack(b) {
  return normText(
    [
      b.name,
      b.shopName,
      b.origin?.country,
      b.origin?.en,
      b.origin?.region,
      ...(b.varieties ?? []),
      ...(b.processes ?? []),
      ...(b.tags ?? []),
      ...(b.notes ?? []).flatMap((n) => [n.label, CATEGORY_NAME[n.category]]),
      b.description,
    ]
      .filter(Boolean)
      .join(' | '),
  );
}

export function matchesTerm(bean, term, hay = haystack(bean)) {
  return expandTerm(term).some((t) => hay.includes(t));
}

/** '케냐 AA' 처럼 여러 단어인 키워드: 통째로 맞거나, 단어마다 모두 맞으면 통과 */
export function matchesPhrase(bean, phrase, hay = haystack(bean)) {
  if (matchesTerm(bean, phrase, hay)) return true;
  const words = normText(phrase).split(' ').filter(Boolean);
  return words.length > 1 && words.every((w) => matchesTerm(bean, w, hay));
}

const list = (v) =>
  (Array.isArray(v) ? v : String(v ?? '').split(','))
    .map((s) => s.trim())
    .filter(Boolean);
const num = (v) => (v === undefined || v === null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
const truthy = (v) => v === true || v === '1' || v === 'true';

/** 검색 조건 하나로 한 생두가 걸리는지. 알림 조건 비교에도 같은 함수를 쓴다. */
export function beanMatches(b, params, now = new Date()) {
  const hay = haystack(b);
  for (const token of normText(params.q).split(' ').filter(Boolean)) {
    if (!matchesTerm(b, token, hay)) return false;
  }
  const origins = list(params.origin);
  if (origins.length && !origins.some((o) => b.origin && expandTerm(o).includes(normText(b.origin.country)))) return false;
  const varieties = list(params.variety);
  if (varieties.length && !varieties.some((v) => (b.varieties ?? []).includes(v))) return false;
  const processes = list(params.process);
  if (processes.length && !processes.some((p) => (b.processes ?? []).includes(p))) return false;
  const shops = list(params.shop);
  if (shops.length && !shops.includes(b.shopId)) return false;
  const flavors = list(params.flavor);
  if (flavors.length && !flavors.some((f) => (b.notes ?? []).some((n) => n.category === f))) return false;
  // 키워드는 모두 만족해야 한다 (칩을 누를수록 좁혀짐)
  for (const k of list(params.keyword)) if (!matchesPhrase(b, k, hay)) return false;

  const basisKg = params.priceBasis === 'kg';
  const price = basisKg ? (b.pricePerKg ?? null) : b.price;
  const min = num(params.minPrice);
  const max = num(params.maxPrice);
  if ((min != null || max != null) && price == null) return false;
  if (min != null && price < min) return false;
  if (max != null && price > max) return false;

  if (truthy(params.inStock) && b.soldOut) return false;
  if (!truthy(params.includeDelisted) && b.delisted) return false;
  const days = num(params.newWithinDays);
  if (days != null && now - new Date(b.firstSeenAt) > days * 86400_000) return false;
  return true;
}

const byNullsLast = (get, dir) => (a, b) => {
  const x = get(a);
  const y = get(b);
  if (x == null && y == null) return 0;
  if (x == null) return 1;
  if (y == null) return -1;
  return dir * (x - y);
};

const SORTS = {
  new: (a, b) => String(b.firstSeenAt ?? '').localeCompare(String(a.firstSeenAt ?? '')) || a.name.localeCompare(b.name, 'ko'),
  price_asc: byNullsLast((b) => b.price, 1),
  price_desc: byNullsLast((b) => b.price, -1),
  kg_asc: byNullsLast((b) => b.pricePerKg, 1),
  kg_desc: byNullsLast((b) => b.pricePerKg, -1),
  name: (a, b) => a.name.localeCompare(b.name, 'ko'),
};

export function search(beans, params = {}, now = new Date()) {
  const hits = beans.filter((b) => beanMatches(b, params, now));
  // 품절은 항상 뒤로
  const sort = SORTS[params.sort] ?? SORTS.new;
  hits.sort((a, b) => Number(a.soldOut) - Number(b.soldOut) || sort(a, b));
  const pageSize = Math.min(100, Math.max(1, num(params.pageSize) ?? 30));
  const page = Math.max(1, num(params.page) ?? 1);
  return {
    total: hits.length,
    page,
    pageSize,
    items: hits.slice((page - 1) * pageSize, page * pageSize).map(publicBean),
  };
}

function countBy(beans, keysOf) {
  const m = new Map();
  for (const b of beans) for (const k of new Set(keysOf(b))) if (k) m.set(k, (m.get(k) ?? 0) + 1);
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

export function facets(beans, shops) {
  const live = beans.filter((b) => !b.delisted);
  const originMeta = Object.fromEntries(ORIGINS.map((o) => [o.country, o]));
  const prices = live.map((b) => b.price).filter(Boolean);
  const kgPrices = live.map((b) => b.pricePerKg).filter(Boolean);
  return {
    total: live.length,
    origins: countBy(live, (b) => [b.origin?.country]).map(([country, count]) => ({
      country,
      flag: originMeta[country]?.flag ?? '🌍',
      continent: originMeta[country]?.continent ?? null,
      count,
    })),
    varieties: countBy(live, (b) => b.varieties ?? []).map(([name, count]) => ({ name, count })),
    processes: countBy(live, (b) => b.processes ?? []).map(([name, count]) => ({ name, count })),
    tags: countBy(live, (b) => b.tags ?? []).map(([name, count]) => ({ name, count, group: TAGS.find((t) => t.name === name)?.group ?? null })),
    flavors: countBy(live, (b) => (b.notes ?? []).map((n) => n.category)).map(([id, count]) => ({ ...FLAVOR_CATEGORIES.find((c) => c.id === id), count })),
    notes: countBy(live, (b) => (b.notes ?? []).map((n) => n.label)).slice(0, 60).map(([label, count]) => ({ label, count, category: FLAVOR_NOTES.find((n) => n.label === label)?.category })),
    shops: shops.map((s) => ({ id: s.id, name: s.name, homepage: s.homepage, count: live.filter((b) => b.shopId === s.id).length })),
    price: prices.length ? { min: Math.min(...prices), max: Math.max(...prices) } : null,
    pricePerKg: kgPrices.length ? { min: Math.min(...kgPrices), max: Math.max(...kgPrices) } : null,
  };
}
