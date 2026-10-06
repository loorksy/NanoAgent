<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/mokli/client';
	import { mokliText } from '$lib/mokli/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type ModelRow = { provider?: string; model?: string; total_tokens?: number };
	type DayRow = { date?: string; total_tokens?: number };
	type Usage = {
		total_tokens?: number;
		total_tokens_30d?: number;
		requests_30d?: number;
		failed_requests_30d?: number;
		peak_day_tokens?: number;
		current_streak_days?: number;
		providers_30d?: ModelRow[];
		days?: DayRow[];
	};

	let state: 'loading' | 'ready' | 'error' = 'loading';
	let body: Usage | null = null;

	function text(key: string): string {
		return mokliText($i18n?.language, key);
	}

	function count(value: number | undefined): string {
		return (value ?? 0).toLocaleString();
	}

	onMount(async () => {
		try {
			body = (await gateway('usage?days=30')) as Usage;
			state = 'ready';
		} catch {
			state = 'error';
		}
	});

	$: models = (body?.providers_30d ?? []).filter((row) => (row.total_tokens ?? 0) > 0);
	$: days = (body?.days ?? []).slice(-14).filter((row) => (row.total_tokens ?? 0) > 0);
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
	<h1 class="text-lg font-medium">{text('usage')}</h1>
	{#if state === 'loading'}
		<p class="text-sm text-gray-500">{text('loading')}</p>
	{:else if state === 'error' || !body}
		<p class="text-sm text-red-500">{text('error')}</p>
	{:else}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('tokens_30d')}</div>
				<div class="text-sm">{count(body.total_tokens_30d)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('tokens_all')}</div>
				<div class="text-sm">{count(body.total_tokens)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('requests_30d')}</div>
				<div class="text-sm">{count(body.requests_30d)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('failed_requests')}</div>
				<div class="text-sm">{count(body.failed_requests_30d)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('peak_day')}</div>
				<div class="text-sm">{count(body.peak_day_tokens)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('streak_days')}</div>
				<div class="text-sm">{count(body.current_streak_days)}</div>
			</div>
		</div>
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{text('by_model')}</h2>
			{#if models.length === 0}
				<p class="text-sm text-gray-500">{text('empty')}</p>
			{:else}
				{#each models as row, index (`model-${index}`)}
					<p class="flex justify-between gap-3 text-sm">
						<span>{row.provider} · {row.model}</span>
						<span>{count(row.total_tokens)}</span>
					</p>
				{/each}
			{/if}
		</div>
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{text('daily')}</h2>
			{#if days.length === 0}
				<p class="text-sm text-gray-500">{text('empty')}</p>
			{:else}
				{#each days as row, index (`day-${index}`)}
					<p class="flex justify-between gap-3 text-sm">
						<span>{row.date}</span>
						<span>{count(row.total_tokens)}</span>
					</p>
				{/each}
			{/if}
		</div>
	{/if}
</section>
