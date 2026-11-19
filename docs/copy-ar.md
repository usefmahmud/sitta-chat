# Arabic UI copy — sitta-chat

Single source of truth for every user-facing string in `apps/chat-web`. Interface is
RTL Arabic; code, keys and comments stay English.

## Rules for implementers

- Keys are stable. **Rename the Arabic text freely, never rename a key** — the key is
  what `t('chat.empty.title')` resolves.
- Keys are grouped by screen (`login.*`, `chat.*`, `thread.*`, `message.*`,
  `connection.*`, `common.*`). Do not add keys outside these groups without updating
  this file.
- Text is Egyptian colloquial on purpose — short, spoken, not literal MSA. Do not
  "correct" it to فصحى during review; length and tone are part of the copy.
- `{placeholders}` are ICU-style values filled by the component (name, count, date).
- Every string here ends without a trailing full stop unless it is a second sentence.
- No emoji in UI copy unless explicitly listed.

## 1. Login

| Key | Arabic | Note |
|---|---|---|
| `login.title` | أهلاً بيك تاني | h1 |
| `login.subtitle` | ادخل وكمّل كلامك مع أصحابك | under title |
| `login.email.label` | الإيميل | |
| `login.email.placeholder` | name@example.com | LTR input |
| `login.password.label` | الباسورد | |
| `login.password.placeholder` | •••••••• | |
| `login.password.show` | إظهار الباسورد | aria-label / eye toggle |
| `login.password.hide` | إخفاء الباسورد | aria-label |
| `login.submit` | دخول | |
| `login.submitting` | بندخّلك… | button busy state |
| `login.forgot` | نسيت الباسورد؟ | link |
| `login.no_account` | لسه معندكش حساب؟ | |
| `login.register_link` | اعمل حساب | link |

## 2. Register

| Key | Arabic | Note |
|---|---|---|
| `register.title` | حساب جديد | h1 |
| `register.subtitle` | دقيقة وتكون جوه | |
| `register.name.label` | اسمك | display name |
| `register.name.placeholder` | اللي أصحابك يعرفوك بيه | |
| `register.username.label` | اسم المستخدم | handle, no spaces |
| `register.username.placeholder` | مثال: ahmed | LTR input, `@` rendered by UI |
| `register.email.label` | الإيميل | |
| `register.password.label` | الباسورد | |
| `register.password.hint` | 8 حروف على الأقل | helper text |
| `register.submit` | اعمل الحساب | |
| `register.submitting` | بنعمل حسابك… | |
| `register.have_account` | عندك حساب؟ | |
| `register.login_link` | ادخل من هنا | link |

## 3. Auth errors

| Key | Arabic | Note |
|---|---|---|
| `error.email.invalid` | الإيميل ده مش مظبوط — راجع الكتابة | inline, under field |
| `error.email.taken` | الإيميل ده متسجل قبل كده — جرّب تدخل بيه | 409 |
| `error.username.taken` | اسم المستخدم ده واخدوه — جرّب غيره | 409 |
| `error.username.invalid` | اسم المستخدم بحروف إنجليزي وأرقام بس، من غير مسافات | |
| `error.password.short` | الباسورد قصير — 8 حروف على الأقل | |
| `error.password.weak` | الباسورد سهل — جرّب حاجة أصعب شوية | used only if API returns it |
| `error.credentials.invalid` | الإيميل أو الباسورد غلط | 401, form-level, no field hint |
| `error.field.required` | الحقل ده لازم يتملا | |
| `error.rate_limited` | حاولت كتير — استنى شوية وجرّب تاني | 429 |
| `error.network` | النت قطع — جرّب تاني | offline / fetch failed |
| `error.generic` | حصلت مشكلة — جرّب كمان مرة | 5xx fallback |

## 4. Conversations list

| Key | Arabic | Note |
|---|---|---|
| `chat.title` | المحادثات | |
| `chat.new` | محادثة جديدة | |
| `chat.empty.title` | لسه مفيش محادثات | empty state h2 |
| `chat.empty.body` | ابدأ واحدة وابعت أول رسالة | |
| `chat.empty.action` | ابدأ محادثة | CTA button |
| `chat.item.no_preview` | لسه مفيش رسايل | conversation with no messages |
| `chat.item.you_prefix` | أنت: {preview} | prefix for own last message |
| `chat.item.deleted_preview` | رسالة اتشالت | last message was deleted |
| `chat.item.unread` | {count} جديدة | badge, count ≥ 1 |
| `chat.item.typing` | بيكتب… | replaces preview |
| `chat.load_more` | شوف الأقدم | pagination |
| `chat.loading` | بنجيب المحادثات… | |
| `chat.error.title` | مش قادرين نجيب المحادثات | |
| `chat.error.retry` | جرّب تاني | |

## 5. Search

| Key | Arabic | Note |
|---|---|---|
| `search.placeholder` | دوّر على حد أو محادثة | |
| `search.hint` | اكتب حرفين على الأقل | shown before 2 chars |
| `search.empty.title` | مفيش نتايج | |
| `search.empty.body` | مفيش حد بالاسم ده — جرّب كتابة تانية | |
| `search.section.people` | ناس | |
| `search.section.chats` | محادثات | |
| `search.results_count` | {count} نتيجة | a11y live region |
| `search.clear` | امسح البحث | aria-label |

## 6. Thread

| Key | Arabic | Note |
|---|---|---|
| `thread.empty.title` | لسه مفيش كلام هنا | h2 |
| `thread.empty.body` | ابعت أول رسالة وكسّروا التلج | |
| `thread.input.placeholder` | اكتب رسالة… | |
| `thread.input.send` | إرسال | aria-label on send button |
| `thread.input.hint_newline` | Enter يبعت · Shift+Enter سطر جديد | desktop only |
| `thread.typing.one` | {name} بيكتب… | |
| `thread.typing.two` | {name1} و{name2} بيكتبوا… | |
| `thread.load_older` | شوف اللي قبله | pagination up |
| `thread.jump_latest` | آخر الرسايل | floating button, plural-safe |
| `thread.new_messages` | رسايل جديدة | divider |
| `thread.loading` | بنجيب الرسايل… | |
| `thread.error.load` | مش قادرين نحمّل الرسايل — جرّب تاني | |
| `thread.members_count` | {count} عضو | group header, only if groups ship |

## 7. Last seen & presence

| Key | Arabic | Note |
|---|---|---|
| `presence.online` | متصل دلوقتي | |
| `presence.just_now` | كان هنا دلوقتي | < 1 min |
| `presence.minutes` | آخر ظهور قبل {count} دقيقة | 1–59 |
| `presence.hours` | آخر ظهور قبل {count} ساعة | 1–23 |
| `presence.yesterday` | آخر ظهور امبارح | |
| `presence.date` | آخر ظهور {date} | older than 2 days |
| `presence.hidden` | آخر ظهور مش متاح | privacy off |

## 8. Connection state

| Key | Arabic | Note |
|---|---|---|
| `connection.online` | متصل | green dot |
| `connection.connecting` | بنحاول نتصل… | initial connect |
| `connection.reconnecting` | النت وقع — بنحاول تاني | socket drop, auto-retry |
| `connection.offline` | مش متصل | |
| `connection.queued` | هتتبعت أول ما النت يرجع | on message typed while offline |
| `connection.restored` | رجعنا | transient toast |

## 9. Message status

| Key | Arabic | Note |
|---|---|---|
| `message.status.sending` | بيتبعت | clock icon |
| `message.status.sent` | اتبعتت | single tick |
| `message.status.delivered` | وصلت | double tick — only if delivery ack exists |
| `message.status.read` | اتقرأت | double tick, coloured |
| `message.status.failed` | فشل الإرسال | red, paired with retry |
| `message.status.retry` | إعادة المحاولة | action button |
| `message.action.copy` | انسخ | context menu |
| `message.action.delete` | امسح | context menu |
| `message.copied` | اتنسخ | toast |

## 10. Delete, confirm, cancel

| Key | Arabic | Note |
|---|---|---|
| `confirm.delete_message.title` | تمسح الرسالة؟ | |
| `confirm.delete_message.body` | هتتشال من عندك وعند الطرف التاني، ومش هترجع | |
| `confirm.delete_chat.title` | تمسح المحادثة؟ | |
| `confirm.delete_chat.body` | هتتشال من قايمتك — الطرف التاني هيفضل شايف الرسايل | |
| `confirm.cancel` | إلغاء | default focus |
| `confirm.delete` | امسح | destructive |
| `confirm.ok` | تمام | non-destructive confirm |
| `toast.message_deleted` | الرسالة اتشالت | |
| `toast.message_delete_failed` | مش قادرين نمسحها — جرّب تاني | |
| `toast.chat_deleted` | المحادثة اتشالت | |

## 11. Common

| Key | Arabic | Note |
|---|---|---|
| `common.cancel` | إلغاء | |
| `common.retry` | جرّب تاني | |
| `common.close` | اقفل | aria-label |
| `common.back` | رجوع | |
| `common.loading` | لحظة… | |
| `common.saving` | بنحفظ… | |
| `common.error_title` | حصلت مشكلة | |
| `common.error_body` | جرّب تاني، ولو كملت ابعتلنا | |
| `menu.profile` | حسابي | |
| `menu.logout` | خروج | |

## Open product decisions

These block final copy for the listed keys — do not ship them before the answer lands:

1. **`message.status.delivered`** — needs a server-side delivery ack. If the API only
   has sent/read, drop the key; otherwise the tick stays grey forever.
2. **`message.status.read`** — requires read receipts. Are they always on, or a
   per-user setting? If optional, a second key `message.status.read_disabled` is needed.
3. **`confirm.delete_message.body`** — copy promises "gone for both sides". Confirm the
   API hard-deletes for everyone; if it is delete-for-me only, the text flips to
   "هتتشال من عندك بس" and needs a decision.
4. **`presence.*`** — depends on last-seen privacy existing at all. If presence only
   exposes online/offline, cut the four time-based keys.
5. **`thread.typing.two` / `thread.members_count`** — only if group chats are in the
   sprint. If it is 1:1 only, cut both and keep `thread.typing.one`.
6. **Digits** — count strings (`{count}`) render Latin digits or Arabic-Indic (٣) in
   RTL? Suggest Egyptian habit: Latin digits (5 جديدة). Needs one decision, applied
   globally, not per string.
7. **Password reset** — `login.forgot` is linked but no reset flow exists in this
   sprint. Either build reset or drop the link until it exists.
