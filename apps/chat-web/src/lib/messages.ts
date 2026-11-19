import type { ChatMessage } from './api';

export type MessageStatus = 'sending' | 'sent' | 'failed';

export type UiMessage = ChatMessage & { status?: MessageStatus };

/**
 * Merge by id and keep the thread ordered by `seq` (never by timestamp).
 * A message that arrives twice — own echo, reconnect catch-up, retry — wins
 * once, so React keys stay unique.
 */
export function mergeMessages(
  current: readonly UiMessage[],
  incoming: readonly UiMessage[],
): UiMessage[] {
  const byId = new Map<string, UiMessage>();
  for (const message of current) byId.set(message.id, message);
  for (const message of incoming) byId.set(message.id, message);
  return [...byId.values()].sort((a, b) => a.seq - b.seq);
}

export function isNearBottom(element: HTMLElement, threshold = 120): boolean {
  return element.scrollHeight - element.scrollTop - element.clientHeight <= threshold;
}

export interface MessageGroup {
  key: string;
  messages: UiMessage[];
}

export function groupMessages(messages: readonly UiMessage[]): MessageGroup[] {
  const groups: MessageGroup[] = [];
  for (const message of messages) {
    const key = message.created_at.slice(0, 10);
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.messages.push(message);
    else groups.push({ key, messages: [message] });
  }
  return groups;
}

export function nextSeq(messages: readonly UiMessage[]): number {
  return messages.reduce((max, message) => (message.seq > max ? message.seq : max), 0) + 1;
}
