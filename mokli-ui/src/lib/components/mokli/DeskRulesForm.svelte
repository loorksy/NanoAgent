<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { gateway } from '$lib/mokli/client';
	import { mokliText } from '$lib/mokli/text';

	const i18n = getContext<{ language?: string }>('i18n');
	const keys = ['propose_order', 'room_message', 'external_message', 'python', 'web'] as const;
	const choices = ['allow', 'approve', 'deny'] as const;

	let values: Record<string, string> = {
		propose_order: 'approve',
		room_message: 'allow',
		external_message: 'approve',
		python: 'allow',
		web: 'allow'
	};
	let message = '';
	let failed = false;
	let busy = false;

	onMount(() => {
		void load();
	});

	async function load() {
		failed = false;
		try {
			const payload = (await gateway('desk/rules')) as Record<string, string>;
			for (const key of keys) {
				if (payload[key]) values[key] = payload[key];
			}
			values = values;
		} catch (error) {
			failed = true;
			message = error instanceof Error ? error.message : mokliText($i18n?.language, 'error');
		}
	}

	async function save() {
		failed = false;
		message = '';
		busy = true;
		try {
			await gateway('desk/rules', { method: 'PUT', body: JSON.stringify(values) });
			message = mokliText($i18n?.language, 'desk_saved');
		} catch (error) {
			failed = true;
			message = error instanceof Error ? error.message : mokliText($i18n?.language, 'error');
		} finally {
			busy = false;
		}
	}

	function label(key: string): string {
		return mokliText($i18n?.language, `desk_${key}`);
	}
</script>

<form class="mt-6 flex flex-col gap-2" on:submit|preventDefault={save}>
	<h3 class="px-1 text-[0.6875rem] font-medium text-gray-400 dark:text-gray-500">
		{mokliText($i18n?.language, 'desk_rules')}
	</h3>
	{#each keys as key (key)}
		<label
			class="flex items-center justify-between gap-3 rounded-2xl border border-gray-200 px-3 py-2.5 text-sm dark:border-gray-800"
		>
			<span>{label(key)}</span>
			<select
				class="h-8 rounded-xl border border-gray-200 bg-transparent px-2 text-xs dark:border-gray-700"
				bind:value={values[key]}
			>
				{#each choices as choice (choice)}
					<option value={choice}>{mokliText($i18n?.language, `desk_${choice}`)}</option>
				{/each}
			</select>
		</label>
	{/each}
	<button
		class="mt-1 h-9 w-fit rounded-xl bg-gray-900 px-4 text-xs text-white disabled:opacity-60 dark:bg-white dark:text-gray-900"
		type="submit"
		disabled={busy}
	>
		{mokliText($i18n?.language, 'desk_save')}
	</button>
	{#if message}
		<p class="text-xs {failed ? 'text-red-500' : 'text-gray-500'}">{message}</p>
	{/if}
</form>
