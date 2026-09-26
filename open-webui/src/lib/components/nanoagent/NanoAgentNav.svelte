<script lang="ts">
	import { page } from '$app/stores';
	import { getContext } from 'svelte';
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
</script>

<nav class={compact ? 'flex flex-col items-center gap-1 py-1' : 'px-1 pb-1'} aria-label="NanoAgent">
	{#each links as link (link.href)}
		<a
			href={link.href}
			class="rounded-xl text-[0.8125rem] leading-5 {compact
				? 'flex size-8 items-center justify-center'
				: 'flex px-2 py-1.5'} {active(link.href)
				? 'bg-black/[0.035] dark:bg-white/[0.06]'
				: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
			aria-current={active(link.href) ? 'page' : undefined}
		>
			{nanoagentText($i18n?.language, link.key)}
		</a>
	{/each}
</nav>
