<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type Job = {
		job_id?: string;
		name?: string;
		status?: string;
		kind?: string;
		next_run_at?: number | null;
	};

	let jobs: Job[] = [];
	let failed = false;
	let name = '';
	let message = '';
	let everyMinutes = 60;
	let note = '';

	async function load() {
		const body = (await gateway('tasks')) as { jobs?: Job[] };
		jobs = body.jobs ?? [];
	}

	async function act(id: string, action: 'pause' | 'resume' | 'cancel') {
		note = '';
		try {
			await gateway(`tasks/${id}/${action}`, { method: 'POST', body: '{}' });
			await load();
		} catch {
			note = nanoagentText($i18n?.language, action === 'cancel' ? 'job_protected' : 'error');
		}
	}

	async function createJob() {
		note = '';
		const minutes = Math.max(1, Number(everyMinutes) || 1);
		try {
			await gateway('tasks', {
				method: 'POST',
				body: JSON.stringify({
					name: name.trim(),
					message: message.trim(),
					schedule: { kind: 'every', every_ms: minutes * 60_000 }
				})
			});
			name = '';
			message = '';
			await load();
		} catch {
			failed = true;
		}
	}

	onMount(() => {
		void load().catch(() => {
			failed = true;
		});
	});
</script>

<section class="mb-4 rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
	<h2 class="font-medium">{nanoagentText($i18n?.language, 'agent_jobs')}</h2>
	{#if failed}
		<p class="mt-2 text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{/if}
	<ul class="mt-2 flex flex-col gap-2">
		{#each jobs as job (`${job.job_id}`)}
			<li class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-100 px-2 py-1.5 dark:border-gray-900">
				<div>
					<div>{job.name}</div>
					<div class="text-xs text-gray-500">{job.kind} · {job.status}</div>
				</div>
				<div class="flex gap-1">
					{#if job.kind === 'cron' && job.status === 'scheduled'}
						<button type="button" class="rounded-lg border px-2 py-1" on:click={() => act(job.job_id ?? '', 'pause')}>
							{nanoagentText($i18n?.language, 'pause')}
						</button>
					{:else if job.kind === 'cron'}
						<button type="button" class="rounded-lg border px-2 py-1" on:click={() => act(job.job_id ?? '', 'resume')}>
							{nanoagentText($i18n?.language, 'resume')}
						</button>
					{/if}
					{#if job.kind === 'cron'}
						<button type="button" class="rounded-lg border px-2 py-1" on:click={() => act(job.job_id ?? '', 'cancel')}>
							{nanoagentText($i18n?.language, 'cancel')}
						</button>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
	<form class="mt-3 grid gap-2" on:submit|preventDefault={createJob}>
		<input
			class="rounded-lg border border-gray-300 bg-transparent px-2 py-1.5 dark:border-gray-700"
			placeholder={nanoagentText($i18n?.language, 'job_name')}
			bind:value={name}
			required
		/>
		<input
			class="rounded-lg border border-gray-300 bg-transparent px-2 py-1.5 dark:border-gray-700"
			placeholder={nanoagentText($i18n?.language, 'job_message')}
			bind:value={message}
			required
		/>
		<label class="flex items-center gap-2 text-gray-500">
			{nanoagentText($i18n?.language, 'job_every_minutes')}
			<input class="w-20 rounded-lg border bg-transparent px-2 py-1 dark:border-gray-700" type="number" min="1" bind:value={everyMinutes} />
		</label>
		<button type="submit" class="w-fit rounded-lg border px-3 py-1.5">
			{nanoagentText($i18n?.language, 'job_create')}
		</button>
	</form>
	{#if note}
		<p class="mt-2 text-gray-500">{note}</p>
	{/if}
</section>
