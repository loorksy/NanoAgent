<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';
	import ProviderMark from './ProviderMark.svelte';
	import ProviderModels from './ProviderModels.svelte';

	const i18n = getContext<{ language?: string }>('i18n');

	type Provider = {
		name: string;
		label?: string;
		configured?: boolean;
		auth_type?: string;
		api_key_required?: boolean;
		api_key_hint?: string | null;
		api_base?: string | null;
		default_api_base?: string | null;
		is_custom?: boolean;
		cli_oauth_hint?: string | null;
		oauth_account?: string | null;
		oauth_login_supported?: boolean;
		selected_models?: string[];
		primary_model?: string | null;
	};

	type Flow = {
		status?: string;
		provider?: string;
		flow_id?: string;
		authorization_url?: string;
		user_code?: string;
		completion_input?: string;
		providers?: Provider[];
	};

	const LOCAL = ['vllm', 'ollama', 'lm_studio', 'atomic_chat', 'ovms'];
	const FLOW_KEY = 'nanoagent-oauth-flow';

	let providers: Provider[] = [];
	let failed = false;
	let busy = false;
	let adding = false;
	let notice = '';
	let selected: Provider | null = null;
	let creating = false;
	let apiKey = '';
	let apiBase = '';
	let displayName = '';
	let token = '';
	let authCode = '';
	let reveal = false;
	let editing = false;
	let flow: Flow | null = null;
	let pollTimer: ReturnType<typeof setTimeout> | undefined;
	let polling = false;
	let dialogTab: 'models' | 'connection' = 'models';

	function text(key: string, vars: Record<string, string> = {}): string {
		let value = nanoagentText($i18n?.language, key);
		for (const [name, replacement] of Object.entries(vars)) {
			value = value.split(`{${name}}`).join(replacement);
		}
		return value;
	}

	function noteFrom(err: unknown): string {
		const message = err instanceof Error ? err.message : '';
		if (!message || message.startsWith('gateway ')) return text('error');
		return message;
	}

	function rank(provider: Provider): number {
		const index = LOCAL.indexOf(provider.name);
		if (index >= 0) return index;
		if (provider.api_key_required === false) return 100;
		return 200;
	}

	function apply(payload: { providers?: Provider[] }) {
		providers = Array.isArray(payload.providers) ? payload.providers : providers;
	}

	function isClaude(provider: Provider | null): boolean {
		return !!provider && (provider.name === 'claude_code_cli' || provider.auth_type === 'cli_oauth');
	}

	function labelOf(provider: Provider): string {
		return provider.label || provider.name;
	}

	function chosenModel(provider: Provider): string {
		return provider.primary_model || provider.selected_models?.[0] || '';
	}

	function rememberModels(event: CustomEvent<{ selected: string[]; primary: string }>) {
		if (!selected) return;
		const next: Provider = {
			...selected,
			selected_models: event.detail.selected,
			primary_model: event.detail.primary || null
		};
		selected = next;
		providers = providers.map((item) => (item.name === next.name ? { ...item, ...next } : item));
	}

	function liftToBody(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	}

	function stopPoll() {
		polling = false;
		clearTimeout(pollTimer);
	}

	function close() {
		stopPoll();
		selected = null;
		creating = false;
		flow = null;
		token = '';
		authCode = '';
		apiKey = '';
		reveal = false;
		editing = false;
	}

	function rememberFlow(providerName: string, started: Flow) {
		if (!started.flow_id || !started.authorization_url) return;
		try {
			sessionStorage.setItem(
				FLOW_KEY,
				JSON.stringify({
					provider: providerName,
					flow_id: started.flow_id,
					authorization_url: started.authorization_url,
					completion_input: started.completion_input,
					user_code: started.user_code
				})
			);
		} catch {
			/* Private browsing can reject session storage. The open dialog still works. */
		}
	}

	function recallFlow(providerName: string): Flow | null {
		try {
			const raw = sessionStorage.getItem(FLOW_KEY);
			if (!raw) return null;
			const saved = JSON.parse(raw) as Flow;
			if (saved.provider !== providerName || !saved.flow_id || !saved.authorization_url) return null;
			return saved;
		} catch {
			return null;
		}
	}

	function forgetFlow() {
		try {
			sessionStorage.removeItem(FLOW_KEY);
		} catch {
			/* Ignore storage failures. */
		}
	}

	function openProvider(provider: Provider, tab: 'models' | 'connection' = 'connection') {
		creating = false;
		adding = false;
		selected = provider;
		dialogTab = provider.configured ? tab : 'connection';
		apiKey = '';
		apiBase = provider.api_base || '';
		displayName = provider.label || '';
		token = '';
		authCode = '';
		reveal = false;
		editing = !provider.configured;
		flow = recallFlow(provider.name);
		notice = '';
	}

	function openCustom() {
		selected = null;
		creating = true;
		adding = false;
		displayName = '';
		apiKey = '';
		apiBase = '';
		reveal = false;
		notice = '';
	}

	onMount(async () => {
		try {
			apply((await gateway('settings/providers')) as { providers?: Provider[] });
		} catch {
			failed = true;
		}
	});

	async function saveClaude() {
		if (!selected) return;
		const value = token.trim();
		if (!value && !selected.configured) {
			notice = text('claude_token_required');
			return;
		}
		if (!value) {
			close();
			return;
		}
		busy = true;
		notice = '';
		try {
			apply(
				(await gateway('settings/claude-code', {
					method: 'POST',
					body: JSON.stringify({ token: value })
				})) as { providers?: Provider[] }
			);
			close();
			notice = text('provider_saved');
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	async function disconnectClaude() {
		busy = true;
		notice = '';
		try {
			apply(
				(await gateway('settings/claude-code', {
					method: 'POST',
					body: JSON.stringify({ clear: true })
				})) as { providers?: Provider[] }
			);
			close();
			notice = text('provider_saved');
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	async function connectClaude() {
		busy = true;
		notice = '';
		try {
			const started = (await gateway('settings/claude-code/connect', {
				method: 'POST',
				body: '{}'
			})) as Flow;
			flow = started;
			if (started.authorization_url) {
				window.open(started.authorization_url, '_blank', 'noopener,noreferrer');
			}
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	async function finishClaude() {
		const pasted = authCode.trim();
		if (!flow?.flow_id || !pasted) return;
		busy = true;
		notice = '';
		try {
			apply(
				(await gateway('settings/claude-code/callback', {
					method: 'POST',
					body: JSON.stringify({
						flow_id: flow.flow_id,
						authorization_response: pasted
					})
				})) as { providers?: Provider[] }
			);
			close();
			notice = text('provider_saved');
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	async function saveKeyProvider() {
		if (!selected) return;
		const key = apiKey.trim();
		if ((selected.api_key_required ?? true) && !selected.configured && !key) {
			notice = text('api_key_required');
			return;
		}
		busy = true;
		notice = '';
		const body: Record<string, string> = { api_base: apiBase.trim() };
		if (key) body.api_key = key;
		if (selected.is_custom) body.display_name = displayName.trim();
		try {
			apply(
				(await gateway(`settings/providers/${encodeURIComponent(selected.name)}`, {
					method: 'PUT',
					body: JSON.stringify(body)
				})) as { providers?: Provider[] }
			);
			close();
			notice = text('provider_saved');
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	async function saveCustom() {
		const name = displayName.trim();
		const base = apiBase.trim();
		if (!name || !base) {
			notice = text('provider_fields_required');
			return;
		}
		busy = true;
		notice = '';
		try {
			apply(
				(await gateway('settings/providers', {
					method: 'POST',
					body: JSON.stringify({
						name,
						api_base: base,
						api_key: apiKey.trim()
					})
				})) as { providers?: Provider[] }
			);
			close();
			notice = text('provider_saved');
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	async function startOAuth() {
		if (!selected) return;
		busy = true;
		notice = '';
		try {
			const started = (await gateway(`settings/providers/${encodeURIComponent(selected.name)}/oauth`, {
				method: 'POST',
				body: JSON.stringify({ action: 'login' })
			})) as Flow;
			if (started.authorization_url && selected) {
				flow = started;
				rememberFlow(selected.name, started);
			} else {
				forgetFlow();
				apply(started as { providers?: Provider[] });
				notice = text('provider_saved');
			}
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	async function pollDevice() {
		if (!selected || flow?.completion_input !== 'device_code' || !flow.flow_id) {
			polling = false;
			return;
		}
		const providerName = selected.name;
		const flowId = flow.flow_id;
		try {
			const result = (await gateway(`settings/providers/${encodeURIComponent(providerName)}/oauth`, {
				method: 'POST',
				body: JSON.stringify({ action: 'complete', flow_id: flowId })
			})) as Flow;
			if (!selected || flow?.flow_id !== flowId) {
				polling = false;
				return;
			}
			if (result.status === 'pending' || result.status === 'authorization_required') {
				pollTimer = setTimeout(() => void pollDevice(), 4000);
				return;
			}
			if (Array.isArray(result.providers)) {
				apply(result);
				forgetFlow();
				close();
				notice = text('provider_saved');
				return;
			}
			pollTimer = setTimeout(() => void pollDevice(), 4000);
		} catch (err) {
			polling = false;
			notice = noteFrom(err);
		}
	}

	function ensurePoll() {
		if (polling || flow?.completion_input !== 'device_code' || !flow.flow_id || !selected) return;
		polling = true;
		void pollDevice();
	}

	async function finishOAuth() {
		if (!selected || !flow?.flow_id) return;
		const pasted = authCode.trim();
		if (!pasted) return;
		busy = true;
		notice = '';
		try {
			apply(
				(await gateway(`settings/providers/${encodeURIComponent(selected.name)}/oauth`, {
					method: 'POST',
					body: JSON.stringify({
						action: 'complete',
						flow_id: flow.flow_id,
						authorization_response: pasted
					})
				})) as { providers?: Provider[] }
			);
			forgetFlow();
			close();
			notice = text('provider_saved');
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	async function logoutOAuth() {
		if (!selected) return;
		busy = true;
		notice = '';
		try {
			apply(
				(await gateway(`settings/providers/${encodeURIComponent(selected.name)}/oauth`, {
					method: 'POST',
					body: JSON.stringify({ action: 'logout' })
				})) as { providers?: Provider[] }
			);
			forgetFlow();
			close();
			notice = text('provider_saved');
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	$: configured = providers.filter((provider) => provider.configured);
	$: unconfigured = providers
		.filter((provider) => !provider.configured && provider.name !== 'custom')
		.slice()
		.sort((left, right) => rank(left) - rank(right));
	$: claude = isClaude(selected);
	$: oauth = !!selected && selected.auth_type === 'oauth';
	$: if (oauth && flow?.completion_input === 'device_code') ensurePoll();

	onDestroy(stopPoll);
</script>

<section id="nanoagent-providers" class="flex flex-col gap-2">
	<h3 class="text-sm font-medium">{text('providers_title')}</h3>
	{#if failed}
		<p class="text-sm text-red-500">{text('error')}</p>
	{/if}
	{#if notice}
		<p class="text-xs text-gray-500">{notice}</p>
	{/if}
	<div class="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800">
		{#each configured as provider (provider.name)}
			<div
				class="flex w-full flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-3 py-2.5 last:border-b-0 dark:border-gray-800"
			>
				<button
					type="button"
					class="flex min-w-0 flex-1 items-center gap-3 text-left"
					on:click={() => openProvider(provider, 'models')}
				>
					<ProviderMark name={provider.name} label={labelOf(provider)} />
					<span class="min-w-0">
						<span class="block truncate text-sm">{labelOf(provider)}</span>
						{#if chosenModel(provider)}
							<span class="block truncate text-xs text-gray-500">{chosenModel(provider)}</span>
						{:else if provider.name === 'claude_code_cli'}
							<span class="block truncate text-xs text-gray-500">
								{text('claude_connected', { hint: provider.cli_oauth_hint || '••••' })}
							</span>
						{/if}
					</span>
				</button>
				<span class="flex shrink-0 items-center gap-2">
					<button
						type="button"
						class="rounded-full border border-gray-900 px-3 py-1 text-xs dark:border-gray-100"
						on:click={() => openProvider(provider, 'models')}
					>
						{text('choose_models')}
					</button>
					<button
						type="button"
						class="text-xs text-gray-500"
						on:click={() => openProvider(provider, 'connection')}
					>
						{text('configure')}
					</button>
				</span>
			</div>
		{/each}
		{#if !selected && !creating}
			<button
				type="button"
				class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
				on:click={() => (adding = !adding)}
			>
				<span class="text-sm">{text('add_provider')}</span>
				<span class="text-xs text-gray-500">{adding ? '−' : '+'}</span>
			</button>
		{/if}
	</div>
	{#if adding}
		<div class="flex max-h-64 flex-col overflow-auto rounded-xl border border-gray-200 dark:border-gray-800">
			<button type="button" class="flex items-center gap-3 px-3 py-2 text-left text-sm" on:click={openCustom}>
				<ProviderMark name="custom" label={text('custom_provider')} />
				{text('custom_provider')}
			</button>
			{#each unconfigured as provider (provider.name)}
				<button
					type="button"
					class="flex items-center gap-3 px-3 py-2 text-left text-sm"
					on:click={() => openProvider(provider)}
				>
					<ProviderMark name={provider.name} label={labelOf(provider)} />
					{labelOf(provider)}
				</button>
			{/each}
		</div>
	{/if}
</section>

{#if selected || creating}
	<div
		use:liftToBody
		class="fixed inset-0 z-[10050] flex items-end justify-center bg-black/50 p-3 sm:items-center"
		role="presentation"
		on:click={close}
	>
		<div
			class="max-h-[85dvh] w-full max-w-2xl overflow-auto rounded-2xl border border-gray-200 bg-white p-4 text-sm shadow-xl dark:border-gray-800 dark:bg-gray-950"
			role="dialog"
			aria-modal="true"
			on:click|stopPropagation
		>
			<div class="mb-3 flex items-center justify-between gap-3">
				<h3 class="flex min-w-0 items-center gap-2 text-base font-medium">
					<ProviderMark
						name={selected ? selected.name : 'custom'}
						label={selected ? labelOf(selected) : text('custom_provider')}
					/>
					<span class="truncate">{selected ? labelOf(selected) : text('custom_provider')}</span>
				</h3>
				<button type="button" class="text-gray-500" on:click={close} aria-label={text('cancel')}>×</button>
			</div>

			{#if selected}
				<div class="mb-3 flex flex-wrap gap-2">
					<button
						type="button"
						class="rounded-full border px-3 py-1.5 {dialogTab === 'models'
							? 'border-gray-900 bg-gray-900 text-white dark:border-gray-100 dark:bg-gray-100 dark:text-gray-950'
							: 'border-gray-300 dark:border-gray-700'}"
						on:click={() => (dialogTab = 'models')}
					>
						{text('choose_models')}
					</button>
					<button
						type="button"
						class="rounded-full border px-3 py-1.5 {dialogTab === 'connection'
							? 'border-gray-900 bg-gray-900 text-white dark:border-gray-100 dark:bg-gray-100 dark:text-gray-950'
							: 'border-gray-300 dark:border-gray-700'}"
						on:click={() => (dialogTab = 'connection')}
					>
						{text('provider_connection')}
					</button>
				</div>
			{/if}

			{#if selected && dialogTab === 'models'}
				<ProviderModels
					name={selected.name}
					configured={selected.configured === true}
					lead
					on:saved={rememberModels}
				/>
			{:else if claude && selected}
				<div class="rounded-xl border border-gray-200 p-3 dark:border-gray-800">
					<p class="font-medium">{text('claude_account')}</p>
					<p class="mt-1 text-xs text-gray-500">
						{selected.configured
							? text('claude_connected', { hint: selected.cli_oauth_hint || '••••' })
							: text('claude_connect_help')}
					</p>
					<button
						id="nanoagent-claude-connect"
						type="button"
						class="mt-3 w-full rounded-full border px-3 py-2"
						disabled={busy}
						on:click={connectClaude}
					>
						{text(busy ? 'signing_in' : 'claude_connect')}
					</button>
				</div>
				{#if flow?.authorization_url}
					<div class="mt-3 space-y-2">
						<p class="text-xs text-gray-500">{text('claude_code_help')}</p>
						<a class="block text-xs underline" href={flow.authorization_url} target="_blank" rel="noreferrer">
							{text('open_sign_in')}
						</a>
						<label class="block text-xs text-gray-500" for="nanoagent-claude-code">{text('claude_code_label')}</label>
						<input
							id="nanoagent-claude-code"
							class="w-full rounded-full border border-gray-300 bg-transparent px-3 py-2 dark:border-gray-700"
							autocomplete="off"
							spellcheck="false"
							bind:value={authCode}
						/>
						<button
							type="button"
							class="w-full rounded-full border px-3 py-2"
							disabled={busy || !authCode.trim()}
							on:click={finishClaude}
						>
							{text(busy ? 'signing_in' : 'finish_sign_in')}
						</button>
					</div>
				{/if}
				<label class="mt-3 block text-xs text-gray-500" for="nanoagent-claude-token">{text('claude_paste')}</label>
				<p class="mt-1 text-xs text-gray-500">{text('claude_token_help')}</p>
				<div class="relative mt-2">
					{#if editing}
						<input
							id="nanoagent-claude-token"
							class="w-full rounded-full border border-gray-300 bg-transparent px-3 py-2 pr-16 dark:border-gray-700"
							type={reveal ? 'text' : 'password'}
							autocomplete="off"
							spellcheck="false"
							placeholder={text('claude_paste')}
							bind:value={token}
						/>
						<button
							type="button"
							class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500"
							on:click={() => (reveal = !reveal)}
						>
							{text(reveal ? 'hide_secret' : 'show_secret')}
						</button>
					{:else}
						<div class="flex h-10 items-center rounded-full border border-gray-300 px-3 pr-16 text-gray-500 dark:border-gray-700">
							{selected.cli_oauth_hint
								? text('claude_connected', { hint: selected.cli_oauth_hint || '' })
								: text('yes')}
						</div>
						<button
							type="button"
							class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500"
							aria-label={text('edit')}
							on:click={() => (editing = true)}
						>
							{text('edit')}
						</button>
					{/if}
				</div>
				<div class="mt-4 flex items-center justify-end gap-2">
					{#if selected.configured}
						<button type="button" class="rounded-full px-3 py-1.5" disabled={busy} on:click={disconnectClaude}>
							{text('claude_disconnect')}
						</button>
					{/if}
					<button type="button" class="rounded-full px-3 py-1.5" on:click={close}>{text('cancel')}</button>
					<button
						type="button"
						class="rounded-full border px-3 py-1.5"
						disabled={busy || (!selected.configured && !token.trim())}
						on:click={saveClaude}
					>
						{text(busy ? 'saving' : 'save_provider')}
					</button>
				</div>
			{:else if oauth && selected}
				<div class="rounded-xl border border-gray-200 p-3 dark:border-gray-800">
					<p class="font-medium">{text('sign_in')}</p>
					<p class="mt-1 text-xs text-gray-500">
						{selected.configured
							? text('oauth_signed_in', { account: selected.oauth_account || labelOf(selected) })
							: text('oauth_help')}
					</p>
					<div class="mt-3 flex justify-end gap-2">
						{#if selected.configured}
							<button type="button" class="rounded-full px-3 py-1.5" disabled={busy} on:click={logoutOAuth}>
								{text('sign_out')}
							</button>
						{/if}
						<button
							type="button"
							class="rounded-full border px-3 py-1.5"
							disabled={busy || selected.oauth_login_supported === false}
							on:click={startOAuth}
						>
							{text(busy ? 'signing_in' : 'sign_in')}
						</button>
					</div>
				</div>
				{#if flow?.completion_input === 'device_code' && flow.user_code}
					<div class="mt-3 space-y-2">
						<p class="text-xs text-gray-500">{text('oauth_device_help')}</p>
						<p class="text-center text-2xl font-medium tracking-widest">{flow.user_code}</p>
						<a class="block text-xs underline" href={flow.authorization_url} target="_blank" rel="noreferrer">
							{text('open_sign_in')}
						</a>
						<p class="text-xs text-gray-500">{notice || text('oauth_device_waiting')}</p>
					</div>
				{:else if flow?.authorization_url}
					<div class="mt-3 space-y-2">
						<p class="text-xs text-gray-500">
							{text(flow.completion_input === 'callback_url' ? 'oauth_callback_help' : 'oauth_code_help')}
						</p>
						<a class="block text-xs underline" href={flow.authorization_url} target="_blank" rel="noreferrer">
							{text('open_sign_in')}
						</a>
						<label class="block text-xs text-gray-500" for="nanoagent-oauth-callback">
							{text(flow.completion_input === 'callback_url' ? 'oauth_callback_paste' : 'oauth_code_paste')}
						</label>
						<textarea
							id="nanoagent-oauth-callback"
							class="w-full rounded-xl border border-gray-300 bg-transparent px-3 py-2 text-xs dark:border-gray-700"
							rows="3"
							autocomplete="off"
							spellcheck="false"
							placeholder={text(
								flow.completion_input === 'callback_url' ? 'oauth_callback_paste' : 'oauth_code_paste'
							)}
							bind:value={authCode}
						></textarea>
						<button
							type="button"
							class="w-full rounded-full border px-3 py-1.5"
							disabled={busy || !authCode.trim()}
							on:click={finishOAuth}
						>
							{text('finish_sign_in')}
						</button>
					</div>
				{/if}
				<div class="mt-4 flex justify-end">
					<button type="button" class="rounded-full px-3 py-1.5" on:click={close}>{text('cancel')}</button>
				</div>
			{:else}
				{#if selected?.is_custom || creating}
					<label class="block text-xs text-gray-500" for="nanoagent-provider-name">{text('provider_name')}</label>
					<input
						id="nanoagent-provider-name"
						class="mt-1 w-full rounded-full border border-gray-300 bg-transparent px-3 py-2 dark:border-gray-700"
						bind:value={displayName}
					/>
				{/if}
				<label class="mt-3 block text-xs text-gray-500" for="nanoagent-provider-key">{text('api_key')}</label>
				<div class="relative mt-1">
					<input
						id="nanoagent-provider-key"
						class="w-full rounded-full border border-gray-300 bg-transparent px-3 py-2 pr-16 dark:border-gray-700"
						type={reveal ? 'text' : 'password'}
						autocomplete="off"
						spellcheck="false"
						placeholder={selected?.configured ? selected.api_key_hint || text('yes') : text('api_key_placeholder')}
						bind:value={apiKey}
					/>
					<button
						type="button"
						class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500"
						on:click={() => (reveal = !reveal)}
					>
						{text(reveal ? 'hide_secret' : 'show_secret')}
					</button>
				</div>
				<label class="mt-3 block text-xs text-gray-500" for="nanoagent-provider-base">{text('api_base')}</label>
				<input
					id="nanoagent-provider-base"
					class="mt-1 w-full rounded-full border border-gray-300 bg-transparent px-3 py-2 dark:border-gray-700"
					autocomplete="off"
					spellcheck="false"
					placeholder={selected?.default_api_base || text('api_base_placeholder')}
					bind:value={apiBase}
				/>
				<div class="mt-4 flex items-center justify-end gap-2">
					<button type="button" class="rounded-full px-3 py-1.5" on:click={close}>{text('cancel')}</button>
					<button
						type="button"
						class="rounded-full border px-3 py-1.5"
						disabled={busy}
						on:click={creating ? saveCustom : saveKeyProvider}
					>
						{text(busy ? 'saving' : 'save_provider')}
					</button>
				</div>
			{/if}
		</div>
	</div>
{/if}
