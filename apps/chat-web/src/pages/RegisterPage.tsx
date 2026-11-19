import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { AuthLayout } from '../components/AuthLayout';
import { TextField } from '../components/TextField';
import { t } from '../i18n';
import { ApiError } from '../lib/api';
import { isEmail, isLongEnoughPassword } from '../lib/validation';
import { useSession } from '../session/SessionProvider';

interface FieldErrors {
  displayName?: string;
  email?: string;
  password?: string;
  form?: string;
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) return t('error.email.taken');
    if (error.code === 'network') return t('error.network');
    if (error.status === 429) return t('error.rate_limited');
    if (error.code === 'validation') return t('error.generic');
  }
  return t('error.generic');
}

export default function RegisterPage() {
  const { api, signIn } = useSession();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const next: FieldErrors = {};
    if (!displayName.trim()) next.displayName = t('error.field.required');

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
      const auth = await api.register({
        email: email.trim(),
        password,
        display_name: displayName.trim(),
      });
      signIn(auth);
    } catch (error) {
      setErrors({ form: messageFor(error) });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title={t('register.title')}
      subtitle={t('register.subtitle')}
      footer={
        <p className="text-start">
          {t('register.have_account')}{' '}
          <Link className="font-medium text-brand-500 hover:underline" to="/login">
            {t('register.login_link')}
          </Link>
        </p>
      }
    >
      <form noValidate onSubmit={handleSubmit} aria-busy={submitting}>
        <TextField
          id="register-name"
          name="display_name"
          autoComplete="name"
          label={t('register.name.label')}
          placeholder={t('register.name.placeholder')}
          value={displayName}
          error={errors.displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />

        <TextField
          id="register-email"
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          dir="ltr"
          label={t('register.email.label')}
          placeholder={t('login.email.placeholder')}
          value={email}
          error={errors.email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <TextField
          id="register-password"
          name="password"
          type="password"
          autoComplete="new-password"
          dir="ltr"
          label={t('register.password.label')}
          placeholder={t('login.password.placeholder')}
          value={password}
          error={errors.password}
          onChange={(event) => setPassword(event.target.value)}
        />

        <p className="mb-4 text-xs text-slate-400">{t('register.password.hint')}</p>

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
          {submitting ? t('register.submitting') : t('register.submit')}
        </button>
      </form>
    </AuthLayout>
  );
}
