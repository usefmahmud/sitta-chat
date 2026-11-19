import type { ReactNode } from 'react';

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <section className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5">
        <header className="mb-6 text-start">
          <h1 className="text-2xl font-bold text-ink">{title}</h1>
          <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
        </header>
        {children}
        <footer className="mt-6 border-t border-slate-100 pt-4 text-sm text-slate-600">
          {footer}
        </footer>
      </section>
    </main>
  );
}
