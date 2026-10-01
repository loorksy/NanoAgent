<script lang="ts">
	import { deskCards, stopDesk } from '$lib/mokli/desk-board';

	let stopping = false;
	let stopError = '';

	async function stop(sessionKey: string) {
		stopping = true;
		stopError = '';
		try {
			await stopDesk(sessionKey);
		} catch (error) {
			stopError = error instanceof Error ? error.message : 'stop failed';
		} finally {
			stopping = false;
		}
	}
</script>

{#if $deskCards.length > 0}
	<section
		class="pointer-events-auto absolute bottom-4 left-4 z-30 w-72 rounded-xl border border-gray-200 bg-white/95 p-3 text-sm shadow-lg dark:border-gray-800 dark:bg-gray-950/95"
	>
		<p class="mb-2 font-medium">Trading desk</p>
		<ul class="flex flex-col gap-2">
			{#each $deskCards as card (card.roleId)}
				<li class="rounded-lg border border-gray-100 px-2 py-1.5 dark:border-gray-800">
					<p>
						{card.role}
						{#if card.roomId}
							<span class="text-gray-500">· {card.roomId}</span>
						{/if}
						{#if card.layer !== null}
							<span class="text-gray-500">· layer {card.layer}</span>
						{/if}
					</p>
					<p class="text-xs text-gray-500">{card.stage}{card.summary ? ` — ${card.summary}` : ''}</p>
				</li>
			{/each}
		</ul>
		<button
			class="mt-2 rounded-lg border border-gray-300 px-2 py-1 text-xs dark:border-gray-700"
			type="button"
			disabled={stopping}
			on:click={() => stop($deskCards[0]?.sessionKey || '')}
		>
			Stop swarm
		</button>
		{#if stopError}
			<p class="mt-1 text-xs text-red-500">{stopError}</p>
		{/if}
	</section>
{/if}
