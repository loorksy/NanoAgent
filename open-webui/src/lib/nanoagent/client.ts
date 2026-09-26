/** Calls the Open WebUI proxy. The gateway bearer token never reaches the browser. */

export async function gateway(path: string, init: RequestInit = {}): Promise<unknown> {
	const headers = new Headers(init.headers);
	if (init.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}
	const response = await fetch(`/api/v1/nanoagent/${path.replace(/^\//, '')}`, {
		credentials: 'include',
		...init,
		headers
	});
	const payload: unknown = await response.json().catch(() => ({}));
	if (!response.ok) {
		throw new Error(`gateway ${response.status}`);
	}
	return payload;
}
