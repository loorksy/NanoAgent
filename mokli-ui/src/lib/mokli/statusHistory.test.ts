import { describe, expect, it } from 'vitest';

import {
	applyStatusUpdate,
	expandedStatusDone,
	statusLineClamped,
	type StatusUpdate
} from './statusHistory';

const activity = (description: string, done = false): StatusUpdate => ({
	description,
	done
});

describe('applyStatusUpdate', () => {
	it('keeps one live activity line across consecutive runtime snapshots', () => {
		const first = applyStatusUpdate(undefined, activity('جاري المعالجة…'));
		const second = applyStatusUpdate(first, activity('يفحص سعر الذهب الحالي… …'));
		const third = applyStatusUpdate(
			second,
			activity('يفحص سعر الذهب الحالي… ✓ · يتحقق من شروط القرار… …')
		);

		expect(third).toEqual([activity('يفحص سعر الذهب الحالي… ✓ · يتحقق من شروط القرار… …')]);
	});

	it('appends a search status that names an action', () => {
		const live = applyStatusUpdate(undefined, activity('يفحص سعر الذهب الحالي… …'));
		const withSearch = applyStatusUpdate(live, {
			action: 'web_search',
			description: 'Searched {{count}} sites',
			done: true,
			urls: ['https://example.test']
		});

		expect(withSearch).toHaveLength(2);
		expect(withSearch[0]).toEqual(activity('يفحص سعر الذهب الحالي… …'));
		expect(withSearch[1]?.action).toBe('web_search');
	});

	it('does not collapse two action statuses into one', () => {
		const history = applyStatusUpdate(
			[{ action: 'knowledge_search', description: 'Searching Knowledge', query: 'gold' }],
			{ action: 'sources_retrieved', description: 'Retrieved {{count}} sources', count: 2 }
		);

		expect(history.map((status) => status.action)).toEqual([
			'knowledge_search',
			'sources_retrieved'
		]);
	});

	it('keeps the search row when a later activity line arrives', () => {
		const history = applyStatusUpdate(
			[
				activity('يفحص سعر الذهب الحالي… …'),
				{ action: 'web_search', description: 'Searched {{count}} sites', done: true }
			],
			activity('يفحص سعر الذهب الحالي… ✓', true)
		);

		expect(history).toHaveLength(3);
		expect(history[1]?.action).toBe('web_search');
		expect(history[2]?.done).toBe(true);
	});
});

describe('statusLineClamped', () => {
	it('lets a Mokli activity group wrap', () => {
		expect(statusLineClamped(activity('يفحص سعر الذهب الحالي… ✓ · يتحقق من شروط القرار… …'))).toBe(
			false
		);
	});

	it('keeps a search row on one line', () => {
		expect(statusLineClamped({ action: 'web_search', description: 'Searched {{count}} sites' })).toBe(
			true
		);
	});
});

describe('expandedStatusDone', () => {
	it('does not mark the live activity row done', () => {
		const row = activity('يفحص سعر الذهب الحالي… …');
		expect(expandedStatusDone(row, 0, 1)).toBe(false);
	});

	it('uses the real done flag on the latest row', () => {
		const row = activity('تم فحص سعر الذهب ✓', true);
		expect(expandedStatusDone(row, 1, 2)).toBe(true);
	});

	it('leaves an older unfinished activity snapshot unfinished', () => {
		const row = activity('يفحص سعر الذهب الحالي… …', false);
		expect(expandedStatusDone(row, 0, 2)).toBe(false);
	});

	it('marks an older search action completed', () => {
		const row: StatusUpdate = {
			action: 'web_search',
			description: 'Searching the web',
			done: false
		};
		expect(expandedStatusDone(row, 0, 2)).toBe(true);
	});
});
