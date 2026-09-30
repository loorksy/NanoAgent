export type StatusUpdate = {
	action?: unknown;
	description?: unknown;
	done?: unknown;
};

function hasAction(status: StatusUpdate | null | undefined): boolean {
	return typeof status?.action === 'string' && status.action.length > 0;
}

/** Search rows stay on one line. A Mokli activity group has no action and must wrap. */
export function statusLineClamped(status: StatusUpdate | null | undefined): boolean {
	return hasAction(status);
}

/**
 * The pipe emits one full activity line per runtime event. Those lines have
 * no `action`. Replacing the previous line keeps a single live group.
 * Open WebUI search statuses set `action` and stay in the history.
 */
export function applyStatusUpdate<T extends StatusUpdate>(
	history: readonly T[] | null | undefined,
	next: T
): T[] {
	const current = history ? [...history] : [];
	const last = current.at(-1);
	if (last && !hasAction(last) && !hasAction(next)) {
		current[current.length - 1] = next;
		return current;
	}
	current.push(next);
	return current;
}

/**
 * The expanded list must not paint an unfinished activity snapshot as done.
 * The latest row uses its own flag. An older row with an action is a finished
 * search step. An older description-only row keeps its own flag.
 */
export function expandedStatusDone(status: StatusUpdate, index: number, length: number): boolean {
	if (index === length - 1 || !hasAction(status)) {
		return status?.done === true;
	}
	return true;
}
