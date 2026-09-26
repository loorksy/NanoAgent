import type { ApprovalDecision, GatewayClient, PushPayload } from "@mokli/sdk";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

import { t } from "../i18n";
import type { AuthStoreApi } from "../stores/auth";
import type { InboxStoreApi } from "../stores/notifications";
import { pushPayloadFromData } from "../stores/notifications";

export const ANDROID_CHANNEL_ID = "default";
export const APPROVAL_CATEGORY = "mokli.approval";
export const OPEN_CATEGORY = "mokli.open";
export const ACTION_CONFIRM = "confirm";
export const ACTION_CANCEL = "cancel";
export const ACTION_OPEN = "open";

/** Foreground presentation: show banners, keep the badge honest. */
export function installNotificationHandler(): void {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
    }),
  });
}

/** Categories with actions; labels use the active locale at install time. */
export async function installNotificationCategories(): Promise<void> {
  await Notifications.setNotificationCategoryAsync(APPROVAL_CATEGORY, [
    {
      identifier: ACTION_CONFIRM,
      buttonTitle: t("notifications.action.confirm"),
      options: { opensAppToForeground: true },
    },
    {
      identifier: ACTION_CANCEL,
      buttonTitle: t("notifications.action.cancel"),
      options: { isDestructive: true, opensAppToForeground: false },
    },
  ]);
  await Notifications.setNotificationCategoryAsync(OPEN_CATEGORY, [
    { identifier: ACTION_OPEN, buttonTitle: t("notifications.action.open"), options: { opensAppToForeground: true } },
  ]);
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync(ANDROID_CHANNEL_ID, {
      name: t("app.name"),
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#f5b833",
    });
  }
}

export type PushRegistrationResult =
  | { ok: true; platform: "ios" | "android"; token: string; deviceId: string }
  | { ok: false; reason: "denied" | "unsupported" | "error"; error?: unknown };

/**
 * Ask for permission, fetch the native FCM/APNs token and register it with the gateway
 * (`POST /devices`). The gateway routes pushes to this device only while no live
 * WebSocket/SSE connection is open for the session.
 */
export async function registerForPush(
  client: GatewayClient,
  auth: AuthStoreApi,
  options: { label?: string } = {},
): Promise<PushRegistrationResult> {
  if (Platform.OS !== "ios" && Platform.OS !== "android") return { ok: false, reason: "unsupported" };
  const platform = Platform.OS;
  try {
    let permission = await Notifications.getPermissionsAsync();
    if (permission.status !== "granted") permission = await Notifications.requestPermissionsAsync();
    if (permission.status !== "granted") return { ok: false, reason: "denied" };
    const native = await Notifications.getDevicePushTokenAsync();
    const token = typeof native.data === "string" ? native.data : JSON.stringify(native.data);
    const { locale } = auth.getState();
    const device = await client.registerDevice({
      platform,
      push_token: token,
      label: options.label ?? "",
      locale,
    });
    await auth.getState().setPushRegistration(platform, token, device.id);
    return { ok: true, platform, token, deviceId: device.id };
  } catch (error) {
    return { ok: false, reason: "error", error };
  }
}

export function payloadFromNotification(notification: Notifications.Notification): PushPayload | undefined {
  const data = notification.request.content.data as Record<string, unknown> | null | undefined;
  return pushPayloadFromData(data);
}

export interface PushResponseHandlers {
  /** Confirm/cancel straight from the notification (biometric gate is applied by the caller). */
  decide(approvalId: string, decision: ApprovalDecision, session?: string): Promise<void>;
  open(deepLink: string | undefined, payload: PushPayload): void;
}

/** Translate a tap / action button into an app action. */
export async function handleNotificationResponse(
  response: Notifications.NotificationResponse,
  handlers: PushResponseHandlers,
): Promise<void> {
  const payload = payloadFromNotification(response.notification);
  if (!payload) return;
  const action = response.actionIdentifier;
  if (payload.approval_id && (action === ACTION_CONFIRM || action === ACTION_CANCEL)) {
    await handlers.decide(payload.approval_id, action === ACTION_CONFIRM ? "confirm" : "cancel", payload.session);
    return;
  }
  handlers.open(payload.deep_link, payload);
}

/** Store pushes that arrived while the app was in the foreground/background. */
export function subscribeInbox(inbox: InboxStoreApi): () => void {
  const received = Notifications.addNotificationReceivedListener((notification) => {
    const payload = payloadFromNotification(notification);
    if (payload) void inbox.getState().addPush(payload, { id: notification.request.identifier, ts: notification.date });
  });
  return () => received.remove();
}
