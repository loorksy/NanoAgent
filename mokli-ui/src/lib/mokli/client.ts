/** Calls the Mokli proxy. The gateway bearer token never reaches the browser. */

export async function gateway(path: string, init: RequestInit = {}): Promise<unknown> {
	const headers = new Headers(init.headers);
	if (init.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}
	const response = await fetch(`/api/v1/mokli/${path.replace(/^\//, '')}`, {
		...init,
		credentials: 'include',
		headers
	});
	let payload: unknown;
	try {
		payload = await response.json();
	} catch {
		throw new Error(response.ok ? 'gateway response was not JSON' : `gateway ${response.status}`);
	}
	if (!response.ok) {
		const details =
			payload &&
			typeof payload === 'object' &&
			'error' in payload &&
			(payload as { error?: { details?: { message?: unknown } } }).error?.details?.message;
		const message = typeof details === 'string' && details.trim() ? details : `gateway ${response.status}`;
		throw new Error(message);
	}
	return payload;
}
