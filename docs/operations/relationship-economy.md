# Relationship economy

Migration0019 adds relationship wallets, an append-only encrypted-comment ledger,
shop listings and multi-item ritual policies. Back up before migration. It preserves
existing single-reward policies/grants/history, populating policy items and binding
legacy policies to a current direct relationship. An unbound legacy policy cannot
borrow authority from a later relationship. The runtime requires schema0019.
Downgrade is allowed only with legacy-only data; it fails rather than silently losing
currency, shop listings or new reward bundles. Restore from a verified backup when
rolling back a populated economy.

New member endpoints:

- `GET /api/v1/relations/{id}/wallet`: parties' balance and latest500 ledger entries.
- `POST .../wallet/credits`: dominant grants amount+comment+idempotency_key.
- `GET/POST /api/v1/relations/{id}/shop`: available/managed listings and creation.
- `PATCH /api/v1/shop/{id}`: expected_version, price, active.
- `POST /api/v1/shop/{id}/purchases`: expected_version and idempotency_key.
- `PUT /api/v1/ritual-assignments/{id}/rewards`: expected_version,
  reward_version_ids and currency_amount, affecting future uncreated slots only.

`RitualAssign` accepts either the legacy reward_version_id or the new bundle fields,
not both. An empty bundle gives no reward. Up to20 distinct owned reward versions
and zero or positive whole coins are supported; each amount/price is bounded at1e9.
Balances are bounded at the largest exact JavaScript integer and generated Android
wallet balances use Long. No real-money exchange, negative credits, transfers,
refund flow, stock limits or daily-rule bonuses are implemented.

All writes check the exact relationship's current authority, consent-derived active
state and participant availability. Party locks, relationship locks and wallet locks
serialize purchase/credit effects. Balance is derived from ledger rows, not a mutable
balance field. Database uniqueness prevents repeated per-occurrence awards and
per-wallet request effects; a trigger rejects ledger UPDATE/DELETE. Reward creation,
ledger effects, transition history and existing reward notification outbox share one
transaction. Currency-only operations currently appear in wallet history; they do
not create a separate Telegram currency notification.

Revocation stops new operations and hides the shop from the recipient; both parties
retain the old wallet history. Recreated relationships start with a different wallet.
Purchased grants identify their source and cannot be cancelled through the legacy
proposal endpoint. Earned grants retain their version and source relationship.

Local acceptance uses only vowen_test and isolated vowen_ui_test. The UI database
was backed up before0019; production has not been migrated for this slice. Run
`make migrate-test`, backend tests, `make test-e2e`, web gates, native build gates,
contract checks and secret scan before deployment. Actual Telegram and native-device
acceptance remain separate from this automated/local evidence.
