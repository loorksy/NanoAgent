<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';
	import { gateway } from '$lib/mokli/client';
	import { mokliText } from '$lib/mokli/text';
	import RiskPanel from '$lib/components/mokli/RiskPanel.svelte';

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
	let levels: { name: string; label: string }[] = [];
	let savingLevel = false;
	let levelNote = '';
	let telegram: ChannelRow = {};
	let whatsapp: ChannelRow = {};
	let telegramToken = '';
	let telegramNote = '';
	let savingTelegram = false;
	let whatsappStatus = '';
	let whatsappQr = '';
	let whatsappSession = '';
	let whatsappTimer: ReturnType<typeof setInterval> | undefined;

	type Mt5Status = {
		configured?: boolean;
		connected?: boolean;
		login?: string;
		server?: string;
		host?: string;
		port?: number;
		account?: { name?: string; login?: string; balance?: number | string; currency?: string };
		last_action?: { ok?: boolean; message?: string };
	};

	let mt5: Mt5Status = {};
	let mt5Login = '';
	let mt5Password = '';
	let mt5Server = '';
	let showPassword = false;
	let mt5Saving = false;
	let mt5Note = '';
	let mt5Ok = false;

	function flag(value: boolean): string {
		return mokliText($i18n?.language, value ? 'yes' : 'no');
	}

	function channelLabel(row: ChannelRow): string {
		if (!row.installed) return mokliText($i18n?.language, 'channel_missing');
		if (row.running) return mokliText($i18n?.language, 'channel_running');
		if (row.configured || row.enabled) return mokliText($i18n?.language, 'channel_configured');
		return mokliText($i18n?.language, 'channel_not_connected');
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
			telegramNote = mokliText($i18n?.language, 'token_required');
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
			telegramNote = mokliText($i18n?.language, 'token_saved');
			if (saved.requires_restart) {
				telegramNote = `${telegramNote}. ${mokliText($i18n?.language, 'restart_required')}`;
			}
		} catch {
			telegramNote = mokliText($i18n?.language, 'error');
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
					mt5?: { configured?: boolean; login?: string; server?: string };
				};
				mt5_permissions?: {
					permissions?: { level?: string };
					levels?: { name: string; label: string }[];
				};
			};
			const feed = body.brokers?.oanda;
			const linked = body.brokers?.mt5;
			oanda = `${flag(Boolean(feed?.configured))} ${feed?.env ?? ''}`.trim();
			broker = `${flag(Boolean(linked?.configured))} ${linked?.login ?? ''}`.trim();
			mt5Login = linked?.login ?? '';
			mt5Server = linked?.server ?? '';
			mt5 = {
				configured: linked?.configured,
				login: linked?.login,
				server: linked?.server,
				connected: false
			};
			level = body.mt5_permissions?.permissions?.level ?? '';
			levels = body.mt5_permissions?.levels ?? [];
			await loadChannels();
		} catch {
			failed = true;
		}
	});

	onDestroy(() => {
		stopWhatsappPoll();
	});

	function localeCode(): string {
		return ($i18n?.language ?? '').toLowerCase().startsWith('ar') ? 'ar' : 'en';
	}

	async function saveMt5() {
		mt5Note = '';
		const login = mt5Login.trim();
		const password = mt5Password;
		const server = mt5Server.trim();
		if (!login || !password.trim() || !server) {
			mt5Ok = false;
			mt5Note = mokliText($i18n?.language, 'mt5_incomplete');
			return;
		}
		mt5Saving = true;
		try {
			const next = (await gateway('connect/mt5', {
				method: 'POST',
				body: JSON.stringify({ login, password, server, locale: localeCode() })
			})) as Mt5Status;
			mt5 = next;
			mt5Login = next.login || login;
			mt5Server = next.server || server;
			mt5Password = '';
			mt5Ok = true;
			mt5Note = mokliText($i18n?.language, 'mt5_saved');
			broker = `${flag(true)} ${next.login || login}`.trim();
		} catch (err) {
			mt5Ok = false;
			mt5.connected = false;
			mt5Note = err instanceof Error && err.message ? err.message : mokliText($i18n?.language, 'mt5_failed');
		} finally {
			mt5Saving = false;
		}
	}

	async function disconnectMt5() {
		mt5Saving = true;
		mt5Note = '';
		try {
			mt5 = (await gateway('connect/mt5/disconnect', { method: 'POST', body: '{}' })) as Mt5Status;
			mt5Ok = true;
			mt5Note = '';
			broker = flag(false);
		} catch (err) {
			mt5Ok = false;
			mt5Note = err instanceof Error && err.message ? err.message : mokliText($i18n?.language, 'mt5_failed');
		} finally {
			mt5Saving = false;
		}
	}

	async function saveLevel() {
		savingLevel = true;
		levelNote = '';
		try {
			const saved = (await gateway('connect/mt5/permissions', {
				method: 'PUT',
				body: JSON.stringify({ permissions: { level } })
			})) as { permissions?: { level?: string } };
			level = saved.permissions?.level ?? level;
			levelNote = mokliText($i18n?.language, 'permission_saved');
		} catch {
			levelNote = mokliText($i18n?.language, 'error');
		} finally {
			savingLevel = false;
		}
	}

	async function control(path: string, enabled: boolean) {
		await gateway(path, { method: 'POST', body: JSON.stringify({ enabled }) });
		confirming = false;
	}
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
	<h1 class="text-lg font-medium">{mokliText($i18n?.language, 'connect')}</h1>
	{#if failed}
		<p class="text-sm text-red-500">{mokliText($i18n?.language, 'error')}</p>
	{/if}

	<div class="grid gap-3 sm:grid-cols-3">
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{mokliText($i18n?.language, 'price_feed')}</div>
			<div>{oanda}</div>
		</div>
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{mokliText($i18n?.language, 'broker')}</div>
			<div>{broker}</div>
		</div>
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{mokliText($i18n?.language, 'permissions')}</div>
			{#if levels.length}
				<select
					class="mt-1 w-full rounded-lg border border-gray-300 bg-transparent px-2 py-1 dark:border-gray-700"
					bind:value={level}
					on:change={saveLevel}
					disabled={savingLevel}
				>
					{#each levels as option (option.name)}
						<option value={option.name}>{option.label}</option>
					{/each}
				</select>
			{:else}
				<div>{level}</div>
			{/if}
			{#if levelNote}
				<p class="mt-1 text-xs text-gray-500">{levelNote}</p>
			{/if}
		</div>
	</div>

	<section class="rounded-2xl border border-gray-200 p-5 dark:border-gray-800">
		<h2 class="text-base font-medium">{mokliText($i18n?.language, 'mt5_account')}</h2>
		<p class="mt-2 text-sm leading-6 text-gray-500">{mokliText($i18n?.language, 'mt5_form_hint')}</p>
		{#if mt5.connected}
			<p class="mt-4 text-sm text-green-600">{mokliText($i18n?.language, 'mt5_connected')}</p>
			<p class="mt-2 text-base">{mt5.account?.name || mt5.login}</p>
			{#if mt5.account?.login || mt5.login}
				<p class="text-sm text-gray-500">{mt5.account?.login || mt5.login}</p>
			{/if}
			{#if mt5.server}
				<p class="text-sm text-gray-500">{mt5.server}</p>
			{/if}
			<button
				class="mt-5 h-12 w-full rounded-xl border text-base"
				disabled={mt5Saving}
				on:click={disconnectMt5}
			>
				{mokliText($i18n?.language, 'mt5_disconnect')}
			</button>
		{:else}
			<form class="mt-4" on:submit|preventDefault={saveMt5}>
				<label class="block text-sm text-gray-500" for="mt5-login">
					{mokliText($i18n?.language, 'mt5_login')}
				</label>
				<input
					id="mt5-login"
					class="mt-1 h-12 w-full rounded-xl border border-gray-300 bg-transparent px-4 text-base dark:border-gray-700"
					inputmode="numeric"
					autocomplete="username"
					bind:value={mt5Login}
				/>
				<label class="mt-4 block text-sm text-gray-500" for="mt5-password">
					{mokliText($i18n?.language, 'mt5_password')}
				</label>
				<div class="relative mt-1">
					<input
						id="mt5-password"
						class="h-12 w-full rounded-xl border border-gray-300 bg-transparent px-4 pe-16 text-base dark:border-gray-700"
						type={showPassword ? 'text' : 'password'}
						autocomplete="current-password"
						bind:value={mt5Password}
					/>
					<button
						class="absolute inset-y-0 end-3 text-sm text-gray-500"
						type="button"
						on:click={() => (showPassword = !showPassword)}
					>
						{mokliText($i18n?.language, showPassword ? 'mt5_hide_password' : 'mt5_show_password')}
					</button>
				</div>
				<label class="mt-4 block text-sm text-gray-500" for="mt5-server">
					{mokliText($i18n?.language, 'mt5_server')}
				</label>
				<input
					id="mt5-server"
					class="mt-1 h-12 w-full rounded-xl border border-gray-300 bg-transparent px-4 text-base dark:border-gray-700"
					autocomplete="off"
					autocapitalize="off"
					spellcheck="false"
					placeholder={mokliText($i18n?.language, 'mt5_server_placeholder')}
					bind:value={mt5Server}
				/>
				<p class="mt-3 text-xs leading-5 text-gray-500">{mokliText($i18n?.language, 'mt5_password_note')}</p>
				<button
					class="mt-5 h-12 w-full rounded-xl bg-gray-900 text-base text-white disabled:opacity-60 dark:bg-white dark:text-gray-900"
					type="submit"
					disabled={mt5Saving}
				>
					{mokliText($i18n?.language, mt5Saving ? 'mt5_saving' : 'mt5_connect')}
				</button>
			</form>
		{/if}
		{#if mt5Note}
			<p class="mt-3 text-sm {mt5Ok ? 'text-green-600' : 'text-red-500'}">{mt5Note}</p>
		{/if}
	</section>

	<div class="flex flex-wrap gap-2">
		{#if confirming}
			<button
				class="rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white"
				on:click={() => control('control/kill', true)}
			>
				{mokliText($i18n?.language, 'kill_confirm')}
			</button>
		{:else}
			<button class="rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white" on:click={() => (confirming = true)}>
				{mokliText($i18n?.language, 'kill')}
			</button>
		{/if}
		<button class="rounded-lg border px-3 py-1.5 text-sm" on:click={() => control('control/pause', true)}>
			{mokliText($i18n?.language, 'pause')}
		</button>
		<button class="rounded-lg border px-3 py-1.5 text-sm" on:click={() => control('control/resume', false)}>
			{mokliText($i18n?.language, 'resume')}
		</button>
	</div>

	<div class="grid gap-4 lg:grid-cols-2">
		<section class="rounded-xl border border-gray-200 p-4 text-sm dark:border-gray-800">
			<h2 class="font-medium">{mokliText($i18n?.language, 'telegram')}</h2>
			<p class="mt-1 text-gray-500">{channelLabel(telegram)}</p>
			<ol class="mt-3 list-decimal space-y-1 pl-5 text-gray-500">
				<li>{mokliText($i18n?.language, 'telegram_step_botfather')}</li>
				<li>{mokliText($i18n?.language, 'telegram_step_create')}</li>
				<li>{mokliText($i18n?.language, 'telegram_step_paste')}</li>
			</ol>
			<input
				class="mt-3 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 dark:border-gray-700"
				type="password"
				autocomplete="off"
				placeholder={mokliText($i18n?.language, 'token_placeholder')}
				bind:value={telegramToken}
			/>
			<button
				class="mt-3 rounded-lg border px-3 py-1.5"
				disabled={savingTelegram}
				on:click={saveTelegram}
			>
				{mokliText($i18n?.language, savingTelegram ? 'saving' : 'save_token')}
			</button>
			{#if telegramNote}
				<p class="mt-2 text-gray-500">{telegramNote}</p>
			{/if}
		</section>

		<section class="rounded-xl border border-gray-200 p-4 text-sm dark:border-gray-800">
			<h2 class="font-medium">{mokliText($i18n?.language, 'whatsapp')}</h2>
			<p class="mt-1 text-gray-500">{channelLabel(whatsapp)}</p>
			{#if whatsappQr}
				<img
					class="mt-3 h-52 w-52 rounded-lg bg-white p-2"
					alt={mokliText($i18n?.language, 'whatsapp')}
					src={whatsappQr}
				/>
				<p class="mt-2 text-gray-500">{mokliText($i18n?.language, 'whatsapp_scan')}</p>
			{/if}
			{#if whatsappStatus === 'pending'}
				<p class="mt-2 text-gray-500">{mokliText($i18n?.language, 'whatsapp_waiting')}</p>
			{:else if whatsappStatus === 'succeeded'}
				<p class="mt-2 text-gray-500">{mokliText($i18n?.language, 'whatsapp_connected')}</p>
			{/if}
			<button class="mt-3 rounded-lg border px-3 py-1.5" on:click={() => startWhatsapp(Boolean(whatsappQr))}>
				{mokliText($i18n?.language, whatsappQr ? 'whatsapp_again' : 'whatsapp_start')}
			</button>
		</section>
	</div>

	<RiskPanel mode="primary" />
</section>
