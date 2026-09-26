/** Prefer the Mokli pipe when a playground or automation needs a model. */
export function preferMokliModel(
	models: { id?: string }[] | undefined,
	fallback: string
): string {
	const match = (models ?? []).find((model) => String(model.id ?? '').includes('mokli'));
	if (match?.id) return match.id;
	return fallback;
}
