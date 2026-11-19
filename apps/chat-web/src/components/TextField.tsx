import type { InputHTMLAttributes, ReactNode } from 'react';

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  trailing?: ReactNode;
}

export function TextField({
  label,
  error,
  trailing,
  id,
  className,
  ...rest
}: TextFieldProps) {
  const describedBy = error ? `${id}-error` : undefined;

  return (
    <div className="mb-4">
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={[
            'w-full rounded-lg border bg-white px-3 py-2 text-sm text-ink',
            'placeholder:text-slate-400',
            error ? 'border-rose-400' : 'border-slate-300',
            trailing ? 'pe-12' : '',
            className ?? '',
          ]
            .filter(Boolean)
            .join(' ')}
          {...rest}
        />
        {trailing ? (
          <div className="absolute inset-y-0 end-1 flex items-center">{trailing}</div>
        ) : null}
      </div>
      {error ? (
        <p id={describedBy} role="alert" className="mt-1 text-xs text-rose-600">
          {error}
        </p>
      ) : null}
    </div>
  );
}
