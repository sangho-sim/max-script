// 생두 목록: 통합 검색 + 산지/품종/가공/맛/회사/가격 필터 + 내 키워드 칩 + 썸네일 그리드
import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { BeanCard } from '@/components/BeanCard';
import { Chip } from '@/components/Chip';
import { PriceSheet } from '@/components/PriceSheet';
import { SelectSheet, type Option } from '@/components/Sheet';
import { EMPTY_FILTERS, api } from '@/lib/api';
import { useAppState } from '@/lib/app-state';
import { ago, won } from '@/lib/format';
import { useTheme } from '@/lib/theme';
import type { Bean, Filters, SortKey } from '@/lib/types';

type SheetKey = 'origin' | 'variety' | 'process' | 'flavor' | 'shop' | 'sort' | 'price' | null;

const SORTS: { value: SortKey; label: string }[] = [
  { value: 'new', label: '신규 입고순' },
  { value: 'price_asc', label: '낮은 가격순' },
  { value: 'price_desc', label: '높은 가격순' },
  { value: 'kg_asc', label: 'kg당 낮은 가격순' },
  { value: 'kg_desc', label: 'kg당 높은 가격순' },
  { value: 'name', label: '이름순' },
];

// 홀수 개일 때 마지막 카드가 두 칸을 차지하지 않도록 빈 칸을 채운다
const FILLER = { id: '__filler' } as Bean;

const listParam = (v: string | string[] | undefined) => (v ? String(v).split(',').filter(Boolean) : null);

export default function BrowseScreen() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { meta, metaError, reloadMeta, keywords } = useAppState();
  const params = useLocalSearchParams<{ keyword?: string; origin?: string; shop?: string; variety?: string; process?: string }>();

  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<Bean[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sheet, setSheet] = useState<SheetKey>(null);
  const reqId = useRef(0);

  // 상세 화면에서 태그를 눌러 들어오면 그 조건으로 필터
  useEffect(() => {
    const patch: Partial<Filters> = {};
    for (const k of ['keyword', 'origin', 'shop', 'variety', 'process'] as const) {
      const v = listParam(params[k]);
      if (v) patch[k] = v;
    }
    if (Object.keys(patch).length) setFilters({ ...EMPTY_FILTERS, ...patch });
  }, [params.keyword, params.origin, params.shop, params.variety, params.process]);

  // 검색어는 입력이 멈춘 뒤 반영
  useEffect(() => {
    const h = setTimeout(() => setFilters((f) => (f.q === query ? f : { ...f, q: query })), 300);
    return () => clearTimeout(h);
  }, [query]);

  const load = useCallback(
    async (p: number, mode: 'reset' | 'more' | 'refresh') => {
      const id = ++reqId.current;
      if (mode === 'refresh') setRefreshing(true);
      else setLoading(true);
      try {
        const r = await api.search(filters, p);
        if (id !== reqId.current) return;
        setItems((prev) => (p === 1 ? r.items : [...prev, ...r.items.filter((b) => !prev.some((x) => x.id === b.id))]));
        setTotal(r.total);
        setPage(p);
        setError(null);
      } catch (e) {
        if (id === reqId.current) setError((e as Error).message);
      } finally {
        if (id === reqId.current) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [filters],
  );

  useEffect(() => {
    load(1, 'reset');
  }, [load]);

  const f = meta?.facets;
  const options: Record<'origin' | 'variety' | 'process' | 'flavor' | 'shop', Option[]> = useMemo(
    () => ({
      origin: (f?.origins ?? []).map((o) => ({ value: o.country, label: o.country, prefix: o.flag, count: o.count })),
      variety: (f?.varieties ?? []).map((v) => ({ value: v.name, label: v.name, count: v.count })),
      process: (f?.processes ?? []).map((v) => ({ value: v.name, label: v.name, count: v.count })),
      flavor: (f?.flavors ?? []).map((v) => ({ value: v.id, label: v.name, prefix: v.emoji, count: v.count })),
      shop: (f?.shops ?? []).map((s) => ({ value: s.id, label: s.name, count: s.count })),
    }),
    [f],
  );

  const set = (patch: Partial<Filters>) => setFilters((cur) => ({ ...cur, ...patch }));
  const toggleKeyword = (k: string) => set({ keyword: filters.keyword.includes(k) ? filters.keyword.filter((x) => x !== k) : [...filters.keyword, k] });

  const priceLabel =
    filters.minPrice == null && filters.maxPrice == null
      ? '가격'
      : `${filters.priceBasis === 'kg' ? 'kg당 ' : ''}${filters.minPrice ? won(filters.minPrice) : ''}~${filters.maxPrice ? won(filters.maxPrice) : ''}`;
  const facetLabel = (name: string, sel: string[], opts: Option[]) =>
    sel.length === 0 ? name : sel.length === 1 ? (opts.find((o) => o.value === sel[0])?.label ?? sel[0]) : `${name} ${sel.length}`;

  const activeCount =
    filters.origin.length + filters.variety.length + filters.process.length + filters.flavor.length + filters.shop.length + filters.keyword.length +
    (filters.minPrice != null || filters.maxPrice != null ? 1 : 0) + (filters.inStock ? 1 : 0) + (filters.newWithinDays ? 1 : 0);

  // 칩에는 내 키워드 + (내 키워드에 없는) 지금 선택된 키워드
  const keywordChips = [...keywords, ...filters.keyword.filter((k) => !keywords.includes(k))];

  const header = (
    <View style={{ paddingTop: insets.top + 8 }}>
      <View style={styles.titleRow}>
        <Text style={[styles.title, { color: t.text }]}>☕ 생두 알리미</Text>
        <Text style={[styles.subtitle, { color: t.muted }]}>
          {meta ? `${meta.shops.length}개 쇼핑몰 · ${meta.facets.total.toLocaleString()}개 생두${meta.lastCrawlAt ? ` · ${ago(meta.lastCrawlAt)} 갱신` : ''}` : ''}
        </Text>
      </View>
      <View style={[styles.searchBox, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={{ fontSize: 16 }}>🔍</Text>
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder="이름·산지·품종·노트 검색"
          placeholderTextColor={t.muted}
          style={[styles.searchInput, { color: t.text }]}
          returnKeyType="search"
          clearButtonMode="while-editing"
          autoCorrect={false}
        />
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
        <Chip small label={facetLabel('산지', filters.origin, options.origin)} trailing="▾" selected={filters.origin.length > 0} onPress={() => setSheet('origin')} />
        <Chip small label={facetLabel('품종', filters.variety, options.variety)} trailing="▾" selected={filters.variety.length > 0} onPress={() => setSheet('variety')} />
        <Chip small label={facetLabel('가공', filters.process, options.process)} trailing="▾" selected={filters.process.length > 0} onPress={() => setSheet('process')} />
        <Chip small label={facetLabel('맛', filters.flavor, options.flavor)} trailing="▾" selected={filters.flavor.length > 0} onPress={() => setSheet('flavor')} />
        <Chip small label={facetLabel('회사', filters.shop, options.shop)} trailing="▾" selected={filters.shop.length > 0} onPress={() => setSheet('shop')} />
        <Chip small label={priceLabel} trailing="▾" selected={filters.minPrice != null || filters.maxPrice != null} onPress={() => setSheet('price')} />
        <Chip small label="재고만" selected={filters.inStock} onPress={() => set({ inStock: !filters.inStock })} />
        <Chip small label="7일 내 입고" selected={filters.newWithinDays === 7} onPress={() => set({ newWithinDays: filters.newWithinDays ? null : 7 })} />
      </ScrollView>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
        {keywordChips.map((k) => (
          <Chip key={k} small label={`#${k}`} selected={filters.keyword.includes(k)} onPress={() => toggleKeyword(k)} />
        ))}
      </ScrollView>
      <View style={styles.resultRow}>
        <Text style={{ color: t.muted, fontSize: 13 }}>{total.toLocaleString()}개</Text>
        <View style={{ flexDirection: 'row', gap: 14 }}>
          {activeCount > 0 ? (
            <Pressable onPress={() => { setFilters({ ...EMPTY_FILTERS, sort: filters.sort }); setQuery(''); }}>
              <Text style={{ color: t.accent, fontSize: 13, fontWeight: '600' }}>필터 초기화</Text>
            </Pressable>
          ) : null}
          <Pressable onPress={() => setSheet('sort')}>
            <Text style={{ color: t.text, fontSize: 13, fontWeight: '600' }}>{SORTS.find((s) => s.value === filters.sort)?.label} ▾</Text>
          </Pressable>
        </View>
      </View>
      {error || metaError ? (
        <Pressable onPress={() => { reloadMeta(); load(1, 'reset'); }} style={[styles.error, { backgroundColor: t.sunken }]}>
          <Text style={{ color: t.danger, fontWeight: '600' }}>서버에 연결할 수 없습니다</Text>
          <Text style={{ color: t.muted, fontSize: 12.5 }}>{error ?? metaError} · 눌러서 다시 시도</Text>
        </Pressable>
      ) : null}
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: t.bg }}>
      <FlatList
        data={items.length % 2 ? [...items, FILLER] : items}
        keyExtractor={(b) => b.id}
        numColumns={2}
        ListHeaderComponent={header}
        columnWrapperStyle={styles.column}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => <View style={styles.cell}>{item === FILLER ? null : <BeanCard bean={item} />}</View>}
        onEndReachedThreshold={0.6}
        onEndReached={() => {
          if (!loading && items.length < total) load(page + 1, 'more');
        }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { reloadMeta(); load(1, 'refresh'); }} tintColor={t.muted} />}
        ListEmptyComponent={
          loading ? null : (
            <View style={styles.empty}>
              <Text style={{ fontSize: 40 }}>🫘</Text>
              <Text style={{ color: t.muted, textAlign: 'center' }}>{error ? '목록을 불러오지 못했습니다' : '조건에 맞는 생두가 없습니다'}</Text>
            </View>
          )
        }
        ListFooterComponent={loading ? <ActivityIndicator style={{ margin: 24 }} color={t.muted} /> : null}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
      />

      {(['origin', 'variety', 'process', 'flavor', 'shop'] as const).map((k) => (
        <SelectSheet
          key={k}
          visible={sheet === k}
          title={{ origin: '산지', variety: '품종', process: '가공방식', flavor: '맛 (향미 계열)', shop: '회사 (쇼핑몰)' }[k]}
          options={options[k]}
          selected={filters[k]}
          searchable={k === 'origin' || k === 'variety'}
          onClose={() => setSheet(null)}
          onApply={(v) => set({ [k]: v } as Partial<Filters>)}
        />
      ))}
      <SelectSheet
        visible={sheet === 'sort'}
        title="정렬"
        multi={false}
        options={SORTS}
        selected={[filters.sort]}
        onClose={() => setSheet(null)}
        onApply={(v) => set({ sort: v[0] as SortKey })}
      />
      <PriceSheet
        visible={sheet === 'price'}
        value={{ min: filters.minPrice, max: filters.maxPrice, basis: filters.priceBasis }}
        onClose={() => setSheet(null)}
        onApply={(v) => set({ minPrice: v.min, maxPrice: v.max, priceBasis: v.basis })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  list: { paddingHorizontal: 12, paddingBottom: 24 },
  column: { gap: 10 },
  cell: { flex: 1, marginBottom: 10 },
  titleRow: { paddingHorizontal: 4, marginBottom: 10 },
  title: { fontSize: 24, fontWeight: '800' },
  subtitle: { fontSize: 12.5, marginTop: 2 },
  searchBox: { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, marginBottom: 10 },
  searchInput: { flex: 1, fontSize: 15, paddingVertical: 11 },
  chipRow: { gap: 6, paddingBottom: 8, paddingHorizontal: 2 },
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 4, paddingVertical: 6 },
  error: { padding: 12, borderRadius: 10, marginBottom: 8, gap: 2 },
  empty: { alignItems: 'center', gap: 8, paddingVertical: 60 },
});
