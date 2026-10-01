<script lang="ts">
	import { onMount } from 'svelte';

	import { gateway } from '$lib/mokli/client';

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
			message = error instanceof Error ? error.message : 'load failed';
		}
	}

	async function save() {
		failed = false;
		message = '';
		try {
			await gateway('desk/rules', { method: 'PUT', body: JSON.stringify(values) });
			message = 'saved';
		} catch (error) {
			failed = true;
			message = error instanceof Error ? error.message : 'save failed';
		}
	}
</script>

<form class="mt-4 flex flex-col gap-2" on:submit|preventDefault={save}>
	<p class="text-sm font-medium">Desk rules</p>
	{#each keys as key (key)}
		<label class="flex items-center justify-between gap-3 text-sm">
			<span>{key}</span>
			<select class="rounded-lg border border-gray-200 bg-transparent px-2 py-1 dark:border-gray-800" bind:value={values[key]}>
				{#each choices as choice (choice)}
					<option value={choice}>{choice}</option>
				{/each}
			</select>
		</label>
	{/each}
	<button class="w-fit rounded-lg border border-gray-300 px-3 py-1 text-sm dark:border-gray-700" type="submit">
		Save
	</button>
	{#if message}
		<p class="text-xs {failed ? 'text-red-500' : 'text-gray-500'}">{message}</p>
	{/if}
</form>
