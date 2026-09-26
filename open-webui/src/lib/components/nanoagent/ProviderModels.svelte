<script lang="ts">
	import { getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	export let name: string;
	export let configured = false;

	type Model = {
		id: string;
		label?: string;
		description?: string;
		context_window?: number;
		input_modalities?: string[];
		output_modalities?: string[];
		price_in?: number;
		price_out?: number;
		released_at?: number;
	};

	type Catalog = {
		status?: string;
		catalog_kind?: string;
		message?: string | null;
		models?: Model[];
		model_count?: number;
		selected?: string[];
		primary?: string | null;
	};

	const i18n = getContext<{ language?: string }>('i18n');
	const modalityClass: Record<string, string> = {
		text: 'bg-blue-600 text-white',
		image: 'bg-emerald-600 text-white',
		video: 'bg-orange-600 text-white',
		audio: 'bg-violet-600 text-white',
		file: 'bg-gray-500 text-white'
	};

	let models: Model[] = [];
	let manual: Model[] = [];
	let selectedIds: string[] = [];
	let primaryId = '';
	let query = '';
	let customId = '';
	let status = '';
	let catalogMessage = '';
	let notice = '';
	let loading = false;
	let failed = false;
	let busy = false;
	let request = 0;

	function text(key: string, vars: Record<string, string> = {}): string {
		let value = nanoagentText($i18n?.language, key);
		for (const [token, replacement] of Object.entries(vars)) {
			value = value.split(`{${token}}`).join(replacement);
		}
		return value;
	}

	function noteFrom(err: unknown): string {
		const message = err instanceof Error ? err.message : '';
		if (!message || message.startsWith('gateway ')) return text('error');
		return message;
	}

	function locale(): string {
		return ($i18n?.language ?? '').toLowerCase().startsWith('ar') ? 'ar' : 'en';
	}

	function stamp(model: Model): string {
		const inputs = model.input_modalities ?? [];
		if (inputs.some((item) => item !== 'text')) return text('model_multimodal');
		if (inputs.length) return text('model_text_only');
		return '';
	}

	function money(value: number | undefined): string {
		if (value === undefined || Number.isNaN(value)) return '';
		const digits = Math.abs(value) >= 0.01 ? 2 : 4;
		return `$${value.toFixed(digits)}`;
	}

	function contextLabel(tokens: number | undefined): string {
		if (!tokens) return '';
		if (tokens >= 1_000_000) {
			const millions = tokens / 1_000_000;
			const rounded = millions >= 10 ? millions.toFixed(0) : millions.toFixed(1);
			return `${rounded.replace(/\.0$/, '')}M`;
		}
		if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}K`;
		return String(tokens);
	}

	function releasedLabel(stampSeconds: number | undefined): string {
		if (!stampSeconds) return '';
		return new Intl.DateTimeFormat(locale(), {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		}).format(new Date(stampSeconds * 1000));
	}

	function inferred(id: string): Model {
		const leaf = id.split('/').pop()?.toLowerCase() ?? '';
		const claude = leaf === 'sonnet' || leaf === 'opus' || leaf === 'haiku' || leaf.startsWith('claude');
		if (!claude) return { id };
		return { id, input_modalities: ['text', 'image'], output_modalities: ['text'] };
	}

	async function load(providerName: string, isConfigured: boolean) {
		if (!isConfigured) {
			request += 1;
			models = [];
			manual = [];
			selectedIds = [];
			primaryId = '';
			loading = false;
			failed = false;
			return;
		}
		const ticket = ++request;
		loading = true;
		failed = false;
		notice = '';
		try {
			const payload = (await gateway(
				`settings/providers/${encodeURIComponent(providerName)}/models`
			)) as Catalog;
			if (ticket !== request) return;
			models = Array.isArray(payload.models) ? payload.models : [];
			selectedIds = Array.isArray(payload.selected) ? payload.selected : [];
			primaryId = payload.primary || selectedIds[0] || '';
			status = payload.status || '';
			catalogMessage = payload.message || '';
			manual = selectedIds
				.filter((id) => !models.some((model) => model.id === id))
				.map((id) => inferred(id));
		} catch (err) {
			if (ticket !== request) return;
			failed = true;
			notice = noteFrom(err);
		} finally {
			if (ticket === request) loading = false;
		}
	}

	function toggle(id: string) {
		if (selectedIds.includes(id)) {
			selectedIds = selectedIds.filter((item) => item !== id);
			if (primaryId === id) primaryId = selectedIds[0] || '';
			return;
		}
		if (selectedIds.length >= 12) {
			notice = text('model_limit');
			return;
		}
		selectedIds = [...selectedIds, id];
		if (!primaryId) primaryId = id;
	}

	function addCustom() {
		const id = customId.trim();
		if (!id || /\s/.test(id)) {
			notice = text('model_manual');
			return;
		}
		if (!models.some((model) => model.id === id) && !manual.some((model) => model.id === id)) {
			manual = [...manual, inferred(id)];
		}
		if (!selectedIds.includes(id)) toggle(id);
		customId = '';
	}

	async function save() {
		if (!configured) {
			notice = text('model_configure_first');
			return;
		}
		busy = true;
		notice = '';
		const primary = selectedIds.includes(primaryId) ? primaryId : selectedIds[0] || '';
		const contextWindows: Record<string, number> = {};
		for (const id of selectedIds) {
			const model = [...models, ...manual].find((item) => item.id === id);
			if (model?.context_window) contextWindows[id] = model.context_window;
		}
		try {
			const saved = (await gateway(`settings/providers/${encodeURIComponent(name)}/models`, {
				method: 'PUT',
				body: JSON.stringify({
					models: selectedIds,
					primary: primary || undefined,
					context_windows: contextWindows
				})
			})) as { selected?: string[]; primary?: string | null };
			selectedIds = Array.isArray(saved.selected) ? saved.selected : selectedIds;
			primaryId = saved.primary || selectedIds[0] || '';
			notice = selectedIds.length ? text('model_saved') : text('model_cleared');
		} catch (err) {
			notice = noteFrom(err);
		} finally {
			busy = false;
		}
	}

	$: if (name) void load(name, configured);

	$: catalog = [...manual, ...models.filter((model) => !manual.some((item) => item.id === model.id))];
	$: needle = query.trim().toLowerCase();
	$: filtered = catalog.filter((model) => {
		if (!needle) return true;
		return `${model.label ?? ''} ${model.id}`.toLowerCase().includes(needle);
	});
	$: chosenModels = selectedIds.map(
		(id) => catalog.find((model) => model.id === id) ?? inferred(id)
	);
	$: visible = [
		...chosenModels,
		...filtered.filter((model) => !selectedIds.includes(model.id)).slice(0, needle ? 80 : 24)
	];
</script>

<section class="mt-4 border-t border-gray-200 pt-4 dark:border-gray-800">
	<div class="mb-2 flex items-center justify-between gap-3">
		<h4 class="text-sm font-medium">{text('model_pick')}</h4>
		{#if selectedIds.length}
			<span class="text-xs text-gray-500">{selectedIds.length}</span>
		{/if}
	</div>
	<p class="mb-3 text-xs text-gray-500">{text('model_pick_help')}</p>

	{#if !configured}
		<p class="text-xs text-gray-500">{text('model_configure_first')}</p>
	{:else if loading}
		<p class="text-xs text-gray-500">{text('model_loading')}</p>
	{:else if failed}
		<p class="text-xs text-gray-500">{notice || text('model_unavailable')}</p>
	{:else}
		<label class="block text-xs text-gray-500" for="nanoagent-model-search">{text('model_search')}</label>
		<input
			id="nanoagent-model-search"
			class="mt-1 w-full rounded-full border border-gray-300 bg-transparent px-3 py-2 dark:border-gray-700"
			bind:value={query}
			autocomplete="off"
			spellcheck="false"
		/>

		{#if catalogMessage && !models.length}
			<p class="mt-2 text-xs text-gray-500">{catalogMessage}</p>
		{/if}

		<div class="mt-3 max-h-80 space-y-2 overflow-auto pr-1">
			{#each visible as model (model.id)}
				{@const inputs = model.input_modalities ?? []}
				{@const outputs = model.output_modalities ?? []}
				{@const chosen = selectedIds.includes(model.id)}
				<article
					class="rounded-xl border p-3 {chosen
						? 'border-gray-900 dark:border-gray-100'
						: 'border-gray-200 dark:border-gray-800'}"
				>
					<div class="flex items-start gap-3">
						<input
							class="mt-1"
							type="checkbox"
							checked={chosen}
							aria-label={model.label || model.id}
							on:change={() => toggle(model.id)}
						/>
						<div class="min-w-0 flex-1">
							<div class="flex items-start justify-between gap-2">
								<div class="min-w-0">
									<p class="truncate font-medium">{model.label || model.id}</p>
									{#if model.label && model.label !== model.id}
										<p class="truncate text-xs text-gray-500">{model.id}</p>
									{/if}
								</div>
								{#if stamp(model)}
									<span class="shrink-0 rounded-full border border-gray-300 px-2 py-0.5 text-[10px] uppercase tracking-wide text-gray-500 dark:border-gray-700">
										{stamp(model)}
									</span>
								{/if}
							</div>
							<div class="mt-2 grid grid-cols-2 gap-2">
								{#if inputs.length || outputs.length}
									<div class="rounded-lg bg-gray-50 p-2 dark:bg-gray-900">
										<p class="text-[10px] uppercase tracking-wide text-gray-500">{text('model_modalities')}</p>
										<div class="mt-1 flex flex-wrap items-center gap-1">
											{#each inputs as kind}
												<span class="grid h-6 w-6 place-items-center rounded-md text-[11px] font-semibold {modalityClass[kind] || modalityClass.file}" title={kind}>
													{#if kind === 'text'}T
													{:else if kind === 'image'}
														<svg viewBox="0 0 16 16" class="h-3.5 w-3.5" aria-hidden="true"><rect x="2" y="3" width="12" height="10" rx="1.5" fill="none" stroke="currentColor" /><circle cx="6" cy="7" r="1" fill="currentColor" /><path d="M3.5 12.5 7 8.5l2 2 1.5-1.5 2 3" fill="none" stroke="currentColor" /></svg>
													{:else if kind === 'video'}
														<svg viewBox="0 0 16 16" class="h-3.5 w-3.5" aria-hidden="true"><rect x="1.5" y="4" width="9" height="8" rx="1.5" fill="none" stroke="currentColor" /><path d="M11 6.5 14.5 5v6L11 9.5z" fill="currentColor" /></svg>
													{:else if kind === 'audio'}
														<svg viewBox="0 0 16 16" class="h-3.5 w-3.5" aria-hidden="true"><path d="M4 6.5h1.2v3H4zm2.4-2h1.2v7H6.4zm2.4 1.2h1.2v4.6H8.8zm2.4-2.2H12v9h-1.2z" fill="currentColor" /></svg>
													{:else}
														<svg viewBox="0 0 16 16" class="h-3.5 w-3.5" aria-hidden="true"><path d="M4 2.5h5l3 3V13.5H4z" fill="none" stroke="currentColor" /></svg>
													{/if}
												</span>
											{/each}
											{#if outputs.length}
												<span class="px-0.5 text-gray-400" aria-hidden="true">→</span>
												{#each outputs as kind}
													<span class="grid h-6 w-6 place-items-center rounded-md text-[11px] font-semibold {modalityClass[kind] || modalityClass.file}">
														{#if kind === 'text'}T{:else}{kind.slice(0, 1).toUpperCase()}{/if}
													</span>
												{/each}
											{/if}
										</div>
									</div>
								{/if}
								{#if money(model.price_in) || money(model.price_out)}
									<div class="rounded-lg bg-gray-50 p-2 dark:bg-gray-900">
										<p class="text-[10px] uppercase tracking-wide text-gray-500">{text('model_price')}</p>
										<p class="mt-1 text-sm font-medium">
											{money(model.price_in) || '—'} / {money(model.price_out) || '—'}
											<span class="text-[10px] font-normal text-gray-500">{text('model_price_per')}</span>
										</p>
									</div>
								{/if}
								{#if contextLabel(model.context_window)}
									<div class="rounded-lg bg-gray-50 p-2 dark:bg-gray-900">
										<p class="text-[10px] uppercase tracking-wide text-gray-500">{text('model_context')}</p>
										<p class="mt-1 text-sm font-medium">{contextLabel(model.context_window)}</p>
									</div>
								{/if}
								{#if releasedLabel(model.released_at)}
									<div class="rounded-lg bg-gray-50 p-2 dark:bg-gray-900">
										<p class="text-[10px] uppercase tracking-wide text-gray-500">{text('model_released')}</p>
										<p class="mt-1 text-sm font-medium">{releasedLabel(model.released_at)}</p>
									</div>
								{/if}
							</div>
							{#if chosen}
								<button
									type="button"
									class="mt-2 text-xs {primaryId === model.id ? 'font-medium' : 'text-gray-500'}"
									on:click={() => (primaryId = model.id)}
								>
									{primaryId === model.id ? text('model_primary') : text('model_make_primary')}
								</button>
							{/if}
						</div>
					</div>
				</article>
			{:else}
				<p class="text-xs text-gray-500">{text(status === 'unsupported' ? 'model_manual' : 'model_empty')}</p>
			{/each}
		</div>
		{#if filtered.length > visible.length}
			<p class="mt-2 text-xs text-gray-500">{text('model_search_more', { count: String(filtered.length) })}</p>
		{/if}

		<form class="mt-3 flex gap-2" on:submit|preventDefault={addCustom}>
			<input
				class="min-w-0 flex-1 rounded-full border border-gray-300 bg-transparent px-3 py-2 dark:border-gray-700"
				bind:value={customId}
				placeholder={text('model_manual')}
				autocomplete="off"
				spellcheck="false"
			/>
			<button type="submit" class="rounded-full border px-3 py-2">{text('model_add')}</button>
		</form>

		<div class="mt-3 flex items-center justify-end gap-3">
			{#if notice}
				<p class="mr-auto text-xs text-gray-500">{notice}</p>
			{/if}
			<button type="button" class="rounded-full border px-3 py-1.5" disabled={busy} on:click={save}>
				{text(busy ? 'saving' : 'model_save')}
			</button>
		</div>
	{/if}
</section>
