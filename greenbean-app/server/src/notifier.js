// 크롤 결과(신규/재입고)를 사용자별 알림 조건에 맞춰 카카오톡으로 보낸다.
import { beanMatches } from './search.js';
import { buildAlertTemplate } from './kakao.js';

/** 사용자 알림 조건 → 검색 조건 */
export function alertMatches(bean, alerts) {
  if (alerts.shops?.length && !alerts.shops.includes(bean.shopId)) return false;
  if (alerts.origins?.length && !beanMatches(bean, { origin: alerts.origins })) return false;
  // kg당 가격을 모르는 생두는 가격 조건으로 거르지 않는다 (놓치는 것보다 한 번 더 받는 게 낫다)
  if (alerts.maxPricePerKg && bean.pricePerKg && bean.pricePerKg > alerts.maxPricePerKg) return false;
  // 키워드는 하나라도 맞으면 알림 (예: '게이샤', '무산소' 중 아무거나)
  if (alerts.keywords?.length && !alerts.keywords.some((k) => beanMatches(bean, { keyword: [k], includeDelisted: '1' }))) return false;
  return true;
}

/**
 * @param {object} p
 * @param {import('./store.js').Store} p.store
 * @param {import('./kakao.js').KakaoClient} p.kakao
 * @param {object[]} p.newBeans
 * @param {object[]} p.restocked
 * @param {string} p.baseUrl
 * @param {(msg: string) => void} [p.log]
 * @returns {Promise<{ sent: number, failed: number }>}
 */
export async function notifyUsers({ store, kakao, newBeans, restocked, baseUrl, log = console.log }) {
  let sent = 0;
  let failed = 0;
  if (!newBeans.length && !restocked.length) return { sent, failed };

  for (const user of store.allUsers()) {
    const a = user.alerts;
    if (!user.kakao?.refreshToken || !a?.enabled) continue;
    const batches = [];
    if (a.newArrivals) batches.push(['new', newBeans.filter((b) => alertMatches(b, a))]);
    if (a.restock) batches.push(['restock', restocked.filter((b) => alertMatches(b, a))]);
    for (const [kind, beans] of batches) {
      if (!beans.length) continue;
      try {
        const updated = await kakao.sendWithRefresh(user.kakao, buildAlertTemplate(beans, { baseUrl, kind }));
        store.upsertUser(user.deviceId, { kakao: { ...user.kakao, ...updated }, lastNotifiedAt: new Date().toISOString() });
        sent++;
      } catch (e) {
        failed++;
        log(`[알림] ${user.deviceId} 전송 실패: ${e.message}`);
        // 리프레시 토큰이 만료/철회되면 다시 연결해야 한다
        if (e.status === 400 || e.status === 401) store.upsertUser(user.deviceId, { kakaoError: e.message });
      }
    }
  }
  store.save();
  return { sent, failed };
}
