// 앱 전체에서 쓰는 상태: 기기 ID(알림 설정 식별용), 내 키워드, 서버 메타(패싯·향미 색 등).
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from './api';
import type { FlavorCategory, Meta } from './types';

const KEY_DEVICE = 'greenbean.deviceId';
const KEY_KEYWORDS = 'greenbean.keywords';
export const DEFAULT_KEYWORDS = ['게이샤', '내추럴', '워시드', '무산소 발효', '디카페인', 'G1', 'COE', '마이크로랏'];

interface AppState {
  deviceId: string | null;
  keywords: string[];
  setKeywords: (k: string[]) => void;
  toggleKeyword: (k: string) => void;
  meta: Meta | null;
  metaError: string | null;
  reloadMeta: () => Promise<void>;
  flavor: (id: string) => FlavorCategory | undefined;
}

const Ctx = createContext<AppState | null>(null);

// 서버에 연결되기 전에도 노트 색이 보이도록 기본값을 둔다 (서버 dictionaries/flavors.js 와 같은 값)
const FALLBACK_FLAVORS: FlavorCategory[] = [
  { id: 'floral', name: '꽃향', emoji: '🌸', color: '#E889B5' },
  { id: 'citrus', name: '시트러스', emoji: '🍋', color: '#F2C230' },
  { id: 'berry', name: '베리', emoji: '🍓', color: '#D6455D' },
  { id: 'stonefruit', name: '과일', emoji: '🍑', color: '#F29A6B' },
  { id: 'tropical', name: '열대과일', emoji: '🥭', color: '#F5A623' },
  { id: 'wine', name: '와인·발효', emoji: '🍷', color: '#8E3B5A' },
  { id: 'tea', name: '차·허브', emoji: '🍵', color: '#7FAF6A' },
  { id: 'sweet', name: '캐러멜·단맛', emoji: '🍯', color: '#D08A2E' },
  { id: 'chocolate', name: '초콜릿', emoji: '🍫', color: '#6B4226' },
  { id: 'nutty', name: '견과', emoji: '🌰', color: '#A67C52' },
  { id: 'grain', name: '곡물·구운빵', emoji: '🍞', color: '#C9A66B' },
  { id: 'spice', name: '향신료', emoji: '🌶️', color: '#B5502F' },
  { id: 'earthy', name: '흙·우디', emoji: '🌲', color: '#5E6B4E' },
];

async function loadDeviceId() {
  let id = await AsyncStorage.getItem(KEY_DEVICE).catch(() => null);
  if (!id) {
    id = Crypto.randomUUID().replace(/-/g, '');
    await AsyncStorage.setItem(KEY_DEVICE, id).catch(() => {});
  }
  return id;
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [keywords, setKeywordsState] = useState<string[]>(DEFAULT_KEYWORDS);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);

  useEffect(() => {
    loadDeviceId().then(setDeviceId);
    AsyncStorage.getItem(KEY_KEYWORDS)
      .then((v) => v && setKeywordsState(JSON.parse(v)))
      .catch(() => {});
  }, []);

  const setKeywords = useCallback((k: string[]) => {
    setKeywordsState(k);
    AsyncStorage.setItem(KEY_KEYWORDS, JSON.stringify(k)).catch(() => {});
  }, []);

  const toggleKeyword = useCallback(
    (k: string) => setKeywords(keywords.includes(k) ? keywords.filter((x) => x !== k) : [...keywords, k]),
    [keywords, setKeywords],
  );

  const reloadMeta = useCallback(async () => {
    try {
      setMeta(await api.meta());
      setMetaError(null);
    } catch (e) {
      setMetaError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    reloadMeta();
  }, [reloadMeta]);

  const value = useMemo<AppState>(() => {
    const flavors = meta?.flavorCategories ?? FALLBACK_FLAVORS;
    const byId = new Map(flavors.map((f) => [f.id as string, f]));
    return { deviceId, keywords, setKeywords, toggleKeyword, meta, metaError, reloadMeta, flavor: (id) => byId.get(id) };
  }, [deviceId, keywords, setKeywords, toggleKeyword, meta, metaError, reloadMeta]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState() {
  const v = useContext(Ctx);
  if (!v) throw new Error('AppStateProvider 가 필요합니다');
  return v;
}
