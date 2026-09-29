// 아주 단순한 JSON 파일 저장소. 국내 생두 상품은 많아야 수천 개라 DB 없이도 충분하다.
import fs from 'node:fs';
import path from 'node:path';
import { normalizeProduct } from './normalize.js';

const DETAIL_REFRESH_DAYS = 14;

export class Store {
  constructor(file) {
    this.file = file;
    this.data = { beans: {}, users: {}, shops: {} };
    if (file && fs.existsSync(file)) {
      this.data = { ...this.data, ...JSON.parse(fs.readFileSync(file, 'utf8')) };
    }
  }

  save() {
    if (!this.file) return;
    fs.mkdirSync(path.dirname(this.file), { recursive: true });
    const tmp = `${this.file}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(this.data));
    fs.renameSync(tmp, this.file);
  }

  // ---- 생두 ----
  allBeans() {
    return Object.values(this.data.beans);
  }

  getBean(id) {
    return this.data.beans[id] ?? null;
  }

  /** 이 상품의 상세 페이지를 (다시) 읽어야 하는지 */
  needsDetail(shopId, productId, now = new Date()) {
    const b = this.data.beans[`${shopId}:${productId}`];
    const at = b?._src?.detailFetchedAt;
    if (!at) return true;
    return now - new Date(at) > DETAIL_REFRESH_DAYS * 86400_000;
  }

  /**
   * 크롤 결과를 반영한다.
   * @returns {{ newBeans: object[], restocked: object[] }} 알림 대상
   */
  applyCrawl(shop, rawProducts, { ok, now = new Date() }) {
    const nowIso = now.toISOString();
    const shopState = (this.data.shops[shop.id] ??= { initialized: false });
    const seen = new Set();
    const newBeans = [];
    const restocked = [];

    for (const raw of rawProducts) {
      const id = `${shop.id}:${raw.productId}`;
      const prev = this.data.beans[id];
      // 이번에 상세를 안 읽었으면 예전 상세 정보를 재사용
      const input = raw.detailText || raw.description ? raw : { ...raw, ...(prev?._src ? { description: prev._src.description, noteText: prev._src.noteText, optionText: prev._src.optionText, detailFetchedAt: prev._src.detailFetchedAt } : {}) };
      const bean = normalizeProduct(input, shop);
      seen.add(id);

      if (!prev) {
        bean.firstSeenAt = nowIso;
        // 처음 등록하는 몰의 기존 상품은 '신규 입고' 로 치지 않는다
        if (shopState.initialized) newBeans.push(bean);
      } else {
        bean.firstSeenAt = prev.firstSeenAt;
        if ((prev.soldOut || prev.delisted) && !bean.soldOut) {
          bean.restockedAt = nowIso;
          restocked.push(bean);
        } else if (prev.restockedAt) {
          bean.restockedAt = prev.restockedAt;
        }
        if (prev.price && bean.price && prev.price !== bean.price) bean.prevPrice = prev.price;
        else if (prev.prevPrice) bean.prevPrice = prev.prevPrice;
      }
      bean.lastSeenAt = nowIso;
      bean.delisted = false;
      this.data.beans[id] = bean;
    }

    // 목록을 제대로 읽었는데 안 보이는 상품은 판매 종료로 표시 (지우지는 않는다)
    if (ok && rawProducts.length) {
      for (const b of Object.values(this.data.beans)) {
        if (b.shopId === shop.id && !seen.has(b.id) && !b.delisted) {
          b.delisted = true;
          b.delistedAt = nowIso;
        }
      }
      shopState.initialized = true;
    }
    return { newBeans, restocked };
  }

  setShopStatus(shopId, status) {
    this.data.shops[shopId] = { ...(this.data.shops[shopId] ?? { initialized: false }), ...status };
  }

  shopStatus(shopId) {
    return this.data.shops[shopId] ?? null;
  }

  // ---- 사용자(기기) ----
  getUser(deviceId) {
    return this.data.users[deviceId] ?? null;
  }

  upsertUser(deviceId, patch) {
    const u = (this.data.users[deviceId] ??= { deviceId, createdAt: new Date().toISOString(), alerts: defaultAlerts() });
    Object.assign(u, patch);
    return u;
  }

  allUsers() {
    return Object.values(this.data.users);
  }
}

export function defaultAlerts() {
  return {
    enabled: true,
    newArrivals: true, // 신규 입고
    restock: false, // 재입고
    keywords: [], // 비어 있으면 모든 생두
    origins: [],
    shops: [],
    maxPricePerKg: null,
  };
}

/** API 로 내보낼 때 내부 필드 제거 */
export function publicBean(b) {
  if (!b) return b;
  const { _src, ...rest } = b;
  return rest;
}
