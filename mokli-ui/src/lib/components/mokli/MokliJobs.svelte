<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/mokli/client';
	import { mokliText } from '$lib/mokli/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type Job = {
		job_id?: string;
		name?: string;
		status?: string;
		kind?: string;
	};

	let jobs: Job[] = [];
	let failed = false;
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
			note = mokliText($i18n?.language, action === 'cancel' ? 'job_protected' : 'error');
		}
	}

	onMount(() => {
		void load().catch(() => {
			failed = true;
		});
	});
</script>

{#if jobs.length > 0 || failed}
	<section class="mb-4 rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-800">
		<h2 class="font-medium">{mokliText($i18n?.language, 'agent_jobs')}</h2>
		{#if failed}
			<p class="mt-2 text-red-500">{mokliText($i18n?.language, 'error')}</p>
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
								{mokliText($i18n?.language, 'pause')}
							</button>
						{:else if job.kind === 'cron'}
							<button type="button" class="rounded-lg border px-2 py-1" on:click={() => act(job.job_id ?? '', 'resume')}>
								{mokliText($i18n?.language, 'resume')}
							</button>
						{/if}
						{#if job.kind === 'cron'}
							<button type="button" class="rounded-lg border px-2 py-1" on:click={() => act(job.job_id ?? '', 'cancel')}>
								{mokliText($i18n?.language, 'cancel')}
							</button>
						{/if}
					</div>
				</li>
			{/each}
		</ul>
		{#if note}
			<p class="mt-2 text-gray-500">{note}</p>
		{/if}
	</section>
{/if}
