<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/mokli/client';
	import { mokliText } from '$lib/mokli/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type Quote = { mid?: number | null; bid?: number | null; ask?: number | null };
	type Row = Record<string, unknown>;
	type Briefing = {
		symbol?: string;
		summary?: string;
		quote?: Quote;
		openRecommendation?: Row | null;
		recentRecommendations?: Row[];
	};

	let state: 'loading' | 'ready' | 'error' = 'loading';
	let body: Briefing | null = null;

	function text(key: string): string {
		return mokliText($i18n?.language, key);
	}

	function price(value: number | null | undefined): string {
		if (value == null || Number.isNaN(value)) return '—';
		return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
	}

	function planLine(row: Row): string {
		const parts = [row.direction, row.status ?? row.outcomeStatus, row.summary ?? row.title ?? row.id]
			.map((part) => (part == null ? '' : String(part).trim()))
			.filter(Boolean);
		return parts.join(' · ') || text('empty');
	}

	onMount(async () => {
		const locale = ($i18n?.language ?? '').toLowerCase().startsWith('ar') ? 'ar' : 'en';
		try {
			body = (await gateway(`briefing?locale=${locale}`)) as Briefing;
			state = 'ready';
		} catch {
			state = 'error';
		}
	});
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
	<h1 class="text-lg font-medium">{text('briefing')}</h1>
	{#if state === 'loading'}
		<p class="text-sm text-gray-500">{text('loading')}</p>
	{:else if state === 'error' || !body}
		<p class="text-sm text-red-500">{text('error')}</p>
	{:else}
		<p class="text-sm">{body.summary || text('empty')}</p>
		<div class="grid grid-cols-3 gap-3">
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('quote')} · bid</div>
				<div class="text-sm">{price(body.quote?.bid)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('quote')} · mid</div>
				<div class="text-sm">{price(body.quote?.mid)}</div>
			</div>
			<div class="rounded-xl border border-gray-200 px-3 py-2 dark:border-gray-800">
				<div class="text-xs text-gray-500">{text('quote')} · ask</div>
				<div class="text-sm">{price(body.quote?.ask)}</div>
			</div>
		</div>
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{text('open_plan')}</h2>
			{#if body.openRecommendation}
				<p class="rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
					{planLine(body.openRecommendation)}
				</p>
			{:else}
				<p class="text-sm text-gray-500">{text('empty')}</p>
			{/if}
		</div>
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{text('recent_plans')}</h2>
			{#if !body.recentRecommendations?.length}
				<p class="text-sm text-gray-500">{text('empty')}</p>
			{:else}
				{#each body.recentRecommendations as row, index (`brief-${index}`)}
					<p class="rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
						{planLine(row)}
					</p>
				{/each}
			{/if}
		</div>
	{/if}
</section>
