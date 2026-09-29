import { Tabs } from 'expo-router/js-tabs';
import { Text } from 'react-native';
import { useTheme } from '@/lib/theme';

const icon = (emoji: string) =>
  function TabIcon({ focused }: { focused: boolean }) {
    return <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.5 }}>{emoji}</Text>;
  };

export default function TabLayout() {
  const t = useTheme();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: t.accent,
        tabBarInactiveTintColor: t.muted,
        tabBarStyle: { backgroundColor: t.card, borderTopColor: t.border },
        sceneStyle: { backgroundColor: t.bg },
      }}
    >
      <Tabs.Screen name="index" options={{ title: '생두', tabBarIcon: icon('🫘') }} />
      <Tabs.Screen name="keywords" options={{ title: '키워드', tabBarIcon: icon('🏷️') }} />
      <Tabs.Screen name="alerts" options={{ title: '알림', tabBarIcon: icon('🔔') }} />
    </Tabs>
  );
}
