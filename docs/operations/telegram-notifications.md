# Telegram ritual and reward notifications

Apply Alembic 0013 (`make migrate`); rebuild API, ritual worker and bot together.
The existing `telegram` Compose profile runs the bot and its delivery loop:
`docker compose --profile telegram up -d --build bot`.
The Compose token is read from `secrets/bot-token`; local Python reads `.env`
(`TELEGRAM_BOT_TOKEN` or `BOT_API_TOKEN`). Never print these files or bot exceptions.
Configured username is verified against getMe before polling begins.

A member must already be provisioned with their Telegram ID. In a private bot chat,
`/notifications_on` explicitly allows delivery; `/notifications_off` disables it.
Neither command creates an application user. Contacts and users remain distinct;
unlinked contacts never receive ritual/reward notices. Existing form/guest deliveries
retain their own invitation queue and policy.

## Privacy and rights

Telegram receives only a localized neutral update and the instance root URL. No
ritual/reward titles, names, status, report text, evidence, object UUIDs or bearer
capabilities. Parse mode and link previews are disabled. Language follows existing
member profile preferences (en/ru). Quiet-hour scheduling and new channel settings
are not implemented in this slice; the explicit bot opt-out remains available.

Each newly inserted in-app notice atomically creates at most one outbox row in the
same transaction. No historic backfill. Opt-in and active/unpaused membership are
required at event creation and checked again at claim and immediately before send.
Ritual delivery requires effective assignment plus executor/current explicit reviewer
access; reward delivery requires the fixed issuer/recipient and current direct
rewards.grant authority. In-app earned history remains readable after withdrawal,
but no new Telegram delivery is made under withdrawn authority.

Pause, account disable, relation pause/revoke/version change and bot opt-out suppress
pending/claimed deliveries transactionally. Restoring permission does not resurrect
cancelled messages. Sending requests already in flight cannot be recalled reliably;
there is a small unavoidable interval between the final DB commit and Telegram send.
No database transaction is held across network IO. The message contains no private
resource content even in that interval; resource reads still use their current ACL.

Outdated occurrence or reward revisions are suppressed. Notifications expire after
24 hours; due reminders additionally require a still-scheduled, unexpired occurrence.
This lifetime and the limits below are implementation defaults, not separately
confirmed customer preferences. Missed/suppressed messages remain available via the
application's ordinary current-access views; the bot is not a source of truth.

## Repeats, restart and failures

`member_deliveries` has unique source-notice foreign keys. SKIP LOCKED claims use a
one-minute UUID-fenced lease, with one claim per row. An expired claim that has not
begun sending can be reclaimed. Sending is recorded before the request; after a crash
or timeout the outcome is `uncertain` and is never automatically resent. This favors
avoiding duplicates over guaranteeing delivery; it is not an exactly-once guarantee.

Only explicit Telegram429 rejection is retried after `retry_after`, at most three
attempts total, with fresh authorization on every attempt. Forbidden disables the
contact and ends this delivery. Bad request/exhausted429 ends as
`manual_delivery_required`. Other network/server errors are conservatively uncertain;
no error payload, token or message is logged. Successful rows are terminal. Each tick
handles at most one form and one member delivery, independently, every five seconds.
The Bot API parameters and retry semantics follow the
[official API](https://core.telegram.org/bots/api#sendmessage) and
[ResponseParameters](https://core.telegram.org/bots/api#responseparameters).

Operator-only aggregate queue inspection (does not reveal recipients or contents):

```sh
docker compose exec -T db psql -U vowen -d vowen -c \
  'SELECT status,count(*) FROM member_deliveries GROUP BY status ORDER BY status;'
```

Do not reset uncertain/delivered rows to pending: that can duplicate a message. There
is no automatic manual-redrive command. Ask the member to inspect the app if needed.

## Acceptance

PostgreSQL integration tests exercise real domain events, idempotency, rollback,
concurrent claims, fencing, withdrawal, contact/pause restore intervals, stale events,
neutral localized adapter requests,429 timing/exhaustion, blocking and ambiguity.
A synthetic transport replaces only the Telegram network boundary. `getMe` with a
live token verifies bot credentials, not message receipt. Live delivery must use an
already linked, opted-in eligible member; never send test data to synthetic IDs.
