export const MIN_PASSWORD_LENGTH = 8;

export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function isEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim());
}

export function isLongEnoughPassword(value: string): boolean {
  return value.length >= MIN_PASSWORD_LENGTH;
}
