import * as LocalAuthentication from "expo-local-authentication";

import { t } from "../i18n";

export type BiometricResult = { ok: true } | { ok: false; reason: "unavailable" | "failed" | "cancelled" };

/**
 * Local confirmation required before `approve` and before raising an MT5 permission level
 * (05 §4). Falls back to the device passcode when no biometrics are enrolled; when the
 * device has no lock at all the caller decides whether to continue.
 */
export async function confirmWithBiometrics(prompt?: string): Promise<BiometricResult> {
  const hardware = await LocalAuthentication.hasHardwareAsync();
  const enrolled = hardware && (await LocalAuthentication.isEnrolledAsync());
  const level = await LocalAuthentication.getEnrolledLevelAsync();
  if (!enrolled && level === LocalAuthentication.SecurityLevel.NONE) return { ok: false, reason: "unavailable" };
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: prompt ?? t("biometric.prompt"),
    cancelLabel: t("common.cancel"),
    disableDeviceFallback: false,
  });
  if (result.success) return { ok: true };
  return { ok: false, reason: result.error === "user_cancel" || result.error === "system_cancel" ? "cancelled" : "failed" };
}
