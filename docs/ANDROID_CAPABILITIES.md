# Android capabilities at M2 + M3 rules

| Flow | Native Android | Mini App / guest web |
|---|---|---|
| Member login | Bot challenge, HTTPS, encrypted refresh | Telegram Mini App |
| Relationships, sessions, profile | Implemented | Implemented |
| Rules: drafts, versions, publish/archive, assignment, consent/history | Native screens implemented | Implemented |
| Ritual templates, schedules, occurrences, reports/reviews/history | Native screens implemented | Implemented |
| Supplied crest / velvet startup | Local assets, actual bootstrap | Local assets, actual loading |
| Rewards | Not implemented | Not implemented |
| Basic form builder / new version / publish | Implemented, ten question kinds | Implemented |
| Conditional rule editor / preview | Existing rules preserved; editor deferred | Implemented |
| Internal and guest invitation / reader selection | Implemented, default 7-day invite / 90-day retention after submission | Implemented, editable limits |
| Reader removal / invitation revoke / archive | Use Mini App | Implemented |
| Internal drafts / review / submit / results / delete | Implemented | Implemented |
| Guest form / independent receipt / delete | Native entry by pasting HTTPS link | Standalone /f and /r, no Telegram |
| Guest credential persistence | Memory-only ViewModel survives activity recreation; closing loses draft capability | Secure HttpOnly cookie, at most 24 hours |
| Automatic App Links | Not implemented | Secret links open in browser |

Android guest entry is separate from the selected member instance and never attaches
member bearer credentials. A pasted link's origin is validated before transport creation;
redirects, HTTP, userinfo and query tokens are rejected. Secrets/answers are not saved
in SharedPreferences or logs. Save a receipt before closing after submission. If the
session is lost before submission, ask the sender to revoke and replace the invitation.

Validated: JVM transport/body/visibility tests, native Compose interactions on an owned
Android 16 emulator, lint and builds. These do not prove real Telegram login, physical
Keystore behavior or a production end-to-end Android-to-server flow.
