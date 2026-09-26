<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

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
		min?: number;
		max?: number;
		slider?: { min: number; max: number; step: number };
	};
	type Toggle = { name: string; label: string; enabled: boolean };
	type Preset = { name: string; label: string };

	const GROUPS: { keys: string[] }[] = [
		{ keys: ['news_shield', 'early_exit'] },
		{ keys: ['drawdown_breaker'] },
		{ keys: ['cooldown_lock'] },
		{ keys: ['spread_guard'] },
		{ keys: ['session_lock', 'holiday_lock'] }
	];
	const ALWAYS_ON = new Set(['rr_filter', 'max_positions']);

	let fields: Field[] = [];
	let toggles: Toggle[] = [];
	let presets: Preset[] = [];
	let profile = '';
	let failed = false;
	let busy = false;

	function grouped(name: string): boolean {
		return GROUPS.some((group) => group.keys.includes(name));
	}

	async function load() {
		const body = (await gateway('connect/risk')) as {
			groups?: { fields?: Field[] }[];
			toggles?: Toggle[];
			profile?: { name?: string; presets?: Preset[] };
		};
		fields = (body.groups ?? []).flatMap((group) => group.fields ?? []);
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

	$: visible = fields.filter((field) =>
		mode === 'primary' ? field.tier === 'primary' : field.tier !== 'primary'
	);
	$: visibleToggles =
		mode === 'primary'
			? GROUPS
			: toggles
					.filter((toggle) => !grouped(toggle.name) || ALWAYS_ON.has(toggle.name))
					.map((toggle) => ({ keys: [toggle.name] }));

	function bounds(field: Field): { min: number; max: number; step: number } {
		return {
			min: field.slider?.min ?? field.min ?? 0,
			max: field.slider?.max ?? field.max ?? 100,
			step: field.slider?.step ?? field.step ?? 1
		};
	}

	function groupOn(keys: string[]): boolean {
		return keys.every((key) => toggles.find((toggle) => toggle.name === key)?.enabled);
	}

	function groupLabel(keys: string[]): string {
		return toggles.find((toggle) => toggle.name === keys[0])?.label ?? keys[0];
	}

	async function saveField(field: Field, raw: string) {
		const value = field.type === 'integer' ? Number.parseInt(raw, 10) : Number(raw);
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

	async function setGroup(keys: string[], enabled: boolean) {
		const next: Record<string, boolean> = {};
		for (const key of keys) next[key] = enabled;
		busy = true;
		try {
			await gateway('connect/risk', {
				method: 'PUT',
				body: JSON.stringify({ toggles: next, derive: false })
			});
			await load();
		} catch {
			failed = true;
		} finally {
			busy = false;
		}
	}
</script>

<div class="flex flex-col gap-4">
	{#if failed}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{/if}

	{#if mode === 'primary'}
		<div class="flex flex-wrap gap-2">
			{#each presets as preset (preset.name)}
				<button
					class="rounded-lg border px-3 py-1.5 text-sm {profile === preset.name
						? 'border-gray-900 dark:border-white'
						: 'border-gray-200 dark:border-gray-700'}"
					disabled={busy}
					on:click={() => setProfile(preset.name)}
				>
					{preset.label}
				</button>
			{/each}
		</div>
	{/if}

	{#each visible as field (field.name)}
		{@const range = bounds(field)}
		<label class="flex flex-col gap-1 text-sm">
			<span>{field.label} · {field.value} {field.unit}</span>
			<input
				type="range"
				min={range.min}
				max={range.max}
				step={range.step}
				value={field.value}
				disabled={busy}
				on:change={(event) => saveField(field, event.currentTarget.value)}
			/>
		</label>
	{/each}

	{#each visibleToggles as group (`${group.keys.join(',')}`)}
		<label class="flex items-center justify-between gap-3 text-sm">
			<span>{groupLabel(group.keys)}</span>
			<input
				type="checkbox"
				checked={groupOn(group.keys)}
				disabled={busy}
				on:change={(event) => setGroup(group.keys, event.currentTarget.checked)}
			/>
		</label>
	{/each}
</div>
