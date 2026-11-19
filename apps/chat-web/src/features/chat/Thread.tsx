import type { RefObject } from 'react';

import { t } from '../../i18n';
import type { Conversation } from '../../lib/api';
import { groupMessages, type UiMessage } from '../../lib/messages';
import { dayLabelFor } from '../../lib/time';
import { MessageBubble } from './MessageBubble';

interface ThreadProps {
  conversation: Conversation | null;
  messages: UiMessage[];
  viewerId: string;
  state: 'idle' | 'loading' | 'ready' | 'error';
  hasMore: boolean;
  showPill: boolean;
  scrollRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
  onLoadOlder: () => void;
  onJumpLatest: () => void;
  onRetryMessage: (message: UiMessage) => void;
  onBack: () => void;
  onRetryLoad: () => void;
}

export function Thread({
  conversation,
  messages,
  viewerId,
  state,
  hasMore,
  showPill,
  scrollRef,
  onScroll,
  onLoadOlder,
  onJumpLatest,
  onRetryMessage,
  onBack,
  onRetryLoad,
}: ThreadProps) {
  if (!conversation) {
    return (
      <section className="flex h-full flex-1 items-center justify-center p-8">
        <div className="max-w-sm text-center">
          <h2 className="text-lg font-semibold">{t('thread.empty.title')}</h2>
          <p className="mt-2 text-sm text-slate-500">{t('thread.empty.body')}</p>
        </div>
      </section>
    );
  }

  const groups = groupMessages(messages);

  return (
    <section className="relative flex h-full min-w-0 flex-1 flex-col bg-canvas">
      <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium md:hidden"
        >
          {t('common.back')}
        </button>
        <div className="text-start">
          <h2 className="text-sm font-bold">{conversation.peer.display_name}</h2>
        </div>
      </header>

      <div
        id="thread"
        ref={scrollRef}
        onScroll={onScroll}
        className="flex-1 space-y-4 overflow-y-auto px-3 py-4 md:px-6"
      >
        {hasMore ? (
          <div className="text-center">
            <button
              type="button"
              onClick={onLoadOlder}
              className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600"
            >
              {t('thread.load_older')}
            </button>
          </div>
        ) : null}

        {state === 'loading' ? (
          <p className="text-center text-sm text-slate-500">{t('thread.loading')}</p>
        ) : null}

        {state === 'error' ? (
          <div className="text-center text-sm">
            <p className="text-rose-700">{t('thread.error.load')}</p>
            <button
              type="button"
              onClick={onRetryLoad}
              className="mt-2 rounded-lg border border-slate-300 px-3 py-1 text-xs font-medium"
            >
              {t('common.retry')}
            </button>
          </div>
        ) : null}

        {state === 'ready' && messages.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-sm font-semibold">{t('thread.empty.title')}</p>
            <p className="mt-1 text-xs text-slate-500">{t('thread.empty.body')}</p>
          </div>
        ) : null}

        {groups.map((group) => (
          <div key={group.key} className="space-y-2">
            <div className="flex items-center gap-2" role="separator">
              <span className="h-px flex-1 bg-slate-200" />
              <span className="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-500 ring-1 ring-slate-200">
                {dayLabelFor(group.messages[0].created_at)}
              </span>
              <span className="h-px flex-1 bg-slate-200" />
            </div>
            {group.messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                isOwn={message.sender_id === viewerId}
                onRetry={onRetryMessage}
              />
            ))}
          </div>
        ))}
      </div>

      {showPill ? (
        <button
          type="button"
          onClick={onJumpLatest}
          className="absolute bottom-24 start-1/2 -translate-x-1/2 rounded-full bg-ink px-4 py-2 text-xs font-semibold text-white shadow-lg"
        >
          {t('thread.new_messages')}
        </button>
      ) : null}
    </section>
  );
}
