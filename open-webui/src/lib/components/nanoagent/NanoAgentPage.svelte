<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	export let titleKey: string;
	export let path: string;
	export let listKey = '';

	const i18n: { language?: string } = getContext('i18n');
	let state: 'loading' | 'ready' | 'error' = 'loading';
	let rows: unknown[] = [];
	let raw = '';

	onMount(async () => {
		try {
			const body = (await gateway(path)) as Record<string, unknown>;
			const listed = listKey && Array.isArray(body[listKey]) ? (body[listKey] as unknown[]) : null;
			rows = listed ?? [];
			raw = listed ? '' : JSON.stringify(body, null, 2);
			state = 'ready';
		} catch {
			state = 'error';
		}
	});

	function line(row: unknown): string {
		if (!row || typeof row !== 'object') return String(row);
		const record = row as Record<string, unknown>;
		return String(record.summary ?? record.name ?? record.id ?? record.kind ?? record.job_id ?? JSON.stringify(record));
	}
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-3 p-6">
	<h1 class="text-lg font-medium">{nanoagentText($i18n?.language, titleKey)}</h1>
	{#if state === 'loading'}
		<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'loading')}</p>
	{:else if state === 'error'}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{:else if rows.length === 0 && !raw}
		<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each rows as row, index (`${index}`)}
				<li class="rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">{line(row)}</li>
			{/each}
		</ul>
		{#if raw}
			<pre class="overflow-auto rounded-xl bg-gray-50 p-3 text-xs dark:bg-gray-950">{raw}</pre>
		{/if}
	{/if}
	<slot />
</section>
