// 생두 상세: 큰 썸네일, 컵노트(색·이모지), 맛 그래프, 산지/품종/가공 정보, 구매 페이지로 이동
import { router, Stack, useLocalSearchParams } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Linking, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Badges, BeanThumb } from '@/components/BeanCard';
import { Chip } from '@/components/Chip';
import { FlavorMixLegend, FlavorStripe, NoteChips, ProfileBars } from '@/components/Flavor';
import { api } from '@/lib/api';
import { ago, discountRate, won, weight } from '@/lib/format';
import { useTheme } from '@/lib/theme';
import type { Bean } from '@/lib/types';

async function openShop(url: string) {
  // 앱 안 브라우저로 열고, 안 되면 기본 브라우저로
  try {
    if (Platform.OS === 'web') await Linking.openURL(url);
    else await WebBrowser.openBrowserAsync(url);
  } catch {
    Linking.openURL(url);
  }
}

// 상세의 태그를 누르면 목록으로 돌아가 그 조건으로 필터
const filterBy = (key: 'keyword' | 'origin' | 'shop' | 'variety' | 'process', value: string) =>
  router.navigate({ pathname: '/', params: { [key]: value } });

export default function BeanScreen() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [bean, setBean] = useState<Bean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.bean(String(id)).then(setBean, (e) => setError(e.message));
  }, [id]);

  if (error) return <Text style={{ color: t.danger, padding: 24 }}>{error}</Text>;
  if (!bean) return <ActivityIndicator style={{ marginTop: 48 }} color={t.muted} />;

  const d = discountRate(bean);
  const rows: [string, string | null, (() => void)?][] = [
    ['산지', bean.origin ? `${bean.origin.flag} ${bean.origin.country}${bean.origin.region ? ` · ${bean.origin.region}` : ''}` : null, bean.origin ? () => filterBy('origin', bean.origin!.country) : undefined],
    ['품종', bean.varieties.join(', ') || null, bean.varieties[0] ? () => filterBy('variety', bean.varieties[0]) : undefined],
    ['가공', bean.processes.join(', ') || null, bean.processes[0] ? () => filterBy('process', bean.processes[0]) : undefined],
    ['중량', bean.weightGrams ? weight(bean.weightGrams) : null],
    ['판매처', bean.shopName, () => filterBy('shop', bean.shopId)],
    ['입고', `${ago(bean.firstSeenAt)} 처음 확인${bean.restockedAt ? ` · ${ago(bean.restockedAt)} 재입고` : ''}`],
  ];

  return (
    <View style={{ flex: 1, backgroundColor: t.bg }}>
      <Stack.Screen options={{ title: bean.shopName }} />
      <ScrollView contentContainerStyle={{ paddingBottom: 110 + insets.bottom }}>
        <View>
          <BeanThumb bean={bean} style={styles.hero} />
          <Badges bean={bean} />
          <FlavorStripe mix={bean.flavorMix} height={8} />
        </View>

        <View style={styles.section}>
          <Text style={[styles.shop, { color: t.muted }]}>{bean.shopName}</Text>
          <Text style={[styles.name, { color: t.text }]}>{bean.name}</Text>
          <View style={styles.priceRow}>
            {d ? <Text style={[styles.discount, { color: t.danger }]}>{d}%</Text> : null}
            <Text style={[styles.price, { color: t.text }]}>{bean.price ? won(bean.price) : '가격 문의'}</Text>
            {bean.listPrice ? <Text style={[styles.listPrice, { color: t.muted }]}>{won(bean.listPrice)}</Text> : null}
          </View>
          {bean.pricePerKg ? <Text style={{ color: t.muted }}>1kg당 {won(bean.pricePerKg)}</Text> : null}
          {bean.prevPrice && bean.price && bean.prevPrice !== bean.price ? (
            <Text style={{ color: bean.price < bean.prevPrice ? t.accent : t.danger, marginTop: 2 }}>
              이전 {won(bean.prevPrice)} → 지금 {won(bean.price)}
            </Text>
          ) : null}
          {bean.soldOut ? <Text style={[styles.soldOut, { color: t.danger }]}>현재 품절입니다</Text> : null}
        </View>

        <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
          <Text style={[styles.h2, { color: t.text }]}>🎯 컵노트</Text>
          {bean.notes.length ? (
            <>
              <NoteChips notes={bean.notes} size="lg" />
              <FlavorStripe mix={bean.flavorMix} height={10} rounded />
              <FlavorMixLegend mix={bean.flavorMix} />
            </>
          ) : (
            <Text style={{ color: t.muted }}>쇼핑몰에 컵노트가 적혀 있지 않습니다. 구매 페이지의 상세 설명을 확인해 주세요.</Text>
          )}
        </View>

        {bean.profile ? (
          <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
            <Text style={[styles.h2, { color: t.text }]}>📊 맛 그래프</Text>
            <ProfileBars profile={bean.profile} />
            <Text style={[styles.note, { color: t.muted }]}>컵노트와 설명을 바탕으로 자동 추정한 값입니다.</Text>
          </View>
        ) : null}

        <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
          <Text style={[styles.h2, { color: t.text }]}>ℹ️ 정보</Text>
          {rows
            .filter(([, v]) => v)
            .map(([k, v, onPress]) => (
              <Pressable key={k} onPress={onPress} disabled={!onPress} style={[styles.infoRow, { borderColor: t.border }]}>
                <Text style={[styles.infoKey, { color: t.muted }]}>{k}</Text>
                <Text style={[styles.infoVal, { color: onPress ? t.accent : t.text }]}>{v}</Text>
              </Pressable>
            ))}
          {bean.tags.length ? (
            <View style={styles.tags}>
              {bean.tags.map((tag) => (
                <Chip key={tag} small label={`#${tag}`} onPress={() => filterBy('keyword', tag)} />
              ))}
            </View>
          ) : null}
          {bean.description ? <Text style={[styles.desc, { color: t.muted }]}>{bean.description}</Text> : null}
        </View>
      </ScrollView>

      <View style={[styles.bottom, { paddingBottom: insets.bottom + 10, backgroundColor: t.bg, borderColor: t.border }]}>
        <Pressable
          onPress={() => openShop(bean.url)}
          style={({ pressed }) => [styles.buy, { backgroundColor: t.accent, opacity: pressed ? 0.85 : 1 }]}
          accessibilityRole="link"
        >
          <Text style={[styles.buyText, { color: t.accentText }]}>{bean.shopName}에서 구매하기 →</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  hero: { aspectRatio: 1.25 },
  section: { padding: 16, gap: 4 },
  shop: { fontSize: 13 },
  name: { fontSize: 21, fontWeight: '700', lineHeight: 28 },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: 8, marginTop: 6 },
  discount: { fontSize: 20, fontWeight: '800' },
  price: { fontSize: 22, fontWeight: '800' },
  listPrice: { fontSize: 14, textDecorationLine: 'line-through' },
  soldOut: { fontWeight: '700', marginTop: 4 },
  card: { marginHorizontal: 12, marginBottom: 12, padding: 16, borderRadius: 14, borderWidth: StyleSheet.hairlineWidth, gap: 12 },
  h2: { fontSize: 16, fontWeight: '700' },
  note: { fontSize: 12 },
  infoRow: { flexDirection: 'row', paddingVertical: 9, borderBottomWidth: StyleSheet.hairlineWidth, gap: 12 },
  infoKey: { width: 56, fontSize: 14 },
  infoVal: { flex: 1, fontSize: 14, fontWeight: '500' },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  desc: { fontSize: 13.5, lineHeight: 20 },
  bottom: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: 16, paddingTop: 10, borderTopWidth: StyleSheet.hairlineWidth },
  buy: { borderRadius: 14, paddingVertical: 16, alignItems: 'center' },
  buyText: { fontSize: 16, fontWeight: '700' },
});
