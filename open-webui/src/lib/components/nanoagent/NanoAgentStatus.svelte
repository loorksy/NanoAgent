<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	const i18n: { language?: string } = getContext('i18n');
	let label = '';
	let timer: ReturnType<typeof setInterval> | undefined;

	async function refresh() {
		try {
			const body = (await gateway('health')) as { version?: string; sessions_running?: number };
			const running = body.sessions_running ?? 0;
			label = `${nanoagentText($i18n?.language, 'status')}: ${running} · ${body.version ?? ''}`;
		} catch {
			label = nanoagentText($i18n?.language, 'error');
		}
	}

	onMount(() => {
		void refresh();
		timer = setInterval(() => void refresh(), 15000);
	});
	onDestroy(() => {
		if (timer) clearInterval(timer);
	});
</script>

{#if label}
	<div class="pointer-events-none absolute top-2 right-3 z-20 text-[11px] text-gray-500 dark:text-gray-400">
		{label}
	</div>
{/if}
