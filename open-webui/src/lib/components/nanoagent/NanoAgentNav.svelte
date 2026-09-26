<script lang="ts">
	import { page } from '$app/stores';
	import { getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { nanoagentText } from '$lib/nanoagent/text';

	export let compact = false;
	const i18n: { language?: string } = getContext('i18n');

	const links = [
		{ href: '/', key: 'agent' },
		{ href: '/tasks', key: 'tasks' },
		{ href: '/recommendations', key: 'recommendations' },
		{ href: '/connect', key: 'connect' },
		{ href: '/log', key: 'log' }
	];

	$: pathname = $page.url.pathname;

	function active(href: string): boolean {
		if (href === '/') return pathname === '/';
		return pathname === href || pathname.startsWith(`${href}/`);
	}

	function label(key: string): string {
		return nanoagentText($i18n?.language, key);
	}
</script>

<nav class={compact ? 'flex flex-col items-center gap-1 py-1' : 'px-1 pb-1'} aria-label="NanoAgent">
	{#each links as link (link.href)}
		{#if compact}
			<Tooltip content={label(link.key)} placement="right">
				<a
					href={link.href}
					class="flex size-8 items-center justify-center rounded-xl {active(link.href)
						? 'bg-black/[0.035] dark:bg-white/[0.06]'
						: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
					aria-label={label(link.key)}
					aria-current={active(link.href) ? 'page' : undefined}
				>
					<span
						class="flex size-[calc(30px*var(--app-text-scale,1))] items-center justify-center rounded-lg"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							class="size-4"
							aria-hidden="true"
						>
							{#if link.key === 'agent'}
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M7 5h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H12l-3.5 3v-3H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"
								/>
							{:else if link.key === 'tasks'}
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M9 7h11M9 12h11M9 17h11M4.5 7.5l1.2 1.2 2-2M4.5 12.5l1.2 1.2 2-2M4.5 17.5l1.2 1.2 2-2"
								/>
							{:else if link.key === 'recommendations'}
								<circle cx="12" cy="12" r="7" />
								<circle cx="12" cy="12" r="2.5" />
								<path stroke-linecap="round" d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2" />
							{:else if link.key === 'connect'}
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M10 13a5 5 0 0 0 7.1 0l1.4-1.4a5 5 0 0 0-7.1-7.1L10 6M14 11a5 5 0 0 0-7.1 0L5.5 12.4a5 5 0 0 0 7.1 7.1L14 18"
								/>
							{:else}
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M8 7h12M8 12h12M8 17h12M4 7h.01M4 12h.01M4 17h.01"
								/>
							{/if}
						</svg>
					</span>
				</a>
			</Tooltip>
		{:else}
			<a
				href={link.href}
				class="flex items-center gap-2 rounded-xl px-2 py-1.5 text-[0.8125rem] leading-5 {active(
					link.href
				)
					? 'bg-black/[0.035] dark:bg-white/[0.06]'
					: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
				aria-current={active(link.href) ? 'page' : undefined}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					class="size-4 shrink-0"
					aria-hidden="true"
				>
					{#if link.key === 'agent'}
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M7 5h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H12l-3.5 3v-3H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"
						/>
					{:else if link.key === 'tasks'}
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M9 7h11M9 12h11M9 17h11M4.5 7.5l1.2 1.2 2-2M4.5 12.5l1.2 1.2 2-2M4.5 17.5l1.2 1.2 2-2"
						/>
					{:else if link.key === 'recommendations'}
						<circle cx="12" cy="12" r="7" />
						<circle cx="12" cy="12" r="2.5" />
						<path stroke-linecap="round" d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2" />
					{:else if link.key === 'connect'}
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M10 13a5 5 0 0 0 7.1 0l1.4-1.4a5 5 0 0 0-7.1-7.1L10 6M14 11a5 5 0 0 0-7.1 0L5.5 12.4a5 5 0 0 0 7.1 7.1L14 18"
						/>
					{:else}
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M8 7h12M8 12h12M8 17h12M4 7h.01M4 12h.01M4 17h.01"
						/>
					{/if}
				</svg>
				<span>{label(link.key)}</span>
			</a>
		{/if}
	{/each}
</nav>
