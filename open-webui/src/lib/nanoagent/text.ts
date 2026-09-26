import ar from '$lib/nanoagent/i18n/ar.json';
import en from '$lib/nanoagent/i18n/en.json';

const catalogs: Record<string, Record<string, string>> = { en, ar };

export function nanoagentText(language: string | undefined, key: string): string {
	const code = (language ?? '').toLowerCase().startsWith('ar') ? 'ar' : 'en';
	return catalogs[code][key] ?? catalogs.en[key] ?? key;
}
