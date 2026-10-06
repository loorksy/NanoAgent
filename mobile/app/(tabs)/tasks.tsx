import type { Approval, ApprovalDecision, Job } from "@mokli/sdk";
import { useApprovals, useJobs } from "@mokli/sdk/react";
import { useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, View } from "react-native";

import { ApprovalCard } from "../../src/components/cards";
import { Badge, Body, Button, Card, CardTitle, Empty, ErrorBox, Loading, Muted, Row, Screen, SectionTitle, describeError } from "../../src/components/ui";
import { useDecide } from "../../src/lib/approve";
import { useLocale, useRequiredClient, useT } from "../../src/lib/app-context";
import { formatRelative, toMillis } from "../../src/lib/format";
import { colors, spacing } from "../../src/lib/theme";

const POLL_MS = 15_000;

function jobTone(status: string): string {
  if (status === "working" || status === "active") return colors.info;
  if (status === "waiting" || status === "blocked") return colors.warning;
  if (status === "failed" || status === "error") return colors.danger;
  if (status === "finished" || status === "completed") return colors.success;
  return colors.textMuted;
}

function JobCard({ job, onPause, onResume, onCancel, highlighted }: { job: Job; onPause: () => void; onResume: () => void; onCancel: () => void; highlighted: boolean }) {
  const t = useT();
  const locale = useLocale();
  const status = String(job.status);
  const statusLabel = t(`job.status.${status}`);
  const progress = job.progress ?? null;
  const summary = progress ? String(progress["ui_summary"] ?? progress["recap"] ?? progress["objective"] ?? "") : "";
  const controllable = job.kind === "cron";
  return (
    <Card tone={highlighted ? colors.accent : undefined}>
      <CardTitle right={<Badge tone={jobTone(status)}>{statusLabel === `job.status.${status}` ? status : statusLabel}</Badge>}>
        {job.name || job.job_id}
      </CardTitle>
      <Row label={t("job.kind.cron")} value={t(`job.kind.${job.kind}`)} />
      {summary ? <Body>{summary}</Body> : null}
      {job.next_run_at ? <Muted>{t("tasks.next_run", { when: formatRelative(toMillis(job.next_run_at), locale) })}</Muted> : null}
      {job.last_run_at ? <Muted>{t("tasks.last_run", { when: formatRelative(toMillis(job.last_run_at), locale) })}</Muted> : null}
      {controllable ? (
        <View style={styles.actions}>
          {status === "paused" ? (
            <Button title={t("tasks.resume")} variant="secondary" onPress={onResume} style={styles.action} />
          ) : (
            <Button title={t("tasks.pause")} variant="secondary" onPress={onPause} style={styles.action} />
          )}
          <Button title={t("tasks.cancel")} variant="danger" onPress={onCancel} style={styles.action} />
        </View>
      ) : null}
    </Card>
  );
}

function approvalToPayload(approval: Approval) {
  return {
    approval_id: approval.approval_id,
    type: approval.type,
    summary: approval.summary,
    expires_at: approval.expires_at,
    actions: ["confirm", "cancel"] as ApprovalDecision[],
    permission_level: (approval.details["permission_level"] as "recommend" | "propose" | "execute" | undefined) ?? "propose",
  };
}

export default function TasksScreen() {
  const t = useT();
  const client = useRequiredClient();
  const params = useLocalSearchParams<{ approval?: string; job?: string }>();
  const jobs = useJobs(client, { pollMs: POLL_MS });
  const approvals = useApprovals(client, { pollMs: POLL_MS });
  const describe = useCallback((err: unknown) => describeError(err, t), [t]);
  const decide = useDecide(client, describe);
  const [busy, setBusy] = useState<string | undefined>(undefined);
  const [actionError, setActionError] = useState<unknown>(undefined);

  const onDecide = async (approvalId: string, decision: ApprovalDecision) => {
    setBusy(approvalId);
    try {
      const response = await decide(approvalId, decision);
      if (response) {
        approvals.setData((items) => items.map((item) => (item.approval_id === approvalId ? { ...item, status: response.status } : item)));
        await approvals.refresh();
      }
    } finally {
      setBusy(undefined);
    }
  };

  const run = async (action: () => Promise<void>) => {
    try {
      setActionError(undefined);
      await action();
    } catch (err) {
      setActionError(err);
    }
  };

  const pending = approvals.data.filter((item) => item.status === "pending");
  const sortedPending = params.approval ? [...pending].sort((a, b) => (a.approval_id === params.approval ? -1 : b.approval_id === params.approval ? 1 : 0)) : pending;

  return (
    <Screen>
      <SectionTitle>{t("tasks.approvals")}</SectionTitle>
      {approvals.loading && approvals.data.length === 0 ? <Loading /> : null}
      {approvals.error ? <ErrorBox error={approvals.error} onRetry={() => void approvals.refresh()} /> : null}
      {!approvals.loading && sortedPending.length === 0 ? <Empty text={t("tasks.no_approvals")} /> : null}
      {sortedPending.map((approval) => (
        <ApprovalCard
          key={approval.approval_id}
          payload={approvalToPayload(approval)}
          status={approval.status}
          busy={busy === approval.approval_id}
          onDecide={(id, decision) => void onDecide(id, decision)}
        />
      ))}

      <SectionTitle>{t("tasks.jobs")}</SectionTitle>
      {actionError ? <ErrorBox error={actionError} /> : null}
      {jobs.loading && jobs.data.length === 0 ? <Loading /> : null}
      {jobs.error ? <ErrorBox error={jobs.error} onRetry={() => void jobs.refresh()} /> : null}
      {!jobs.loading && jobs.data.length === 0 ? <Empty text={t("tasks.no_jobs")} /> : null}
      {jobs.data.map((job) => (
        <JobCard
          key={job.job_id}
          job={job}
          highlighted={params.job === job.job_id}
          onPause={() => void run(() => jobs.pause(job.job_id))}
          onResume={() => void run(() => jobs.resume(job.job_id))}
          onCancel={() => void run(() => jobs.cancel(job.job_id))}
        />
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.xs },
  action: { flex: 1 },
});
