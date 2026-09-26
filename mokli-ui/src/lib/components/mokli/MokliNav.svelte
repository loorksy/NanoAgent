<script lang="ts">
	import { page } from '$app/stores';
	import { getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { mokliText } from '$lib/mokli/text';

	export let compact = false;
	export let onSelect: () => void = () => {};
	const i18n: { language?: string } = getContext('i18n');

	const links = [
		{ href: '/', key: 'agent' },
		{ href: '/briefing', key: 'briefing' },
		{ href: '/performance', key: 'performance' },
		{ href: '/recommendations', key: 'recommendations' },
		{ href: '/tasks', key: 'tasks' },
		{ href: '/connect', key: 'connect' },
		{ href: '/log', key: 'log' },
		{ href: '/usage', key: 'usage' }
	];

	$: pathname = $page.url.pathname;

	function active(href: string): boolean {
		if (href === '/') return pathname === '/';
		return pathname === href || pathname.startsWith(`${href}/`);
	}

	function label(key: string): string {
		return mokliText($i18n?.language, key);
	}
</script>

{#snippet mark(key: string)}
	<svg
		xmlns="http://www.w3.org/2000/svg"
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="1.5"
		class="size-4 shrink-0"
		aria-hidden="true"
	>
		{#if key === 'agent'}
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M7 5h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H12l-3.5 3v-3H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"
			/>
		{:else if key === 'briefing'}
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M6 5.5h12v13H6zM9 9h6M9 12h6M9 15h3"
			/>
		{:else if key === 'performance'}
			<path stroke-linecap="round" stroke-linejoin="round" d="M5 19V10M12 19V5M19 19v-7" />
		{:else if key === 'tasks'}
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M9 7h11M9 12h11M9 17h11M4.5 7.5l1.2 1.2 2-2M4.5 12.5l1.2 1.2 2-2M4.5 17.5l1.2 1.2 2-2"
			/>
		{:else if key === 'recommendations'}
			<circle cx="12" cy="12" r="7" />
			<circle cx="12" cy="12" r="2.5" />
			<path stroke-linecap="round" d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2" />
		{:else if key === 'connect'}
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M10 13a5 5 0 0 0 7.1 0l1.4-1.4a5 5 0 0 0-7.1-7.1L10 6M14 11a5 5 0 0 0-7.1 0L5.5 12.4a5 5 0 0 0 7.1 7.1L14 18"
			/>
		{:else if key === 'usage'}
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M12 4c2 3 4 4.5 4 8a4 4 0 1 1-8 0c0-3.5 2-5 4-8z"
			/>
		{:else}
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M8 7h12M8 12h12M8 17h12M4 7h.01M4 12h.01M4 17h.01"
			/>
		{/if}
	</svg>
{/snippet}

<nav
	class={compact
		? 'flex flex-col items-center gap-1 py-1'
		: 'px-1 pb-1 text-gray-700 dark:text-gray-300'}
	aria-label="Mokli"
>
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
					on:click={() => onSelect()}
				>
					<span
						class="flex size-[calc(30px*var(--app-text-scale,1))] items-center justify-center rounded-lg"
					>
						{@render mark(link.key)}
					</span>
				</a>
			</Tooltip>
		{:else}
			<a
				href={link.href}
				class="flex grow items-center space-x-2 rounded-xl px-2 py-1.5 transition {active(link.href)
					? 'bg-black/[0.035] dark:bg-white/[0.06]'
					: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
				aria-current={active(link.href) ? 'page' : undefined}
				on:click={() => onSelect()}
			>
				<div class="flex size-4 shrink-0 items-center justify-center self-center">
					{@render mark(link.key)}
				</div>
				<div class="flex translate-y-[0.5px] self-center">
					<div class="self-center text-[0.8125rem] leading-5">{label(link.key)}</div>
				</div>
			</a>
		{/if}
	{/each}
</nav>
