import { t } from '../i18n';
import { useSession } from '../session/SessionProvider';

/**
 * Placeholder shell until CHAT-8 brings the conversation list and thread.
 * It exists so the auth flow has somewhere to land.
 */
export default function HomePage() {
  const { user, signOut } = useSession();

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 px-4 py-10">
      <header className="flex items-center justify-between gap-4">
        <div className="text-start">
          <h1 className="text-2xl font-bold">{t('chat.title')}</h1>
          <p className="text-sm text-slate-500">{user?.display_name}</p>
        </div>
        <button
          type="button"
          onClick={signOut}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-white"
        >
          {t('menu.logout')}
        </button>
      </header>

      <section className="rounded-2xl bg-white p-8 text-center shadow-sm ring-1 ring-black/5">
        <h2 className="text-lg font-semibold">{t('chat.empty.title')}</h2>
        <p className="mt-2 text-sm text-slate-500">{t('chat.empty.body')}</p>
      </section>
    </main>
  );
}
