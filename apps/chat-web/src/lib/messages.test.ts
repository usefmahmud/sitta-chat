import { describe, expect, it } from 'vitest';

import type { ChatMessage } from './api';
import { groupMessages, isNearBottom, mergeMessages, nextSeq, type UiMessage } from './messages';

function message(seq: number, overrides: Partial<UiMessage> = {}): UiMessage {
  return {
    id: `m-${seq}`,
    conversation_id: 'c-1',
    sender_id: 'u-1',
    seq,
    body: `message ${seq}`,
    client_msg_id: null,
    created_at: `2026-01-0${(seq % 9) + 1}T10:00:0${seq % 10}Z`,
    ...overrides,
  };
}

describe('mergeMessages', () => {
  it('keeps one entry per id and sorts by seq', () => {
    const merged = mergeMessages([message(3), message(1)], [message(2), message(3)]);

    expect(merged.map((item) => item.seq)).toEqual([1, 2, 3]);
    expect(new Set(merged.map((item) => item.id)).size).toBe(3);
  });

  it('does not duplicate a message delivered twice (reconnect catch-up)', () => {
    const first = mergeMessages([], [message(1), message(2)]);
    const second = mergeMessages(first, [message(2), message(3)]);

    expect(second.map((item) => item.id)).toEqual(['m-1', 'm-2', 'm-3']);
  });

  it('drops the optimistic copy once the server row arrives', () => {
    const optimistic: UiMessage = message(4, {
      id: 'local-abc',
      status: 'sending',
      client_msg_id: 'abc',
    });
    const saved: ChatMessage = {
      id: 'm-4',
      conversation_id: 'c-1',
      sender_id: 'u-1',
      seq: 4,
      body: 'message 4',
      client_msg_id: 'abc',
      created_at: '2026-01-01T10:00:00Z',
    };

    const merged = mergeMessages(
      mergeMessages([], [optimistic]).filter((item) => item.id !== 'local-abc'),
      [{ ...saved, status: 'sent' }],
    );

    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe('m-4');
    expect(merged[0].status).toBe('sent');
  });
});

describe('nextSeq', () => {
  it('starts at 1 and follows the highest seq', () => {
    expect(nextSeq([])).toBe(1);
    expect(nextSeq([message(1), message(7)])).toBe(8);
  });
});

describe('groupMessages', () => {
  it('groups consecutive messages by day', () => {
    const groups = groupMessages([
      message(1, { created_at: '2026-01-01T09:00:00Z' }),
      message(2, { created_at: '2026-01-01T23:00:00Z' }),
      message(3, { created_at: '2026-01-02T08:00:00Z' }),
    ]);

    expect(groups.map((group) => group.key)).toEqual(['2026-01-01', '2026-01-02']);
    expect(groups.map((group) => group.messages.length)).toEqual([2, 1]);
  });
});

describe('isNearBottom', () => {
  it('is true within 120px of the bottom and false above it', () => {
    const element = {
      scrollHeight: 1000,
      clientHeight: 500,
      scrollTop: 420,
    } as HTMLElement;

    expect(isNearBottom(element)).toBe(true);

    element.scrollTop = 300;
    expect(isNearBottom(element)).toBe(false);
  });
});
