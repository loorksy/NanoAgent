<script lang="ts">
	import { getContext } from 'svelte';
	import { gateway } from '$lib/mokli/client';
	import { mokliText } from '$lib/mokli/text';
	import MokliProviders from './MokliProviders.svelte';
	import RiskPanel from './RiskPanel.svelte';

	export let tab: string;
	const i18n = getContext<{ language?: string }>('i18n');

	let body = '';
	let failed = false;
	let devices: { id?: string; platform?: string; label?: string }[] = [];
	let capabilities: { key?: string; enabled?: boolean }[] = [];
	let trading: string[] = [];
	let system: {
		timezone?: string;
		host?: string;
		port?: number;
		enabled?: boolean;
		version?: string;
	} | null = null;

	const paths: Record<string, string> = {
		overview: 'settings/overview',
		capabilities: 'settings/capabilities',
		system: 'settings/system',
		channels: 'devices'
	};

	let requestId = 0;

	async function loadTab(next: string) {
		const mine = ++requestId;
		failed = false;
		body = '';
		devices = [];
		capabilities = [];
		trading = [];
		system = null;
		if (next === 'models' || next === 'risk' || next === 'advanced') return;
		const path = paths[next];
		if (!path) return;
		try {
			const payload = (await gateway(path)) as Record<string, unknown>;
			if (mine !== requestId) return;
			if (next === 'channels' && Array.isArray(payload.devices)) {
				devices = payload.devices as { id?: string; platform?: string; label?: string }[];
			}
			if (next === 'capabilities') {
				capabilities = Array.isArray(payload.items)
					? (payload.items as { key?: string; enabled?: boolean }[])
					: [];
				trading = Array.isArray(payload.trading) ? (payload.trading as string[]) : [];
			}
			if (next === 'system') {
				system = payload as {
					timezone?: string;
					host?: string;
					port?: number;
					enabled?: boolean;
					version?: string;
				};
			}
			body = JSON.stringify(payload, null, 2);
		} catch {
			if (mine === requestId) failed = true;
		}
	}

	let seenTab = '';
	$: if (tab !== seenTab) {
		seenTab = tab;
		void loadTab(tab);
	}
</script>

<div class="flex h-full flex-col gap-3 overflow-auto">
	<h2 class="text-sm font-medium">{mokliText($i18n?.language, tab)}</h2>
	{#if tab === 'risk'}
		<RiskPanel mode="primary" />
	{:else if tab === 'advanced'}
		<RiskPanel mode="advanced" />
	{:else if tab === 'models'}
		<p class="text-sm text-gray-500">{mokliText($i18n?.language, 'models_hint')}</p>
		<MokliProviders />
	{:else if failed}
		<p class="text-sm text-red-500">{mokliText($i18n?.language, 'error')}</p>
	{:else if tab === 'capabilities'}
		{#each capabilities as item (`${item.key}`)}
			<p class="text-sm">
				{mokliText($i18n?.language, item.key || '')} · {mokliText(
					$i18n?.language,
					item.enabled ? 'passed' : 'failed'
				)}
			</p>
		{/each}
		{#each trading as name (`${name}`)}
			<p class="text-sm text-gray-500">{name}</p>
		{/each}
	{:else if tab === 'system' && system}
		<p class="text-sm">{mokliText($i18n?.language, 'timezone')} · {system.timezone}</p>
		<p class="text-sm">{mokliText($i18n?.language, 'api')} · {system.host}:{system.port}</p>
		<p class="text-sm">
			{mokliText($i18n?.language, 'enabled')} · {mokliText(
				$i18n?.language,
				system.enabled ? 'passed' : 'failed'
			)}
		</p>
		<p class="text-sm">{mokliText($i18n?.language, 'version')} · {system.version}</p>
	{:else if tab === 'channels'}
		{#if devices.length === 0}
			<p class="text-sm text-gray-500">{mokliText($i18n?.language, 'empty')}</p>
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
