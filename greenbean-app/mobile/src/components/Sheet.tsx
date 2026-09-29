// 아래에서 올라오는 필터 시트. 여러 개 고르기(산지·품종·회사…)와 하나 고르기(정렬)를 모두 지원.
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { FlatList, Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/lib/theme';

export function Sheet({ visible, title, onClose, children, footer }: { visible: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={[styles.backdrop, { backgroundColor: t.overlay }]} onPress={onClose} accessibilityLabel="닫기" />
      <View style={[styles.sheet, { backgroundColor: t.bg, paddingBottom: insets.bottom + 12 }]}>
        <View style={[styles.handle, { backgroundColor: t.border }]} />
        <Text style={[styles.title, { color: t.text }]}>{title}</Text>
        {children}
        {footer}
      </View>
    </Modal>
  );
}

export interface Option {
  value: string;
  label: string;
  count?: number;
  prefix?: string;
}

interface SelectProps {
  visible: boolean;
  title: string;
  options: Option[];
  selected: string[];
  multi?: boolean;
  searchable?: boolean;
  onClose: () => void;
  onApply: (values: string[]) => void;
}

export function SelectSheet({ visible, title, options, selected, multi = true, searchable, onClose, onApply }: SelectProps) {
  const t = useTheme();
  const [draft, setDraft] = useState<string[]>(selected);
  const [q, setQ] = useState('');
  useEffect(() => {
    if (visible) {
      setDraft(selected);
      setQ('');
    }
  }, [visible, selected]);

  const shown = useMemo(() => (q ? options.filter((o) => o.label.toLowerCase().includes(q.toLowerCase())) : options), [q, options]);

  const toggle = (v: string) => {
    if (!multi) {
      onApply([v]);
      onClose();
      return;
    }
    setDraft((d) => (d.includes(v) ? d.filter((x) => x !== v) : [...d, v]));
  };

  return (
    <Sheet
      visible={visible}
      title={title}
      onClose={onClose}
      footer={
        multi ? (
          <View style={styles.footer}>
            <Pressable style={[styles.btn, { borderColor: t.border }]} onPress={() => setDraft([])}>
              <Text style={{ color: t.text, fontWeight: '600' }}>초기화</Text>
            </Pressable>
            <Pressable
              style={[styles.btn, styles.primary, { backgroundColor: t.accent, borderColor: t.accent }]}
              onPress={() => {
                onApply(draft);
                onClose();
              }}
            >
              <Text style={{ color: t.accentText, fontWeight: '700' }}>{draft.length ? `${draft.length}개 적용` : '전체 보기'}</Text>
            </Pressable>
          </View>
        ) : null
      }
    >
      {searchable ? (
        <TextInput
          value={q}
          onChangeText={setQ}
          placeholder="찾기"
          placeholderTextColor={t.muted}
          style={[styles.search, { backgroundColor: t.card, color: t.text, borderColor: t.border }]}
        />
      ) : null}
      <FlatList
        data={shown}
        keyExtractor={(o) => o.value}
        style={{ maxHeight: 420 }}
        ListEmptyComponent={<Text style={{ color: t.muted, padding: 16 }}>항목이 없습니다</Text>}
        renderItem={({ item }) => {
          const on = draft.includes(item.value) || (!multi && selected.includes(item.value));
          return (
            <Pressable onPress={() => toggle(item.value)} style={[styles.row, { borderColor: t.border }]} accessibilityRole="checkbox" accessibilityState={{ checked: on }}>
              <Text style={[styles.rowText, { color: t.text }]}>
                {item.prefix ? `${item.prefix} ` : ''}
                {item.label}
                {item.count != null ? <Text style={{ color: t.muted }}>  {item.count}</Text> : null}
              </Text>
              <View style={[styles.check, { borderColor: on ? t.accent : t.border, backgroundColor: on ? t.accent : 'transparent' }]}>
                {on ? <Text style={{ color: t.accentText, fontSize: 13, fontWeight: '800' }}>✓</Text> : null}
              </View>
            </Pressable>
          );
        }}
      />
    </Sheet>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1 },
  sheet: { borderTopLeftRadius: 18, borderTopRightRadius: 18, paddingHorizontal: 16, paddingTop: 8, maxHeight: '85%' },
  handle: { alignSelf: 'center', width: 40, height: 4, borderRadius: 2, marginBottom: 10 },
  title: { fontSize: 18, fontWeight: '700', marginBottom: 10 },
  search: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 9, fontSize: 15, marginBottom: 6 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 13, borderBottomWidth: StyleSheet.hairlineWidth },
  rowText: { fontSize: 15.5, flex: 1 },
  check: { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center' },
  footer: { flexDirection: 'row', gap: 10, marginTop: 12 },
  btn: { flex: 1, borderWidth: 1, borderRadius: 12, paddingVertical: 13, alignItems: 'center' },
  primary: { flex: 2 },
});
