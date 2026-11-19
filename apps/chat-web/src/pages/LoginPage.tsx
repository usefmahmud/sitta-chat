import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { AuthLayout } from '../components/AuthLayout';
import { TextField } from '../components/TextField';
import { t } from '../i18n';
import { ApiError } from '../lib/api';
import { isEmail, isLongEnoughPassword } from '../lib/validation';
import { useSession } from '../session/SessionProvider';

interface FieldErrors {
  email?: string;
  password?: string;
  form?: string;
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return t('error.credentials.invalid');
    if (error.code === 'network') return t('error.network');
    if (error.status === 429) return t('error.rate_limited');
  }
  return t('error.generic');
}

export default function LoginPage() {
  const { api, signIn } = useSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [reveal, setReveal] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const next: FieldErrors = {};
    if (!email.trim()) next.email = t('error.field.required');
    else if (!isEmail(email)) next.email = t('error.email.invalid');

    if (!password) next.password = t('error.field.required');
    else if (!isLongEnoughPassword(password)) next.password = t('error.password.short');

    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || !validate()) return;

    setSubmitting(true);
    setErrors({});
    try {
      const auth = await api.login({ email: email.trim(), password });
      signIn(auth);
    } catch (error) {
      setErrors({ form: messageFor(error) });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title={t('login.title')}
      subtitle={t('login.subtitle')}
      footer={
        <p className="text-start">
          {t('login.no_account')}{' '}
          <Link className="font-medium text-brand-500 hover:underline" to="/register">
            {t('login.register_link')}
          </Link>
        </p>
      }
    >
      <form noValidate onSubmit={handleSubmit} aria-busy={submitting}>
        <TextField
          id="login-email"
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          dir="ltr"
          label={t('login.email.label')}
          placeholder={t('login.email.placeholder')}
          value={email}
          error={errors.email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <TextField
          id="login-password"
          name="password"
          type={reveal ? 'text' : 'password'}
          autoComplete="current-password"
          dir="ltr"
          label={t('login.password.label')}
          placeholder={t('login.password.placeholder')}
          value={password}
          error={errors.password}
          onChange={(event) => setPassword(event.target.value)}
          trailing={
            <button
              type="button"
              className="rounded-md px-2 py-1 text-xs text-slate-500 hover:text-ink"
              aria-label={
                reveal ? t('login.password.hide') : t('login.password.show')
              }
              onClick={() => setReveal((current) => !current)}
            >
              {reveal ? t('login.password.hide') : t('login.password.show')}
            </button>
          }
        />

        {errors.form ? (
          <p role="alert" className="mb-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {errors.form}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-600 disabled:opacity-60"
        >
          {submitting ? t('login.submitting') : t('login.submit')}
        </button>

        <p className="mt-3 text-center text-xs text-slate-400">{t('login.forgot')}</p>
      </form>
    </AuthLayout>
  );
}
