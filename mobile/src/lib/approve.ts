import type { ApprovalDecision, ApprovalDecisionResponse, GatewayClient } from "@nanoagent/sdk";
import { useCallback } from "react";
import { Alert } from "react-native";

import { t } from "../i18n";
import { confirmWithBiometrics } from "./biometric";

export type DecideResult =
  | { ok: true; response: ApprovalDecisionResponse }
  | { ok: false; reason: "biometric" | "cancelled" | "error"; error?: unknown };

/**
 * `POST /approvals/{id}`; a `confirm` needs local biometric/passcode confirmation first
 * (05 §4). A device without any screen lock is refused rather than silently allowed.
 */
export async function decideApproval(
  client: GatewayClient,
  approvalId: string,
  decision: ApprovalDecision,
): Promise<DecideResult> {
  if (decision === "confirm") {
    const gate = await confirmWithBiometrics(t("biometric.prompt"));
    if (!gate.ok) return { ok: false, reason: gate.reason === "cancelled" ? "cancelled" : "biometric" };
  }
  try {
    const response = await client.decideApproval(approvalId, decision);
    return { ok: true, response };
  } catch (error) {
    return { ok: false, reason: "error", error };
  }
}

export function useDecide(client: GatewayClient | undefined, describe: (error: unknown) => string) {
  return useCallback(
    async (approvalId: string, decision: ApprovalDecision): Promise<ApprovalDecisionResponse | undefined> => {
      if (!client) return undefined;
      const result = await decideApproval(client, approvalId, decision);
      if (result.ok) return result.response;
      if (result.reason === "biometric") Alert.alert(t("biometric.unavailable"));
      else if (result.reason === "error") Alert.alert(t("common.error_generic"), describe(result.error));
      return undefined;
    },
    [client, describe],
  );
}
