# §11 post-reset runbook (production closure)

Run on branch `cursor/section11-vps-rows-d9e1` after OpenRouter quota probe shows **`in>0`**.  
**Done** = `bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13` with **`closure_errors=0`** and report §11 rows **1–13** filled.

1. `bash scripts/mokli_upgrade_section11_check_wake.sh --sync-vps-rev`  
   Check `/opt/cursor/artifacts/timer_wake_wait_quota.log` for `after_reset_wake` or `TIMER_WAKE_FINAL_EXIT=0`.  
   If sleep finished but the chain did not: `bash scripts/mokli_upgrade_section11_timer_wake.sh` (no `--wait-quota`).

2. `bash scripts/vps_section11_quota_probe.sh` — must show **`in>0`**.

3. `OANDA_API_TOKEN=… OANDA_ACCOUNT_ID=… bash scripts/vps_section11_set_oanda_env.sh`  
   `bash scripts/vps_section11_env_check.sh --require-oanda` → exit **0**.

4. `bash scripts/mokli_upgrade_section11_rerun_partials.sh` (rows **5**, **10**).

5. `bash scripts/mokli_upgrade_section11_remaining_rows.sh`  
   - Row **11:** `vps_section11_row11_paper.sh` (if not done by `timer_wake`).  
   - Row **12:** `bash scripts/vps_section11_row12_pipe_turn.sh` (headless pipe; same gateway path as UI), or Mokli UI pipe + `SHOW_DIAGNOSTICS` → `12-desktop-ui.jsonl`.  
   - Row **13:** device/SDK session → `section11-events/13-mobile.jsonl`.

6. `bash scripts/mokli_upgrade_section11_sync_from_vps.sh --pull-vps`  
   Fill `section11-results-partial.json` rows **11–13** (`docs/section11-results.example.json`).

7. `bash scripts/mokli_upgrade_section11_operator_unblock.sh --pull-vps` → exit **0**.

8. `bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13 --results section11-results-partial.json`

9. Optional gate: `bash scripts/mokli_upgrade_aggregate_pytest.sh` (expect **2551** passed, 1 skipped).

See also: `docs/mokli-agent-upgrade-operator-handoff.md` (full Arabic/English closure list).
