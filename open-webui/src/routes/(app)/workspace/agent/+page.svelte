<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { gateway } from '$lib/nanoagent/client';
	import { nanoagentText } from '$lib/nanoagent/text';

	const i18n = getContext<{ language?: string }>('i18n');

	type Skill = { name?: string; source?: string; enabled?: boolean; description?: string };
	type Tool = { name?: string; description?: string };

	let skills: Skill[] = [];
	let tools: Tool[] = [];
	let failed = false;

	async function load() {
		const [skillBody, toolBody] = await Promise.all([
			gateway('workspace/skills') as Promise<{ skills?: Skill[] }>,
			gateway('workspace/tools') as Promise<{ tools?: Tool[] }>
		]);
		skills = skillBody.skills ?? [];
		tools = toolBody.tools ?? [];
	}

	async function toggle(skill: Skill) {
		if (!skill.name) return;
		await gateway(`workspace/skills/${encodeURIComponent(skill.name)}`, {
			method: 'PUT',
			body: JSON.stringify({ enabled: skill.enabled === false })
		});
		await load();
	}

	onMount(() => {
		void load().catch(() => {
			failed = true;
		});
	});
</script>

<div class="flex h-full flex-col gap-6 overflow-auto p-4">
	{#if failed}
		<p class="text-sm text-red-500">{nanoagentText($i18n?.language, 'error')}</p>
	{/if}
	<section>
		<h1 class="text-lg font-medium">{nanoagentText($i18n?.language, 'agent_skills')}</h1>
		<ul class="mt-3 flex flex-col gap-2">
			{#each skills as skill (`${skill.name}`)}
				<li class="flex items-center justify-between gap-3 rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
					<div>
						<div>{skill.name}</div>
						<div class="text-xs text-gray-500">{skill.source}</div>
					</div>
					<button type="button" class="rounded-lg border px-2 py-1" on:click={() => toggle(skill)}>
						{nanoagentText($i18n?.language, skill.enabled === false ? 'skill_disabled' : 'skill_enabled')}
					</button>
				</li>
			{/each}
		</ul>
	</section>
	<section>
		<h2 class="text-lg font-medium">{nanoagentText($i18n?.language, 'agent_tools')}</h2>
		<ul class="mt-3 flex flex-col gap-2">
			{#each tools as tool (`${tool.name}`)}
				<li class="rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
					<div class="font-medium">{tool.name}</div>
					{#if tool.description}
						<p class="text-gray-500">{tool.description}</p>
					{/if}
				</li>
			{/each}
		</ul>
	</section>
</div>
