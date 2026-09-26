<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type Job = { job_id?: string; name?: string; status?: string };
	type Approval = { id?: string; summary?: string; status?: string };
	type Circuit = { strategy?: string; losses?: number; safe_mode?: boolean };

	let state: 'loading' | 'ready' | 'error' = 'loading';
	let jobs: Job[] = [];
	let approvals: Approval[] = [];
	let circuits: Circuit[] = [];

	async function load() {
		const [taskBody, approvalBody, deskBody] = await Promise.all([
			gateway('tasks') as Promise<{ jobs?: Job[] }>,
			gateway('approvals?status=pending') as Promise<{ approvals?: Approval[] }>,
			gateway('tasks/desk') as Promise<{ circuits?: Circuit[] }>
		]);
		jobs = taskBody.jobs ?? [];
		approvals = approvalBody.approvals ?? [];
		circuits = deskBody.circuits ?? [];
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

	async function decide(id: string, approved: boolean) {
		await gateway(`approvals/${id}`, {
			method: 'POST',
			body: JSON.stringify({ decision: approved ? 'confirm' : 'cancel' })
		});
		await load();
	}
</script>

<section class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
	<h1 class="text-lg font-medium">{nanoagentText($i18n?.language, 'tasks')}</h1>
	{#if state === 'loading'}
		<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'loading')}</p>
	{:else if state === 'error'}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{:else}
		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{nanoagentText($i18n?.language, 'approvals')}</h2>
			{#if approvals.length === 0}
				<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
			{:else}
				{#each approvals as approval (`${approval.id}`)}
					<div class="flex items-center justify-between gap-3 rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
						<span>{approval.summary || approval.id}</span>
						<span class="flex gap-2">
							<button class="underline" on:click={() => approval.id && decide(approval.id, true)}>
								{nanoagentText($i18n?.language, 'yes')}
							</button>
							<button class="underline" on:click={() => approval.id && decide(approval.id, false)}>
								{nanoagentText($i18n?.language, 'cancel')}
							</button>
						</span>
					</div>
				{/each}
			{/if}
		</div>

		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{nanoagentText($i18n?.language, 'desk')}</h2>
			{#if circuits.length === 0}
				<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
			{:else}
				{#each circuits as circuit (`${circuit.strategy}`)}
					<p class="text-sm">{circuit.strategy} · {circuit.losses}{circuit.safe_mode ? ' · safe' : ''}</p>
				{/each}
			{/if}
		</div>

		<div class="flex flex-col gap-2">
			<h2 class="text-sm font-medium">{nanoagentText($i18n?.language, 'tasks')}</h2>
			{#if jobs.length === 0}
				<p class="text-sm text-gray-500">{nanoagentText($i18n?.language, 'empty')}</p>
			{:else}
				{#each jobs as job (`${job.job_id}`)}
					<div class="flex items-center justify-between gap-3 rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
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
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</section>
