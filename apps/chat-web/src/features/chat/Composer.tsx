import { useState, type FormEvent, type KeyboardEvent } from 'react';

import { t } from '../../i18n';

interface ComposerProps {
  disabled: boolean;
  onSend: (body: string) => Promise<boolean>;
}

export function Composer({ disabled, onSend }: ComposerProps) {
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);

  const locked = disabled || busy;

  async function submit() {
    const text = body.trim();
    if (!text || locked) return;

    setBusy(true);
    const queued = await onSend(text);
    setBusy(false);
    if (queued) setBody('');
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-slate-200 bg-white p-3">
      <div className="flex items-end gap-2">
        <label htmlFor="composer" className="sr-only">
          {t('thread.input.placeholder')}
        </label>
        <textarea
          id="composer"
          rows={1}
          value={body}
          disabled={locked}
          onChange={(event) => setBody(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('thread.input.placeholder')}
          className="max-h-32 min-h-[2.75rem] w-full resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm text-ink placeholder:text-slate-400 disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={locked || !body.trim()}
          aria-label={t('thread.input.send')}
          className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-600 disabled:opacity-50"
        >
          {t('thread.input.send')}
        </button>
      </div>
      <p className="mt-1 hidden text-[11px] text-slate-400 md:block">
        {t('thread.input.hint_newline')}
      </p>
    </form>
  );
}
