"""Convert application payloads to plaintext; old keys are only used during conversion."""

import sqlalchemy as sa
from alembic import op

from vowen.core.config import Settings
from vowen.core.crypto import EncryptedEnvelope, PayloadCipher

revision = "0035"
down_revision = "0034"

BINDINGS = {
    "relation_versions": "agreement",
    "rule_versions": "rule_version",
    "ritual_versions": "ritual_version",
    "ritual_reports": "ritual_report",
    "ritual_evidence": "ritual_evidence",
    "reward_definition_versions": "reward_version",
    "discipline_versions": "discipline_version",
    "discipline_transitions": "discipline_transition",
    "discipline_dictionary": "discipline_dictionary",
    "punishment_templates": "punishment_template",
    "form_submissions": "form_submission",
    "notification_deliveries": "delivery",
    "journal_entries": "journal_entry",
    "currency_entries": "currency_entry",
    "change_requests": "change_request",
}


def convert(connection, keyring):
    # Serialize conversion with writes; transaction rollback also restores trigger state.
    connection.execute(sa.text("LOCK TABLE " + ", ".join(BINDINGS) + " IN ACCESS EXCLUSIVE MODE"))
    connection.execute(
        sa.text("ALTER TABLE currency_entries DISABLE TRIGGER currency_entries_immutable")
    )
    codec = PayloadCipher(keyring)
    for name, kind in BINDINGS.items():
        table = sa.table(
            name,
            sa.column("id", sa.UUID()),
            sa.column("key_id", sa.Text()),
            sa.column("nonce", sa.LargeBinary()),
            sa.column("ciphertext", sa.LargeBinary()),
        )
        rows = connection.execute(
            sa.select(table)
            .where(table.c.ciphertext.is_not(None))
            .order_by(table.c.id)
            .execution_options(yield_per=1)
        )
        for row in rows:
            try:
                data = codec.open_payload(
                    kind,
                    row.id,
                    1,
                    EncryptedEnvelope(row.key_id, bytes(row.nonce), bytes(row.ciphertext)),
                )
            except Exception:
                # Never print a row payload, key identifier, or keyring contents in migration logs.
                raise RuntimeError(
                    "Payload conversion failed; original data keyring is required"
                ) from None
            if row.key_id != "plaintext-v1":
                connection.execute(
                    sa.update(table)
                    .where(table.c.id == row.id)
                    .values(key_id="plaintext-v1", nonce=b"", ciphertext=data)
                )
        rows.close()
    connection.execute(
        sa.text("ALTER TABLE currency_entries ENABLE TRIGGER currency_entries_immutable")
    )


def upgrade():
    convert(op.get_bind(), Settings().data_keyring_file)


def downgrade():
    # This data conversion has no reverse operation: schema rollback preserves plaintext.
    # Restoring encryption for an old binary requires the pre-conversion database backup.
    pass
