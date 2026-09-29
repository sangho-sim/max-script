import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useTheme } from '@/lib/theme';
import { Chip } from './Chip';
import { Sheet } from './Sheet';

type Basis = 'item' | 'kg';
interface Value {
  min: number | null;
  max: number | null;
  basis: Basis;
}

const PRESETS: { label: string; min: number | null; max: number | null }[] = [
  { label: '~1만원', min: null, max: 10000 },
  { label: '1~1.5만원', min: 10000, max: 15000 },
  { label: '1.5~2만원', min: 15000, max: 20000 },
  { label: '2~3만원', min: 20000, max: 30000 },
  { label: '3~5만원', min: 30000, max: 50000 },
  { label: '5만원~', min: 50000, max: null },
];

const toNum = (s: string) => {
  const n = parseInt(s.replace(/[^\d]/g, ''), 10);
  return Number.isFinite(n) && n > 0 ? n : null;
};

export function PriceSheet({ visible, value, onClose, onApply }: { visible: boolean; value: Value; onClose: () => void; onApply: (v: Value) => void }) {
  const t = useTheme();
  const [d, setD] = useState<Value>(value);
  useEffect(() => {
    if (visible) setD(value);
  }, [visible, value]);

  const input = (key: 'min' | 'max', placeholder: string) => (
    <TextInput
      value={d[key] == null ? '' : d[key]!.toLocaleString('ko-KR')}
      onChangeText={(s) => setD({ ...d, [key]: toNum(s) })}
      keyboardType="number-pad"
      placeholder={placeholder}
      placeholderTextColor={t.muted}
      style={[styles.input, { borderColor: t.border, color: t.text, backgroundColor: t.card }]}
    />
  );

  return (
    <Sheet visible={visible} title="가격" onClose={onClose}>
      <View style={styles.row}>
        <Chip label="상품 가격" selected={d.basis === 'item'} onPress={() => setD({ ...d, basis: 'item' })} />
        <Chip label="1kg당 가격" selected={d.basis === 'kg'} onPress={() => setD({ ...d, basis: 'kg' })} />
      </View>
      <Text style={[styles.hint, { color: t.muted }]}>
        {d.basis === 'kg' ? '용량이 달라도 1kg 기준으로 비교합니다 (200g·5kg 상품 등)' : '쇼핑몰에 표시된 판매가 기준입니다'}
      </Text>
      <View style={[styles.row, { flexWrap: 'wrap' }]}>
        {PRESETS.map((p) => (
          <Chip key={p.label} small label={p.label} selected={d.min === p.min && d.max === p.max} onPress={() => setD({ ...d, min: p.min, max: p.max })} />
        ))}
      </View>
      <View style={[styles.row, { alignItems: 'center' }]}>
        {input('min', '최소')}
        <Text style={{ color: t.muted }}>~</Text>
        {input('max', '최대')}
        <Text style={{ color: t.muted }}>원</Text>
      </View>
      <View style={styles.footer}>
        <Pressable style={[styles.btn, { borderColor: t.border }]} onPress={() => setD({ min: null, max: null, basis: d.basis })}>
          <Text style={{ color: t.text, fontWeight: '600' }}>초기화</Text>
        </Pressable>
        <Pressable
          style={[styles.btn, { flex: 2, backgroundColor: t.accent, borderColor: t.accent }]}
          onPress={() => {
            onApply(d);
            onClose();
          }}
        >
          <Text style={{ color: t.accentText, fontWeight: '700' }}>적용</Text>
        </Pressable>
      </View>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  hint: { fontSize: 13, marginBottom: 12 },
  input: { flex: 1, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  footer: { flexDirection: 'row', gap: 10, marginTop: 4 },
  btn: { flex: 1, borderWidth: 1, borderRadius: 12, paddingVertical: 13, alignItems: 'center' },
});
