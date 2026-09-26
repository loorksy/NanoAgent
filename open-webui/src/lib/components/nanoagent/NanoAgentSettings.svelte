<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';
	import RiskPanel from './RiskPanel.svelte';

	export let tab: string;
	const i18n = getContext<{ language?: string }>('i18n');

	let body = '';
	let failed = false;
	let devices: { id?: string; platform?: string; label?: string }[] = [];

	const paths: Record<string, string> = {
		overview: 'settings/overview',
		capabilities: 'settings/overview',
		system: 'health',
		channels: 'devices'
	};

	onMount(async () => {
		const path = paths[tab];
		if (!path) return;
		try {
			const payload = (await gateway(path)) as Record<string, unknown>;
			if (tab === 'channels' && Array.isArray(payload.devices)) {
				devices = payload.devices as { id?: string; platform?: string; label?: string }[];
			}
			body = JSON.stringify(payload, null, 2);
		} catch {
			failed = true;
		}
	});
</script>

<div class="flex h-full flex-col gap-3 overflow-auto">
	<h2 class="text-sm font-medium">{nanoagentText($i18n?.language, tab)}</h2>
	{#if tab === 'risk'}
		<RiskPanel mode="primary" />
	{:else if tab === 'advanced'}
		<RiskPanel mode="advanced" />
	{:else if tab === 'models'}
		<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'models_hint')}</p>
	{:else if failed}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{:else if tab === 'channels'}
		{#if devices.length === 0}
			<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
		{:else}
			<ul class="flex flex-col gap-2">
				{#each devices as device (`${device.id}`)}
					<li class="rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
						{device.label || device.platform || device.id}
					</li>
				{/each}
			</ul>
		{/if}
	{:else}
		<pre class="overflow-auto text-xs">{body}</pre>
	{/if}
</div>
