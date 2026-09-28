<script lang="ts">
	import { onDestroy, tick, getContext } from 'svelte';
	import { chartOpen } from '$lib/mokli/chart';
	import { mokliText } from '$lib/mokli/text';

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
	let symbol = 'XAUUSD';
	let query = '';
	let matches: { name: string; description?: string; digits?: number }[] = [];
	let failed = '';
	let loading = false;
	let container: HTMLDivElement | undefined;
	let generation = 0;
	let mounted = false;
	let widget: {
		remove?: () => void;
		activeChart?: () => { setResolution: (value: string) => void; setSymbol: (value: string) => void };
	} | null = null;
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

	const digitsOf = new Map<string, number>();

	async function searchSymbols(text: string) {
		const response = await fetch(
			`/api/v1/mokli/market/symbols?q=${encodeURIComponent(text)}&limit=30`,
			{ credentials: 'include' }
		);
		if (!response.ok) return [];
		const body = (await response.json()) as {
			symbols?: { name: string; description?: string; digits?: number }[];
		};
		for (const row of body.symbols ?? []) {
			if (row?.name && Number.isFinite(row.digits)) digitsOf.set(row.name, Number(row.digits));
		}
		return body.symbols ?? [];
	}

	function datafeed() {
		const resolutions = ['1', '5', '15', '60', '240', '1D'];
		const barSeconds: Record<string, number> = {
			'1': 60,
			'5': 300,
			'15': 900,
			'60': 3600,
			'240': 14400,
			'1D': 86400,
			D: 86400
		};
		const intervalOf = (resolution: string) =>
			({ '1': '1m', '5': '5m', '15': '15m', '60': '1h', '240': '4h', '1D': '1d', D: '1d' })[
				resolution
			] ?? '15m';
		const bars = async (name: string, resolution: string, from?: number, to?: number, limit = 300) => {
			const params = new URLSearchParams({
				symbol: name,
				interval: intervalOf(resolution),
				limit: String(limit)
			});
			if (from) params.set('from', String(from * 1000));
			if (to) params.set('to', String(to * 1000));
			const response = await fetch(`/api/v1/mokli/market/klines?${params}`, {
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
		const quote = async (name: string) => {
			const response = await fetch(
				`/api/v1/mokli/market/quote?symbol=${encodeURIComponent(name)}`,
				{ credentials: 'include' }
			);
			if (!response.ok) throw new Error('quote');
			const body = (await response.json()) as {
				quote?: { bid?: number; ask?: number; mid?: number; time?: number };
			};
			const tick = body.quote;
			if (!tick || tick.bid == null || tick.ask == null) return null;
			const bid = Number(tick.bid);
			const ask = Number(tick.ask);
			return {
				mid: Number(tick.mid ?? (bid + ask) / 2),
				time: Number(tick.time) || Math.floor(Date.now() / 1000)
			};
		};
		return {
			onReady: (callback: (config: object) => void) => {
				setTimeout(
					() => callback({ supported_resolutions: resolutions, supports_search: true }),
					0
				);
			},
			searchSymbols: (
				userInput: string,
				_exchange: string,
				_symbolType: string,
				onResult: (rows: unknown[]) => void
			) => {
				void searchSymbols(userInput).then((rows) =>
					onResult(
						rows.map((row) => ({
							symbol: row.name,
							full_name: row.name,
							description: row.description || row.name,
							exchange: 'MT5',
							ticker: row.name,
							type: 'forex'
						}))
					)
				);
			},
			resolveSymbol: (name: string, onResolve: (info: object) => void) => {
				const digits = digitsOf.get(name) ?? 2;
				setTimeout(
					() =>
						onResolve({
							name,
							ticker: name,
							description: name,
							type: 'forex',
							session: '24x7',
							timezone: 'Etc/UTC',
							exchange: 'MT5',
							minmov: 1,
							pricescale: 10 ** Math.min(Math.max(digits, 0), 8),
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
				info: { ticker?: string; name?: string },
				resolution: string,
				period: { from?: number; to?: number; countBack?: number },
				onResult: (rows: unknown[], meta: { noData: boolean }) => void,
				onError: (reason: string) => void
			) => {
				const name = info?.ticker || info?.name || symbol;
				bars(name, resolution, period.from, period.to, Math.min(period.countBack ?? 300, 4000))
					.then((rows) => setTimeout(() => onResult(rows, { noData: rows.length === 0 }), 0))
					.catch((error: Error) => setTimeout(() => onError(error.message), 0));
			},
			subscribeBars: (
				info: { ticker?: string; name?: string },
				resolution: string,
				onTick: (bar: { time: number; open: number; high: number; low: number; close: number }) => void,
				guid: string
			) => {
				const name = info?.ticker || info?.name || symbol;
				const step = barSeconds[resolution] ?? 900;
				let current: {
					time: number;
					open: number;
					high: number;
					low: number;
					close: number;
					volume: number;
				} | null = null;
				const timer = setInterval(() => {
					void quote(name)
						.then((tick) => {
							if (!tick || !Number.isFinite(tick.mid)) return;
							const bucket = Math.floor(tick.time / step) * step * 1000;
							if (!current || current.time !== bucket) {
								current = {
									time: bucket,
									open: tick.mid,
									high: tick.mid,
									low: tick.mid,
									close: tick.mid,
									volume: 0
								};
							} else {
								current = {
									...current,
									high: Math.max(current.high, tick.mid),
									low: Math.min(current.low, tick.mid),
									close: tick.mid
								};
							}
							onTick(current);
						})
						.catch(() => undefined);
				}, 1000);
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

	async function alignSymbol() {
		try {
			const rows = await searchSymbols(symbol);
			const exact = rows.find((row) => row.name.toLowerCase() === symbol.toLowerCase());
			if (exact) {
				symbol = exact.name;
				return;
			}
			const prefixed = rows
				.filter((row) => row.name.toLowerCase().startsWith(symbol.toLowerCase()))
				.sort((left, right) => left.name.length - right.name.length);
			if (prefixed[0]) symbol = prefixed[0].name;
		} catch {
			/* keep the typed symbol; the gateway also resolves the account suffix */
		}
	}

	async function mountChart() {
		const token = ++generation;
		loading = true;
		failed = '';
		await tick();
		if (token !== generation || !container) {
			if (token === generation) loading = false;
			return;
		}
		destroyWidget();
		try {
			await alignSymbol();
			if (token !== generation || !container) {
				if (token === generation) loading = false;
				return;
			}
			await loadScript();
			if (token !== generation || !container) {
				if (token === generation) loading = false;
				return;
			}
			const tradingView = (window as unknown as { TradingView?: { widget?: new (options: object) => typeof widget } })
				.TradingView;
			if (!tradingView?.widget || !container) throw new Error('chart_library');
			const dark = document.documentElement.classList.contains('dark');
			widget = new tradingView.widget({
				symbol,
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
			failed = mokliText($i18n?.language, 'chart_missing');
			loading = false;
		}
	}

	async function lookup() {
		const text = query.trim();
		if (text.length < 1) {
			matches = [];
			return;
		}
		try {
			matches = await searchSymbols(text);
		} catch {
			matches = [];
		}
	}

	function pickSymbol(name: string) {
		symbol = name;
		query = name;
		matches = [];
		try {
			widget?.activeChart?.().setSymbol(name);
		} catch {
			void mountChart();
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

	$: if ($chartOpen && !mounted) {
		mounted = true;
		void mountChart();
	}
	$: if (!$chartOpen) {
		generation += 1;
		mounted = false;
		destroyWidget();
	}

	onDestroy(destroyWidget);
</script>

{#if $chartOpen}
	<div
		class="fixed inset-x-0 bottom-0 z-[80] flex h-[min(78vh,720px)] flex-col border-t border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950"
		role="dialog"
		aria-label={mokliText($i18n?.language, 'chart')}
	>
		<div class="flex items-center gap-2 border-b border-gray-200 px-3 py-2 dark:border-gray-800">
			<div class="relative">
				<input
					class="w-28 rounded-lg border border-gray-200 bg-transparent px-2 py-1 text-sm dark:border-gray-800"
					placeholder={mokliText($i18n?.language, 'chart_symbol')}
					bind:value={query}
					on:input={lookup}
				/>
				{#if matches.length}
					<ul
						class="absolute left-0 top-9 z-10 max-h-48 w-56 overflow-auto rounded-lg border border-gray-200 bg-white text-sm dark:border-gray-800 dark:bg-gray-950"
					>
						{#each matches as row (row.name)}
							<li>
								<button
									type="button"
									class="block w-full px-2 py-1 text-start hover:bg-gray-100 dark:hover:bg-gray-900"
									on:click={() => pickSymbol(row.name)}
								>
									{row.name}
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
			<div class="text-sm font-medium">{symbol}</div>
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
				aria-label={mokliText($i18n?.language, 'chart_hide')}
				on:click={() => chartOpen.set(false)}
			>
				{mokliText($i18n?.language, 'chart_hide')}
			</button>
		</div>
		<div class="relative min-h-0 flex-1">
			<div class="h-full w-full" bind:this={container}></div>
			{#if loading}
				<p class="absolute left-3 top-3 text-sm text-gray-500">
					{mokliText($i18n?.language, 'chart_loading')}
				</p>
			{/if}
			{#if failed}
				<p class="absolute left-3 top-3 text-sm text-red-500">{failed}</p>
			{/if}
		</div>
	</div>
{/if}
