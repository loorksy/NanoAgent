import { writable } from 'svelte/store';

import { gateway } from '$lib/mokli/client';

export type DeskCard = {
	roleId: string;
	role: string;
	roomId: string;
	layer: number | null;
	stage: string;
	summary: string;
	sessionKey: string;
};

export const deskCards = writable<DeskCard[]>([]);

export function noteDeskStatus(desk: Record<string, unknown> | null | undefined) {
	if (!desk || typeof desk !== 'object') return;
	const roleId = String(desk.role_id || desk.role || '').trim();
	if (!roleId) return;
	const layer = typeof desk.layer === 'number' ? desk.layer : null;
	const card: DeskCard = {
		roleId,
		role: String(desk.role || roleId),
		roomId: String(desk.room_id || ''),
		layer,
		stage: String(desk.stage || 'started'),
		summary: String(desk.summary || ''),
		sessionKey: String(desk.session_key || '')
	};
	deskCards.update((cards) => [...cards.filter((item) => item.roleId !== roleId), card]);
}

export async function stopDesk(sessionKey: string) {
	if (sessionKey) {
		await gateway(`sessions/${encodeURIComponent(sessionKey)}/cancel`, { method: 'POST' });
	}
	await gateway('desk/stop', { method: 'POST' });
}
