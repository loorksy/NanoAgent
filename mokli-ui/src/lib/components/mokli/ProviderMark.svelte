<script lang="ts">
	import { providerLogo } from '$lib/mokli/provider-brand';

	export let name: string;
	export let label = '';

	let index = 0;
	let current = '';

	$: if (name !== current) {
		current = name;
		index = 0;
	}

	$: logo = providerLogo(name);
	$: urls = logo?.logoUrls ?? [];
	$: src = index < urls.length ? urls[index] : '';
	$: initials =
		logo?.initials ||
		(label.trim()[0] || name.trim()[0] || '?').toUpperCase();

	function next() {
		index += 1;
	}
</script>

<span
	class="grid h-8 w-8 shrink-0 place-items-center overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700"
	style={src ? undefined : `background-color: ${logo?.color || '#6b7280'}`}
>
	{#if src}
		<img
			class="h-5 w-5 object-contain"
			alt=""
			src={src}
			referrerpolicy="no-referrer"
			on:error={next}
		/>
	{:else}
		<span class="text-[10px] font-semibold text-white">{initials}</span>
	{/if}
</span>
