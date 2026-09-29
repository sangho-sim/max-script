import { Image } from 'expo-image';
import { Link } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useAppState } from '@/lib/app-state';
import { discountRate, isNew, isRestocked, won, weight } from '@/lib/format';
import { tint, useTheme } from '@/lib/theme';
import type { Bean } from '@/lib/types';
import { FlavorStripe, NoteChips } from './Flavor';

/** 썸네일. 이미지가 없으면 대표 향미 색 + 국기로 채운다. */
export function BeanThumb({ bean, style }: { bean: Bean; style?: object }) {
  const { flavor } = useAppState();
  const t = useTheme();
  const main = bean.flavorMix?.[0] ? flavor(bean.flavorMix[0].category) : undefined;
  return (
    <View style={[styles.thumb, { backgroundColor: main ? tint(main.color, 0.22) : t.sunken }, style]}>
      {bean.imageUrl ? (
        <Image source={{ uri: bean.imageUrl }} style={StyleSheet.absoluteFill} contentFit="cover" transition={150} recyclingKey={bean.id} />
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderFlag}>{bean.origin?.flag ?? '☕'}</Text>
          <Text style={[styles.placeholderText, { color: t.text }]} numberOfLines={1}>
            {bean.origin?.region ?? bean.origin?.country ?? ''}
          </Text>
          {main ? <Text style={styles.placeholderEmoji}>{bean.flavorMix.slice(0, 3).map((m) => flavor(m.category)?.emoji).join(' ')}</Text> : null}
        </View>
      )}
      {bean.soldOut ? (
        <View style={[StyleSheet.absoluteFill, styles.soldOut, { backgroundColor: t.overlay }]}>
          <Text style={styles.soldOutText}>품절</Text>
        </View>
      ) : null}
    </View>
  );
}

export function Badges({ bean }: { bean: Bean }) {
  const t = useTheme();
  const d = discountRate(bean);
  return (
    <View style={styles.badges}>
      {isNew(bean) ? <Text style={[styles.badge, { backgroundColor: t.newBadge }]}>NEW</Text> : null}
      {isRestocked(bean) ? <Text style={[styles.badge, { backgroundColor: t.accent }]}>재입고</Text> : null}
      {d >= 3 ? <Text style={[styles.badge, { backgroundColor: t.danger }]}>{d}%</Text> : null}
    </View>
  );
}

export function BeanCard({ bean }: { bean: Bean }) {
  const t = useTheme();
  const origin = bean.origin ? `${bean.origin.flag} ${bean.origin.country}` : '';
  const sub = [origin, bean.processes[0]].filter(Boolean).join(' · ');
  return (
    <Link href={{ pathname: '/bean/[id]', params: { id: bean.id } }} asChild>
      <Pressable style={({ pressed }) => [styles.card, { backgroundColor: t.card, borderColor: t.border, opacity: pressed ? 0.85 : 1 }]}>
        <View>
          <BeanThumb bean={bean} />
          <Badges bean={bean} />
          <FlavorStripe mix={bean.flavorMix} />
        </View>
        <View style={styles.body}>
          <Text style={[styles.shop, { color: t.muted }]} numberOfLines={1}>
            {bean.shopName}
          </Text>
          <Text style={[styles.name, { color: t.text }]} numberOfLines={2}>
            {bean.name}
          </Text>
          {sub ? (
            <Text style={[styles.sub, { color: t.muted }]} numberOfLines={1}>
              {sub}
            </Text>
          ) : null}
          <View style={styles.priceRow}>
            <Text style={[styles.price, { color: t.text }]}>{bean.price ? won(bean.price) : '가격 문의'}</Text>
            {bean.weightGrams ? <Text style={[styles.per, { color: t.muted }]}>/{weight(bean.weightGrams)}</Text> : null}
          </View>
          {bean.pricePerKg && bean.weightGrams !== 1000 ? (
            <Text style={[styles.per, { color: t.muted }]}>kg당 {won(bean.pricePerKg)}</Text>
          ) : null}
          <NoteChips notes={bean.notes} max={3} />
        </View>
      </Pressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  card: { flex: 1, borderRadius: 14, overflow: 'hidden', borderWidth: StyleSheet.hairlineWidth },
  thumb: { width: '100%', aspectRatio: 1, overflow: 'hidden' },
  placeholder: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 4, padding: 8 },
  placeholderFlag: { fontSize: 44 },
  placeholderText: { fontSize: 13, fontWeight: '600' },
  placeholderEmoji: { fontSize: 18, marginTop: 2 },
  soldOut: { alignItems: 'center', justifyContent: 'center' },
  soldOutText: { color: '#fff', fontWeight: '700', fontSize: 16, letterSpacing: 2 },
  badges: { position: 'absolute', top: 8, left: 8, flexDirection: 'row', gap: 4 },
  badge: { color: '#fff', fontSize: 11, fontWeight: '700', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
  body: { padding: 10, gap: 4 },
  shop: { fontSize: 12 },
  name: { fontSize: 14, fontWeight: '600', lineHeight: 19 },
  sub: { fontSize: 12.5 },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', marginTop: 2 },
  price: { fontSize: 15, fontWeight: '700' },
  per: { fontSize: 12 },
});
