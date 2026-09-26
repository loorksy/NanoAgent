<script lang="ts">
	import { onDestroy, tick, getContext } from 'svelte';
	import { chartOpen } from '$lib/nanoagent/chart';
	import { nanoagentText } from '$lib/nanoagent/text';

	const i18n = getContext<{ language?: string }>('i18n');

	const INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1d'] as const;
	const RES: Record<string, string> = {
		'1m': '1',
		'5m': '5',
		'15m': '15',
		'1h': '60',
		'4h': '240',
		'1d': '1D'
	};

	let interval = '15m';
	let failed = '';
	let loading = false;
	let container: HTMLDivElement | undefined;
	let generation = 0;
	let widget: { remove?: () => void; activeChart?: () => { setResolution: (value: string) => void } } | null =
		null;
	let scriptPromise: Promise<void> | null = null;

	function loadScript(): Promise<void> {
		const tradingView = (window as unknown as { TradingView?: { widget?: unknown } }).TradingView;
		if (tradingView?.widget) return Promise.resolve();
		if (scriptPromise) return scriptPromise;
		scriptPromise = new Promise((resolve, reject) => {
			const script = document.createElement('script');
			script.src = '/charting_library/charting_library.standalone.js';
			script.async = true;
			script.onload = () => resolve();
			script.onerror = () => reject(new Error('chart_library'));
			document.head.appendChild(script);
		});
		return scriptPromise;
	}

	function datafeed() {
		const resolutions = ['1', '5', '15', '60', '240', '1D'];
		const intervalOf = (resolution: string) =>
			({ '1': '1m', '5': '5m', '15': '15m', '60': '1h', '240': '4h', '1D': '1d', D: '1d' })[
				resolution
			] ?? '15m';
		const bars = async (resolution: string, from?: number, to?: number, limit = 300) => {
			const params = new URLSearchParams({
				symbol: 'XAUUSD',
				interval: intervalOf(resolution),
				limit: String(limit)
			});
			if (from) params.set('from', String(from * 1000));
			if (to) params.set('to', String(to * 1000));
			const response = await fetch(`/api/v1/nanoagent/market/klines?${params}`, {
				credentials: 'include'
			});
			if (!response.ok) throw new Error('klines');
			const body = (await response.json()) as {
				candles?: { time: number; open: number; high: number; low: number; close: number; volume?: number }[];
			};
			return (body.candles ?? [])
				.filter((candle) => Number.isFinite(candle.time) && candle.time > 0)
				.map((candle) => ({
					time: candle.time * 1000,
					open: candle.open,
					high: candle.high,
					low: candle.low,
					close: candle.close,
					volume: candle.volume ?? 0
				}))
				.sort((left, right) => left.time - right.time);
		};
		const timers = new Map<string, ReturnType<typeof setInterval>>();
		return {
			onReady: (callback: (config: object) => void) => {
				setTimeout(() => callback({ supported_resolutions: resolutions }), 0);
			},
			searchSymbols: (
				_userInput: string,
				_exchange: string,
				_symbolType: string,
				onResult: (rows: unknown[]) => void
			) => onResult([]),
			resolveSymbol: (
				_name: string,
				onResolve: (info: object) => void
			) => {
				setTimeout(
					() =>
						onResolve({
							name: 'XAUUSD',
							ticker: 'XAUUSD',
							description: 'Gold',
							type: 'forex',
							session: '24x7',
							timezone: 'Etc/UTC',
							minmov: 1,
							pricescale: 100,
							has_intraday: true,
							has_daily: true,
							supported_resolutions: resolutions,
							volume_precision: 0,
							data_status: 'streaming'
						}),
					0
				);
			},
			getBars: (
				_symbol: object,
				resolution: string,
				period: { from?: number; to?: number; countBack?: number },
				onResult: (rows: unknown[], meta: { noData: boolean }) => void,
				onError: (reason: string) => void
			) => {
				bars(resolution, period.from, period.to, Math.min(period.countBack ?? 300, 4000))
					.then((rows) => onResult(rows, { noData: rows.length === 0 }))
					.catch((error: Error) => onError(error.message));
			},
			subscribeBars: (
				_symbol: object,
				resolution: string,
				onTick: (bar: object) => void,
				guid: string
			) => {
				const timer = setInterval(() => {
					void bars(resolution, undefined, undefined, 2)
						.then((rows) => {
							const latest = rows[rows.length - 1];
							if (latest) onTick(latest);
						})
						.catch(() => undefined);
				}, 5000);
				timers.set(guid, timer);
			},
			unsubscribeBars: (guid: string) => {
				const timer = timers.get(guid);
				if (timer) clearInterval(timer);
				timers.delete(guid);
			}
		};
	}

	function destroyWidget() {
		try {
			widget?.remove?.();
		} catch {
			/* widget already gone */
		}
		widget = null;
	}

	async function mountChart() {
		const token = ++generation;
		loading = true;
		failed = '';
		await tick();
		if (token !== generation || !container) return;
		destroyWidget();
		try {
			await loadScript();
			if (token !== generation || !container) return;
			const tradingView = (window as unknown as { TradingView?: { widget?: new (options: object) => typeof widget } })
				.TradingView;
			if (!tradingView?.widget || !container) throw new Error('chart_library');
			const dark = document.documentElement.classList.contains('dark');
			widget = new tradingView.widget({
				symbol: 'XAUUSD',
				interval: RES[interval] ?? '15',
				container,
				library_path: '/charting_library/',
				locale: 'en',
				autosize: true,
				theme: dark ? 'dark' : 'light',
				disabled_features: [
					'header_symbol_search',
					'symbol_search_hot_key',
					'header_compare',
					'left_toolbar',
					'header_saveload',
					'header_settings',
					'header_undo_redo',
					'header_screenshot',
					'header_fullscreen_button'
				],
				enabled_features: [],
				datafeed: datafeed()
			});
			loading = false;
		} catch {
			failed = nanoagentText($i18n?.language, 'chart_missing');
			loading = false;
		}
	}

	function setIntervalChoice(next: string) {
		interval = next;
		try {
			widget?.activeChart?.().setResolution(RES[next] ?? '15');
		} catch {
			void mountChart();
		}
	}

	$: if ($chartOpen) {
		void mountChart();
	} else {
		generation += 1;
		destroyWidget();
	}

	onDestroy(destroyWidget);
</script>

{#if $chartOpen}
	<div
		class="fixed inset-x-0 bottom-0 z-[80] flex h-[min(78vh,720px)] flex-col border-t border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950"
		role="dialog"
		aria-label={nanoagentText($i18n?.language, 'chart')}
	>
		<div class="flex items-center gap-2 border-b border-gray-200 px-3 py-2 dark:border-gray-800">
			<div class="text-sm font-medium">{nanoagentText($i18n?.language, 'chart')}</div>
			<div class="flex flex-1 gap-1 overflow-x-auto">
				{#each INTERVALS as choice (choice)}
					<button
						type="button"
						class="rounded-lg px-2 py-1 text-xs {choice === interval
							? 'bg-black text-white dark:bg-white dark:text-black'
							: 'border border-gray-200 dark:border-gray-800'}"
						on:click={() => setIntervalChoice(choice)}
					>
						{choice}
					</button>
				{/each}
			</div>
			<button
				type="button"
				class="rounded-lg px-2 py-1 text-sm"
				aria-label={nanoagentText($i18n?.language, 'chart_hide')}
				on:click={() => chartOpen.set(false)}
			>
				{nanoagentText($i18n?.language, 'chart_hide')}
			</button>
		</div>
		<div class="relative min-h-0 flex-1">
			<div class="h-full w-full" bind:this={container}></div>
			{#if loading}
				<p class="absolute left-3 top-3 text-sm text-gray-500">
					{nanoagentText($i18n?.language, 'chart_loading')}
				</p>
			{/if}
			{#if failed}
				<p class="absolute left-3 top-3 text-sm text-red-500">{failed}</p>
			{/if}
		</div>
	</div>
{/if}
