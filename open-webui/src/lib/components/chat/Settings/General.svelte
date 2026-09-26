<script lang="ts">
	import { canEditParameters } from '$lib/utils/settings-access';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { getLanguages, changeLanguage } from '$lib/i18n';
	const dispatch = createEventDispatcher();

	import { config, models, settings, theme, user } from '$lib/stores';

	const i18n: any = getContext('i18n');

	import UserSettingRow from './UserSettingRow.svelte';
	import UserSettingSection from './UserSettingSection.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	export let saveSettings: Function;
	export let getModels: Function;

	// General
	let themes = ['dark', 'light', 'oled-dark'];
	let selectedTheme = 'system';

	let languages: Awaited<ReturnType<typeof getLanguages>> = [];
	let lang = $i18n.language;
	let params = {
		stream_response: null,
		function_calling: null,
		reasoning_tags: null
	};

	$: canEditParams = canEditParameters({ user: $user, config: $config });

	const saveHandler = async () => {
		const updated: Record<string, any> = {};
		updated.system = null;
		if (canEditParams) {
			updated.params = {
				stream_response: params.stream_response !== null ? params.stream_response : undefined,
				function_calling: params.function_calling !== null ? params.function_calling : undefined,
				reasoning_tags: params.reasoning_tags !== null ? params.reasoning_tags : undefined
			};
		}
		try {
			await saveSettings(updated);
			dispatch('save');
		} catch {
			// The settings modal displays the save error; do not report success.
		}
	};

	onMount(async () => {
		selectedTheme = localStorage.theme ?? 'system';

		languages = await getLanguages();

		if (!$config?.features?.enable_easter_eggs) {
			languages = languages.filter((l) => l.code !== 'dg-DG');
		}

		params = { ...params, ...$settings.params };
	});

	const applyTheme = (_theme: string) => {
		let themeToApply = _theme === 'oled-dark' ? 'dark' : _theme === 'her' ? 'light' : _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		}

		if (themeToApply === 'dark' && !_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#333');
			document.documentElement.style.setProperty('--color-gray-850', '#262626');
			document.documentElement.style.setProperty('--color-gray-900', '#171717');
			document.documentElement.style.setProperty('--color-gray-950', '#0d0d0d');
		}

		themes
			.filter((e) => e !== themeToApply)
			.forEach((e) => {
				e.split(' ').forEach((e) => {
					document.documentElement.classList.remove(e);
				});
			});

		themeToApply.split(' ').forEach((e) => {
			document.documentElement.classList.add(e);
		});

		const metaThemeColor = document.querySelector('meta[name="theme-color"]');
		if (metaThemeColor) {
			if (_theme.includes('system')) {
				const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
					? 'dark'
					: 'light';
				console.log('Setting system meta theme color: ' + systemTheme);
				metaThemeColor.setAttribute('content', systemTheme === 'light' ? '#ffffff' : '#171717');
			} else {
				console.log('Setting meta theme color: ' + _theme);
				metaThemeColor.setAttribute(
					'content',
					_theme === 'dark'
						? '#171717'
						: _theme === 'oled-dark'
							? '#000000'
							: _theme === 'her'
								? '#983724'
								: '#ffffff'
				);
			}
		}

		if (typeof window !== 'undefined' && window.applyTheme) {
			window.applyTheme();
		}

		if (_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#101010');
			document.documentElement.style.setProperty('--color-gray-850', '#050505');
			document.documentElement.style.setProperty('--color-gray-900', '#000000');
			document.documentElement.style.setProperty('--color-gray-950', '#000000');
			document.documentElement.classList.add('dark');
		}

		console.log(_theme);
	};

	const themeChangeHandler = (_theme: string) => {
		theme.set(_theme);
		localStorage.setItem('theme', _theme);
		applyTheme(_theme);
	};
</script>

<div class="flex flex-col h-full justify-between text-sm" id="tab-general">
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('settings.personal.general.title')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<UserSettingSection
			title={$i18n.t('settings.personal.general.sections.webuiSettings.title')}
			first
		>
			<UserSettingRow
				label={$i18n.t('settings.personal.general.theme.label')}
				description={$i18n.t('settings.personal.general.theme.description')}
			>
				<SettingsSelect
					bind:value={selectedTheme}
					ariaLabel={$i18n.t('settings.personal.general.theme.label')}
					placeholder={$i18n.t('Select a theme')}
					on:change={() => themeChangeHandler(selectedTheme)}
				>
					<option value="system">⚙️ {$i18n.t('System')}</option>
					<option value="dark">🌑 {$i18n.t('Dark')}</option>
					<option value="oled-dark">🌃 {$i18n.t('OLED Dark')}</option>
					<option value="light">☀️ {$i18n.t('Light')}</option>
					{#if $config?.features?.enable_easter_eggs}
						<option value="her">🌷 Her</option>
					{/if}
				</SettingsSelect>
			</UserSettingRow>

			<UserSettingRow
				label={$i18n.t('settings.personal.general.language.label')}
				description={$i18n.t('settings.personal.general.language.description')}
			>
				<SettingsSelect
					bind:value={lang}
					ariaLabel={$i18n.t('settings.personal.general.language.label')}
					placeholder={$i18n.t('Select a language')}
					on:change={(e) => {
						changeLanguage(lang);
					}}
				>
					{#each languages as language}
						<option value={language['code']}>{language['title']}</option>
					{/each}
				</SettingsSelect>
			</UserSettingRow>
			{#if $i18n.language === 'en-US' && !($config?.license_metadata ?? false)}
				<div class="-mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
					{$i18n.t("Couldn't find your language?")}
					<a
						class="font-normal underline text-gray-400 dark:text-gray-600"
						href="https://github.com/open-webui/open-webui/blob/main/docs/CONTRIBUTING.md#-translations-and-internationalization"
						target="_blank"
					>
						<!-- LICENSE covers this Open WebUI wordmark.
						Do not alter, remove, obscure, or replace it except as LICENSE permits:
						https://docs.openwebui.com/license. -->
						{$i18n.t('Help us translate Open WebUI!')}
					</a>
				</div>
			{/if}
		</UserSettingSection>

	</div>

	<div class="shrink-0 flex justify-end pt-3 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={() => {
				saveHandler();
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
