# Android capabilities at M5

| Flow | Native Android | Mini App / guest web |
|---|---|---|
| Member login | Bot challenge, HTTPS, encrypted refresh | Telegram Mini App |
| Relationships, sessions, profile | Implemented | Implemented |
| Rules: drafts, versions, publish/archive, assignment, consent/history | Native screens implemented | Implemented |
| Ritual templates, schedules, occurrences, reports/reviews/history | Native screens implemented | Implemented |
| Supplied crest / velvet startup | Local assets, actual bootstrap | Local assets, actual loading |
| Basic form builder / new version / publish | Implemented, ten question kinds | Implemented |
| Conditional rule editor / preview | Existing rules preserved; editor deferred | Implemented |
| Internal and guest invitation / reader selection | Implemented, editable TTL/retention and optional Telegram delivery | Implemented, editable limits |
| Reader removal / invitation revoke / archive | Native screens implemented | Implemented |
| Internal drafts / review / submit / results / delete | Implemented | Implemented |
| Ritual evidence: links, photo/video, required policy | Native system picker/save; protected API, bounded memory | Implemented, authenticated download |
| Discipline: exact rule/event link, proposal/revision, personal consent, transitions/comments/history | Native Compose | Implemented |
| Diary: private drafts, explicit/snapshot readers, edit/delete, search/tags | Native Compose | Implemented |
| Diary ACL-filtered JSON file export | Not implemented | Implemented |
| Reward catalogue, manual/automatic offers, accept/decline/deliver/cancel | Native Compose | Implemented |
| Guest form / independent receipt / delete | Native entry by pasting HTTPS link | Standalone /f and /r, no Telegram |
| Guest credential persistence | Memory-only ViewModel survives activity recreation; closing loses draft capability | Secure HttpOnly cookie, at most 24 hours |
| Recurring surveys: periodic/approved ritual, fixed version, own pause, waves | Native Compose | Implemented |
| Personal notification channels and DST-aware quiet hours | Native Compose | Implemented |
| Device-local dark/light/system appearance | Native Material theme | Member and guest web |
| Automatic App Links | Not implemented | Secret links open in browser |

Android guest entry is separate from the selected member instance and never attaches
member bearer credentials. A pasted link's origin is validated before transport creation;
redirects, HTTP, userinfo and query tokens are rejected. Secrets/answers are not saved
in SharedPreferences or logs. Save a receipt before closing after submission. If the
session is lost before submission, ask the sender to revoke and replace the invitation.

Validated: JVM transport/body/visibility tests, native Compose interactions on an owned
Android 16 emulator, lint and builds. These do not prove real Telegram login, physical
Keystore behavior or a production end-to-end Android-to-server flow.
