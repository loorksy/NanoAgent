<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';
	import RiskPanel from '$lib/components/nanoagent/RiskPanel.svelte';

	const i18n = getContext<{ language?: string }>('i18n');

	let failed = false;
	let confirming = false;
	let oanda = '';
	let broker = '';
	let level = '';

	function flag(value: boolean): string {
		return nanoagentText($i18n?.language, value ? 'yes' : 'no');
	}

	onMount(async () => {
		try {
			const body = (await gateway('connect')) as {
				brokers?: {
					oanda?: { configured?: boolean; env?: string };
					metaapi?: { configured?: boolean; account_id?: string };
				};
				mt5_permissions?: { permissions?: { level?: string } };
			};
			const feed = body.brokers?.oanda;
			const mt5 = body.brokers?.metaapi;
			oanda = `${flag(Boolean(feed?.configured))} ${feed?.env ?? ''}`.trim();
			broker = `${flag(Boolean(mt5?.configured))} ${mt5?.account_id ?? ''}`.trim();
			level = body.mt5_permissions?.permissions?.level ?? '';
		} catch {
			failed = true;
		}
	});

	async function control(path: string, enabled: boolean) {
		await gateway(path, { method: 'POST', body: JSON.stringify({ enabled }) });
		confirming = false;
	}
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
	<h1 class="text-lg font-medium">{nanoagentText($i18n?.language, 'connect')}</h1>
	{#if failed}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{/if}

	<div class="grid gap-3 sm:grid-cols-3">
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{nanoagentText($i18n?.language, 'price_feed')}</div>
			<div>{oanda}</div>
		</div>
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{nanoagentText($i18n?.language, 'broker')}</div>
			<div>{broker}</div>
		</div>
		<div class="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
			<div class="text-gray-500">{nanoagentText($i18n?.language, 'permissions')}</div>
			<div>{level}</div>
		</div>
	</div>

	<div class="flex flex-wrap gap-2">
		{#if confirming}
			<button
				class="rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white"
				on:click={() => control('control/kill', true)}
			>
				{nanoagentText($i18n?.language, 'kill_confirm')}
			</button>
		{:else}
			<button class="rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white" on:click={() => (confirming = true)}>
				{nanoagentText($i18n?.language, 'kill')}
			</button>
		{/if}
		<button class="rounded-lg border px-3 py-1.5 text-sm" on:click={() => control('control/pause', true)}>
			{nanoagentText($i18n?.language, 'pause')}
		</button>
		<button class="rounded-lg border px-3 py-1.5 text-sm" on:click={() => control('control/resume', false)}>
			{nanoagentText($i18n?.language, 'resume')}
		</button>
	</div>

	<RiskPanel mode="primary" />
</section>
