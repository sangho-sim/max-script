import type { Bean } from './types';

export const won = (n: number | null | undefined) => (n == null ? '' : `${n.toLocaleString('ko-KR')}원`);

export const weight = (g: number | null) => (g == null ? '' : g >= 1000 ? `${+(g / 1000).toFixed(2)}kg` : `${g}g`);

export function ago(iso: string | null | undefined): string {
  if (!iso) return '';
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return '방금';
  if (min < 60) return `${min}분 전`;
  const h = Math.round(min / 60);
  if (h < 24) return `${h}시간 전`;
  return `${Math.round(h / 24)}일 전`;
}

const DAY = 86400_000;
export const isNew = (b: Bean, days = 3) => Date.now() - new Date(b.firstSeenAt).getTime() < days * DAY;
export const isRestocked = (b: Bean, days = 3) => !!b.restockedAt && Date.now() - new Date(b.restockedAt).getTime() < days * DAY;

export const discountRate = (b: Bean) =>
  b.listPrice && b.price && b.listPrice > b.price ? Math.round((1 - b.price / b.listPrice) * 100) : 0;
