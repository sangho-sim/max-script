// 컵노트를 한눈에: 향미 카테고리 색 + 이모지 칩, 카테고리 비중 막대, 산미/단맛/바디 그래프.
import { StyleSheet, Text, View } from 'react-native';
import { useAppState } from '@/lib/app-state';
import { tint, useTheme } from '@/lib/theme';
import type { Bean, Note } from '@/lib/types';

export function NoteChips({ notes, max, size = 'sm' }: { notes: Note[]; max?: number; size?: 'sm' | 'lg' }) {
  const { flavor } = useAppState();
  const t = useTheme();
  const shown = max ? notes.slice(0, max) : notes;
  if (!shown.length) return null;
  const lg = size === 'lg';
  return (
    <View style={styles.wrap}>
      {shown.map((n) => {
        const f = flavor(n.category);
        const color = f?.color ?? t.muted;
        return (
          <View key={n.label} style={[styles.note, lg && styles.noteLg, { backgroundColor: tint(color, lg ? 0.2 : 0.16), borderColor: tint(color, 0.45) }]}>
            <Text style={[styles.noteText, lg && styles.noteTextLg, { color: t.text }]} numberOfLines={1}>
              {f?.emoji} {n.label}
            </Text>
          </View>
        );
      })}
      {max && notes.length > max ? <Text style={[styles.more, { color: t.muted }]}>+{notes.length - max}</Text> : null}
    </View>
  );
}

/** 카테고리 비중을 색 띠로 (썸네일 아래·상세 화면) */
export function FlavorStripe({ mix, height = 5, rounded = false }: { mix: Bean['flavorMix']; height?: number; rounded?: boolean }) {
  const { flavor } = useAppState();
  if (!mix?.length) return null;
  return (
    <View style={[styles.stripe, { height, borderRadius: rounded ? height / 2 : 0 }]}>
      {mix.map((m) => (
        <View key={m.category} style={{ flex: m.ratio, backgroundColor: flavor(m.category)?.color ?? '#999' }} />
      ))}
    </View>
  );
}

export function FlavorMixLegend({ mix }: { mix: Bean['flavorMix'] }) {
  const { flavor } = useAppState();
  const t = useTheme();
  return (
    <View style={styles.wrap}>
      {mix.map((m) => {
        const f = flavor(m.category);
        return (
          <View key={m.category} style={styles.legendItem}>
            <View style={[styles.dot, { backgroundColor: f?.color }]} />
            <Text style={[styles.legendText, { color: t.muted }]}>
              {f?.emoji} {f?.name} {Math.round(m.ratio * 100)}%
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const PROFILE_ROWS = [
  { key: 'acidity', label: '산미', emoji: '🍋', color: '#E2B200' },
  { key: 'sweetness', label: '단맛', emoji: '🍯', color: '#D08A2E' },
  { key: 'body', label: '바디', emoji: '🫘', color: '#6B4226' },
] as const;

export function ProfileBars({ profile }: { profile: NonNullable<Bean['profile']> }) {
  const t = useTheme();
  return (
    <View style={{ gap: 10 }}>
      {PROFILE_ROWS.map((r) => (
        <View key={r.key} style={styles.profileRow} accessibilityLabel={`${r.label} 5점 중 ${profile[r.key]}점`}>
          <Text style={[styles.profileLabel, { color: t.text }]}>
            {r.emoji} {r.label}
          </Text>
          <View style={styles.profileTrack}>
            {[1, 2, 3, 4, 5].map((i) => (
              <View key={i} style={[styles.profileCell, { backgroundColor: i <= profile[r.key] ? r.color : t.sunken }]} />
            ))}
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 5, alignItems: 'center' },
  note: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 999, borderWidth: StyleSheet.hairlineWidth },
  noteLg: { paddingHorizontal: 12, paddingVertical: 7 },
  noteText: { fontSize: 11.5 },
  noteTextLg: { fontSize: 15, fontWeight: '500' },
  more: { fontSize: 11.5 },
  stripe: { flexDirection: 'row', overflow: 'hidden', width: '100%' },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4, marginRight: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 12.5 },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  profileLabel: { width: 64, fontSize: 14, fontWeight: '500' },
  profileTrack: { flex: 1, flexDirection: 'row', gap: 4 },
  profileCell: { flex: 1, height: 12, borderRadius: 3 },
});
