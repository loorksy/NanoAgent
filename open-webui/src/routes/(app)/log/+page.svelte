<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type Row = Record<string, unknown>;
	let state: 'loading' | 'ready' | 'error' = 'loading';
	let entries: Row[] = [];
	let journal: Row[] = [];
	let events: Row[] = [];

	function line(row: Row): string {
		return String(row.summary ?? row.kind ?? row.title ?? row.prompt_key ?? row.id ?? '');
	}

	onMount(async () => {
		try {
			const [logBody, journalBody, calendarBody] = await Promise.all([
				gateway('log') as Promise<{ entries?: Row[] }>,
				gateway('log/journal') as Promise<{ entries?: Row[] }>,
				gateway('log/calendar') as Promise<{ events?: Row[] }>
			]);
			entries = logBody.entries ?? [];
			journal = journalBody.entries ?? [];
			events = calendarBody.events ?? [];
			state = 'ready';
		} catch {
			state = 'error';
		}
	});
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
	<h1 class="text-lg font-medium">{nanoagentText($i18n?.language, 'log')}</h1>
	{#if state === 'loading'}
		<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'loading')}</p>
	{:else if state === 'error'}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{:else}
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{nanoagentText($i18n?.language, 'log')}</h2>
			{#if entries.length === 0}
				<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
			{:else}
				{#each entries as row, index (`log-${index}`)}
					<p class="rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">{line(row)}</p>
				{/each}
			{/if}
		</div>
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{nanoagentText($i18n?.language, 'journal')}</h2>
			{#if journal.length === 0}
				<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
			{:else}
				{#each journal as row, index (`journal-${index}`)}
					<p class="text-sm">{line(row)}</p>
				{/each}
			{/if}
		</div>
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{nanoagentText($i18n?.language, 'calendar')}</h2>
			{#if events.length === 0}
				<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
			{:else}
				{#each events as row, index (`cal-${index}`)}
					<p class="text-sm">{line(row)} · {row.impact ?? ''}</p>
				{/each}
			{/if}
		</div>
	{/if}
</section>
