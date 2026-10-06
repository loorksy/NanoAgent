<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/mokli/client';
	import { mokliText } from '$lib/mokli/text';

	export let mode: 'primary' | 'advanced' = 'primary';

	const i18n = getContext<{ language?: string }>('i18n');

	type Field = {
		name: string;
		label: string;
		unit: string;
		value: number;
		tier: string;
		step: number;
		type: string;
		group: string;
		group_label: string;
		min?: number;
		max?: number;
		slider?: { min: number; max: number; step: number };
	};
	type Group = { id: string; label: string; fields?: Field[] };
	type Toggle = { name: string; label: string; enabled: boolean };
	type Preset = { name: string; label: string };

	const primaryToggles = new Set([
		'news_shield',
		'early_exit',
		'spread_guard',
		'cooldown_lock',
		'drawdown_breaker',
		'session_lock',
		'holiday_lock'
	]);

	let groups: Group[] = [];
	let toggles: Toggle[] = [];
	let presets: Preset[] = [];
	let profile = '';
	let failed = false;
	let busy = false;

	async function load() {
		const body = (await gateway('connect/risk')) as {
			groups?: Group[];
			toggles?: Toggle[];
			profile?: { name?: string; presets?: Preset[] };
		};
		groups = body.groups ?? [];
		toggles = body.toggles ?? [];
		presets = body.profile?.presets ?? [];
		profile = body.profile?.name ?? '';
	}

	onMount(async () => {
		try {
			await load();
		} catch {
			failed = true;
		}
	});

	function shown(field: Field): boolean {
		return mode === 'primary' ? field.tier === 'primary' : field.tier !== 'primary';
	}

	$: visibleGroups = groups
		.map((group) => ({
			...group,
			fields: (group.fields ?? []).filter(shown)
		}))
		.filter((group) => group.fields.length > 0);

	$: visibleToggles = toggles.filter((toggle) =>
		mode === 'primary' ? primaryToggles.has(toggle.name) : !primaryToggles.has(toggle.name)
	);

	function bounds(field: Field): { min: number; max: number; step: number } | null {
		const min = field.slider?.min ?? field.min;
		const max = field.slider?.max ?? field.max;
		if (min == null || max == null) return null;
		return { min, max, step: field.slider?.step ?? field.step ?? 1 };
	}

	function formatValue(field: Field): string {
		const value = field.value;
		if (field.type === 'integer') return String(value);
		const digits = String(field.step ?? 1).includes('.')
			? String(field.step).split('.')[1].length
			: 0;
		return Number(value).toLocaleString(undefined, {
			minimumFractionDigits: 0,
			maximumFractionDigits: digits || 2
		});
	}

	async function saveField(field: Field, raw: string) {
		const value = field.type === 'integer' ? Number.parseInt(raw, 10) : Number(raw);
		if (Number.isNaN(value)) return;
		busy = true;
		try {
			await gateway(`connect/risk/${field.name}`, {
				method: 'PUT',
				body: JSON.stringify({ value, derive: true })
			});
			await load();
		} catch {
			failed = true;
		} finally {
			busy = false;
		}
	}

	async function stepField(field: Field, direction: number) {
		const range = bounds(field);
		const step = range?.step ?? field.step ?? 1;
		let next = Number(field.value) + direction * step;
		if (range) next = Math.min(range.max, Math.max(range.min, next));
		const rounded = field.type === 'integer' ? Math.round(next) : Number(next.toFixed(4));
		await saveField(field, String(rounded));
	}

	async function setProfile(name: string) {
		busy = true;
		try {
			await gateway('connect/risk-profile', {
				method: 'PUT',
				body: JSON.stringify({ name })
			});
			await load();
		} catch {
			failed = true;
		} finally {
			busy = false;
		}
	}

	async function setToggle(name: string, enabled: boolean) {
		busy = true;
		try {
			await gateway('connect/risk', {
				method: 'PUT',
				body: JSON.stringify({ toggles: { [name]: enabled }, derive: false })
			});
			await load();
		} catch {
			failed = true;
		} finally {
			busy = false;
		}
	}
</script>

<div class="flex flex-col gap-5">
	{#if failed}
		<p class="text-sm text-red-500">{mokliText($i18n?.language, 'error')}</p>
	{/if}

	{#if mode === 'primary' && presets.length}
		<div
			class="flex flex-wrap gap-1 rounded-full border border-gray-200 p-1 dark:border-gray-800"
			role="group"
		>
			{#each presets as preset (preset.name)}
				<button
					type="button"
					class="h-8 rounded-full px-3 text-xs transition {profile === preset.name
						? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
						: 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'}"
					disabled={busy}
					aria-pressed={profile === preset.name}
					on:click={() => setProfile(preset.name)}
				>
					{preset.label}
				</button>
			{/each}
		</div>
	{/if}

	{#each visibleGroups as group (group.id)}
		<section class="flex flex-col gap-2">
			<h3 class="px-1 text-[0.6875rem] font-medium text-gray-400 dark:text-gray-500">
				{group.label}
			</h3>
			<div class="flex flex-col gap-2">
				{#each group.fields as field (field.name)}
					{@const range = bounds(field)}
					<div class="rounded-2xl border border-gray-200 px-3 py-3 dark:border-gray-800">
						<div class="mb-2 flex items-center justify-between gap-3">
							<span class="text-sm">{field.label}</span>
							<span
								class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs tabular-nums text-gray-700 dark:bg-gray-800 dark:text-gray-200"
							>
								{formatValue(field)} {field.unit}
							</span>
						</div>
						{#if range}
							<input
								class="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-gray-200 accent-gray-900 dark:bg-gray-700 dark:accent-white"
								type="range"
								min={range.min}
								max={range.max}
								step={range.step}
								value={field.value}
								disabled={busy}
								aria-label={field.label}
								on:change={(event) => saveField(field, event.currentTarget.value)}
							/>
						{:else}
							<div class="flex items-center gap-2">
								<button
									type="button"
									class="flex size-8 items-center justify-center rounded-xl border border-gray-200 text-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-800 dark:hover:bg-gray-900"
									disabled={busy}
									aria-label="-"
									on:click={() => stepField(field, -1)}
								>
									−
								</button>
								<button
									type="button"
									class="flex size-8 items-center justify-center rounded-xl border border-gray-200 text-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-800 dark:hover:bg-gray-900"
									disabled={busy}
									aria-label="+"
									on:click={() => stepField(field, 1)}
								>
									+
								</button>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/each}

	{#if visibleToggles.length}
		<section class="flex flex-col gap-2">
			{#each visibleToggles as toggle (toggle.name)}
				<div
					class="flex items-center justify-between gap-3 rounded-2xl border border-gray-200 px-3 py-2.5 dark:border-gray-800"
				>
					<span class="text-sm">{toggle.label}</span>
					<button
						type="button"
						role="switch"
						aria-checked={toggle.enabled}
						aria-label={toggle.label}
						class="relative h-5 w-9 shrink-0 rounded-full transition {toggle.enabled
							? 'bg-gray-900 dark:bg-white'
							: 'bg-gray-200 dark:bg-gray-700'}"
						disabled={busy}
						on:click={() => setToggle(toggle.name, !toggle.enabled)}
					>
						<span
							class="absolute top-0.5 size-4 rounded-full bg-white shadow-sm transition dark:bg-gray-900 {toggle.enabled
								? 'start-4'
								: 'start-0.5'}"
						></span>
					</button>
				</div>
			{/each}
		</section>
	{/if}
</div>
