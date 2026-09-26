<script lang="ts">
	import { createEventDispatcher, onDestroy, onMount } from 'svelte';

	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronRight from './icons/ChevronRight.svelte';
	import Plus from './icons/Plus.svelte';

	const dispatch = createEventDispatcher();
	type AddHandler = () => void | Promise<void>;

	export let open = true;
	export let id = '';
	export let name = '';
	export let collapsible = true;
	export let className = '';
	export let buttonClassName = '';
	export let contentClassName = 'px-1.5';
	export let onAddLabel = '';
	export let onAdd: null | AddHandler = null;
	export let dragAndDrop = true;

	let sectionElement: HTMLDivElement;
	let loaded = false;
	let draggedOver = false;

	const setOpen = (state: boolean) => {
		open = state;
		dispatch('change', state);
		localStorage.setItem(`${id}-folder-state`, `${state}`);
	};

	const onDragOver = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		draggedOver = true;
	};

	const onDrop = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();

		if (!sectionElement.contains(e.target as Node)) {
			return;
		}

		if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
			for (const item of Array.from(e.dataTransfer.items)) {
				if (item.kind === 'file') {
					const file = item.getAsFile();
					if (file && file.type === 'application/json') {
						const reader = new FileReader();
						reader.onload = async function (event) {
							try {
								const fileContent = JSON.parse(event.target?.result as string);
								open = true;
								dispatch('import', fileContent);
							} catch (error) {
								console.error('Error parsing JSON file:', error);
							}
						};
						reader.readAsText(file);
					}
				} else {
					open = true;
					try {
						const dataTransfer = e.dataTransfer.getData('text/plain');
						if (dataTransfer) {
							dispatch('drop', JSON.parse(dataTransfer));
						}
					} catch {
						// Ignore drops that are not sidebar JSON payloads.
					} finally {
						draggedOver = false;
					}
					break;
				}
			}
		}

		draggedOver = false;
	};

	const onDragLeave = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		draggedOver = false;
	};

	onMount(() => {
		const state = localStorage.getItem(`${id}-folder-state`);
		if (state !== null) {
			open = state === 'true';
		}

		loaded = true;

		if (!dragAndDrop) {
			return;
		}

		sectionElement.addEventListener('dragover', onDragOver);
		sectionElement.addEventListener('drop', onDrop);
		sectionElement.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		if (!dragAndDrop) {
			return;
		}

		sectionElement.removeEventListener('dragover', onDragOver);
		sectionElement.removeEventListener('drop', onDrop);
		sectionElement.removeEventListener('dragleave', onDragLeave);
	});
</script>

<div bind:this={sectionElement} class="relative {className}">
	{#if loaded}
		{#if draggedOver}
			<div
				class="absolute inset-0 z-50 rounded-md bg-gray-100/50 pointer-events-none touch-none dark:bg-gray-700/20"
			></div>
		{/if}

		{#if collapsible}
			<Collapsible bind:open className="w-full" buttonClassName="w-full" onChange={setOpen}>
				<div class="flex h-8 w-full shrink-0 items-center justify-between px-2">
					<button
						type="button"
						class="group flex h-full flex-1 items-center gap-2 text-left text-gray-500 transition-colors duration-100 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 {buttonClassName}"
						aria-expanded={open}
						aria-controls="{id}-content"
					>
						<span class="flex size-4 shrink-0 items-center justify-center" aria-hidden="true">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.5"
								class="size-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M4 7h16M4 12h16M4 17h16"
								/>
							</svg>
						</span>
						<span class="text-[0.8125rem] leading-5">{name}</span>
						<span
							class="flex transition-transform duration-100"
							style="transform: rotate({open ? '90deg' : '0deg'})"
						>
							<ChevronRight className="size-4" />
						</span>
					</button>

					<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
					<div class="contents" on:click={(e) => e.stopPropagation()}>
						<slot name="action" />
					</div>

					{#if onAdd}
						<button
							type="button"
							class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-300 hover:text-gray-500 dark:text-gray-600 dark:hover:text-gray-400 transition-colors duration-100"
							aria-label={onAddLabel}
							on:click={(e) => {
								e.stopPropagation();
								onAdd();
							}}
						>
							<Tooltip content={onAddLabel}>
								<Plus className="size-3.5" />
							</Tooltip>
						</button>
					{/if}
				</div>

				<div id="{id}-content" slot="content" class="w-full {contentClassName}">
					<slot></slot>
				</div>
			</Collapsible>
		{:else}
			<slot></slot>
		{/if}
	{/if}
</div>
