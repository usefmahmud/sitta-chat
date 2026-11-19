/**
 * Conventional Commits, enforced by commitlint (local hook + CI).
 * Format: type(scope): subject
 *   type  : feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert
 *   scope : optional, one of the allow-listed areas below
 */
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'build', 'ci', 'chore', 'revert'],
    ],
    'scope-enum': [
      2,
      'always',
      [
        'api', 'web', 'auth', 'chat', 'messages', 'realtime', 'presence',
        'notifications', 'search', 'infra', 'ci', 'deps', 'docs', 'release',
      ],
    ],
    'subject-case': [2, 'always', 'lower-case'],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 72],
    'body-max-line-length': [2, 'always', 100],
  },
};
