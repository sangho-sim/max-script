import Constants from 'expo-constants';
import type { Alerts, Bean, DeviceState, Filters, Meta, SearchResult } from './types';

// 서버 주소: EXPO_PUBLIC_API_URL 환경변수 > app.json 의 extra.apiUrl
export const API_URL = (
  process.env.EXPO_PUBLIC_API_URL ??
  (Constants.expoConfig?.extra as { apiUrl?: string } | undefined)?.apiUrl ??
  'http://localhost:8787'
).replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error ?? `서버 오류 (${res.status})`);
  return body as T;
}

export function filtersToQuery(f: Filters, page: number, pageSize = 30): string {
  const q = new URLSearchParams();
  if (f.q.trim()) q.set('q', f.q.trim());
  const lists: (keyof Filters)[] = ['origin', 'variety', 'process', 'flavor', 'shop', 'keyword'];
  for (const k of lists) {
    const v = f[k] as string[];
    if (v.length) q.set(k, v.join(','));
  }
  if (f.minPrice != null) q.set('minPrice', String(f.minPrice));
  if (f.maxPrice != null) q.set('maxPrice', String(f.maxPrice));
  if (f.minPrice != null || f.maxPrice != null) q.set('priceBasis', f.priceBasis);
  if (f.inStock) q.set('inStock', '1');
  if (f.newWithinDays) q.set('newWithinDays', String(f.newWithinDays));
  q.set('sort', f.sort);
  q.set('page', String(page));
  q.set('pageSize', String(pageSize));
  return q.toString();
}

export const api = {
  search: (f: Filters, page: number) => request<SearchResult>(`/api/beans?${filtersToQuery(f, page)}`),
  bean: (id: string) => request<Bean>(`/api/beans/${encodeURIComponent(id)}`),
  meta: () => request<Meta>('/api/meta'),
  device: (deviceId: string) => request<DeviceState>(`/api/devices/${deviceId}`),
  saveAlerts: (deviceId: string, alerts: Alerts) =>
    request<{ alerts: Alerts }>(`/api/devices/${deviceId}/alerts`, { method: 'PUT', body: JSON.stringify(alerts) }),
  testAlert: (deviceId: string) => request<{ ok: true }>(`/api/devices/${deviceId}/test`, { method: 'POST' }),
  disconnectKakao: (deviceId: string) => request<{ ok: true }>(`/api/devices/${deviceId}/kakao`, { method: 'DELETE' }),
  kakaoLoginUrl: (deviceId: string, returnUrl: string) =>
    `${API_URL}/auth/kakao/login?device=${deviceId}&return=${encodeURIComponent(returnUrl)}`,
};

export const EMPTY_FILTERS: Filters = {
  q: '',
  origin: [],
  variety: [],
  process: [],
  flavor: [],
  shop: [],
  keyword: [],
  minPrice: null,
  maxPrice: null,
  priceBasis: 'item',
  sort: 'new',
  inStock: false,
  newWithinDays: null,
};
