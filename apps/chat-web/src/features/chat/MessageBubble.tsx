import { clockTime } from '../../lib/time';
import { t } from '../../i18n';
import type { UiMessage } from '../../lib/messages';

interface MessageBubbleProps {
  message: UiMessage;
  isOwn: boolean;
  onRetry: (message: UiMessage) => void;
}

export function MessageBubble({ message, isOwn, onRetry }: MessageBubbleProps) {
  const failed = message.status === 'failed';

  return (
    <article
      className={['flex w-full', isOwn ? 'justify-end' : 'justify-start'].join(' ')}
      data-seq={message.seq}
      data-status={message.status ?? 'sent'}
    >
      <div
        className={[
          'max-w-[85%] rounded-2xl px-3 py-2 text-sm shadow-sm',
          isOwn ? 'bg-brand-500 text-white' : 'bg-white text-ink ring-1 ring-black/5',
        ].join(' ')}
      >
        <p className="whitespace-pre-wrap break-words text-start">{message.body}</p>
        <div
          className={[
            'mt-1 flex items-center gap-2 text-[11px]',
            isOwn ? 'justify-end text-white/80' : 'justify-start text-slate-400',
          ].join(' ')}
        >
          <time dateTime={message.created_at}>{clockTime(message.created_at)}</time>
          {isOwn ? (
            <span aria-live="polite">
              {message.status === 'sending' ? t('message.status.sending') : null}
              {message.status === 'failed' ? t('message.status.failed') : null}
            </span>
          ) : null}
        </div>

        {failed ? (
          <button
            type="button"
            onClick={() => onRetry(message)}
            className="mt-1 rounded-md bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700"
          >
            {t('message.status.retry')}
          </button>
        ) : null}
      </div>
    </article>
  );
}
