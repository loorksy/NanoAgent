/** Prefer the NanoAgent pipe when a playground or automation needs a model. */
export function preferNanoagentModel(
	models: { id?: string }[] | undefined,
	fallback: string
): string {
	const match = (models ?? []).find((model) => String(model.id ?? '').includes('nanoagent'));
	if (match?.id) return match.id;
	return fallback;
}
