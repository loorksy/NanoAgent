<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';
	import RiskPanel from '$lib/components/nanoagent/RiskPanel.svelte';

	const i18n = getContext<{ language?: string }>('i18n');

	type ChannelRow = {
		name?: string;
		installed?: boolean;
		enabled?: boolean;
		configured?: boolean;
		running?: boolean;
		status?: string;
	};

	let failed = false;
	let confirming = false;
	let oanda = '';
	let broker = '';
	let level = '';
	let telegram: ChannelRow = {};
	let whatsapp: ChannelRow = {};
	let telegramToken = '';
	let telegramNote = '';
	let savingTelegram = false;
	let whatsappStatus = '';
	let whatsappQr = '';
	let whatsappSession = '';
	let whatsappTimer: ReturnType<typeof setInterval> | undefined;

	function flag(value: boolean): string {
		return nanoagentText($i18n?.language, value ? 'yes' : 'no');
	}

	function channelLabel(row: ChannelRow): string {
		if (!row.installed) return nanoagentText($i18n?.language, 'channel_missing');
		if (row.running) return nanoagentText($i18n?.language, 'channel_running');
		if (row.configured || row.enabled) return nanoagentText($i18n?.language, 'channel_configured');
		return nanoagentText($i18n?.language, 'channel_not_connected');
	}

	function applyChannels(rows: ChannelRow[]) {
		telegram = rows.find((row) => row.name === 'telegram') ?? {};
		whatsapp = rows.find((row) => row.name === 'whatsapp') ?? {};
	}

	async function loadChannels() {
		const body = (await gateway('connect/channels')) as { channels?: ChannelRow[] };
		applyChannels(body.channels ?? []);
	}

	async function saveTelegram() {
		const value = telegramToken.trim();
		telegramNote = '';
		if (!value) {
			telegramNote = nanoagentText($i18n?.language, 'token_required');
			return;
		}
		savingTelegram = true;
		try {
			const saved = (await gateway('connect/channels/telegram', {
				method: 'POST',
				body: JSON.stringify({ token: value })
			})) as ChannelRow & { requires_restart?: boolean };
			telegramToken = '';
			telegram = saved;
			telegramNote = nanoagentText($i18n?.language, 'token_saved');
			if (saved.requires_restart) {
				telegramNote = `${telegramNote}. ${nanoagentText($i18n?.language, 'restart_required')}`;
			}
		} catch {
			telegramNote = nanoagentText($i18n?.language, 'error');
		} finally {
			savingTelegram = false;
		}
	}

	async function whatsappAction(action: string, force = false) {
		const body = (await gateway('connect/channels/whatsapp', {
			method: 'POST',
			body: JSON.stringify({
				action,
				session_id: whatsappSession,
				force
			})
		})) as {
			session_id?: string;
			status?: string;
			qr_data_url?: string;
			interval_ms?: number;
			requires_restart?: boolean;
			channel?: ChannelRow;
		};
		whatsappSession = body.session_id ?? '';
		whatsappStatus = body.status ?? '';
		if (body.qr_data_url) whatsappQr = body.qr_data_url;
		if (body.channel) whatsapp = body.channel;
		if (body.status === 'succeeded' || body.status === 'expired' || body.status === 'cancelled' || body.status === 'failed') {
			stopWhatsappPoll();
		}
		return body.interval_ms ?? 2000;
	}

	function stopWhatsappPoll() {
		if (whatsappTimer) clearInterval(whatsappTimer);
		whatsappTimer = undefined;
	}

	async function startWhatsapp(force = false) {
		stopWhatsappPoll();
		whatsappQr = '';
		whatsappStatus = 'pending';
		try {
			const interval = await whatsappAction('start', force);
			whatsappTimer = setInterval(() => {
				void whatsappAction('poll').catch(() => {
					whatsappStatus = 'failed';
					stopWhatsappPoll();
				});
			}, Math.max(interval, 1500));
		} catch {
			whatsappStatus = 'failed';
		}
	}

	onMount(async () => {
		try {
			const body = (await gateway('connect')) as {
				brokers?: {
					oanda?: { configured?: boolean; env?: string };
					metaapi?: { configured?: boolean; account_id?: string };
				};
				mt5_permissions?: { permissions?: { level?: string } };
			};
			const feed = body.brokers?.oanda;
			const mt5 = body.brokers?.metaapi;
			oanda = `${flag(Boolean(feed?.configured))} ${feed?.env ?? ''}`.trim();
			broker = `${flag(Boolean(mt5?.configured))} ${mt5?.account_id ?? ''}`.trim();
			level = body.mt5_permissions?.permissions?.level ?? '';
			await loadChannels();
		} catch {
			failed = true;
		}
	});

	onDestroy(() => stopWhatsappPoll());

	async function control(path: string, enabled: boolean) {
		await gateway(path, { method: 'POST', body: JSON.stringify({ enabled }) });
		confirming = false;
	}
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
	<h1 class="text-lg font-medium">{nanoagentText($i18n?.language, 'connect')}</h1>
	{#if failed}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{/if}

	<div class="grid gap-3 sm:grid-cols-3">
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{nanoagentText($i18n?.language, 'price_feed')}</div>
			<div>{oanda}</div>
		</div>
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{nanoagentText($i18n?.language, 'broker')}</div>
			<div>{broker}</div>
		</div>
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{nanoagentText($i18n?.language, 'permissions')}</div>
			<div>{level}</div>
		</div>
	</div>

	<div class="flex flex-wrap gap-2">
		{#if confirming}
			<button
				class="rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white"
				on:click={() => control('control/kill', true)}
			>
				{nanoagentText($i18n?.language, 'kill_confirm')}
			</button>
		{:else}
			<button class="rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white" on:click={() => (confirming = true)}>
				{nanoagentText($i18n?.language, 'kill')}
			</button>
		{/if}
		<button class="rounded-lg border px-3 py-1.5 text-sm" on:click={() => control('control/pause', true)}>
			{nanoagentText($i18n?.language, 'pause')}
		</button>
		<button class="rounded-lg border px-3 py-1.5 text-sm" on:click={() => control('control/resume', false)}>
			{nanoagentText($i18n?.language, 'resume')}
		</button>
	</div>

	<div class="grid gap-4 lg:grid-cols-2">
		<section class="rounded-xl border border-gray-200 p-4 text-sm dark:border-gray-800">
			<h2 class="font-medium">{nanoagentText($i18n?.language, 'telegram')}</h2>
			<p class="mt-1 text-gray-500">{channelLabel(telegram)}</p>
			<ol class="mt-3 list-decimal space-y-1 pl-5 text-gray-500">
				<li>{nanoagentText($i18n?.language, 'telegram_step_botfather')}</li>
				<li>{nanoagentText($i18n?.language, 'telegram_step_create')}</li>
				<li>{nanoagentText($i18n?.language, 'telegram_step_paste')}</li>
			</ol>
			<input
				class="mt-3 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 dark:border-gray-700"
				type="password"
				autocomplete="off"
				placeholder={nanoagentText($i18n?.language, 'token_placeholder')}
				bind:value={telegramToken}
			/>
			<button
				class="mt-3 rounded-lg border px-3 py-1.5"
				disabled={savingTelegram}
				on:click={saveTelegram}
			>
				{nanoagentText($i18n?.language, savingTelegram ? 'saving' : 'save_token')}
			</button>
			{#if telegramNote}
				<p class="mt-2 text-gray-500">{telegramNote}</p>
			{/if}
		</section>

		<section class="rounded-xl border border-gray-200 p-4 text-sm dark:border-gray-800">
			<h2 class="font-medium">{nanoagentText($i18n?.language, 'whatsapp')}</h2>
			<p class="mt-1 text-gray-500">{channelLabel(whatsapp)}</p>
			{#if whatsappQr}
				<img
					class="mt-3 h-52 w-52 rounded-lg bg-white p-2"
					alt={nanoagentText($i18n?.language, 'whatsapp')}
					src={whatsappQr}
				/>
				<p class="mt-2 text-gray-500">{nanoagentText($i18n?.language, 'whatsapp_scan')}</p>
			{/if}
			{#if whatsappStatus === 'pending'}
				<p class="mt-2 text-gray-500">{nanoagentText($i18n?.language, 'whatsapp_waiting')}</p>
			{:else if whatsappStatus === 'succeeded'}
				<p class="mt-2 text-gray-500">{nanoagentText($i18n?.language, 'whatsapp_connected')}</p>
			{/if}
			<button class="mt-3 rounded-lg border px-3 py-1.5" on:click={() => startWhatsapp(Boolean(whatsappQr))}>
				{nanoagentText($i18n?.language, whatsappQr ? 'whatsapp_again' : 'whatsapp_start')}
			</button>
		</section>
	</div>

	<RiskPanel mode="primary" />
</section>
