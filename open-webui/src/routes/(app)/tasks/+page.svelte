<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type Job = { job_id?: string; name?: string; status?: string };
	let state: 'loading' | 'ready' | 'error' = 'loading';
	let jobs: Job[] = [];

	async function load() {
		const body = (await gateway('tasks')) as { jobs?: Job[] };
		jobs = body.jobs ?? [];
		state = 'ready';
	}

	onMount(async () => {
		try {
			await load();
		} catch {
			state = 'error';
		}
	});

	async function act(id: string, action: 'pause' | 'resume' | 'cancel') {
		await gateway(`tasks/${id}/${action}`, { method: 'POST', body: '{}' });
		await load();
	}
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-3 p-6">
	<h1 class="text-lg font-medium">{nanoagentText($i18n?.language, 'tasks')}</h1>
	{#if state === 'loading'}
		<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'loading')}</p>
	{:else if state === 'error'}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{:else if jobs.length === 0}
		<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each jobs as job (`${job.job_id}`)}
				<li class="flex items-center justify-between gap-3 rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
					<span>{job.name || job.job_id} · {job.status}</span>
					<span class="flex gap-2">
						<button class="underline" on:click={() => job.job_id && act(job.job_id, 'pause')}>
							{nanoagentText($i18n?.language, 'pause')}
						</button>
						<button class="underline" on:click={() => job.job_id && act(job.job_id, 'resume')}>
							{nanoagentText($i18n?.language, 'resume')}
						</button>
						<button class="underline" on:click={() => job.job_id && act(job.job_id, 'cancel')}>
							{nanoagentText($i18n?.language, 'cancel')}
						</button>
					</span>
				</li>
			{/each}
		</ul>
	{/if}
</section>
