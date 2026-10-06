import * as Notifications from "expo-notifications";
import * as Localization from "expo-localization";
import { Stack, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useMemo, useState } from "react";
import { I18nManager, Platform, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { isRTL } from "../src/i18n";
import { AppProvider, createAppStores, useAuth, useClient, useStores, useT, type AppStores } from "../src/lib/app-context";
import { decideApproval } from "../src/lib/approve";
import { parseDeepLink, routeFor } from "../src/lib/deeplink";
import { handleNotificationResponse, installNotificationCategories, installNotificationHandler, subscribeInbox } from "../src/lib/push";
import { secureStore } from "../src/lib/storage";
import { isPaired } from "../src/stores/auth";
import { colors } from "../src/lib/theme";
import { Loading } from "../src/components/ui";

installNotificationHandler();

export default function RootLayout() {
  const [stores, setStores] = useState<AppStores | undefined>(undefined);

  useEffect(() => {
    let active = true;
    (async () => {
      const storage = await secureStore();
      const deviceLocale = Localization.getLocales()[0]?.languageCode ?? undefined;
      const created = createAppStores(storage, deviceLocale);
      await Promise.all([created.auth.getState().hydrate(), created.inbox.getState().hydrate()]);
      const rtl = isRTL(created.auth.getState().locale);
      if (I18nManager.isRTL !== rtl) {
        I18nManager.allowRTL(rtl);
        I18nManager.forceRTL(rtl);
      }
      if (active) setStores(created);
    })();
    return () => {
      active = false;
    };
  }, []);

  if (!stores) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        <Loading />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AppProvider stores={stores}>
          <StatusBar style="light" />
          <Navigation />
        </AppProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

function Navigation() {
  const t = useT();
  const paired = useAuth((state) => isPaired(state));
  return (
    <>
      <PushBridge />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTintColor: colors.text,
          headerTitleStyle: { color: colors.text },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Protected guard={paired}>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="settings" options={{ title: t("settings.title"), presentation: "modal" }} />
          <Stack.Screen name="notifications" options={{ title: t("notifications.title") }} />
          <Stack.Screen name="result/[id]" options={{ title: t("result.title") }} />
        </Stack.Protected>
        <Stack.Protected guard={!paired}>
          <Stack.Screen name="pairing" options={{ title: t("pairing.title"), headerShown: false }} />
        </Stack.Protected>
      </Stack>
    </>
  );
}

/** Notification categories, inbox capture and response routing (tap / action buttons). */
function PushBridge() {
  const router = useRouter();
  const { inbox } = useStores();
  const client = useClient();
  const locale = useAuth((state) => state.locale);
  const lastResponse = Notifications.useLastNotificationResponse();
  const handlers = useMemo(
    () => ({
      async decide(approvalId: string, decision: "confirm" | "cancel") {
        if (!client) return;
        await decideApproval(client, approvalId, decision);
        router.push(routeFor({ kind: "approval", id: approvalId }));
      },
      open(deepLink: string | undefined) {
        const parsed = deepLink ? parseDeepLink(deepLink) : undefined;
        router.push(parsed ? routeFor(parsed) : "/notifications");
      },
    }),
    [client, router],
  );

  useEffect(() => {
    if (Platform.OS === "web") return;
    void installNotificationCategories();
  }, [locale]);

  useEffect(() => subscribeInbox(inbox), [inbox]);

  useEffect(() => {
    const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
      void handleNotificationResponse(response, handlers);
    });
    return () => subscription.remove();
  }, [handlers]);

  useEffect(() => {
    if (lastResponse && lastResponse.actionIdentifier === Notifications.DEFAULT_ACTION_IDENTIFIER) {
      void handleNotificationResponse(lastResponse, handlers);
      void Notifications.clearLastNotificationResponseAsync();
    }
  }, [lastResponse, handlers]);

  return null;
}
