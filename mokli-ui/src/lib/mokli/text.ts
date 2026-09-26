import ar from '$lib/mokli/i18n/ar.json';
import en from '$lib/mokli/i18n/en.json';

const catalogs: Record<string, Record<string, string>> = { en, ar };

export function mokliText(language: string | undefined, key: string): string {
	const code = (language ?? '').toLowerCase().startsWith('ar') ? 'ar' : 'en';
	return catalogs[code][key] ?? catalogs.en[key] ?? key;
}
