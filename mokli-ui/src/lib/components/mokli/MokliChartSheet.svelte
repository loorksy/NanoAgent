<script lang="ts">
	import { onDestroy, tick, getContext } from 'svelte';
	import { chartOpen } from '$lib/mokli/chart';
	import { mokliText } from '$lib/mokli/text';

	const i18n = getContext<{ language?: string }>('i18n');

	let symbol = 'XAUUSD';
	let failed = '';
	let loading = false;
	let container: HTMLDivElement | undefined;
	let generation = 0;
	let kept = false;
	let starting = false;
	let widget: {
		remove?: () => void;
		resize?: () => void;
		onChartReady?: (cb: () => void) => void;
		activeChart?: () => { setSymbol: (value: string) => void };
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
		const resolutions = ['1', '5', '15', '30', '60', '240', '1D', '1W'];
		const barSeconds: Record<string, number> = {
			'1': 60,
			'5': 300,
			'15': 900,
			'30': 1800,
			'60': 3600,
			'240': 14400,
			'1D': 86400,
			D: 86400,
			'1W': 604800,
			W: 604800
		};
		const intervalOf = (resolution: string) =>
			({
				'1': '1m',
				'5': '5m',
				'15': '15m',
				'30': '30m',
				'60': '1h',
				'240': '4h',
				'1D': '1d',
				D: '1d',
				'1W': '1w',
				W: '1w'
			})[resolution] ?? '15m';
		const lastBars = new Map<
			string,
			{ time: number; open: number; high: number; low: number; close: number; volume: number }
		>();
		const bars = async (name: string, resolution: string, from?: number, to?: number, limit = 500) => {
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
				candles?: {
					time: number;
					open: number;
					high: number;
					low: number;
					close: number;
					volume?: number;
				}[];
			};
			return (body.candles ?? [])
				.filter(
					(candle) =>
						Number.isFinite(candle.time) &&
						candle.time > 0 &&
						candle.open > 0 &&
						candle.high > 0 &&
						candle.low > 0 &&
						candle.close > 0
				)
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
					() =>
						callback({
							supported_resolutions: resolutions,
							supports_search: true,
							supports_group_request: false,
							supports_marks: false,
							supports_timescale_marks: false,
							supports_time: true
						}),
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
							exchange: 'OANDA',
							ticker: row.name,
							type: 'forex'
						}))
					)
				);
			},
			resolveSymbol: (name: string, onResolve: (info: object) => void) => {
				void (async () => {
					if (!digitsOf.has(name)) {
						try {
							await searchSymbols(name);
						} catch {
							/* digits stay at the gold default */
						}
					}
					const digits = digitsOf.get(name) ?? 2;
					onResolve({
						name,
						ticker: name,
						description: name,
						type: 'forex',
						session: '24x7',
						timezone: 'Etc/UTC',
						exchange: 'OANDA',
						minmov: 1,
						pricescale: 10 ** Math.min(Math.max(digits, 0), 8),
						has_intraday: true,
						has_daily: true,
						has_weekly_and_monthly: true,
						supported_resolutions: resolutions,
						volume_precision: 0,
						data_status: 'streaming'
					});
				})();
			},
			getBars: (
				info: { ticker?: string; name?: string },
				resolution: string,
				period: { from?: number; to?: number; countBack?: number },
				onResult: (rows: unknown[], meta: { noData: boolean }) => void,
				onError: (reason: string) => void
			) => {
				const name = info?.ticker || info?.name || symbol;
				const count = Math.min(Math.max(period.countBack ?? 500, 300), 5000);
				bars(name, resolution, period.from, period.to, count)
					.then((rows) => {
						if (rows.length) lastBars.set(`${name}:${resolution}`, rows[rows.length - 1]);
						setTimeout(() => onResult(rows, { noData: rows.length === 0 }), 0);
					})
					.catch((error: Error) => setTimeout(() => onError(error.message), 0));
			},
			subscribeBars: (
				info: { ticker?: string; name?: string },
				resolution: string,
				onTick: (bar: {
					time: number;
					open: number;
					high: number;
					low: number;
					close: number;
					volume: number;
				}) => void,
				guid: string
			) => {
				const name = info?.ticker || info?.name || symbol;
				const step = barSeconds[resolution] ?? 900;
				const key = `${name}:${resolution}`;
				const seed = lastBars.get(key);
				let current = seed ? { ...seed } : null;
				const timer = setInterval(() => {
					void quote(name)
						.then((tick) => {
							if (!tick || !Number.isFinite(tick.mid)) return;
							const bucket = Math.floor(tick.time / step) * step * 1000;
							if (current && bucket < current.time) return;
							if (!current || current.time !== bucket) {
								const open = current ? current.close : tick.mid;
								current = {
									time: bucket,
									open,
									high: Math.max(open, tick.mid),
									low: Math.min(open, tick.mid),
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
							lastBars.set(key, current);
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

	function hostChart(node: HTMLDivElement) {
		container = node;
		let cancelled = false;
		let frames = 0;
		const waitForBox = () => {
			if (cancelled || widget || starting) return;
			frames += 1;
			if (node.clientHeight < 8 && frames < 30) {
				requestAnimationFrame(waitForBox);
				return;
			}
			void mountChart();
		};
		requestAnimationFrame(waitForBox);
		return {
			destroy() {
				cancelled = true;
			}
		};
	}

	async function mountChart() {
		const node = container;
		if (!node || widget || starting) return;
		starting = true;
		const token = ++generation;
		loading = true;
		failed = '';
		await tick();
		if (token !== generation || container !== node) {
			starting = false;
			if (token === generation) loading = false;
			return;
		}
		try {
			const naming = alignSymbol();
			await loadScript();
			if (token !== generation || container !== node) {
				starting = false;
				if (token === generation) loading = false;
				return;
			}
			const tradingView = (
				window as unknown as {
					TradingView?: { widget?: new (options: object) => typeof widget };
				}
			).TradingView;
			if (!tradingView?.widget) throw new Error('chart_library');
			const dark = document.documentElement.classList.contains('dark');
			const language = ($i18n?.language || 'en').toLowerCase();
			const created = new tradingView.widget({
				symbol,
				interval: '15',
				container: node,
				library_path: '/charting_library/',
				locale: language.startsWith('ar') ? 'ar' : 'en',
				autosize: true,
				theme: dark ? 'dark' : 'light',
				disabled_features: ['header_saveload'],
				enabled_features: [],
				datafeed: datafeed(),
				overrides: {
					'paneProperties.background': dark ? '#030712' : '#ffffff',
					'paneProperties.backgroundType': 'solid'
				}
			});
			widget = created;
			const initial = symbol;
			void naming.then(() => {
				if (widget !== created || symbol === initial) return;
				try {
					created.activeChart?.().setSymbol(symbol);
				} catch {
					/* the typed name still resolves on the server */
				}
			});
			created.onChartReady?.(() => {
				try {
					created.resize?.();
				} catch {
					/* the library sizes itself */
				}
				loading = false;
			});
			loading = false;
		} catch {
			failed = mokliText($i18n?.language, 'chart_missing');
			loading = false;
		}
	}

	$: if ($chartOpen) kept = true;

	onDestroy(() => {
		generation += 1;
		destroyWidget();
	});
</script>

{#if kept}
	<div
		class="fixed inset-x-0 bottom-0 z-[80] flex h-[min(88vh,920px)] flex-col border-t border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950 {$chartOpen
			? ''
			: 'invisible pointer-events-none'}"
		role="dialog"
		aria-hidden={!$chartOpen}
		aria-label={mokliText($i18n?.language, 'chart')}
	>
		<div class="flex justify-end border-b border-gray-200 px-2 py-1 dark:border-gray-800">
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
			<div class="absolute inset-0" use:hostChart></div>
			{#if loading && $chartOpen}
				<p class="absolute left-3 top-3 text-sm text-gray-500">
					{mokliText($i18n?.language, 'chart_loading')}
				</p>
			{/if}
			{#if failed && $chartOpen}
				<p class="absolute left-3 top-3 text-sm text-red-500">{failed}</p>
			{/if}
		</div>
	</div>
{/if}
