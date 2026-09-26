<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type Row = Record<string, unknown>;
	type Counts = { buy?: number; sell?: number; wait?: number };
	type Performance = {
		totalRecommendations?: number;
		openRecommendations?: number;
		closedRecommendations?: number;
		paperActions?: number;
		directionBreakdown?: Counts;
		outcomeBreakdown?: Record<string, number>;
		recentRecommendations?: Row[];
	};

	let state: 'loading' | 'ready' | 'error' = 'loading';
	let body: Performance | null = null;

	function text(key: string): string {
		return nanoagentText($i18n?.language, key);
	}

	function count(value: number | undefined): string {
		return (value ?? 0).toLocaleString();
	}

	function planLine(row: Row): string {
		const parts = [row.direction, row.status, row.summary ?? row.title ?? row.id]
			.map((part) => (part == null ? '' : String(part).trim()))
			.filter(Boolean);
		return parts.join(' · ') || text('empty');
	}

	onMount(async () => {
		try {
			body = (await gateway('performance')) as Performance;
			state = 'ready';
		} catch {
			state = 'error';
		}
	});

	$: outcomes = Object.entries(body?.outcomeBreakdown ?? {}).filter(([, value]) => value > 0);
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
	<h1 class="text-lg font-medium">{text('performance')}</h1>
	{#if state === 'loading'}
		<p class="text-sm text-gray-500">{text('loading')}</p>
	{:else if state === 'error' || !body}
		<p class="text-sm text-red-500">{text('error')}</p>
	{:else}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('perf_total')}</div>
				<div class="text-sm">{count(body.totalRecommendations)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('perf_open')}</div>
				<div class="text-sm">{count(body.openRecommendations)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('perf_closed')}</div>
				<div class="text-sm">{count(body.closedRecommendations)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('perf_paper')}</div>
				<div class="text-sm">{count(body.paperActions)}</div>
			</div>
		</div>
		<div class="flex flex-wrap gap-4 text-sm">
			<span>{text('direction_buy')} {count(body.directionBreakdown?.buy)}</span>
			<span>{text('direction_sell')} {count(body.directionBreakdown?.sell)}</span>
			<span>{text('direction_wait')} {count(body.directionBreakdown?.wait)}</span>
		</div>
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{text('outcomes')}</h2>
			{#if outcomes.length === 0}
				<p class="text-sm text-gray-500">{text('empty')}</p>
			{:else}
				{#each outcomes as [name, value] (`outcome-${name}`)}
					<p class="text-sm">{text(`outcome_${name}`)} · {count(value)}</p>
				{/each}
			{/if}
		</div>
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{text('recent_plans')}</h2>
			{#if !body.recentRecommendations?.length}
				<p class="text-sm text-gray-500">{text('empty')}</p>
			{:else}
				{#each body.recentRecommendations as row, index (`perf-${index}`)}
					<p class="rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
						{planLine(row)}
					</p>
				{/each}
			{/if}
		</div>
	{/if}
</section>
