import { t } from '../../i18n';
import type { Conversation } from '../../lib/api';
import { relativeTime } from '../../lib/time';
import type { SocketStatus } from './useChatSocket';

interface ConversationListProps {
  conversations: Conversation[];
  activeId: string | null;
  unread: Record<string, number>;
  status: 'loading' | 'ready' | 'error';
  connectionStatus: SocketStatus;
  onSelect: (id: string) => void;
  onRetry: () => void;
  onSignOut: () => void;
}

const CONNECTION_COPY = {
  online: 'connection.online',
  connecting: 'connection.connecting',
  reconnecting: 'connection.reconnecting',
  offline: 'connection.offline',
} as const;

export function ConversationList({
  conversations,
  activeId,
  unread,
  status,
  connectionStatus,
  onSelect,
  onRetry,
  onSignOut,
}: ConversationListProps) {
  return (
    <aside className="flex h-full w-full flex-col border-e border-slate-200 bg-white md:w-80">
      <header className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <h1 className="text-lg font-bold">{t('chat.title')}</h1>
        <button
          type="button"
          onClick={onSignOut}
          className="rounded-lg border border-slate-300 px-2 py-1 text-[11px] font-medium text-slate-600"
        >
          {t('menu.logout')}
        </button>
        <span
          className={[
            'rounded-full px-2 py-1 text-[11px] font-medium',
            connectionStatus === 'online'
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-amber-50 text-amber-700',
          ].join(' ')}
          role="status"
        >
          {t(CONNECTION_COPY[connectionStatus])}
        </span>
      </header>

      <div className="flex-1 overflow-y-auto">
        {status === 'loading' ? (
          <p className="p-4 text-sm text-slate-500">{t('chat.loading')}</p>
        ) : null}

        {status === 'error' ? (
          <div className="p-4 text-sm">
            <p className="font-medium text-rose-700">{t('chat.error.title')}</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 rounded-lg border border-slate-300 px-3 py-1 text-xs font-medium"
            >
              {t('chat.error.retry')}
            </button>
          </div>
        ) : null}

        {status === 'ready' && conversations.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-sm font-semibold">{t('chat.empty.title')}</p>
            <p className="mt-1 text-xs text-slate-500">{t('chat.empty.body')}</p>
          </div>
        ) : null}

        <ul>
          {conversations.map((conversation) => {
            const count = unread[conversation.id] ?? 0;
            const active = conversation.id === activeId;
            const preview =
              conversation.last_message_preview ?? t('chat.item.no_preview');

            return (
              <li key={conversation.id}>
                <button
                  type="button"
                  onClick={() => onSelect(conversation.id)}
                  aria-current={active ? 'true' : undefined}
                  className={[
                    'flex w-full items-start gap-3 px-4 py-3 text-start transition',
                    active ? 'bg-slate-100' : 'hover:bg-slate-50',
                  ].join(' ')}
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-500/10 text-sm font-bold text-brand-600">
                    {conversation.peer.display_name.slice(0, 1)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-semibold">
                        {conversation.peer.display_name}
                      </span>
                      {conversation.last_message_at ? (
                        <time
                          dateTime={conversation.last_message_at}
                          className="shrink-0 text-[11px] text-slate-400"
                        >
                          {relativeTime(conversation.last_message_at)}
                        </time>
                      ) : null}
                    </span>
                    <span className="mt-0.5 flex items-center justify-between gap-2">
                      <span className="truncate text-xs text-slate-500">{preview}</span>
                      {count > 0 ? (
                        <span className="shrink-0 rounded-full bg-brand-500 px-2 py-0.5 text-[11px] font-semibold text-white">
                          {t('chat.item.unread', { count })}
                        </span>
                      ) : null}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
